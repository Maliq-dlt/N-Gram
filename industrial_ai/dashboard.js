'use strict';
const $ = id => document.getElementById(id);
let job = null, summary = null, pollTimer = null, history = [], generation = 0;
let currentView='analysis', uploading=false;
const objectNames={karung:'Karung',person:'Orang',car:'Mobil',bus:'Bus',truck:'Truk',motorcycle:'Motor',bicycle:'Sepeda'};
const vehicles = frame => Object.keys(frame).filter(k=>!['person','seconds'].includes(k)).reduce((n,k)=>n+(frame[k] || 0),0);
function syncControls() {
  const blocked=uploading || sending || reviewBusy || currentView==='annotation' || ['uploading','queued','processing','cancelling'].includes(job?.status);
  for(const id of ['newVideoButton','emptyUploadButton','uploadButton']) $(id).disabled=blocked;
  $('historySelect').disabled=uploading || sending || reviewBusy || currentView==='annotation';
  $('closeUpload').disabled=uploading; $('sendChat').disabled=sending || reviewBusy; for(const button of document.querySelectorAll('[data-question]'))button.disabled=sending || reviewBusy;
  $('reanalyzeButton').disabled=blocked || !summary;
  $('retryJob').hidden=!['error','cancelled'].includes(job?.status);
  $('cancelJob').hidden=!['queued','processing','cancelling'].includes(job?.status);
  $('cancelJob').disabled=job?.status==='cancelling';
  for(const button of document.querySelectorAll('[data-view]')) button.disabled=uploading || reviewBusy;
}
async function setView(view) {
  if(view===currentView) return;
  if(reviewBusy || uploading) return;
  if(currentView==='annotation' && !(await persistReview(false))) return;
  if(view==='annotation' && !summary) {showError('uploadError','Pilih rekaman yang selesai dianalisis untuk membuat anotasi.'); return;}
  if(document.fullscreenElement===$('reviewPanel')) await document.exitFullscreen();
  cancelDrawing(); pauseComparison();
  await stopReviewTracking(); currentView=view; reviewVideo.pause();
  $('analysisPane').hidden=view!=='analysis'; $('evidencePane').hidden=view!=='evidence'; $('reviewPanel').hidden=view!=='annotation';
  $('pageTitle').textContent={analysis:'Analisis video',evidence:'Bukti & hasil',annotation:'Anotasi manual'}[view];
  for(const button of document.querySelectorAll('[data-view]')) {if(button.dataset.view===view) button.setAttribute('aria-current','page'); else button.removeAttribute('aria-current');}
  syncControls();
  if(view==='annotation') await loadManualFrame(Math.min(summary.frames-1,Math.round(original.currentTime*summary.fps)));
}
for(const button of document.querySelectorAll('[data-view]')) button.onclick=()=>setView(button.dataset.view);
for(const id of ['newVideoButton','emptyUploadButton']) $(id).onclick=()=>{showError('uploadError','');$('uploadDialog').showModal();};
$('closeUpload').onclick=()=>$('uploadDialog').close();
$('uploadDialog').addEventListener('cancel',event=>{if(uploading) event.preventDefault();});
const original = $('originalVideo'), tracked = $('trackedVideo');
const showError = (id, text) => { $(id).textContent = text; $(id).hidden = !text; };
const mediaUrl = name => `/api/jobs/${job.id}/media/${encodeURIComponent(name)}`;
const timestamp = value => { const s = Math.max(0, Math.floor(value || 0)); return `${Math.floor(s/60).toString().padStart(2,'0')}:${(s%60).toString().padStart(2,'0')}`; };
async function api(url, options) {
  const response = await fetch(url, options);
  const data = await response.json();
  if (!response.ok) throw new Error(typeof data.detail === 'string' ? data.detail : 'Input tidak valid. Periksa isian dan coba lagi.');
  return data;
}
function resetChat() { history = []; $('messages').replaceChildren(); showError('chatError',''); }
function clearResults() {
  pauseComparison(); original.removeAttribute('src'); tracked.removeAttribute('src'); original.load(); tracked.load(); summary = null;
  ['videoContent','stats','resultsContent'].forEach(id => $(id).hidden = true);
  $('emptyVideos').hidden = false; $('resultsEmpty').hidden = false;
  $('resultsEmpty').textContent = 'Hasil akan tersedia setelah video selesai dianalisis.';
  $('comparisonBadge').textContent = 'Menunggu hasil';
  $('chatContext').textContent = 'Chat umum tersedia. Tunggu analisis video untuk bertanya tentang hasilnya.';
}
async function refreshHistory(selected) {
  const jobs = await api('/api/jobs');
  $('historySelect').replaceChildren(new Option(jobs.length ? 'Pilih video tersimpan' : 'Belum ada video',''));
  for (const item of jobs) {
    const mark = {done:'Selesai',processing:'Diproses',queued:'Antrean',error:'Gagal',uploading:'Upload',cancelled:'Dibatalkan',cancelling:'Membatalkan'}[item.status];
    const option = new Option(`${item.filename} · ${mark}`, item.id);
    $('historySelect').append(option);
  }
  $('historySelect').value = selected || '';
  return jobs;
}
function refreshCounts() {
  const occupancy=summary.reviewed_occupancy || summary.occupancy;
  $('peakPeople').textContent=Math.max(0,...occupancy.map(f=>f.person || 0));
  $('peakCars').textContent=Math.max(0,...occupancy.map(vehicles));
  const status=summary.review_status, latest=status?.latest;
  const latestCounts=latest ? Object.entries(latest.counts).filter(([,n])=>n>0).map(([k,n])=>`${n} ${(objectNames[k] || k).toLowerCase()}`).join(' · ') || '0 objek' : '';
  $('correctionCounts').textContent=status ? `${status.saved_positions} posisi koreksi disahkan · ${status.draft_positions} draft belum dihitung${latest ? ` · Terakhir detik ${latest.seconds}: ${latestCounts}` : ''}. Track dan lintasan tetap dari analisis AI awal.` : '';
  updateMoment();
}
function displayResults(data) {
  summary = data.summary; Object.assign(objectNames,summary.object_names || {});
  $('workspaceTitle').textContent=data.filename.length>38 ? data.filename.slice(0,35)+'…' : data.filename;
  $('workspaceTitle').title=data.filename;
  for(const kind of summary.object_classes || []) {if(!Array.from($('evidenceFilter').options).some(o=>o.value===kind)) $('evidenceFilter').add(new Option(objectNames[kind] || kind,kind));}
  $('videoContent').hidden = false; $('emptyVideos').hidden = true; $('stats').hidden = false;
  $('resultsContent').hidden = false; $('resultsEmpty').hidden = true; $('comparisonBadge').textContent = 'Analisis selesai';
  original.src = mediaUrl('original.mp4'); tracked.src = mediaUrl('tracked.mp4');
  $('chatContext').textContent = `Konteks: ${data.filename}. Chat hanya membaca hasil video ini.`;
  refreshCounts();
  $('crossingCount').textContent = summary.crossings.length;
  $('candidateCount').textContent = summary.tracks.filter(t => t.kind === 'person' && t.helmet_candidate).length;
  const count = kind => summary.tracks.filter(t => t.kind === kind).length;
  const crossing = kind => summary.crossings.filter(t => t.kind === kind).length;
  const kinds=summary.object_classes || ['person','car'];
  const details = [['Durasi / frame analisis',`${summary.duration} detik / ${summary.frames}`],...kinds.map(k=>[`Track / lintasan ${objectNames[k].toLowerCase()}`,`${count(k)} / ${crossing(k)}`]),['Waktu pemrosesan',`${summary.processing_seconds} detik`],['Perangkat analisis',summary.device_reason || summary.device || 'CPU (analisis lama)']];
  $('resultDetails').replaceChildren();
  for (const [label,value] of details) { const dt = document.createElement('dt'), dd = document.createElement('dd'); dt.textContent = label; dd.textContent = value; $('resultDetails').append(dt,dd); }
  renderEvidence();
  for (const [id,name] of [['downloadTracked','tracked.mp4'],['downloadSummary','summary_reviewed.json'],['downloadOriginal','upload.bin']]) { $(id).href = mediaUrl(name); $(id).setAttribute('download',name); }
  $('downloadSummary').href=`/api/jobs/${job.id}/summary`;
  $('analysisModel').value=summary.model_id || '';
  $('resultMode').value='ai'; $('correctedOption').disabled=true;
  const evidence=summary.learning_evidence;
  $('modelHelp').textContent=evidence ? `Hasil fine-tuning nyata · checkpoint ${evidence.checkpoint_sha256.slice(0,12)} · ${evidence.training_seconds} detik training. Akurasi perlu evaluasi terpisah.` : 'Hasil model dasar. Koreksi manual ditampilkan melalui Tampilan koreksi.';
  refreshQueue().catch(error=>showError('reviewError',error.message));
  updateMoment(); syncControls();
}
function renderEvidence() {
  if (!summary) return;
  $('evidenceList').replaceChildren();
  const filter=$('evidenceFilter').value; const evidence=summary.tracks.filter(t=>filter==='helmet' ? t.helmet_candidate && (t.helmet_evidence || t.evidence) : t.evidence && (filter==='all' || t.kind===filter));
  for (const item of evidence) {
    const row = document.createElement('div'); row.className = 'evidence-row';
    const link = document.createElement('a'); link.href = mediaUrl(filter==='helmet' ? (item.helmet_evidence || item.evidence) : item.evidence); link.target = '_blank'; link.rel = 'noopener'; link.setAttribute('aria-label',`Buka bukti track ${item.id}`);
    const image = document.createElement('img'); image.src = link.href; image.alt = `Bukti track ${item.id} pada detik ${item.evidence_seconds}`; image.loading = 'lazy'; link.append(image);
    const body = document.createElement('div'), title = document.createElement('strong'), detail = document.createElement('p'), seek = document.createElement('button');
    title.textContent = `ID #${item.id} · ${objectNames[item.kind] || item.kind}${filter==='helmet' ? ' · Kandidat tanpa helm' : ''}`;
    detail.textContent = `Detik ${filter==='helmet' ? (item.helmet_seconds ?? item.evidence_seconds) : item.evidence_seconds} · ${item.kind !== 'person' ? 'Objek ditandai pada foto' : ({helmet:'Helm terdeteksi',no_helmet:'Tanpa helm terdeteksi',unknown:'Helm belum jelas'}[item.evidence_status || item.status] || 'Helm belum jelas')}`;
    seek.type = 'button'; seek.className='button button--secondary button--sm'; seek.textContent = 'Lihat momen'; seek.onclick = () => { pauseComparison(); const at=filter==='helmet' ? (item.helmet_seconds ?? item.evidence_seconds) : item.evidence_seconds; original.currentTime=at; tracked.currentTime=at; setView('analysis'); original.scrollIntoView({block:'center'}); };
    body.append(title,detail,seek); row.append(link,body); $('evidenceList').append(row);
  }
  if (!evidence.length) { const p = document.createElement('p'); p.className = 'hint'; p.textContent = 'Belum ada bukti untuk jenis ini. Analisis lama mungkin belum menyimpan foto track orang biasa; analisis ulang melengkapinya.'; $('evidenceList').append(p); }
}
$('evidenceFilter').onchange=renderEvidence;
async function selectJob(id) {
  const current = ++generation;
  clearTimeout(pollTimer);clearTimeout(trainingPoll);clearTimeout(exportPoll);$('learningProgress').hidden=true;$('exportProgress').hidden=true;$('showLearnedResult').hidden=true; resetChat(); clearResults();
  $('currentFile').textContent='Pilih rekaman untuk mulai.';
  if (!id) { job = null; $('progressArea').hidden = true; $('comparisonBadge').textContent = 'Menunggu video'; syncControls(); return; }
  async function check() {
    try {
      const data = await api(`/api/jobs/${id}`);
      if (current !== generation) return;
      job = data; $('currentFile').textContent=data.filename; syncControls(); $('progressArea').hidden = false; $('jobProgress').value = data.progress; $('jobStatus').textContent = data.message;
      syncControls();
      if (data.status === 'done') { displayResults(data); await refreshHistory(id); }
      else if (['error','cancelled'].includes(data.status)) { $('comparisonBadge').textContent = 'Analisis gagal'; showError('uploadError',data.message); await refreshHistory(id); }
      else { $('comparisonBadge').textContent = 'Sedang diproses'; pollTimer = setTimeout(check,1500); }
    } catch (error) { if (current === generation) { showError('uploadError',error.message); syncControls(); } }
  }
  await check();
}
$('countLine').oninput = () => $('lineValue').textContent = `${$('countLine').value}%`;
$('uploadForm').onsubmit = async event => {
  event.preventDefault(); showError('uploadError','');
  const file = $('videoFile').files[0];
  if (!file) return;
  if (file.size > 250*1024*1024) { showError('uploadError','Ukuran video maksimal 250 MB.'); return; }
  uploading=true; syncControls(); $('progressArea').hidden = false; $('jobStatus').textContent = 'Mengunggah video…'; $('jobProgress').removeAttribute('value');
  const form = new FormData(); form.append('file',file); form.append('line',Number($('countLine').value)/100); form.append('device',$('deviceMode').value); form.append('model_id',$('analysisModel').value);
  try { const data = await api('/api/jobs',{method:'POST',body:form}); $('uploadDialog').close(); uploading=false; await setView('analysis'); await refreshHistory(data.id); await selectJob(data.id); }
  catch(error) { showError('uploadError',error.message); $('uploadDialog').close(); $('jobProgress').value = 0; }
  finally {uploading=false; syncControls();}
};
$('historySelect').onchange = () => { showError('uploadError',''); selectJob($('historySelect').value); };
function updateMoment() {
  if (!summary) return;
  $('videoTime').textContent = `${timestamp(original.currentTime)} / ${timestamp(summary.duration)}`;
  const occupancy=summary.reviewed_occupancy || summary.occupancy;
  const index = Math.min(occupancy.length-1, Math.round(original.currentTime*summary.fps));
  const frame = occupancy[index]; if(!frame) return; $('visibleNow').textContent = `Frame: ${frame.person || 0} orang · ${vehicles(frame)} objek lain`;
  $('playBoth').textContent = original.paused ? 'Putar bersama' : 'Jeda bersama';
}
let playbackEpoch=0;
function pauseComparison() {
  ++playbackEpoch; original.pause(); tracked.pause(); updateMoment();
}
async function playComparison(source=original) {
  if(currentView!=='analysis') return;
  const epoch=++playbackEpoch, other=source===original ? tracked : original;
  if(source.ended || other.ended) {original.currentTime=0; tracked.currentTime=0;}
  else if(Math.abs(source.currentTime-other.currentTime)>.08) other.currentTime=source.currentTime;
  showError('uploadError','');
  try {await Promise.all([source.play(),other.play()]);}
  catch(error) {
    if(epoch!==playbackEpoch || currentView!=='analysis' || error.name==='AbortError') return;
    pauseComparison(); showError('uploadError','Video gagal diputar. Periksa apakah kedua video dapat dimuat.');
  }
  updateMoment();
}
for (const [source,other] of [[original,tracked],[tracked,original]]) {
  source.addEventListener('play',() => {
    if(source.paused || currentView!=='analysis') return;
    if(other.paused) playComparison(source);
    updateMoment();
  });
  source.addEventListener('pause',() => {if(source.paused) pauseComparison();});
  source.addEventListener('seeking',() => {if(Math.abs(source.currentTime-other.currentTime)>.08) other.currentTime=source.currentTime; updateMoment();});
  source.addEventListener('ratechange',() => {if(source.playbackRate!==other.playbackRate) other.playbackRate=source.playbackRate;});
  source.addEventListener('error',() => {if(source.getAttribute('src')) {pauseComparison();showError('uploadError','Video gagal dimuat. Periksa koneksi server lokal.');}});
}
original.addEventListener('timeupdate',() => {if(!original.paused && !tracked.paused && Math.abs(original.currentTime-tracked.currentTime)>.3) tracked.currentTime=original.currentTime; updateMoment();});
$('playBoth').onclick=()=>{if(!original.paused || !tracked.paused) pauseComparison(); else playComparison();};
$('restartVideos').onclick=()=>{pauseComparison();original.currentTime=0;tracked.currentTime=0;updateMoment();};
function addMessage(role,text,detail,evidence=[]) {
  const div = document.createElement('div'); div.className = `message ${role}`; div.textContent = text;
  if (detail) { const small = document.createElement('small'); small.textContent = detail; div.append(small); }
  for (const item of evidence) { const a = document.createElement('a'); a.href=mediaUrl(item.file); a.target='_blank'; a.rel='noopener'; a.textContent=`Bukti ${(objectNames[item.kind] || item.kind).toLowerCase()} ID #${item.track_id} · ${timestamp(item.seconds)}`; div.append(a); }
  $('messages').append(div); $('messages').scrollTop = $('messages').scrollHeight;
}
$('clearChat').onclick = resetChat;
let sending = false;
$('chatForm').onsubmit = async event => {
  event.preventDefault(); if(currentView==='annotation'){if(trackingWanted || !reviewVideo.paused)await pauseReview();if(!(await persistReview(false)))return;} let message=$('chatInput').value.trim(); if(currentView==='annotation' && !/\b(detik|second|menit|minute)\b/i.test(message) && /(berapa|jumlah|siapa)/i.test(message)) message+=` pada detik ${(reviewFrame/summary.fps).toFixed(2)}`; if (!message || sending) return;
  sending=true; syncControls(); const current=generation; $('sendChat').disabled=true; $('clearChat').disabled=true; $('historySelect').disabled=true; showError('chatError','');
  addMessage('user',message); $('chatInput').value=''; $('chatStatus').textContent='AI sedang menyiapkan jawaban…';
  try {
    const data=await api('/api/chat',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({message,device:$('deviceMode').value,job_id:summary ? job.id : null,history:history.slice(-6)})});
    if (current!==generation) return;
    const label=data.mode==='reviewed' ? 'Hitungan AI + koreksi pengguna' : data.mode==='facts' ? 'Data analisis AI tersimpan' : data.mode==='manual' ? 'Koreksi manual pengguna' : data.mode==='guide' ? 'Panduan kemampuan aplikasi' : `${data.mode==='lora' ? 'Qwen lokal + LoRA pilot' : 'Qwen lokal · base model'} · ${data.seconds} detik${data.device ? ' · '+(data.device.startsWith('cuda') ? 'GPU' : 'CPU') : ''}`;
    addMessage('assistant',data.answer,label+(data.truncated ? ' · batas panjang respons tercapai' : ''),data.evidence); history.push({role:'user',content:message},{role:'assistant',content:data.answer.slice(0,2000)}); history=history.slice(-6);
  } catch(error) { showError('chatError',error.message); }
  finally { sending=false; $('sendChat').disabled=false; $('clearChat').disabled=false; syncControls(); $('chatStatus').textContent=''; }
};
$('chatInput').addEventListener('keydown',event => { if (event.key==='Enter' && !event.shiftKey) {event.preventDefault(); $('chatForm').requestSubmit();} });
for (const button of document.querySelectorAll('[data-question]')) button.onclick = () => { $('chatInput').value=button.dataset.question; $('chatForm').requestSubmit(); };
const manualNames={...objectNames,Hardhat:'Helm','NO-Hardhat':'Kepala tanpa helm'};
const labelColors={person:'#0f766e',car:'#2563eb',bus:'#7c3aed',truck:'#c2410c',motorcycle:'#0369a1',bicycle:'#a16207',Hardhat:'#15803d','NO-Hardhat':'#dc2626'};
function automaticColor(label) {
  const palette=['#0f766e','#2563eb','#7c3aed','#c2410c','#0369a1','#a16207'];
  let hash=0; for(const char of label) hash=(hash*31+char.charCodeAt(0))>>>0;
  return labelColors[label] || palette[hash%palette.length];
}
let reviewData={revision:0,frames:[]}, reviewBoxes=[], reviewFrame=0, reviewDirty=false, reviewBusy=false, reviewReady=false, editBox=-1, unsavedAdds=[], reviewBaseline=[];
const reviewSvg=$('reviewSvg'); let dragStart=null, dragBox=null, pointerDown=false, secondClick=false;
function boxMetadata() {
  const label=$('reviewLabel').value==='__custom__' ? $('customLabel').value.trim() : $('reviewLabel').value;
  const name=$('reviewName').value.trim();
  if(!/^[A-Za-z][A-Za-z0-9_-]{0,39}$/.test(label)) throw new Error('Isi label: huruf, angka, _ atau -, maksimal 40 karakter.');
  if(name.length>60 || /[\x00-\x1f\x7f]/.test(name)) throw new Error('Nama maksimal 60 karakter tanpa karakter kontrol.');
  return {label,name:name || null,color:$('reviewColorMode').value==='custom' ? $('reviewColor').value : null};
}
function syncMetadata() {
  $('customLabelField').hidden=$('reviewLabel').value!=='__custom__';
  const label=$('reviewLabel').value==='__custom__' ? $('customLabel').value.trim() : $('reviewLabel').value;
  $('reviewColor').disabled=reviewBusy || $('reviewColorMode').value!=='custom';
  if($('reviewColorMode').value==='auto') $('reviewColor').value=automaticColor(label);
  if(dragBox) {try {Object.assign(dragBox,boxMetadata());} catch {} drawManualBoxes();}
}
for(const id of ['reviewLabel','customLabel','reviewName','reviewColorMode','reviewColor']) $(id).addEventListener('input',syncMetadata);
function reviewBusyState(value) {
  reviewBusy=value; for(const button of $('reviewQueue').querySelectorAll('button'))button.disabled=value; $('nextPending').disabled=value; for(const button of $('boxList').querySelectorAll('button')) button.disabled=value;
  for(const id of ['reviewControls','boxControls','metadataControls']) $(id).disabled=value;
  for(const id of ['saveReview','reloadReview','exportDataset','exportCorrectedVideo','closeReview','suggestBoxes','reviewGroup','applyBoxButton','cancelEditButton','reviewPlayback','reviewTimeline','learnDetector']) $(id).disabled=value;
  syncMetadata(); syncControls();
}
function cancelDrawing() {
  dragStart=null; dragBox=null; pointerDown=false; secondClick=false; editBox=-1;
  $('addManualBox').textContent='Tambah kotak'; $('editActions').hidden=true;
  $('drawingStatus').textContent='Tarik kotak atau klik dua titik.';
  drawManualBoxes();
}
function renderReviewOverlay(boxes) {
  reviewSvg.replaceChildren();
  for (const [i,box] of boxes.entries()) {
    const color=box.color || automaticColor(box.label);
    const [x1,y1,x2,y2]=box.bbox, rect=document.createElementNS('http://www.w3.org/2000/svg','rect');
    for(const [k,v] of Object.entries({x:x1,y:y1,width:x2-x1,height:y2-y1,fill:color,'fill-opacity':.1,stroke:color,'stroke-width':i===editBox ? 3 : 2,'vector-effect':'non-scaling-stroke'})) rect.setAttribute(k,v);
    const label=document.createElementNS('http://www.w3.org/2000/svg','text');
    for(const [k,v] of Object.entries({x:x1,y:Math.max(.025,y1-.005),'font-size':'.025',fill:color,stroke:'#fff','stroke-width':'.003','paint-order':'stroke'})) label.setAttribute(k,v);
    label.textContent=`${box.track_id ? (box.source==='prompt_tracker' ? 'T' : '#')+box.track_id : i+1}: ${manualNames[box.label] || box.label}${box.name ? ' · '+box.name : ''}`;
    reviewSvg.append(rect,label);
  }
}
function drawManualBoxes() {
  renderReviewOverlay([...reviewBoxes,...(dragBox ? [dragBox] : [])]);
  $('boxList').replaceChildren();
  reviewBoxes.forEach((box,i)=> {
    const li=document.createElement('li'), title=document.createElement('span'), swatch=document.createElement('i');
    title.className='box-name'; swatch.className='box-swatch'; swatch.style.background=box.color || automaticColor(box.label);
    title.append(swatch,document.createTextNode(`${i+1} · ${manualNames[box.label] || box.label}${box.name ? ' / '+box.name : ''}`));
    const edit=document.createElement('button'); edit.type='button'; edit.className='button button--secondary button--sm'; edit.textContent=`Edit kotak ${i+1}`; edit.disabled=reviewBusy;
    edit.onclick=()=>{
      cancelDrawing(); editBox=i; const [x1,y1,x2,y2]=box.bbox;
      $('reviewLabel').value=Array.from($('reviewLabel').options).some(o=>o.value===box.label) ? box.label : '__custom__'; $('customLabel').value=box.label;
      $('reviewName').value=box.name || ''; $('reviewColorMode').value=box.color ? 'custom' : 'auto';
      $('reviewColor').value=box.color || automaticColor(box.label); syncMetadata();
      for(const [id,v] of [['boxX',x1],['boxY',y1],['boxW',x2-x1],['boxH',y2-y1]]) $(id).value=(100*v).toFixed(4);
      $('addManualBox').textContent='Perbarui kotak'; $('editActions').hidden=false;
      $('drawingStatus').textContent=`Mengedit kotak ${i+1}. Terapkan perubahan atau klik kanan/Escape untuk batal.`;
      drawManualBoxes(); $('reviewLabel').focus();
    };
    const remove=document.createElement('button'); remove.type='button'; remove.className='button button--tertiary button--sm'; remove.textContent=`Hapus kotak ${i+1}`; remove.disabled=reviewBusy;
    remove.onclick=()=>{const removed=reviewBoxes.splice(i,1)[0]; unsavedAdds=unsavedAdds.filter(b=>b!==removed); reviewDirty=true; cancelDrawing();};
    li.append(title,edit,remove); $('boxList').append(li);
  });
  const kinds=[...new Set(reviewBoxes.map(b=>b.label))];
  $('reviewCounts').textContent=`${reviewBoxes.length} kotak${kinds.length ? ' · '+kinds.map(k=>`${reviewBoxes.filter(b=>b.label===k).length} ${(manualNames[k] || k).toLowerCase()}`).join(' · ') : ''}${reviewDirty ? ' · belum disimpan' : ''}`;
}
function cancelInteraction() {
  if(!dragStart && editBox<0 && unsavedAdds.length) {
    const box=unsavedAdds.pop(), at=reviewBoxes.indexOf(box);
    if(at>=0) {
      reviewBoxes.splice(at,1);
      reviewDirty=JSON.stringify(reviewBoxes)!==JSON.stringify(reviewBaseline);
    }
  }
  cancelDrawing();
}
const reviewVideo=$('reviewVideo');
for(const button of document.querySelectorAll('[data-label]')) button.onclick=()=>{$('reviewLabel').value=button.dataset.label;syncMetadata();};
reviewVideo.ontimeupdate=()=>{$('reviewTimeline').value=reviewVideo.currentTime; $('reviewPlayTime').textContent=timestamp(reviewVideo.currentTime);};
let reviewPlaybackEpoch=0, trackingSession=null, trackingJob=null, trackingFrames=new Map(), trackingCursor=0, trackingEnd=false, trackingWanted=false, trackingBuffering=false, trackingFetch=null, analyzedFrames=new Map(), overlayJob=null, trackingSuppressed=new Set(), savedTrackingFrames=new Map(), trackingRevision=0;
function currentReviewFrame() {return Math.min(summary.frames-1,Math.floor(reviewVideo.currentTime*summary.fps+.0001));}
function overlap(a,b) {
  const w=Math.max(0,Math.min(a[2],b[2])-Math.max(a[0],b[0])), h=Math.max(0,Math.min(a[3],b[3])-Math.max(a[1],b[1]));
  return w*h/((a[2]-a[0])*(a[3]-a[1])+(b[2]-b[0])*(b[3]-b[1])-w*h || 1);
}
function overlayAt(index) {
  const row=(trackingWanted && trackingJob===job.id ? trackingFrames.get(index) : null) || savedTrackingFrames.get(index);
  if(row?.merged)return row;
  const prompts=row?.boxes || [], detected=(analyzedFrames.get(index)?.boxes || []).filter(b=>!row || !trackingSuppressed.has(b.track_id));
  return row ? {boxes:[...prompts,...detected.filter(b=>!prompts.some(p=>p.label===b.label && overlap(p.bbox,b.bbox)>.3))],lost:row.lost} : analyzedFrames.get(index);
}
function lostTracks(row) {return (row?.lost || []).map(b=>`T${b.track_id} ${b.name || manualNames[b.label] || b.label}`).join(', ');}
async function stopReviewTracking() {
  trackingWanted=false; trackingBuffering=false; ++reviewPlaybackEpoch;
  const id=trackingSession, owner=trackingJob; trackingSession=null; trackingFetch=null;
  if(id) {try {await api(`/api/jobs/${owner}/tracking/${id}/stop`,{method:'POST'});} catch(error){showError('reviewError',error.message);}}
}
async function pauseReview() {
  trackingWanted=false; trackingBuffering=false; ++reviewPlaybackEpoch; reviewVideo.pause();
  await loadManualFrame(currentReviewFrame());
}
async function prefetchTracking(epoch) {
  if(trackingFetch || !trackingSession || !trackingWanted || trackingEnd || trackingCursor>=currentReviewFrame()+20)return;
  const id=trackingSession;
  const pending=trackingFetch=api(`/api/jobs/${job.id}/tracking/${id}/step`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({after_frame:trackingCursor,count:10})});
  try {
    const data=await pending;
    if(epoch!==reviewPlaybackEpoch || id!==trackingSession)return;
    for(const row of data.frames)trackingFrames.set(row.frame_index,row);
    if(Number.isInteger(data.revision))trackingRevision=data.revision;
    trackingCursor=data.next_frame; trackingEnd=data.ended || trackingCursor>=summary.frames-1;
    if(trackingWanted && trackingBuffering && reviewVideo.paused && trackingFrames.has(currentReviewFrame())) {
      trackingBuffering=false; $('drawingStatus').textContent='Mengikuti kotak · jeda untuk koreksi.';
      await reviewVideo.play(); scheduleTrackingPaint(epoch);
    }
  }catch(error){
    if(epoch===reviewPlaybackEpoch) {trackingWanted=false;reviewVideo.pause();showError('reviewError','Tracker berhenti. '+error.message);await loadManualFrame(currentReviewFrame());}
  }finally{if(trackingFetch===pending)trackingFetch=null;}
  if(epoch===reviewPlaybackEpoch && trackingWanted)prefetchTracking(epoch);
}
function scheduleTrackingPaint(epoch) {
  const paint=(_now,metadata)=>{
    if(epoch!==reviewPlaybackEpoch || !trackingWanted || currentView!=='annotation')return;
    const index=Math.min(summary.frames-1,Math.floor((metadata?.mediaTime ?? reviewVideo.currentTime)*summary.fps+.0001)), row=overlayAt(index);
    if(!trackingFrames.has(index)) {
      trackingBuffering=true;reviewVideo.pause();renderReviewOverlay([]);if(trackingEnd){trackingWanted=false;showError('reviewError','Tracker sudah mencapai akhir video.');loadManualFrame(index);return;}$('drawingStatus').textContent='Menunggu tracker; video dijeda agar kotak tetap selaras.';prefetchTracking(epoch);return;
    }
    renderReviewOverlay(row.boxes);
    $('reviewCounts').textContent=`${row.boxes.length} kotak diikuti${row.lost?.length ? ' · '+'hilang: '+lostTracks(row)+'; jeda dan tandai ulang' : ''}`;
    prefetchTracking(epoch);
    if(!reviewVideo.paused)scheduleTrackingPaint(epoch);
  };
  if(reviewVideo.requestVideoFrameCallback)reviewVideo.requestVideoFrameCallback(paint);
  else requestAnimationFrame(paint);
}
reviewVideo.onpause=()=>{$('reviewPlayback').textContent=trackingWanted ? 'Jeda & anotasi' : 'Putar & ikuti kotak';};
reviewVideo.onended=()=>{if(trackingWanted)pauseReview();};
$('reviewPlayback').onclick=async()=>{
  if(reviewBusy)return;
  if(trackingWanted || !reviewVideo.paused) {await pauseReview();return;}
  if((reviewVideo.ended || reviewFrame>=summary.frames-1) && !(await loadManualFrame(0)))return;
  if(!(await persistReview(false)))return;
  await stopReviewTracking();
  const epoch=++reviewPlaybackEpoch; reviewBusyState(true); showError('reviewError','');
  try {
    const unchanged=new Set(reviewBoxes.filter(b=>b.source==='detector').map(b=>b.track_id));
    trackingSuppressed=new Set((analyzedFrames.get(reviewFrame)?.boxes || []).filter(b=>b.track_id!=null && !unchanged.has(b.track_id)).map(b=>b.track_id));
    const data=await api(`/api/jobs/${job.id}/tracking`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({frame_index:reviewFrame,boxes:analyzedFrames.size ? reviewBoxes.filter(b=>b.source!=='detector') : reviewBoxes,revision:trackingRevision,suppressed_ids:[...trackingSuppressed]})});
    if(epoch!==reviewPlaybackEpoch)return;
    trackingRevision=data.revision;
    trackingSession=data.id;trackingJob=job.id;trackingFrames=new Map([[reviewFrame,data.frame]]);trackingCursor=reviewFrame;trackingEnd=reviewFrame>=summary.frames-1;trackingWanted=true;trackingBuffering=false;
    reviewReady=false;cancelDrawing();reviewSvg.hidden=false;
    await prefetchTracking(epoch);
    if(epoch!==reviewPlaybackEpoch || !trackingWanted)return;
    await reviewVideo.play();scheduleTrackingPaint(epoch);
    $('reviewStatus').textContent='Tracking koreksi otomatis tersimpan saat frame disiapkan. Jeda untuk ekspor video; kotak masih perlu diperiksa sebelum masuk dataset.';
  }catch(error){if(epoch!==reviewPlaybackEpoch || error.name==='AbortError')return;trackingWanted=false;showError('reviewError',error.message);await stopReviewTracking();}
  finally {
    reviewBusyState(false);
    if(trackingWanted){for(const id of ['metadataControls','boxControls','reviewControls','saveReview','suggestBoxes','reloadReview','exportDataset','exportCorrectedVideo','learnDetector'])$(id).disabled=true;for(const button of $('boxList').querySelectorAll('button'))button.disabled=true;$('reviewPlayback').textContent='Jeda & anotasi';$('drawingStatus').textContent='Mengikuti kotak · jeda untuk koreksi.';}
    else reviewReady=true;
  }
};
$('reviewTimeline').onchange=async()=>{
  if(reviewBusy)return;
  const index=Math.min(summary.frames-1,Math.round(Number($('reviewTimeline').value)*summary.fps));
  if(!(await persistReview(false))) {$('reviewTimeline').value=reviewFrame/summary.fps;return;}
  await loadManualFrame(index);
};
$('applyBoxButton').onclick=()=>{if(editBox<0)return; try {commitManualBox({...boxMetadata(),bbox:[...reviewBoxes[editBox].bbox]});} catch(error){showError('reviewError',error.message);}};
$('cancelEditButton').onclick=cancelDrawing;
async function loadManualFrame(index,discard=false) {
  if (!summary || reviewBusy) return;
  if (!discard && !(await persistReview(false))) return;
  if (!Number.isInteger(index) || index<0 || index>=summary.frames) {showError('reviewError','Frame di luar video.'); return;}
  reviewBusyState(true); reviewReady=false; showError('reviewError',''); $('reviewStatus').textContent='Memuat frame dan koreksi tersimpan…'; $('reviewStage').hidden=true;
  try {
    await stopReviewTracking(); reviewVideo.pause();
    if(overlayJob!==job.id){const data=await api(`/api/jobs/${job.id}/overlays`);analyzedFrames=new Map(data.frames.map(f=>[f.frame_index,f]));overlayJob=job.id;trackingSuppressed=new Set();}
    const corrections=await api(`/api/jobs/${job.id}/corrections`);
    savedTrackingFrames=new Map(corrections.frames.map(f=>[f.frame_index,f]));trackingRevision=corrections.revision;
    reviewData=await api(`/api/jobs/${job.id}/annotations`); reviewFrame=index;
    if(reviewVideo.getAttribute('src')!==mediaUrl('original.mp4')) {
      await new Promise((resolve,reject)=>{reviewVideo.onloadedmetadata=resolve; reviewVideo.onerror=()=>reject(new Error('Video anotasi gagal dimuat.')); reviewVideo.src=mediaUrl('original.mp4');});
    }
    $('reviewStage').style.setProperty('--video-ratio',reviewVideo.videoWidth/reviewVideo.videoHeight);
    const at=index/summary.fps;
    if(Math.abs(reviewVideo.currentTime-at)>.001 || reviewVideo.seeking) {
      await new Promise((resolve,reject)=>{
        const timer=setTimeout(()=>{cleanup();reject(new Error('Video belum selesai berpindah posisi. Coba kembali.'));},10000);
        const cleanup=()=>{clearTimeout(timer);reviewVideo.removeEventListener('seeked',done);reviewVideo.removeEventListener('error',failed);};
        const done=()=>{cleanup();resolve();}, failed=()=>{cleanup();reject(new Error('Video anotasi gagal dibaca.'));};
        reviewVideo.addEventListener('seeked',done);reviewVideo.addEventListener('error',failed);reviewVideo.currentTime=at;
      });
    }
    $('reviewTimeline').max=(summary.duration-1/summary.fps).toString(); $('reviewTimeline').value=(index/summary.fps).toString();
    const saved=reviewData.frames.find(f=>f.frame_index===index);
    const predicted=overlayAt(index);
    reviewBoxes=(saved?.boxes || predicted?.boxes || []).map(b=>({...b,bbox:[...b.bbox]}));
    if(!saved && !predicted) {
      try {const suggested=await api(`/api/jobs/${job.id}/suggestions/${index}?group=${$('reviewGroup').value}`);reviewBoxes=suggested.boxes;}
      catch(error){showError('reviewError',error.message+' Anda tetap bisa menggambar kotak sendiri.');}
    }
    reviewBaseline=structuredClone(reviewBoxes);reviewDirty=false; unsavedAdds=[]; cancelDrawing(); $('reviewSeconds').value=(index/summary.fps).toFixed(2); $('reviewSeconds').max=(summary.duration-1/summary.fps).toFixed(2);
    original.currentTime=index/summary.fps; tracked.currentTime=original.currentTime; reviewReady=true; renderQueue(); $('reviewPlayback').textContent='Putar & ikuti kotak'; $('reviewStage').hidden=false; reviewSvg.toggleAttribute('hidden',false); drawManualBoxes();
    $('reviewStatus').textContent=`Frame ${index} · detik ${(index/summary.fps).toFixed(2)} · ${saved ? 'koreksi tersimpan dimuat' : predicted?.lost?.length ? 'hilang: '+lostTracks(predicted)+'; tandai ulang' : predicted?.merged ? 'tracking tersimpan dimuat; periksa sebelum Simpan koreksi' : 'kotak AI/tracker sebagai saran; koreksi sebelum disimpan'}`;
    return true;
  } catch(error) {showError('reviewError',error.message);} finally {reviewBusyState(false);}
}
$('openReview').onclick=()=>setView('annotation');
$('loadReviewFrame').onclick=()=>loadManualFrame(Math.round(Number($('reviewSeconds').value)*summary.fps));
$('previousReviewFrame').onclick=()=>loadManualFrame(reviewFrame-1);
$('nextReviewFrame').onclick=()=>loadManualFrame(reviewFrame+1);
$('reloadReview').onclick=()=>loadManualFrame(reviewFrame,true);
window.addEventListener('beforeunload',event=>{if(reviewDirty){event.preventDefault();event.returnValue='';}});
$('closeReview').onclick=()=>setView('analysis');
$('fullscreenReview').onclick=async()=>{
  showError('reviewError','');
  try {
    if(document.fullscreenElement===$('reviewPanel')) await document.exitFullscreen();
    else await $('reviewPanel').requestFullscreen();
  }catch {showError('reviewError','Browser menolak layar penuh. Anotasi tetap bisa dipakai pada tampilan biasa.');}
};
document.addEventListener('fullscreenchange',()=>{
  const active=document.fullscreenElement===$('reviewPanel'), button=$('fullscreenReview');
  button.textContent=active ? 'Keluar layar penuh' : 'Layar penuh';
  button.setAttribute('aria-pressed',String(active));
  button.focus({preventScroll:true});
});
function commitManualBox(box) {
  if (!reviewReady || reviewBusy) return;
  const [x1,y1,x2,y2]=box.bbox;
  if (!(0<=x1 && x1<x2 && x2<=1 && 0<=y1 && y1<y2 && y2<=1)) {showError('reviewError','Kotak harus mempunyai luas positif dan berada dalam gambar.');return;}
  if(editBox>=0) {const previous=reviewBoxes[editBox]; reviewBoxes[editBox]=box; unsavedAdds=unsavedAdds.map(b=>b===previous?box:b);}
  else if(reviewBoxes.length<100) {reviewBoxes.push(box); unsavedAdds.push(box);}
  else {showError('reviewError','Maksimal 100 kotak per frame.');return;}
  reviewDirty=true; showError('reviewError',''); cancelDrawing();
}
$('boxForm').onsubmit=e=>{
  e.preventDefault(); try {
    const x=Number($('boxX').value)/100,y=Number($('boxY').value)/100,w=Number($('boxW').value)/100,h=Number($('boxH').value)/100;
    commitManualBox({...boxMetadata(),bbox:[x,y,x+w,y+h]});
  } catch(error) {showError('reviewError',error.message);}
};
function pointerPosition(e) { const r=reviewSvg.getBoundingClientRect(); return [Math.max(0,Math.min(1,(e.clientX-r.left)/r.width)),Math.max(0,Math.min(1,(e.clientY-r.top)/r.height))]; }
function previewBox(at) {return {...boxMetadata(),bbox:[Math.min(dragStart[0],at[0]),Math.min(dragStart[1],at[1]),Math.max(dragStart[0],at[0]),Math.max(dragStart[1],at[1])]};}
reviewSvg.onpointerdown=e=>{
  if(reviewBusy || !reviewReady || e.button!==0)return;
  e.preventDefault();
  try {boxMetadata();} catch(error) {showError('reviewError',error.message);return;}
  if(!dragStart) {cancelDrawing(); dragStart=pointerPosition(e); secondClick=false;} else secondClick=true;
  pointerDown=true; reviewSvg.setPointerCapture(e.pointerId);
  $('drawingStatus').textContent='Pilih sudut kedua. Klik kanan/Escape untuk batal.';
};
reviewSvg.onpointermove=e=>{if(!dragStart)return; try {dragBox=previewBox(pointerPosition(e)); drawManualBoxes();} catch(error){showError('reviewError',error.message);cancelDrawing();}};
reviewSvg.onpointerup=e=>{
  if(!dragStart || !pointerDown || e.button!==0)return;
  pointerDown=false; const at=pointerPosition(e), r=reviewSvg.getBoundingClientRect();
  const moved=Math.hypot((at[0]-dragStart[0])*r.width,(at[1]-dragStart[1])*r.height)>5;
  if(secondClick || moved) {
    try {const box=previewBox(at); cancelDrawing(); commitManualBox(box);} catch(error){showError('reviewError',error.message);cancelDrawing();}
  }
};
reviewSvg.oncontextmenu=e=>{e.preventDefault(); if(!reviewBusy && reviewReady) cancelInteraction();};
reviewSvg.onpointercancel=cancelDrawing;
$('reviewPanel').addEventListener('keydown',e=>{if(e.key==='Escape' && !reviewBusy && reviewReady){e.preventDefault();cancelInteraction();}});
async function persistReview(learn) {
  if(reviewBusy) return false;
  if(!reviewReady) return !reviewDirty;
  try {
    if(editBox>=0) commitManualBox({...boxMetadata(),bbox:[...reviewBoxes[editBox].bbox]});
    if(dragBox) {const box=dragBox;cancelDrawing();commitManualBox(box);}
    else if(dragStart) cancelDrawing();
    if(!learn && !reviewDirty) return true;
    reviewBusyState(true);showError('reviewError','');
    const saved=reviewData.frames.find(f=>f.frame_index===reviewFrame), group=$('reviewGroup').value;
    reviewData=await api(`/api/jobs/${job.id}/annotations`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({frame_index:reviewFrame,revision:reviewData.revision,complete:learn ? group==='objects' || !!saved?.complete : false,helmets_complete:learn ? group==='helmets' || !!saved?.helmets_complete : false,learn_group:learn ? group : null,boxes:reviewBoxes})});
    reviewBaseline=structuredClone(reviewBoxes);reviewDirty=false;unsavedAdds=[];cancelDrawing();
    try {const data=await api(`/api/jobs/${job.id}`);summary=data.summary;refreshCounts();}
    catch {showError('reviewError','Koreksi tersimpan, tetapi hitungan belum berhasil dimuat. Buka kembali rekaman untuk memperbaruinya.');}
    $('reviewStatus').textContent=learn ? 'Koreksi tersimpan. Hitungan pada posisi ini, puncak dashboard, dan ringkasan chat sudah diperbarui.' : 'Draft disimpan otomatis. Putar untuk mengikuti kotak; Simpan koreksi setelah posisi ini diperiksa.';
    return true;
  }catch(error){showError('reviewError',error.message);return false;}
  finally{reviewBusyState(false);drawManualBoxes();}
}
$('saveReview').onclick=async()=>{
  if(!(await persistReview(true)))return;
  try {
    const queue=await refreshQueue();
    if(queue.pending) learningStatus(`Koreksi tersimpan. ${queue.pending} posisi ${queue.group==='objects'?'objek':'helm'} belum disahkan. Training dimulai setelah antrean selesai.`);
    else {startExport(false); await startLearning(job.id,$('reviewGroup').value);}
  }catch(error){showError('reviewError',error.message);}
};
$('learnDetector').onclick=async()=>{if(trackingWanted)await pauseReview();if(await persistReview(true))startLearning(job.id,$('reviewGroup').value);};
$('suggestBoxes').onclick=async()=>{
  if(reviewBusy || !reviewReady)return;
  reviewBusyState(true);showError('reviewError','');
  try{
    const data=await api(`/api/jobs/${job.id}/suggestions/${reviewFrame}?group=${$('reviewGroup').value}`);
    // Append only suggestions not already represented; saved/manual edits win.
    for(const box of data.boxes){
      const overlap=reviewBoxes.some(b=>b.label===box.label && b.bbox.every((n,i)=>Math.abs(n-box.bbox[i])<.03));
      if(!overlap && reviewBoxes.length<100){reviewBoxes.push(box);unsavedAdds.push(box);reviewDirty=true;}
    }
    cancelDrawing();$('reviewStatus').textContent='Kotak AI dapat diedit/dihapus. Lengkapi yang terlewat, lalu Simpan koreksi.';
  }catch(error){showError('reviewError',error.message);}finally{reviewBusyState(false);drawManualBoxes();}
};
$('exportDataset').onclick=async()=>{if(reviewDirty){showError('reviewError','Simpan koreksi terlebih dahulu.');return;} reviewBusyState(true); showError('reviewError',''); try{const response=await fetch(`/api/jobs/${job.id}/dataset`); if(!response.ok){const data=await response.json();throw new Error(data.detail);} const url=URL.createObjectURL(await response.blob()), a=document.createElement('a'); a.href=url;a.download=`koreksi_${job.id}.zip`;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000); $('reviewStatus').textContent='Dataset YOLO diekspor. Pisahkan train/val/test berdasarkan video sebelum training.';}catch(error){showError('reviewError',error.message);}finally{reviewBusyState(false);}};
let exportPoll=null, currentExport=null;
async function startExport(download=false) {
  if(!job || !summary)return;
  const source=job.id, current=generation;
  try {
    const data=await api(`/api/jobs/${source}/exports`,{method:'POST'});
    currentExport={source,id:data.id};$('exportProgress').hidden=false;
    async function poll(){
      if(current!==generation)return;
      try {
        const state=await api(`/api/jobs/${source}/exports/${data.id}`);
        if(current!==generation)return;
        $('exportProgressBar').value=state.progress;$('exportStatus').textContent=state.message;
        $('cancelExport').hidden=!['queued','processing','cancelling'].includes(state.status);
        $('cancelExport').disabled=state.status==='cancelling';
        if(['queued','processing','cancelling'].includes(state.status)){exportPoll=setTimeout(poll,1000);return;}
        if(state.status==='done'){
          $('correctedOption').disabled=false; $('correctedOption').dataset.url=state.media_url;
          if(download){const a=document.createElement('a');a.href=state.media_url;a.download=state.filename;a.click();}
          else {$('resultMode').value='corrections';switchResultMode();}
        }
      }catch(error){$('exportStatus').textContent=error.message;}
    }
    clearTimeout(exportPoll);await poll();
  }catch(error){if(current===generation){$('exportProgress').hidden=false;$('exportStatus').textContent=error.message;}}
}
$('exportCorrectedVideo').onclick=async()=>{if(reviewBusy || trackingWanted || !(await persistReview(false)))return;await startExport(true);};
$('cancelExport').onclick=async()=>{if(currentExport)try{await api(`/api/jobs/${currentExport.source}/exports/${currentExport.id}/cancel`,{method:'POST'});}catch(error){$('exportStatus').textContent=error.message;}};
function switchResultMode(){
  if(!job || !summary)return;
  pauseComparison();const at=original.currentTime;
  tracked.src=$('resultMode').value==='corrections' ? $('correctedOption').dataset.url : mediaUrl('tracked.mp4');
  tracked.addEventListener('loadedmetadata',()=>{tracked.currentTime=Math.min(at,tracked.duration);},{once:true});
  $('comparisonBadge').textContent=$('resultMode').value==='corrections' ? 'Koreksi pengguna · belum bukti training' : (summary.model_id ? 'Hasil model fine-tuning' : 'Hasil model dasar');
}
$('resultMode').onchange=()=>{if($('resultMode').value==='corrections' && $('correctedOption').disabled)startExport(false);else switchResultMode();};
$('prepareCorrections').onclick=()=>startExport(false);
let queueData=null;
async function refreshQueue(){
  if(!job || !summary)return null;
  const source=job.id,group=$('reviewGroup').value;
  const data=await api(`/api/jobs/${source}/review-queue?group=${group}`);
  if(job?.id!==source || $('reviewGroup').value!==group)return null;
  queueData=data;renderQueue();return data;
}
function renderQueue(){
  if(!queueData)return;
  $('queueStatus').textContent=`${queueData.reviewed}/${queueData.total} posisi disahkan · ${queueData.pending} perlu review`;
  $('reviewQueue').replaceChildren();
  for(const row of queueData.positions.filter(r=>$('queueFilter').value==='all' || !r.reviewed)){
    const button=document.createElement('button');button.type='button';button.className='queue-position button button--outline button--sm';
    button.textContent=`${row.reviewed?'✓ ':''}${row.seconds.toFixed(1)}s · ${row.reasons.join(' · ')}`;
    button.disabled=reviewBusy;button.onclick=async()=>{if(trackingWanted)await pauseReview();await loadManualFrame(row.frame_index);};
    if(row.frame_index===reviewFrame)button.setAttribute('aria-current','true');$('reviewQueue').append(button);
  }
}
$('queueFilter').onchange=renderQueue;
$('nextPending').onclick=async()=>{if(trackingWanted)await pauseReview();const data=await refreshQueue(),pending=data?.positions.filter(r=>!r.reviewed);if(pending?.length)await loadManualFrame((pending.find(r=>r.frame_index>reviewFrame)||pending[0]).frame_index);};
$('reviewGroup').onchange=async()=>{try{await refreshQueue();}catch(error){showError('reviewError',error.message);}};
$('retryJob').onclick=async()=>{try{const data=await api(`/api/jobs/${job.id}/retry`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({model_id:job.model_id || '',device:$('deviceMode').value})});await refreshHistory(data.id);await selectJob(data.id);}catch(error){showError('uploadError',error.message);}};
$('cancelJob').onclick=async()=>{try{await api(`/api/jobs/${job.id}/cancel`,{method:'POST'});}catch(error){showError('uploadError',error.message);}};
const themeMedia=matchMedia('(prefers-color-scheme: dark)');
try {$('themeSelect').value=localStorage.getItem('video-theme') || 'system';} catch {}
function applyTheme() {const choice=$('themeSelect').value; document.documentElement.dataset.theme=choice==='system' ? (themeMedia.matches ? 'dark' : 'light') : choice; try {localStorage.setItem('video-theme',choice);} catch {}}
$('themeSelect').onchange=applyTheme; themeMedia.addEventListener('change',()=>{if($('themeSelect').value==='system')applyTheme();}); applyTheme();
let trainingPoll=null;
async function refreshTraining(resume=true) {
  const current=generation;
  const selected=$('analysisModel').value, jobs=await api('/api/training');
  if(current!==generation)return;
  $('analysisModel').replaceChildren(new Option('YOLO dasar · pretrained',''));
  for(const item of jobs.filter(j=>j.status==='done')) $('analysisModel').add(new Option(`${item.group==='objects'?'Objek':'Helm'} · ${item.id.slice(0,6)} · hasil koreksi`,item.id));
  if(Array.from($('analysisModel').options).some(o=>o.value===selected)) $('analysisModel').value=selected;
  const active=jobs.find(j=>j.followup_job_id && ['queued','processing','cancelling'].includes(j.status));
  if(active && resume) pollTraining(active.id);
}
function learningStatus(message,progress=0){$('learningProgress').hidden=false;$('learningProgressBar').value=progress;$('learningStatus').textContent=message;}
async function startLearning(source,group){
  const current=generation;
  try{
    $('showLearnedResult').hidden=true;
    const data=await api(`/api/jobs/${source}/learn`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({group,device:$('deviceMode').value})});
    if(current!==generation)return;
    if(data.status==='waiting'){learningStatus(data.message);return;}
    pollTraining(data.id,data.result_job_id);
  }catch(error){learningStatus('Koreksi tersimpan. '+error.message+' Klik Coba belajar lagi untuk mencoba kembali.');}
}
async function pollTraining(id,resultJobId=null,current=generation){
  if(current!==generation)return;clearTimeout(trainingPoll);
  try{
    const data=await api('/api/training/'+id);if(current!==generation)return;learningStatus(data.message,data.progress);
    $('cancelLearning').hidden=!['queued','processing','cancelling'].includes(data.status);$('cancelLearning').disabled=data.status==='cancelling';$('cancelLearning').onclick=async()=>{try{await api('/api/training/'+id+'/cancel',{method:'POST'});}catch(error){learningStatus(error.message);}};
    if(['queued','processing','cancelling'].includes(data.status)){trainingPoll=setTimeout(()=>pollTraining(id,resultJobId,current),1500);return;}
    if(['error','cancelled'].includes(data.status)){learningStatus(data.message);$('cancelLearning').hidden=true;return;}
    $('cancelLearning').hidden=true;await refreshTraining(false);if(current!==generation)return;
    if(resultJobId || data.result_job_id){
      const result=await api('/api/jobs/'+(resultJobId || data.result_job_id));
      if(['queued','processing','cancelling'].includes(result.status)){learningStatus('Belajar selesai. '+result.message,result.progress);trainingPoll=setTimeout(()=>pollTraining(id,resultJobId,current),1500);return;}
      if(current!==generation)return;
      learningStatus(result.status==='done' ? 'Belajar dan analisis ulang selesai. Hasil baru siap dilihat; koreksi tetap bisa ditanya.' : result.message,100);
      $('showLearnedResult').hidden=result.status!=='done';$('showLearnedResult').onclick=async()=>{if(!(await persistReview(false)))return;await setView('analysis');await refreshHistory(result.id);await selectJob(result.id);};
      if(result.status==='done' && data.followup_job_id===job?.id && !reviewDirty && !reviewBusy && !trackingWanted && reviewVideo.paused && !sending){
        await setView('analysis');await refreshHistory(result.id);await selectJob(result.id);
        learningStatus(`Fine-tuning dan analisis ulang selesai · checkpoint ${data.checkpoint_sha256?.slice(0,12)}. Hasil baru sedang ditampilkan.`,100);
      }
    }
  }catch(error){learningStatus(error.message);}
}
$('analysisModel').onchange=()=>{$('modelHelp').textContent=$('analysisModel').value ? 'Kandidat pilot dipilih. Klik Analisis ulang untuk mencoba pada video ini.' : 'Model dasar dipilih. Hasil lama tetap tersimpan.';};
$('reanalyzeButton').onclick=async()=>{if(!job || !summary)return; showError('uploadError',''); try {const data=await api(`/api/jobs/${job.id}/reanalyze`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({model_id:$('analysisModel').value,device:$('deviceMode').value})});await setView('analysis');await refreshHistory(data.id);await selectJob(data.id);}catch(error){showError('uploadError',error.message);}};
syncMetadata();
(async () => {
  try { const health=await api('/api/health'); $('systemStatus').textContent=health.vision_ready && health.chat_ready ? `Model lokal siap · ${health.device.startsWith('cuda') ? 'RTX / CUDA' : 'CPU'}${health.adapter_ready ? ' · LoRA' : ''}` : 'Model belum lengkap · lihat README'; await refreshTraining(); const jobs=await refreshHistory(); if (jobs.length) { const preferred=jobs.find(j=>['queued','processing','cancelling'].includes(j.status)) || jobs.find(j=>j.status==='done') || jobs[0]; $('historySelect').value=preferred.id; await selectJob(preferred.id); } }
  catch(error) { $('systemStatus').textContent='Server tidak terhubung'; showError('uploadError',error.message); }
})();
