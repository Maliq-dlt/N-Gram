"use strict";
const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
const source=fs.readFileSync('dashboard.js','utf8');
function fixture(reduced=false){
 const nodes={},frames=new Map(),cancelled=[],listeners={},draws={dots:0,people:0};let next=0;
 const ctx={clearRect(){},beginPath(){},arc(){draws.dots++;},fill(){},drawImage(){draws.people++;}};
 const node=id=>nodes[id]??=(id.includes('Canvas')?{width:144,height:144,getContext(){return ctx;}}:{hidden:true,value:'system',setAttribute(k,v){this[k]=v;},focus(){this.focused=true;}});
 const media={matches:reduced,addEventListener(name,fn){listeners[name]=fn;}};
 const context={$:node,document:{documentElement:{dataset:{theme:'light'}}},matchMedia(){return media;},performance:{now(){return 100;}},requestAnimationFrame(fn){frames.set(++next,fn);return next;},cancelAnimationFrame(id){cancelled.push(id);frames.delete(id);},Image:class{constructor(){this.naturalWidth=1500;this.naturalHeight=700;context.image=this;}set src(value){this.url=value;}},location:{reload(){context.reloaded=true;}},localStorage:{getItem(){return 'system';},setItem(k,v){context.saved=v;}}};
 vm.createContext(context);vm.runInContext(source.slice(source.indexOf('let orbAnimId='),source.indexOf('let sending = false;')),context);
 return {context,node,frames,cancelled,draws,media,listeners};
}
(async()=>{
 for(const reduced of [false,true]){
  const f=fixture(reduced);f.context.startThinkingOrb();assert.equal(f.node('chatThinkingOrb').hidden,false);assert(f.draws.dots>200);assert.equal(f.frames.size,reduced?0:1);
  f.media.matches=true;f.listeners.change();assert.equal(f.frames.size,0,'motion change cancels orb loop');f.context.stopThinkingOrb();assert.equal(f.node('chatThinkingOrb').hidden,true);
  f.node('loginTransitionLoader').hidden=false;f.context.startLoginCrowd();f.context.image.onload();assert.equal(f.draws.people,12);assert.equal(f.frames.size,0,'reduced crowd renders one frame');f.context.stopLoginCrowd();
 }
 const moving=fixture();moving.node('loginTransitionLoader').hidden=false;moving.context.startLoginCrowd();moving.context.image.onload();assert.equal(moving.frames.size,1);moving.context.stopLoginCrowd();assert.equal(moving.frames.size,0);
 const late=fixture();late.node('loginTransitionLoader').hidden=false;late.context.startLoginCrowd();late.context.stopLoginCrowd();late.context.image.onload();assert.equal(late.draws.people,0,'stopped startup ignores late image even with visible error loader');assert.equal(late.frames.size,0);late.listeners.change();assert.equal(late.frames.size,0,'motion change cannot revive stopped crowd');
 const stale=fixture();stale.node('loginTransitionLoader').hidden=false;stale.context.startLoginCrowd();const oldImage=stale.context.image;stale.context.startLoginCrowd();oldImage.onload();assert.equal(stale.draws.people,0,'repeated start rejects stale image callback');stale.context.image.onload();assert.equal(stale.draws.people,12);assert.equal(stale.frames.size,1);stale.media.matches=true;stale.listeners.change();stale.context.image.onload();assert.equal(stale.frames.size,0,'active crowd switches to static reduced frame');stale.media.matches=false;stale.listeners.change();stale.context.image.onload();assert.equal(stale.frames.size,1,'active crowd resumes when reduced motion turns off');stale.context.stopLoginCrowd();assert.equal(stale.frames.size,0);
 const preference=fixture(true);preference.context.startThinkingOrb();assert.equal(preference.frames.size,0);preference.media.matches=false;preference.listeners.change();assert.equal(preference.frames.size,1,'static orb resumes when reduced motion turns off');preference.context.stopThinkingOrb();assert.equal(preference.frames.size,0);
 for(const fails of [false,true]){
  const f=fixture();let stopped=0,finished;
  Object.assign(f.context,{workspaceAuth:{ready:Promise.resolve(),finishLoading(error){finished=error||'success';}},startLoginCrowd(){},stopLoginCrowd(){stopped++;},api:async()=>{if(fails)throw Error('offline');return {vision_ready:true,chat_ready:true,device:'cpu'};},refreshTraining:async()=>{},refreshHistory:async()=>[],showError(){}});
  const boot=source.slice(source.lastIndexOf('(async () => {'));await vm.runInContext(boot,f.context);
  assert.equal(stopped,1);assert.equal(finished,fails?'Studio belum dapat dimuat. offline':'success');
 }
 for(const fails of [false,true]){
  const f=fixture();Object.assign(f.context,{sending:false,currentView:'analysis',generation:1,summary:null,history:[],syncControls(){},showError(){},addMessage(){},api:async()=>{if(fails)throw Error('chat failed');return {mode:'guide',answer:'Answer',evidence:[]};}});
  vm.runInContext(source.slice(source.indexOf("$('chatForm').onsubmit ="),source.indexOf("$('chatInput').addEventListener('keydown'")),f.context);
  f.node('chatInput').value='Question';await f.node('chatForm').onsubmit({preventDefault(){}});
  assert.equal(f.node('chatThinkingOrb').hidden,true);assert.equal(f.frames.size,0,'chat finally clears RAF on success and failure');assert.equal(f.node('sendChat').disabled,false);assert.equal(f.node('chatStatus').textContent,'');
 }
 const theme=fixture();vm.runInContext(source.slice(source.indexOf('const themeMedia='),source.indexOf("$('themeToggleBtn').onclick="))+source.slice(source.indexOf("$('themeToggleBtn').onclick="),source.indexOf('\n',source.indexOf("$('themeToggleBtn').onclick="))),theme.context);
 assert.equal(theme.context.document.documentElement.dataset.theme,'light');theme.node('themeToggleBtn').onclick();assert.equal(theme.context.document.documentElement.dataset.theme,'dark');assert.equal(theme.node('themeToggleBtn')['aria-checked'],'true');assert.equal(theme.context.saved,'dark');
 theme.node('themeSelect').value='system';theme.media.matches=true;theme.context.applyTheme();assert.equal(theme.context.document.documentElement.dataset.theme,'dark');theme.media.matches=false;theme.context.applyTheme();assert.equal(theme.context.document.documentElement.dataset.theme,'light');
 console.log('PASS: actual orb/crowd reduced motion and cleanup, startup success/error cleanup, theme switch/system state.');
})().catch(error=>{console.error(error);process.exitCode=1;});
