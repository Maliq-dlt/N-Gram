'use strict';
const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
(async()=>{
 const source=fs.readFileSync('dashboard.js','utf8'),nodes={},events=[];
 const $=id=>nodes[id]??={hidden:false,disabled:false,dataset:{},setAttribute(){},removeAttribute(){},focus(){this.focused=true;}};
 const context={$,currentView:'annotation',previousWorkspaceView:'analysis',uploading:false,sending:false,reviewBusy:false,summary:{frames:100,fps:10},original:{currentTime:4.2},reviewVideo:{pause(){events.push('review-pause');}},workspaceAuth:{resetPasswordForm(){events.push('clear-secrets');}},document:{fullscreenElement:$('reviewPanel'),async exitFullscreen(){events.push('exit-fullscreen');this.fullscreenElement=null;},querySelectorAll(){return [];}},persistReview:async()=>{events.push('persist');return true;},cancelDrawing(){events.push('cancel-drawing');},pauseComparison(){events.push('pause-comparison');},stopReviewTracking:async()=>events.push('stop-tracking'),syncControls(){events.push('controls');},loadManualFrame:async frame=>events.push(['frame',frame]),showError(){events.push('error');}};
 vm.createContext(context);
 vm.runInContext(source.slice(source.indexOf('async function setView('),source.indexOf("for(const button of document.querySelectorAll('[data-view]')) button.onclick")),context);
 vm.runInContext(source.slice(source.indexOf("$('openReview').onclick="),source.indexOf("$('loadReviewFrame').onclick=")),context);
 assert.equal(await context.setView('profile'),true);assert.equal(context.currentView,'profile');assert.equal($('videoWorkspace').hidden,true);assert.equal($('profilePane').hidden,false);assert.equal($('pageTitle').textContent,'Profil');assert.equal(context.original.currentTime,4.2);assert.deepEqual(events.slice(0,4),['persist','exit-fullscreen','cancel-drawing','pause-comparison']);
 await $('profileBack').onclick();assert.equal($('profileButton').focused,true,'successful back restores visible profile trigger focus');assert.equal(context.currentView,'annotation');assert.equal($('profilePane').hidden,true);assert.ok(events.includes('clear-secrets'));assert.deepEqual(events.at(-1),['frame',42]);
 context.currentView='profile';$('profileButton').focused=false;context.reviewBusy=true;await $('profileBack').onclick();assert.equal($('profileButton').focused,false,'blocked return does not move focus');context.currentView='annotation';
 context.reviewBusy=true;const before=events.length;assert.equal(await context.setView('profile'),false);assert.equal(events.length,before);assert.equal(context.currentView,'annotation');context.reviewBusy=false;
 context.persistReview=async()=>false;assert.equal(await context.setView('profile'),false);assert.equal($('profilePane').hidden,true);context.persistReview=async()=>true;
 context.currentView='analysis';await $('openReview').onclick();assert.equal(context.currentView,'annotation');
 for(const value of ['split','tracking','original']){$('comparisonLayout').value=value;$('comparisonLayout').onchange();assert.equal($('compare').dataset.layout,value);}
 console.log('PASS: guarded profile navigation, safe annotation persistence/fullscreen exit, timestamp/back, secret clearing and comparison layouts.');
})().catch(error=>{console.error(error);process.exitCode=1;});
