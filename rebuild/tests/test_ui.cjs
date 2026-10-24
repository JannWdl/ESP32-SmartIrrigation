const fs=require('fs'),path=require('path'),assert=require('assert');
const {JSDOM}=require('jsdom');
const ROOT=path.join(__dirname,'..');const html=fs.readFileSync(path.join(ROOT,'firmware/index.html'),'utf8');const script=html.match(/<script src="\/([^"]+)" defer><\/script>/)[1];
const dom=new JSDOM(html,{url:'http://192.168.178.59/',runScripts:'outside-only'});
const w=dom.window;w.structuredClone=structuredClone;w.TextEncoder=TextEncoder;
let hidden=false;Object.defineProperty(w.document,'hidden',{get:()=>hidden});
let next=0;const timers=new Map();w.setTimeout=(fn,ms)=>{timers.set(++next,{fn,ms});return next};w.clearTimeout=id=>timers.delete(id);
w.HTMLCanvasElement.prototype.getContext=()=>({});
const full={name:'Smart Irrigation',wifi:{ssid:'Test',password:'',ap_password:''},safety:{max_total_day_ml:400},channels:[{id:0,name:'Pflanze 1',threshold:35,portion_ml:10,max_day_ml:200}],tank:{},mqtt:{}};
const state={blocked:false,used_total_ml:10,budget_hours_remaining:20,uptime_seconds:60,version:'4.0.1',heap:40000,mqtt:{connected:true},active:null,tank:{safe:true,reason:'ok',percent:45,liters:null,distance_cm:7.7},channels:[{id:0,name:'Pflanze 1',auto:false,moisture:40,reason:'automatik_aus',fault:null,wait_seconds:0,used_ml:10}],events:[{t:1,message:'Test'}]};
const requests=[];
let releaseConfig;const configReady=new Promise(resolve=>{releaseConfig=resolve});
w.fetch=async (url,options)=>{
 assert(!options||options.method==='GET','UI test must not operate actuators');requests.push(url);
 let data;
 if(url.startsWith('/api/overview')){data=structuredClone(state);if(url.includes('config=1'))data.ui={channels:full.channels,safety:full.safety}}
 else if(url==='/api/config'){await configReady;data=full}
 else if(url==='/api/status')data=state;
 else if(url==='/api/history-view')data={history:[],events:state.events};
 else throw Error('unexpected request '+url);
 return {ok:true,json:async()=>structuredClone(data)};
};
const flush=()=>new Promise(resolve=>setImmediate(resolve));
(async()=>{
 w.eval(fs.readFileSync(path.join(ROOT,'firmware',script),'utf8')+'\n globalThis.uiTest={calibrationRuns,waitForCalibrationStop,bundleFileBytes};');
 await flush();await flush();
 assert.deepStrictEqual(requests,['/api/overview?config=1']);
 assert.equal(w.document.getElementById('connection').textContent,'ESP verbunden');
 assert.equal(w.document.getElementById('tank-percent').textContent,'45 %');
 assert(w.document.getElementById('channels').textContent.includes('10 ml gießen'));
 assert.equal([...timers.values()][0].ms,5000);
 w.document.querySelector('[data-page="setup"]').click();await flush();
 assert(w.document.getElementById('next').disabled);
 assert(w.document.getElementById('setup-form').textContent.includes('geladen'));
 releaseConfig();await flush();
 assert(!w.document.getElementById('next').disabled);
 assert.equal(requests.filter(x=>x==='/api/config').length,1);
 assert(w.document.getElementById('setup-form').textContent.includes('WLAN-Name'));
 w.document.querySelector('[data-page="dashboard"]').click();await flush();
 w.document.querySelector('[data-page="setup"]').click();await flush();
 assert.equal(requests.filter(x=>x==='/api/config').length,1);
 w.document.querySelector('[data-page="history"]').click();await flush();await flush();
 assert(requests.includes('/api/history-view'));
 assert(w.document.getElementById('history-events').textContent.includes('Test'));
 hidden=true;w.document.dispatchEvent(new w.Event('visibilitychange'));assert.equal(timers.size,0);
 const count=requests.length;await flush();assert.equal(requests.length,count);
 hidden=false;w.document.dispatchEvent(new w.Event('visibilitychange'));await flush();
 assert(requests.length>count);
 assert(!requests.slice(1).includes('/api/overview?config=1'));

 const binary=w.uiTest.bundleFileBytes({encoding:'base64',content:'AAH/'});assert.deepStrictEqual(Array.from(binary),[0,1,255]);
 assert.equal(new TextDecoder().decode(w.uiTest.bundleFileBytes({encoding:'utf8',content:'Grün'})),'Grün');
 async function calibrationCase(events,success){
  state.events=events;w.uiTest.calibrationRuns[0]={seconds:2,completed:false};
  const result=w.uiTest.waitForCalibrationStop(0,2).then(()=>null,e=>e);
  await flush();const timer=[...timers.entries()].find(([id,t])=>t.ms===500);assert(timer);timers.delete(timer[0]);timer[1].fn();await flush();
  const error=await result;if(success){assert(!error);assert(w.uiTest.calibrationRuns[0].completed)}else{assert(error);assert(error.message.includes('abgebrochen'))}
 }
 const start={id:0,kind:'water',t:1,message:'Start: 50 ml reserviert (calibration)'};
 const stop={id:0,kind:'water',t:3,message:'Stopp: fertig'};
 await calibrationCase([start,stop],true);
 await calibrationCase([start,{...stop,message:'Stopp: tank_wasserreserve'}],false);
 await calibrationCase([stop,start],false);
 dom.window.close();console.log('PASS: binary update decoding and completed/aborted/stale calibration evidence');console.log('PASS: overview renders from one request, setup loads on demand once, history loads on demand, hidden-tab polling stops and visible-tab polling resumes');
})().catch(e=>{console.error(e);process.exitCode=1;dom.window.close()});
