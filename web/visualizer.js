"use strict";
// AV3 VPU State-Space Visualizer | SPEC_AV3_ALPHA_OMEGA_03
// Modules: SquishEngine, GateFSM, VPUHeader, Renderer, UI

class SquishEngine {
    static W_N=0.4; static W_U=0.3; static W_R=0.3;
    static EPS_GUARD=1e-9; static EPS_CAP=0.9997;
    constructor(p=1){this.epsPower=p;}
    compute(n,u,r,err,fric,eps){
        eps=Math.min(eps,SquishEngine.EPS_CAP);
        const ep=Math.pow(eps,this.epsPower);
        const s=SquishEngine.W_N*n+SquishEngine.W_U*u+SquishEngine.W_R*r;
        const dr=(err/(s+SquishEngine.EPS_GUARD))+fric;
        const da=dr/(dr+ep);
        return{s_squish:s,d_ratio:dr,d_asymptotic:da,eps_effective:ep,singularity_safe:ep<1.0};
    }
}

const GATE=Object.freeze({STATIC_ANCHOR:0,QUADRATURE_0DEG:1,QUADRATURE_90DEG:2,SQUISH_RESET:3});
const GATE_NAMES=['STATIC_ANCHOR','QUADRATURE_0DEG','QUADRATURE_90DEG','SQUISH_RESET'];
const GATE_CLR=['#0369a1','#7c3aed','#0f766e','#dc2626'];

class GateFSM {
    constructor(){this.state=GATE.STATIC_ANCHOR;this.phaseSynced=true;this.observerCount=2;this.cycleCount=0;this.spf1Count=0;}
    tick(vol){
        this.cycleCount++;
        if(!this.phaseSynced&&vol){this.spf1Count++;this.state=GATE.STATIC_ANCHOR;return{spf1:true};}
        switch(this.state){
            case GATE.STATIC_ANCHOR:    this.state=GATE.QUADRATURE_0DEG; break;
            case GATE.QUADRATURE_0DEG:  this.state=vol?GATE.QUADRATURE_90DEG:GATE.STATIC_ANCHOR; break;
            case GATE.QUADRATURE_90DEG: this.state=GATE.SQUISH_RESET; break;
            case GATE.SQUISH_RESET:     this.state=GATE.STATIC_ANCHOR; break;
        }
        return{spf1:false};
    }
    get canCommit(){return this.observerCount>=2;}
}

class AV3Renderer {
    constructor(id){
        this.cv=document.getElementById(id);this.ctx=this.cv.getContext('2d');
        this.fsm=new GateFSM();this.squish=new SquishEngine(1);
        this.running=true;this.pace=0;this.epsilon=0.5;this.epsPow=1;
        this.history=[];this._tick=this._tick.bind(this);
        setInterval(this._tick,400);requestAnimationFrame(()=>this._loop());
    }
    _tick(){
        if(!this.running)return;
        const r=this.fsm.tick(document.getElementById('mode-toggle')?.checked??true);
        if(r.spf1)document.getElementById('tel-fb').textContent='ACTIVE (SPF-1)';
        else document.getElementById('tel-fb').textContent='CLEAR';
        const sq=this.squish.compute(0.5,0.3,0.2,1.0,0.05,this.epsilon);
        this.history.push(sq.d_asymptotic);
        if(this.history.length>120)this.history.shift();
        const set=(id,v)=>{const el=document.getElementById(id);if(el)el.textContent=v;};
        set('tel-gate',GATE_NAMES[this.fsm.state]);
        document.getElementById('tel-gate').style.color=GATE_CLR[this.fsm.state];
        set('tel-dasym',sq.d_asymptotic.toFixed(6));
        set('tel-ssquish',sq.s_squish.toFixed(4));
        set('tel-eps',`e=${this.epsilon.toFixed(3)} e^${this.epsPow}=${sq.eps_effective.toFixed(6)}`);
        set('tel-spf1',this.fsm.spf1Count>0?`TRIGGERED(${this.fsm.spf1Count}x)`:'CLEAR');
        set('tel-obs',`N=${this.fsm.observerCount} ${this.fsm.canCommit?'COMMIT-OK':'BLOCKED'}`);
        set('tel-cycle',this.fsm.cycleCount);
    }
    _loop(){if(!this.running)return;this.pace+=0.02;this._draw();requestAnimationFrame(()=>this._loop());}
    _draw(){
        const{cv,ctx}=this;const W=cv.width,H=cv.height;
        ctx.fillStyle='#03060a';ctx.fillRect(0,0,W,H);
        // Wave
        ctx.beginPath();ctx.strokeStyle='rgba(56,189,248,.18)';ctx.lineWidth=1.5;
        for(let x=0;x<W;x++){const y=28+Math.sin(x*.025+this.pace)*9+Math.sin(x*.05+this.pace*1.4)*4;x?ctx.lineTo(x,y):ctx.moveTo(x,y);}ctx.stroke();
        // Gate ring
        const cx=W*.22,cy=H*.42,R=68;
        const angles=[-Math.PI/2,0,Math.PI/2,Math.PI];
        const lbl=['00\nANCHOR','01\nQUAD0','10\nQUAD90','11\nRESET'];
        for(let i=0;i<4;i++){
            const a1=angles[i],a2=angles[(i+1)%4];
            const x1=cx+(R+4)*Math.cos(a1),y1=cy+(R+4)*Math.sin(a1);
            const x2=cx+(R+4)*Math.cos(a2),y2=cy+(R+4)*Math.sin(a2);
            ctx.beginPath();ctx.moveTo(x1,y1);ctx.lineTo(x2,y2);ctx.strokeStyle='rgba(71,85,105,.4)';ctx.lineWidth=1;ctx.stroke();
        }
        [0,1,2,3].forEach(g=>{
            const x=cx+R*Math.cos(angles[g]),y=cy+R*Math.sin(angles[g]);
            const act=g===this.fsm.state;
            ctx.beginPath();ctx.arc(x,y,act?18:13,0,Math.PI*2);
            ctx.fillStyle=act?GATE_CLR[g]+'33':'#0a0f18';ctx.strokeStyle=act?GATE_CLR[g]:'#334155';ctx.lineWidth=act?2:1;ctx.fill();ctx.stroke();
            lbl[g].split('\n').forEach((ln,li)=>{ctx.fillStyle=act?GATE_CLR[g]:'#64748b';ctx.font=`bold ${act?9:8}px monospace`;ctx.textAlign='center';ctx.fillText(ln,x,y-4+li*11);});
        });
        ctx.fillStyle='#94a3b8';ctx.font='8px monospace';ctx.textAlign='center';ctx.fillText('NPU GATE FSM',cx,cy-4);ctx.fillText('100ms cycle',cx,cy+8);
        // Eps chart
        const bx=W*.46,by=H*.12,bw=W*.5,bh=H*.35;
        ctx.fillStyle='#0a0f18';ctx.strokeStyle='#1e293b';ctx.lineWidth=1;ctx.fillRect(bx,by,bw,bh);ctx.strokeRect(bx,by,bw,bh);
        ctx.fillStyle='#475569';ctx.font='9px monospace';ctx.textAlign='left';ctx.fillText(`D_asym curve  e=${this.epsilon.toFixed(2)} p=${this.epsPow}`,bx+5,by+12);
        const ep=Math.pow(Math.min(this.epsilon,.9997),this.epsPow);
        ctx.beginPath();ctx.strokeStyle='#38bdf8';ctx.lineWidth=1.5;
        for(let px=0;px<bw;px++){const x=px/bw*5;const ya=x/(x+ep);ctx.lineTo(bx+px,by+bh-ya*bh*.82-8);}ctx.stroke();
        ctx.beginPath();ctx.strokeStyle='rgba(239,68,68,.5)';ctx.lineWidth=1;ctx.setLineDash([4,4]);
        const capY=by+bh-.9997*bh*.82-8;ctx.moveTo(bx,capY);ctx.lineTo(bx+bw,capY);ctx.stroke();ctx.setLineDash([]);
        ctx.fillStyle='#ef4444';ctx.font='8px monospace';ctx.fillText('e_cap=0.9997',bx+4,capY-3);
        ctx.beginPath();ctx.strokeStyle='rgba(52,211,153,.3)';ctx.lineWidth=1;ctx.setLineDash([3,6]);ctx.moveTo(bx,by+8);ctx.lineTo(bx+bw,by+8);ctx.stroke();ctx.setLineDash([]);
        ctx.fillStyle='#34d399';ctx.font='8px monospace';ctx.fillText('D_asym=1.0 (never reached)',bx+4,by+18);
        // History
        if(this.history.length>1){
            const hx=bx,hy=by+bh+8,hw=bw,hh=H*.28;
            ctx.fillStyle='#0a0f18';ctx.strokeStyle='#1e293b';ctx.lineWidth=1;ctx.fillRect(hx,hy,hw,hh);ctx.strokeRect(hx,hy,hw,hh);
            ctx.fillStyle='#475569';ctx.font='9px monospace';ctx.textAlign='left';ctx.fillText('D_asymptotic live history',hx+5,hy+12);
            ctx.beginPath();ctx.strokeStyle='#a855f7';ctx.lineWidth=1.5;
            this.history.forEach((v,i)=>{const x=hx+i/(this.history.length-1)*hw;const y=hy+hh-v*hh*.82-6;i?ctx.lineTo(x,y):ctx.moveTo(x,y);});ctx.stroke();
        }
        // Progress bar
        ctx.fillStyle='#0f172a';ctx.fillRect(W*.46,H-.1,W*.5,5);
        ctx.fillStyle='#0284c7';ctx.fillRect(W*.46,H-.1,(W*.5)*(this.fsm.cycleCount%100/100),5);
    }
}

let renderer;
function initVisualizer(){
    renderer=new AV3Renderer('av3-canvas');
    document.getElementById('btn-pause')?.addEventListener('click',()=>{renderer.running=!renderer.running;if(renderer.running)renderer._loop();});
    document.getElementById('btn-reset')?.addEventListener('click',()=>{renderer.fsm=new GateFSM();renderer.history=[];renderer.pace=0;});
    document.getElementById('btn-spf1')?.addEventListener('click',()=>{renderer.fsm.phaseSynced=false;setTimeout(()=>{renderer.fsm.phaseSynced=true;},1200);});
    document.getElementById('eps-slider')?.addEventListener('input',e=>{renderer.epsilon=parseFloat(e.target.value);});
    document.getElementById('eps-pow')?.addEventListener('change',e=>{renderer.epsPow=parseInt(e.target.value);renderer.squish=new SquishEngine(renderer.epsPow);});
    document.getElementById('obs-count')?.addEventListener('input',e=>{renderer.fsm.observerCount=parseInt(e.target.value);});
}
document.addEventListener('DOMContentLoaded',initVisualizer);
