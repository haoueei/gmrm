(() => {
'use strict';
const root=document.getElementById('realtime-replay'), base=root.dataset.assets, cache=new Map(); let selection=0;
const $=id=>root.querySelector('#replay-'+id), v=$('video');let active,charts=[],loading=true,velocitySeries=[],velocityBounds=[];
$('joint').innerHTML=Array.from({length:7},(_,i)=>`<option value="${i}">J${i+1}</option>`).join('');
const extent=values=>[Math.min(...values),Math.max(...values)];
function padded(values){let [a,b]=extent(values),p=Math.max((b-a)*.1,.01);return [a-p,b+p]}
const metricBounds=[1.5483502570260343, 1.9865155432647057],errorMax=242.07884232992447,computeMax=0.523054500354192;
function number(x){return Math.abs(x)>=100?x.toFixed(0):Math.abs(x)>=10?x.toFixed(1):x.toFixed(2)}
function chart(id,series,bounds,range=[0,active.duration]){const el=$(id),H=id.startsWith('velocity')?170:150,W=el.clientWidth||540,L=47,R=16,T=10,B=32;el.setAttribute('viewBox',`0 0 ${W} ${H}`);
 const x=t=>L+(t-range[0])/(range[1]-range[0])*(W-L-R),y=z=>H-B-(z-bounds[0])/(bounds[1]-bounds[0])*(H-T-B);let s='';
 let ticks=Array.from({length:4},(_,k)=>bounds[0]+(bounds[1]-bounds[0])*k/3);
 if(id.startsWith('velocity'))ticks=[...ticks.filter(z=>Math.abs(z)>(bounds[1]-bounds[0])*.15),0].sort((a,b)=>a-b);
 for(const z of ticks){s+=`<line x1="${L}" x2="${W-R}" y1="${y(z)}" y2="${y(z)}" stroke="${z===0&&id.startsWith('velocity')?'#bbb':'#ececec'}"/><text x="${L-9}" y="${y(z)+4}" text-anchor="end">${z===0?'0':number(z)}</text>`}
 const detail=id==='velocity-detail',step=detail?(range[1]-range[0])/4:(W<420?1:.5);
 for(let t=range[0];t<=range[1]+1e-9;t+=step)s+=`<text x="${x(t)}" y="${H-17}" text-anchor="middle">${t.toFixed(detail?3:1)}</text>`;
 s+=`<text x="${(L+W-R)/2}" y="${H-1}" text-anchor="middle">Time [s]</text>`;
 if(id==='velocity')s+=`<rect class="window-band" x="${L}" y="${T}" width="0" height="${H-T-B}" fill="#eee"/>`;
 s+=`<defs><clipPath id="clip-${id}"><rect x="${L}" y="${T}" width="${W-L-R}" height="${H-T-B}"/></clipPath></defs>`;
 series.forEach((a,i)=>{s+=`<path clip-path="url(#clip-${id})" d="${a.map((p,j)=>(j?'L':'M')+x(p[0]).toFixed(2)+','+y(p[1]).toFixed(2)).join(' ')}" fill="none" stroke="${i?'#777':'#222'}" stroke-width="1.6" ${i?'stroke-dasharray="6 4"':''}/>`});
 s+=`<line class="cursor" x1="${L}" x2="${L}" y1="${T}" y2="${H-B}" stroke="#aaa" stroke-width="1"/>`;el.innerHTML=s;charts=charts.filter(c=>c.el!==el);charts.push({el,x});}
function render(){if(!active)return;charts=[];chart('metric',[active.metric],metricBounds);chart('position',[active.samples.map(p=>[p[0],p[1]])],[0,errorMax]);chart('compute',[active.timing],[0,computeMax]);
 const j=+$('joint').value;velocitySeries=[active.samples.map(p=>[p[0],p[2+j]]),active.samples.map(p=>[p[0],p[9+j]])];velocityBounds=padded([0,...velocitySeries.flatMap(a=>a.map(p=>p[1]))]);
 chart('velocity',velocitySeries,velocityBounds);drawDetail(interpolate(active.mapping,v.currentTime));update();}
function detailRange(t){const span=+$('window').value,start=Math.max(0,Math.min(t-span/2,active.duration-span));return [start,start+span]}
function drawDetail(t){const range=detailRange(t);const series=velocitySeries.map(a=>{let first=a.findIndex(p=>p[0]>=range[0]),last=a.findIndex(p=>p[0]>range[1]);return a.slice(Math.max(0,first-1),last<0?a.length:last+1)});
 const localBounds=padded([0,...series.flatMap(a=>a.map(p=>p[1]))]);
 chart('velocity-detail',series,localBounds,range);
 const full=charts.find(c=>c.el===$('velocity')),band=full.el.querySelector('.window-band');band.setAttribute('x',full.x(range[0]));band.setAttribute('width',full.x(range[1])-full.x(range[0]));}
function interpolate(pairs,t,input=0){let i=0,h=pairs.length;while(i<h){let m=(i+h)>>1;if(pairs[m][input]<=t)i=m+1;else h=m}i=Math.max(0,Math.min(pairs.length-2,i-1));let a=pairs[i],b=pairs[i+1],f=Math.max(0,Math.min(1,(t-a[input])/(b[input]-a[input])));return a[1-input]+f*(b[1-input]-a[1-input])}
function seek(t){v.currentTime=interpolate(active.mapping,t,1)}
function update(){if(!active)return;let t=interpolate(active.mapping,v.currentTime);if($('details').open)drawDetail(t);$('seek').value=t;$('time').textContent=`${t.toFixed(2)} / ${active.duration.toFixed(2)} s`;charts.forEach(c=>{let line=c.el.querySelector('.cursor');line.setAttribute('x1',c.x(t));line.setAttribute('x2',c.x(t))});if(!loading&&!v.paused&&v.currentTime>=active.mapping.at(-1)[0]){v.pause();seek(active.duration)}$('play').dataset.playing=String(!v.paused);$('play').title=v.paused?'Play':'Pause';$('play').setAttribute('aria-label',v.paused?'Play':'Pause')}
async function select(){
 const token=++selection; v.pause(); loading=true; $('error').hidden=true;
 const key=$('objective').value+'-'+$('trial').value;
 try {
  if(!cache.has(key)){const response=await fetch(base+key+'.json');if(!response.ok)throw new Error('Data could not be loaded. Please retry.');cache.set(key,await response.json());}
  if(token!==selection)return;
  active=cache.get(key); $('seek').max=active.duration; v.src=base+active.video; v.load(); render();
 } catch(e){if(token===selection){$('error').hidden=false;$('error').textContent=e.message;}}
}
v.onloadedmetadata=()=>{loading=false;v.playbackRate=+$('speed').value;seek(0)};v.ontimeupdate=update;v.onseeked=update;v.onpause=update;v.onplay=update;v.onerror=()=>{$('error').hidden=false;$('error').textContent='Video could not be loaded ('+(v.error?.message||'please retry')+').' };
$('play').onclick=()=>{if(loading)return;if(v.paused){if(v.currentTime>=active.mapping.at(-1)[0]-.01)seek(0);v.play().catch(e=>{$('error').hidden=false;$('error').textContent=e.message})}else v.pause()};$('restart').onclick=()=>{v.pause();seek(0)};$('seek').oninput=()=>seek(+$('seek').value);$('speed').onchange=()=>{v.playbackRate=+$('speed').value};$('objective').onchange=select;$('trial').onchange=select;$('joint').onchange=render;$('window').onchange=render;
$('details').ontoggle=render;window.addEventListener('resize',render);
function animate(){if(!v.paused)update();requestAnimationFrame(animate)}new IntersectionObserver((entries,observer)=>{if(entries.some(e=>e.isIntersecting)){select();observer.disconnect();}},{rootMargin:'200px'}).observe(root);requestAnimationFrame(animate);

})();
