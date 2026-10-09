'use strict';
const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
(async()=>{
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
 function node(id){return elements[id]??=(id==='passwordForm'?{reset(){for(const name of ['currentPassword','newPassword','confirmPassword'])node(name).value='';},reportValidity(){return true;}}:{value:'',textContent:'',disabled:false,setCustomValidity(value){this.validity=value;},reportValidity(){return !this.validity;},focus(){this.focused=true;},showModal(){this.open=true;},close(){this.open=false;listeners.close?.();},addEventListener(name,fn){listeners[name]=fn;}});}
 Object.assign(context,{el:node,HTMLDialogElement:function(){},HTMLFormElement:function(){},HTMLButtonElement:function(){},HTMLInputElement:function(){},HTMLElement:function(){}});
 const user={id:'fixture',username:'fixture',role:'admin',tenant_id:'local',tenant_name:'Local'};
 context.session={user,csrf_token:'old-token'};
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
 const pending=submit();assert.equal(node('passwordSubmit').disabled,true);await submit();assert.equal(pendingCalls,1,'double submit sends one request');
 resolveChange({status:200,ok:true,json:async()=>({user,csrf_token:'fresh-token'})});await pending;
 assert.equal(context.session.csrf_token,'fresh-token');assert.equal(node('currentPassword').value,'');assert.equal(node('confirmPassword').value,'');assert.match(node('passwordStatus').textContent,/Sesi lain/);
 context.nativeFetch=async(input,init)=>{calls.push({input,init});return {status:200};};await context.request('/api/jobs',{method:'POST'});assert.equal(calls.at(-1).init.headers.get('X-CSRF-Token'),'fresh-token');
  vm.runInContext(source.slice(source.indexOf('function renderProfile('),source.indexOf('function signedIn(')),context);
 let selectedView;context.setView=async view=>{selectedView=view;return true;};
 await elements.profileButton.onclick();assert.equal(selectedView,'profile');assert.equal(node('passwordStatus').textContent,'');assert.equal(node('profileTitle').focused,true);assert.equal(node('profileUsername').textContent,'fixture');assert.equal(node('profileWorkspace').textContent,'Local');assert.equal(node('profileRole').textContent,'Administrator');assert.equal(node('accountAvatar').textContent,'FI');assert.equal(node('accountIdentity').textContent,'fixture');
 node('profileTitle').focused=false;node('passwordStatus').textContent='kept';context.setView=async()=>false;await elements.profileButton.onclick();assert.equal(node('profileTitle').focused,false,'blocked navigation never focuses hidden profile');assert.equal(node('passwordStatus').textContent,'kept');
 node('newPassword').value='leftover';context.resetPasswordForm();assert.equal(node('newPassword').value,'');
 console.log('PASS: password rotation/confirmation/failure/pending/cleanup, session validation, CSRF, multipart headers, viewer mutation guard, allowed chat and expired sessions.');
})().catch(error=>{console.error(error);process.exitCode=1;});
