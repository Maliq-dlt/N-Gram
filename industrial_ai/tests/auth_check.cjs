'use strict';
const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
(async()=>{
 const source=fs.readFileSync('auth.js','utf8'),calls=[];
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
 console.log('PASS: session validation, CSRF, multipart headers, viewer mutation guard, allowed chat and expired sessions.');
})().catch(error=>{console.error(error);process.exitCode=1;});
