import { useRef, useState } from 'react';

declare const workspaceAuth:{request(input:RequestInfo|URL,init?:RequestInit):Promise<Response>};
interface LedgerEvent {id:string;category:'observation'|'attendance';symbol:string;status:string;job_id:string|null;track_id:number|null;occurred_at:string;verified_at:string;verifier_id?:string;reason:string|null;payload:{subject_id?:string;evidence?:string|null;seconds?:number}}
interface Facts {crossing_event_count:number;observed_track_count:number;attendance_record_count:number;stale_count:number;retracted_count:number;limitations:string[]}
interface Recording {id:string;filename:string;status:string}
interface Summary {crossings:{kind:string;track_id:number;direction:string;seconds:number}[];tracks:{id:number;kind:string;evidence?:string}[]}
async function api<T>(url:string,init?:RequestInit):Promise<T>{
 const response=await workspaceAuth.request(url,init),data=await response.json();
 if(!response.ok)throw new Error(typeof data.detail==='string'?data.detail:'Ledger gagal memproses permintaan.');
 return data as T;
}
const post=(body:unknown):RequestInit=>({method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
export function EventLedger(){
 const [role,setRole]=useState(''),[rows,setRows]=useState<LedgerEvent[]>([]),[facts,setFacts]=useState<Facts|null>(null),[jobs,setJobs]=useState<Recording[]>([]);
 const [job,setJob]=useState(''),[summary,setSummary]=useState<Summary|null>(null),[selected,setSelected]=useState<number[]>([]),[recordedAt,setRecordedAt]=useState('');
 const [novelty,setNovelty]=useState<{runs:{run_id:string;summary:Record<string,unknown>}[];errors:unknown[]}|null>(null);
 const [busy,setBusy]=useState(false),[error,setError]=useState(''),[status,setStatus]=useState('');
 const [subject,setSubject]=useState(''),[sourceKind,setSourceKind]=useState('manual'),[sourceId,setSourceId]=useState(''),[occurredAt,setOccurredAt]=useState(''),[action,setAction]=useState('arrived'),[track,setTrack]=useState('');
 const selectionGeneration=useRef(0);
 const reviewer=role==='admin'||role==='reviewer';
 async function refresh(){
  const [events,current,recordings,session]=await Promise.all([api<{events:LedgerEvent[]}>('/api/ledger/events'),api<Facts>('/api/ledger/facts'),api<Recording[]>('/api/jobs'),api<{user:{role:string}}>('/api/auth/session')]);
  setRows(events.events);setFacts(current);setJobs(recordings.filter(item=>item.status==='done'));setRole(session.user.role);
  try{setNovelty(await api('/api/ledger/novelty/runs'));}catch{setNovelty(null);}
 }
 async function run(operation:()=>Promise<void>){
  if(busy)return;setBusy(true);setError('');setStatus('');
  try{await operation();}catch(reason){setError(reason instanceof Error?reason.message:String(reason));}
  finally{setBusy(false);}
 }
 async function chooseRecording(id:string){
  const generation=++selectionGeneration.current;
  setJob(id);setSummary(null);setSelected([]);setTrack('');setError('');
  if(!id)return;
  try{const value=await api<Summary>(`/api/jobs/${encodeURIComponent(id)}/summary`);if(generation===selectionGeneration.current)setSummary(value);}
  catch(reason){if(generation===selectionGeneration.current)setError(reason instanceof Error?reason.message:String(reason));}
 }
 const people=summary?.tracks.filter(item=>item.kind==='person')||[];
 const crossings=summary?.crossings.map((value,index)=>({value,index})).filter(({value})=>value.kind==='person'&&people.some(item=>item.id===value.track_id))||[];
 return <details className="event-ledger" onToggle={event=>{if(event.currentTarget.open&&!facts)void run(refresh);}}>
  <summary>Kejadian terverifikasi</summary>
  <p className="hint">Crossing adalah lintasan track, bukan identitas atau jumlah orang unik. Badge/QR dicatat setelah verifikasi manual administrator; halaman ini bukan scanner.</p>
  <button className="button button--tertiary button--sm" type="button" disabled={busy} onClick={()=>void run(refresh)}>Perbarui ledger</button>
  {error&&<p className="error" role="alert">{error}</p>}<p className="hint" role="status">{busy?'Memproses bukti ledger…':status}</p>
  {facts&&<dl className="ngram-metrics"><div><dt>Crossing terverifikasi</dt><dd>{facts.crossing_event_count}</dd></div><div><dt>Track teramati, identitas unknown</dt><dd>{facts.observed_track_count}</dd></div><div><dt>Catatan absensi terverifikasi</dt><dd>{facts.attendance_record_count}</dd></div><div><dt>Bukti stale / ditarik</dt><dd>{facts.stale_count} / {facts.retracted_count}</dd></div></dl>}
  {reviewer&&<section><h3>Tinjau crossing dari rekaman</h3>
   <label>Rekaman yang selesai dianalisis<select value={job} disabled={busy} onChange={event=>void chooseRecording(event.target.value)}><option value="">Pilih rekaman</option>{jobs.map(item=><option key={item.id} value={item.id}>{item.filename}</option>)}</select></label>
   <form onSubmit={event=>{event.preventDefault();void run(async()=>{await api(`/api/ledger/jobs/${encodeURIComponent(job)}/import`,post({recorded_at:recordedAt,crossing_indices:selected}));await refresh();setSelected([]);setStatus('Crossing terpilih tercatat. Unknown helm tidak dianggap pelanggaran.');});}}><fieldset disabled={busy}>
    <label>Waktu awal rekaman, termasuk zona waktu<input type="text" required maxLength={80} placeholder="2026-10-10T08:00:00+07:00" value={recordedAt} onChange={event=>setRecordedAt(event.target.value)}/></label>
    {summary&&<div className="ngram-table"><table><caption>Pilih lintasan orang yang sudah ditinjau. Waktu kejadian = awal rekaman + detik crossing.</caption><thead><tr><th>Pilih</th><th>Track</th><th>Arah</th><th>Detik</th><th>Bukti track</th></tr></thead><tbody>{crossings.map(({value,index})=>{const evidence=people.find(item=>item.id===value.track_id)?.evidence;return <tr key={index}><td><input className="ledger-check" type="checkbox" checked={selected.includes(index)} aria-label={`Verifikasi crossing ${index}, track ${value.track_id}, detik ${value.seconds}`} onChange={event=>setSelected(values=>event.target.checked?[...values,index]:values.filter(item=>item!==index))}/></td><td>{value.track_id}</td><td>{value.direction==='down'?'Masuk zona':'Keluar zona'}</td><td>{value.seconds}</td><td>{evidence&&/^evidence_\d+\.jpg$/.test(evidence)?<a href={`/api/jobs/${encodeURIComponent(job)}/media/${evidence}`} target="_blank" rel="noreferrer">Lihat snapshot</a>:'Tidak tersedia'}</td></tr>;})}</tbody></table></div>}
    {summary&&!crossings.length&&<p className="hint">Rekaman ini tidak memiliki crossing orang yang dapat diimpor.</p>}
    <button className="button button--primary" type="submit" disabled={!job||!selected.length}>Sahkan crossing terpilih</button>
   </fieldset></form>
  </section>}
  {role==='admin'&&<details><summary>Catat absensi yang sudah diverifikasi</summary><form onSubmit={event=>{event.preventDefault();void run(async()=>{await api('/api/ledger/attendance',post({subject_id:subject,source_kind:sourceKind,source_id:sourceId,occurred_at:occurredAt,action,job_id:track?job:null,track_id:track?Number(track):null}));await refresh();setSourceId('');setStatus('Absensi terverifikasi dicatat, tanpa inferensi biometrik.');});}}><fieldset disabled={busy}>
   <div className="ngram-inline"><label>ID subjek terverifikasi<input required minLength={1} maxLength={80} pattern="[A-Za-z0-9][A-Za-z0-9_.-]*" value={subject} onChange={event=>setSubject(event.target.value)}/></label><label>Jenis sumber<select value={sourceKind} onChange={event=>setSourceKind(event.target.value)}><option value="manual">Verifikasi manual</option><option value="badge">Badge, diperiksa manual</option><option value="qr">QR, diperiksa manual</option></select></label></div>
   <label>ID bukti sumber, unik untuk kejadian<input required maxLength={120} pattern="[A-Za-z0-9][A-Za-z0-9_.:-]*" value={sourceId} onChange={event=>setSourceId(event.target.value)}/></label>
   <div className="ngram-inline"><label>Waktu absensi, termasuk zona waktu<input required maxLength={80} placeholder="2026-10-10T08:00:00+07:00" value={occurredAt} onChange={event=>setOccurredAt(event.target.value)}/></label><label>Tindakan<select value={action} onChange={event=>setAction(event.target.value)}><option value="arrived">Datang</option><option value="departed">Pulang</option></select></label></div>
   <label>Relasi track opsional dari rekaman terpilih<select value={track} onChange={event=>setTrack(event.target.value)}><option value="">Tanpa relasi track</option>{people.map(item=><option key={item.id} value={item.id}>Track {item.id}</option>)}</select></label><p className="hint">Relasi memerlukan bukti manual yang cocok. Track ID sendiri tidak mengungkap identitas.</p>
   <button className="button button--primary" type="submit">Simpan absensi terverifikasi</button>
  </fieldset></form></details>}
  {!reviewer&&role&&<p className="hint">Viewer melihat observasi dan agregat absensi. Peninjauan crossing membutuhkan reviewer; identitas absensi hanya tersedia bagi administrator.</p>}
  <div className="ngram-table"><table><caption>Catatan ledger, {rows.length} tersedia; menampilkan maksimal 200 terbaru.</caption><thead><tr><th>Waktu</th><th>Kejadian</th><th>Track / subjek</th><th>Status & bukti</th><th>Penarikan</th></tr></thead><tbody>{rows.slice(-200).reverse().map(row=><tr key={row.id}><td><time dateTime={row.occurred_at}>{row.occurred_at}</time></td><td>{row.symbol}</td><td>{row.category==='attendance'?row.payload.subject_id:`Track ${row.track_id??'unknown'}`}</td><td>{row.status}{row.payload.evidence&&/^\/api\/jobs\/[a-f0-9-]+\/media\/evidence_\d+\.jpg$/.test(row.payload.evidence)&&<> · <a href={row.payload.evidence} target="_blank" rel="noreferrer">Snapshot</a></>}{row.reason&&<small>{row.reason}</small>}</td><td>{reviewer&&row.status!=='retracted'&&(row.category!=='attendance'||role==='admin')?<details><summary>Tarik catatan</summary><form onSubmit={event=>{event.preventDefault();const data=new FormData(event.currentTarget),reason=String(data.get('reason')||'');void run(async()=>{await api(`/api/ledger/events/${encodeURIComponent(row.id)}/retract`,post({reason}));await refresh();setStatus('Catatan ditarik; riwayat tetap tersimpan.');});}}><label>Alasan penarikan<input name="reason" required maxLength={200} disabled={busy}/></label><button className="button button--tertiary button--sm" type="submit" disabled={busy}>Sahkan penarikan</button></form></details>:'—'}</td></tr>)}</tbody></table></div>
  {!rows.length&&facts&&<p className="hint">Belum ada observasi terverifikasi dalam workspace ini. Pilih crossing nyata untuk memulai.</p>}
  <details><summary>Novelty kejadian, laporan riset</summary><p className="hint">Skor urutan yang jarang bukan bukti bahaya atau pelanggaran. Hanya run tersimpan dalam workspace ini yang ditampilkan.</p>{novelty?.runs.length?novelty.runs.map(item=><section key={item.run_id}><h3>{item.run_id}</h3><pre>{JSON.stringify(item.summary,null,2)}</pre></section>):<p className="hint">Belum ada laporan novelty kejadian yang tersedia.</p>}{!!novelty?.errors.length&&<p className="error">Sebagian laporan tidak dapat diverifikasi: {JSON.stringify(novelty.errors)}</p>}</details>
  {facts?.limitations.map(value=><p className="hint" key={value}>{value}</p>)}
 </details>;
}
