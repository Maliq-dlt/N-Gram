'use strict';
const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
(async()=>{
 for(const file of ['auth.ts','auth.js','tests/auth_check.cjs'])assert.doesNotThrow(()=>new TextDecoder('utf-8',{fatal:true}).decode(fs.readFileSync(file)),`${file} must be valid UTF-8`);
 const source=require('typescript').transpileModule(fs.readFileSync('auth.ts','utf8'),{compilerOptions:{target:require('typescript').ScriptTarget.ES2020}}).outputText,calls=[];
 const context={Headers,Request,URL,session:{user:{role:'reviewer'},csrf_token:'session-token'},showLogin(){context.session=null;context.loginShown=true;},nativeFetch:async(input,init)=>{calls.push({input,init});return {status:200};}};
 vm.createContext(context);
 vm.runInContext(source.slice(source.indexOf('async function request('),source.indexOf('async function readSession(')),context);
 await context.request('/api/jobs',{method:'POST',body:'multipart-body'});assert.equal(calls[0].init.headers.get('X-CSRF-Token'),'session-token');assert.equal(calls[0].init.headers.get('Content-Type'),null);assert.equal(calls[0].init.credentials,'same-origin');
 await context.request('/api/jobs');assert.equal(calls[1].init.headers.has('X-CSRF-Token'),false);
 context.session.user.role='viewer';await assert.rejects(context.request('/api/jobs',{method:'POST'}),/viewer/);await context.request('/api/chat',{method:'POST'});
 context.nativeFetch=async()=>({status:401});await context.request('/api/jobs');assert.equal(context.loginShown,true);await assert.rejects(context.request('/api/jobs',{method:'POST'}),/masuk kembali/);
 vm.runInContext(source.slice(source.indexOf('async function readSession('),source.indexOf('function signedIn(')),context);
 await assert.rejects(context.readSession({ok:true,json:async()=>({user:{role:'admin'},csrf_token:'token'})}),/akun tidak valid/);
 await assert.rejects(context.readSession({ok:true,json:async()=>({user:{role:'superadmin'},csrf_token:'token'})}),/sesi tidak valid/);
 // Viewer role must disable correction export even when syncControls enabled its radio.
 const roleNodes={resultCorrections:{disabled:false},resultAi:{disabled:false}};
 class RoleButton {}
 class RoleInput {}
 Object.setPrototypeOf(roleNodes.resultCorrections,RoleInput.prototype);Object.setPrototypeOf(roleNodes.resultAi,RoleInput.prototype);
 context.session={user:{role:'viewer'},csrf_token:'viewer-token'};
 Object.assign(context,{HTMLButtonElement:RoleButton,HTMLInputElement:RoleInput,HTMLFieldSetElement:function(){},document:{getElementById:id=>roleNodes[id]||null,querySelectorAll:()=>[]}});
 vm.runInContext(source.slice(source.indexOf('function applyRole('),source.indexOf('async function request(')),context);
 context.applyRole();assert.equal(roleNodes.resultCorrections.disabled,true);assert.equal(roleNodes.resultAi.disabled,false,'AI media switch remains accessible');
 // Exercise the actual password form handlers against an isolated DOM/API fixture.
 const elements={},listeners={};
 function node(id){return elements[id]??=(id==='passwordForm'?{reset(){for(const name of ['currentPassword','newPassword','confirmPassword'])node(name).value='';},reportValidity(){return true;}}:{value:'',textContent:'',disabled:false,style:{},classList:{toggle(){}},setAttribute(k){if(k==='disabled')this.disabled=true;},removeAttribute(k){if(k==='disabled')this.disabled=false;},setCustomValidity(value){this.validity=value;},reportValidity(){return !this.validity;},focus(){this.focused=true;},showModal(){this.open=true;},close(){this.open=false;listeners.close?.();},addEventListener(name,fn){listeners[name]=fn;}});}
 Object.assign(context,{el:node,HTMLDialogElement:function(){},HTMLFormElement:function(){},HTMLButtonElement:function(){},HTMLInputElement:function(){},HTMLElement:function(){}});
 const user={id:'fixture',username:'fixture',role:'admin',tenant_id:'local',tenant_name:'Local',display_name:'fixture',avatar_url:null};
 context.session={user,csrf_token:'old-token'};context.updatePasswordMeter=value=>{context.meterValue=value;};
 vm.runInContext(source.slice(source.indexOf("el('logoutButton'"),source.indexOf('const passwordForm =')),context);
 context.nativeFetch=async()=>({status:500,ok:false});await node('logoutButton').onclick();assert.equal(node('authError').hidden,false);assert.match(node('authError').textContent,/Gagal keluar/);

 vm.runInContext(source.slice(source.indexOf('const passwordForm ='),source.indexOf('new MutationObserver')),context);
 const submit=()=>elements.passwordForm.onsubmit({preventDefault(){}});
 node('currentPassword').value='fixture-current';node('newPassword').value='fixture-new-password';node('confirmPassword').value='different';
 const before=calls.length;await submit();assert.equal(calls.length,before,'mismatch never reaches server');assert.match(node('passwordStatus').textContent,/tidak cocok/);
 node('confirmPassword').value=node('newPassword').value;
 context.nativeFetch=async(input,init)=>{calls.push({input,init});return {status:400,ok:false,json:async()=>({detail:'Password saat ini salah.'})};};
 await submit();assert.equal(context.session.csrf_token,'old-token','failure retains prior session');assert.equal(node('passwordSubmit').disabled,false);assert.match(node('passwordStatus').textContent,/salah/);
 let resolveChange,pendingCalls=0;context.nativeFetch=()=>{pendingCalls++;return new Promise(resolve=>{resolveChange=resolve;});};
 const pending=submit();assert.equal(node('passwordSubmit').disabled,true);assert.equal(node('saveNameBtn').disabled,true);assert.equal(node('avatarFileInput').disabled,true);await submit();assert.equal(pendingCalls,1,'double submit sends one request');
 resolveChange({status:200,ok:true,json:async()=>({user,csrf_token:'fresh-token'})});await pending;
 assert.equal(context.session.csrf_token,'fresh-token');assert.equal(node('currentPassword').value,'');assert.equal(node('confirmPassword').value,'');assert.match(node('passwordStatus').textContent,/Sesi lain/);
 context.nativeFetch=async(input,init)=>{calls.push({input,init});return {status:200};};await context.request('/api/jobs',{method:'POST'});assert.equal(calls.at(-1).init.headers.get('X-CSRF-Token'),'fresh-token');
  vm.runInContext(source.slice(source.indexOf('function renderProfile('),source.indexOf('function signedIn(')),context);
 let selectedView;context.setView=async view=>{selectedView=view;return true;};
 await elements.profileButton.onclick();assert.equal(selectedView,'profile');assert.equal(node('passwordStatus').textContent,'');assert.equal(node('profileTitle').focused,true);assert.equal(node('profileUsername').textContent,'fixture');assert.equal(node('profileWorkspace').textContent,'Local');assert.equal(node('profileRole').textContent,'Administrator');assert.equal(node('accountAvatar').textContent,'FI');assert.equal(node('accountIdentity').textContent,'fixture');
 node('profileTitle').focused=false;node('passwordStatus').textContent='kept';context.setView=async()=>false;await elements.profileButton.onclick();assert.equal(node('profileTitle').focused,false,'blocked navigation never focuses hidden profile');assert.equal(node('passwordStatus').textContent,'kept');
 node('newPassword').value='leftover';node('newPassword').type='text';context.resetPasswordForm();assert.equal(node('newPassword').value,'');assert.equal(node('newPassword').type,'password');
 assert.equal(context.meterValue,'','reset updates strength meter');
 // Run real server-backed profile helper, including pending and failure behavior.
 vm.runInContext(source.slice(source.indexOf('async function saveProfile('),source.indexOf("el('newPassword'",source.indexOf('async function saveProfile('))),context);
 let resolveProfile,profileCalls=0;context.nativeFetch=()=>{profileCalls++;return new Promise(resolve=>{resolveProfile=resolve;});};
 const profileWait=context.saveProfile('/api/auth/profile',{method:'PATCH',body:'{}'},'nameSaveStatus','Saved');assert.equal(node('passwordSubmit').disabled,true);node('newPassword').value='fixture-next-password';node('confirmPassword').value='fixture-next-password';await submit();assert.equal(profileCalls,1,'password cannot overlap profile request');
 resolveProfile({status:200,ok:true,json:async()=>({user,csrf_token:'profile-pending-token'})});await profileWait;assert.equal(node('passwordSubmit').disabled,false);assert.equal(node('saveNameBtn').disabled,false);assert.equal(node('avatarFileInput').disabled,false);
 context.nativeFetch=()=>{pendingCalls++;return new Promise(resolve=>{resolveChange=resolve;});};const passwordWait=submit();const passwordCalls=pendingCalls;await context.saveProfile('/api/auth/profile',{method:'PATCH',body:'{}'},'nameSaveStatus','Saved');assert.equal(pendingCalls,passwordCalls,'profile cannot overlap password rotation');resolveChange({status:200,ok:true,json:async()=>({user,csrf_token:'rotation-after-profile'})});await passwordWait;assert.equal(node('passwordSubmit').disabled,false);assert.equal(node('removeAvatarBtn').disabled,false);
 context.nativeFetch=async(input,init)=>{calls.push({input,init});return {status:200,ok:true,json:async()=>({user:{...user,display_name:'Updated'},csrf_token:'profile-token'})};};
 await context.saveProfile('/api/auth/profile',{method:'PATCH',body:'{}'},'nameSaveStatus','Saved');
 assert.equal(context.session.user.display_name,'Updated');assert.equal(node('accountIdentity').textContent,'Updated');assert.equal(node('nameSaveStatus').textContent,'Saved');
 context.nativeFetch=async()=>({status:400,ok:false,json:async()=>({detail:'Invalid image'})});
 await context.saveProfile('/api/auth/avatar',{method:'PUT'},'avatarStatus','Saved');assert.match(node('avatarStatus').textContent,/Invalid image/);assert.equal(context.session.csrf_token,'profile-token');
 context.nativeFetch=async(input,init)=>{calls.push({input,init});assert.equal(init.method,'DELETE');assert.equal(init.body,'{}','delete request supplies middleware-required body');assert.equal(init.headers.get('Content-Type'),'application/json');return {status:200,ok:true,json:async()=>({user,csrf_token:'deleted-avatar-token'})};};
 vm.runInContext(source.slice(source.indexOf("el('removeAvatarBtn'"),source.indexOf("el('saveNameBtn'",source.indexOf("el('removeAvatarBtn'"))),context);
 listeners.click();await new Promise(resolve=>setImmediate(resolve));assert.equal(context.session.csrf_token,'deleted-avatar-token');assert.equal(calls.at(-1).input,'/api/auth/avatar');
 vm.runInContext(source.slice(source.indexOf('function signedIn('),source.indexOf('const ready =')),context);
 context.document.getElementById=id=>elements[id]||null;context.document.body={classList:{remove(value){context.removedClass=value;}}};
 context.session=null;context.entered=false;context.gate={hidden:false};context.signedIn({user,csrf_token:'load-token'});
 assert.equal(node('loginTransitionLoader').hidden,false);assert.equal(context.removedClass,undefined);elements.loginTransitionRetry=node('loginTransitionRetry');context.finishLoading('Cannot load');assert.equal(node('loginTransitionRetry').focused,true);assert.equal(node('loginTransitionLoader').hidden,false);assert.equal(node('loginTransitionStatus').textContent,'Cannot load');elements.workspaceTitle=node('workspaceTitle');context.finishLoading();assert.equal(node('workspaceTitle').focused,true);assert.equal(node('loginTransitionLoader').hidden,true);assert.equal(context.removedClass,'signed-out');
 delete elements.workspaceTitle;elements.mainContent=node('mainContent');context.finishLoading();assert.equal(node('mainContent').focused,true,'loading focus falls back to main');
 vm.runInContext(source.slice(source.indexOf('function evaluatePassword('),source.indexOf('let announcementTimer')),context);
 assert.equal(context.evaluatePassword('').score,0);assert.equal(context.evaluatePassword('passwordAb!123').score,1);assert.equal(context.evaluatePassword('Zebra!Moon7').score,3);assert.equal(context.evaluatePassword('Zebra!Moon728').score,4);
 const meterAttributes={},cells=Array.from({length:4},()=>({filled:false,classList:{add(){this.owner.filled=true;},remove(){this.owner.filled=false;}}}));for(const cell of cells)cell.classList.owner=cell;
 const label={textContent:''},common={hidden:true};context.window={clearTimeout(){},setTimeout(fn){fn();return 1;}};
 context.document.getElementById=id=>id==='passwordMeter'?{setAttribute(k,v){meterAttributes[k]=v;},querySelectorAll(){return cells;},querySelector(selector){return selector==='.password-meter-label'?label:common;}}:elements[id]||null;
 vm.runInContext(source.slice(source.indexOf('let announcementTimer'),source.indexOf('async function saveProfile(')),context);
 context.updatePasswordMeter('Zebra!Moon728');assert.equal(meterAttributes['aria-valuenow'],'4');assert.equal(meterAttributes['aria-valuemax'],'4');assert.equal(cells.filter(cell=>cell.filled).length,4);assert.match(node('passwordStrengthAnnouncement').textContent,/Sangat Kuat/);
 context.updatePasswordMeter('');assert.equal(meterAttributes['aria-valuenow'],'0');assert.equal(cells.filter(cell=>cell.filled).length,0);assert.equal(node('passwordStrengthAnnouncement').textContent,'');
 console.log('PASS: password rotation/confirmation/failure/pending/cleanup, session validation, CSRF, role guard, server profile success/failure, real loading lifecycle and accessible strength meter.');
})().catch(error=>{console.error(error);process.exitCode=1;});
