'use strict';
const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
const code=fs.readFileSync('dashboard.js','utf8');
class Media {
 constructor(){this.paused=true;this.ended=false;this.currentTime=0;this.duration=1;this.playbackRate=1;this.listeners={};this.pending=[];}
 addEventListener(event,handler){(this.listeners[event]??=[]).push(handler);}
 emit(event){for(const fn of this.listeners[event]||[])fn();}
 play(){this.paused=false;return new Promise((resolve,reject)=>this.pending.push({resolve,reject}));}
 pause(){this.paused=true;}
 getAttribute(){return 'video.mp4';}
}
(async()=>{
 const original=new Media(),tracked=new Media(),buttons={},errors=[];
 const context={original,tracked,currentView:'analysis',updateMoment(){},showError:(id,msg)=>msg && errors.push(msg),$:id=>buttons[id]??={},console};
 vm.createContext(context);
 vm.runInContext(code.slice(code.indexOf('let playbackEpoch='),code.indexOf('function addMessage')),context);
 // An old peer play is interrupted by leaving the panel. Its rejection arrives after a new play.
 original.paused=false;original.emit('play');
 original.pause();original.emit('pause');
 original.paused=false;original.emit('play');
 tracked.pending[0].reject(Object.assign(new Error('pause interrupted play'),{name:'AbortError'}));
 await new Promise(resolve=>setImmediate(resolve));
 assert.equal(original.paused,false,'stale AbortError must not pause new playback');
 assert.equal(errors.length,0,'intentional interruption must not show media error');
 // A queued pause from an old session must not interrupt current play.
 original.emit('pause');assert.equal(original.paused,false);
 // Genuine decoder failures still stop playback and reach the error UI.
 tracked.pending.at(-1).reject(Object.assign(new Error('codec unsupported'),{name:'NotSupportedError'}));
 await new Promise(resolve=>setImmediate(resolve));
 assert.equal(original.paused,true);assert.equal(errors.length,1);
 // Ended clips restart from zero rather than recursively replaying each other.
 original.ended=true;tracked.ended=true;original.currentTime=tracked.currentTime=1;
 buttons.playBoth.onclick();assert.equal(original.currentTime,0);assert.equal(tracked.currentTime,0);
 console.log('PASS: cancelled/stale playback, queued pause, real media failures and ended restart.');
})().catch(error=>{console.error(error);process.exitCode=1;});
