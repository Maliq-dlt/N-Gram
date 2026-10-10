'use strict';
const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
(async()=>{
 const source=fs.readFileSync('dashboard.js','utf8'),nodes={},events=[];
 const $=id=>nodes[id]??={hidden:false,disabled:false,dataset:{},setAttribute(){},removeAttribute(){},focus(){this.focused=true;}};
 const context={$,currentView:'annotation',previousWorkspaceView:'analysis',uploading:false,sending:false,reviewBusy:false,summary:{frames:100,fps:10},original:{currentTime:4.2},reviewVideo:{pause(){events.push('review-pause');}},workspaceAuth:{resetPasswordForm(){events.push('clear-secrets');}},document:{fullscreenElement:$('reviewPanel'),async exitFullscreen(){events.push('exit-fullscreen');this.fullscreenElement=null;},querySelectorAll(){return [];}},persistReview:async()=>{events.push('persist');return true;},cancelDrawing(){events.push('cancel-drawing');},pauseComparison(){events.push('pause-comparison');},stopReviewTracking:async()=>events.push('stop-tracking'),syncControls(){events.push('controls');},loadManualFrame:async frame=>events.push(['frame',frame]),showError(){events.push('error');}};
 vm.createContext(context);
 vm.runInContext(source.slice(source.indexOf('async function setView('),source.indexOf("for (const button of document.querySelectorAll('[data-view]'))\n    button.onclick")),context);
 vm.runInContext(source.slice(source.indexOf("$('openReview').onclick ="),source.indexOf("$('loadReviewFrame').onclick =")),context);
 assert.equal(await context.setView('profile'),true);assert.equal(context.currentView,'profile');assert.equal($('videoWorkspace').hidden,true);assert.equal($('profilePane').hidden,false);assert.equal($('pageTitle').textContent,'Profil');assert.equal(context.original.currentTime,4.2);assert.deepEqual(events.slice(0,4),['persist','exit-fullscreen','cancel-drawing','pause-comparison']);
 await $('profileBack').onclick();assert.equal($('profileButton').focused,true,'successful back restores visible profile trigger focus');assert.equal(context.currentView,'annotation');assert.equal($('profilePane').hidden,true);assert.ok(events.includes('clear-secrets'));assert.deepEqual(events.at(-1),['frame',42]);
 context.currentView='profile';$('profileButton').focused=false;context.reviewBusy=true;await $('profileBack').onclick();assert.equal($('profileButton').focused,false,'blocked return does not move focus');context.currentView='annotation';
 context.reviewBusy=true;const before=events.length;assert.equal(await context.setView('profile'),false);assert.equal(events.length,before);assert.equal(context.currentView,'annotation');context.reviewBusy=false;
 context.persistReview=async()=>false;assert.equal(await context.setView('profile'),false);assert.equal($('profilePane').hidden,true);context.persistReview=async()=>true;
 context.currentView='analysis';await $('openReview').onclick();assert.equal(context.currentView,'annotation');
 for(const value of ['split','tracking','original']){$('comparisonLayout').value=value;$('comparisonLayout').onchange();assert.equal($('compare').dataset.layout,value);}
 // Actual controller supplies edit/remove callbacks to the React box view.
 let boxRows,overlayRows;Object.assign(context,{studioViews:{boxes(rows){boxRows=rows;},overlay(rows){overlayRows=rows;}},reviewSvg:$('reviewSvg'),reviewBoxes:[{label:'person',bbox:[.1,.2,.5,.6],name:'Actual',color:null}],unsavedAdds:[],reviewBaseline:[],editBox:-1,dragStart:null,dragBox:null,pointerDown:false,secondClick:false,reviewReady:true,reviewDirty:false,manualNames:{person:'Orang'},automaticColor:()=> '#123456',syncMetadata(){}});
 $('reviewLabel').options=[{value:'person'}];
 vm.runInContext(source.slice(source.indexOf('function cancelDrawing('),source.indexOf('const reviewVideo =')),context);
 context.drawManualBoxes();assert.equal(overlayRows.length,1);assert.equal(boxRows.length,1);boxRows[0].edit();assert.equal(context.editBox,0);assert.equal($('boxX').value,'10.0000');assert.equal($('reviewLabel').focused,true);context.cancelInteraction();assert.equal(context.editBox,-1,'cancel interaction preserves the Escape/right-click edit reset');boxRows[0].remove();assert.equal(context.reviewBoxes.length,0);assert.equal(context.reviewDirty,true);assert.equal(boxRows.length,0);
 // Exercise compiled API trust boundaries independently of the DOM controller.
 vm.runInContext(source.slice(source.indexOf('function requireFields('),source.indexOf('async function api(')),context);
 assert.doesNotThrow(()=>context.validateApi('/api/health',{vision_ready:true,chat_ready:false,device:'cpu'}));
 assert.throws(()=>context.validateApi('/api/health',{vision_ready:'yes',chat_ready:false,device:'cpu'}),/vision_ready/);
 assert.throws(()=>context.validateApi('/api/jobs/job1/suggestions/0',{boxes:[{label:'person',bbox:[0,0,1,Infinity]}]}),/Koordinat/);
 assert.throws(()=>context.validateApi('/api/jobs/job1/tracking/id/step',{frames:[{frame_index:0,boxes:[]}],next_frame:'bad',ended:false}),/next_frame/);
 assert.doesNotThrow(()=>context.validateApi('/api/jobs/job1/annotations',{revision:1,frames:[{frame_index:0,boxes:[{label:'person',bbox:[0,0,.5,.5]}]}]}));
 console.log('PASS: guarded profile navigation, safe annotation persistence/fullscreen exit, timestamp/back, secret clearing and comparison layouts.');
})().catch(error=>{console.error(error);process.exitCode=1;});
