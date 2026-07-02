/* ===== MecaTeca — landing de pitch (timelines + logos de patamar) ===== */

/* ---- Contagem dos números do hero ---- */
function countUp(el){
  const target = parseFloat(el.dataset.count);
  const dec = target % 1 !== 0;
  let cur = 0;
  const step = target / 45;
  const tick = () => {
    cur += step;
    if (cur >= target){ el.textContent = dec ? target.toFixed(1).replace('.',',') : target; return; }
    el.textContent = dec ? cur.toFixed(1).replace('.',',') : Math.floor(cur);
    requestAnimationFrame(tick);
  };
  tick();
}

/* ---- Revelar ao scroll ---- */
const io = new IntersectionObserver((entries)=>{
  entries.forEach(e=>{
    if(e.isIntersecting){
      e.target.classList.add('reveal');
      e.target.querySelectorAll?.('.stat__num[data-count]').forEach(countUp);
      io.unobserve(e.target);
    }
  });
},{threshold:.15});
document.querySelectorAll('.section, .hero__stats, .table').forEach(s=>io.observe(s));

/* ---- Separadores das demos ---- */
document.querySelectorAll('.demo-tab').forEach(tab=>{
  tab.addEventListener('click',()=>{
    document.querySelectorAll('.demo-tab').forEach(t=>t.classList.remove('is-active'));
    document.querySelectorAll('.demo-panel').forEach(p=>p.classList.remove('is-active'));
    tab.classList.add('is-active');
    document.querySelector(`[data-panel="${tab.dataset.demo}"]`).classList.add('is-active');
  });
});

/* ===================================================================== */
/* LOGOS DE PATAMAR (SVG)                                                 */
/* ===================================================================== */
const TIER_DATA = {
  Bronze:  {c1:'#d79a5a', c2:'#8a5a28', pips:1},
  Silver:  {c1:'#eef1f6', c2:'#9aa0ac', pips:2},
  Gold:    {c1:'#f7da86', c2:'#c79a2f', pips:3},
  Diamond: {c1:'#cdecff', c2:'#7fb6e6', pips:4},
};
function rankBadge(tier, size=80){
  const d = TIER_DATA[tier];
  const id = 'g_'+tier;
  let pips = '';
  const n = d.pips, gap = 13, startX = 30 - (n-1)*gap/2;
  for(let i=0;i<n;i++){
    const x = startX + i*gap;
    pips += `<rect x="${x-4}" y="30" width="8" height="8" rx="1.5" transform="rotate(45 ${x} 34)" fill="#fff" opacity=".92"/>`;
  }
  return `<svg viewBox="0 0 60 74" width="${size}" height="${size*74/60}" class="badge-svg" aria-label="Rank ${tier}">
    <defs>
      <linearGradient id="${id}" x1="0" y1="0" x2="0" y2="1">
        <stop offset="0" stop-color="${d.c1}"/><stop offset="1" stop-color="${d.c2}"/>
      </linearGradient>
    </defs>
    <path d="M30 3 L55 13 V37 C55 56 30 70 30 70 C30 70 5 56 5 37 V13 Z"
      fill="url(#${id})" stroke="rgba(255,255,255,.55)" stroke-width="1.5"/>
    <path d="M30 3 L55 13 V37 C55 56 30 70 30 70" fill="rgba(0,0,0,.06)"/>
    <circle cx="30" cy="34" r="17" fill="none" stroke="#fff" stroke-opacity=".5" stroke-width="1"/>
    ${pips}
  </svg>`;
}

/* ===================================================================== */
/* MOTOR DE TIMELINE                                                     */
/* ===================================================================== */
const bubble = (who,txt)=>`<div class="tlmsg tlmsg--${who}"><div class="tlmsg__av">${who==='bot'?'✦':'🧑'}</div><div class="tlmsg__b">${txt}</div></div>`;

const TIMELINES = {
  /* ---- Tutor Socrático ---- */
  tutor:[
    {cap:'O aluno faz uma pergunta.',
     stage:bubble('user','Porque é que o céu é azul? Dá-me a resposta.')},
    {cap:'A IA recusa-se a entregar a resposta — devolve uma pergunta.',
     stage:bubble('user','Porque é que o céu é azul? Dá-me a resposta.')+bubble('bot','Não te dou a resposta — vamos lá pensar. A luz do Sol é uma mistura de cores. <strong>Quais achas que se dispersam mais na atmosfera: as curtas ou as longas?</strong>')},
    {cap:'O aluno arrisca um raciocínio.',
     stage:bubble('bot','Quais achas que se dispersam mais: as curtas ou as longas?')+bubble('user','Acho que as curtas… as azuis?')},
    {cap:'Feedback que confirma e aprofunda — constrói a compreensão.',
     stage:bubble('user','Acho que as curtas… as azuis?')+bubble('bot','Exato! 🎯 As curtas (azuis) dispersam-se mais — dispersão de Rayleigh. <strong>Agora, porque achas que fica vermelho ao pôr do sol?</strong>')},
    {cap:'Resultado: o aluno percebe, em vez de copiar.',
     stage:bubble('user','Porque a luz viaja mais e o azul gasta-se, sobra o vermelho.')+bubble('bot','Isso é compreensão real. Pronto para rank up. ✦')},
  ],

  /* ---- Ranked Ladder ---- */
  rank:[
    {tier:'Bronze', xp:8,  cap:'Começas em Bronze. Completas desafios e ganhas XP.'},
    {tier:'Silver', xp:34, cap:'XP acumula, streaks dão bónus. Rank up para Silver.'},
    {tier:'Gold',   xp:68, cap:'Atinges Gold → unlock do direito de marcar a avaliação.', unlock:true},
    {tier:'Diamond',xp:100,cap:'Diamond: domínio do tema. Os ranks são sempre gratuitos.'},
  ],

  /* ---- Gerador de Testes ---- */
  test:[
    {cap:'Escolhes o tema e a dificuldade.',
     stage:`<div class="tl-form"><span class="tl-field">Fotossíntese</span><span class="tl-field tl-field--sel">Médio</span><span class="tl-gen">Gerar teste ▸</span></div>`},
    {cap:'A IA gera perguntas focadas na compreensão, não na memória.',
     stage:`<div class="tl-card"><div class="tl-card__q">P1. Explica o mecanismo central da fotossíntese.</div></div><div class="tl-card"><div class="tl-card__q">P2. Compara fotossíntese com respiração celular. Diferença-chave?</div></div>`},
    {cap:'Mais perguntas, a apontar às tuas lacunas.',
     stage:`<div class="tl-card"><div class="tl-card__q">P3. Qual o erro comum sobre fotossíntese, e porque está errado?</div></div><div class="tl-card"><div class="tl-card__q">P4. Aplica-a para explicar porque as folhas são verdes.</div></div>`},
    {cap:'As abordagens-modelo revelam-se só depois de tentares.',
     stage:`<div class="tl-card"><div class="tl-card__q">P1. Explica o mecanismo central da fotossíntese.</div><div class="tl-card__a">✦ Luz + CO₂ + água → glicose + O₂, nos cloroplastos. Mostra a cadeia causa→efeito.</div></div>`},
  ],

  /* ---- Certificação Presencial (cena gráfica) ---- */
  cert:[
    {cap:'Avaliação presencial 1-on-1 agendada, a partir da rubrica do currículo.',
     speaker:null, checked:0},
    {cap:'O professor faz uma pergunta oral, cara a cara.',
     speaker:'teacher', active:0, checked:0},
    {cap:'O aluno responde ao vivo, em voz alta.',
     speaker:'student', active:1, checked:1},
    {cap:'O professor aprofunda com uma pergunta-sonda para distinguir compreensão de cópia.',
     speaker:'teacher', active:2, checked:2},
    {cap:'O professor decide a nota. Gold rank fica LOCKED como credencial verificável.',
     speaker:null, done:true, checked:4},
  ],
};

function renderRankStage(step){
  const pct = step.xp;
  const unlock = step.unlock ? `<div class="unlock">🏆 Gold atingido! Subir de rank é grátis — agora podes marcar a avaliação para <strong>fazer lock-in deste rank como credencial</strong>.</div>` : '';
  return `<div class="tl-rank">
    <div class="tl-rank__badge">${rankBadge(step.tier,96)}<div class="tl-rank__name t-${step.tier}">${step.tier}</div></div>
    <div class="tl-rank__bars">
      <div class="ladder__bar"><div class="ladder__fill" style="width:${pct}%"></div></div>
      <div class="tl-rank__tiers">
        ${Object.keys(TIER_DATA).map(t=>`<span class="${t===step.tier?'reached':''}">${rankBadge(t,26)}<small>${t}</small></span>`).join('')}
      </div>
      ${unlock}
    </div>
  </div>`;
}

const CERT_RUBRIC = ['Compreensão do conceito','Raciocínio próprio','Aplicação a novo caso','Explicação clara'];
function renderCertStage(step){
  const wave = `<div class="cwave ${step.speaker?'live':''}"><span></span><span></span><span></span><span></span><span></span></div>`;
  const person = (role,emoji,label)=>`<div class="person ${step.speaker===role?'active':''}">
      <div class="person__av">${emoji}</div><span class="person__lbl">${label}</span>
      ${step.speaker===role?'<span class="person__talk">a falar…</span>':''}</div>`;
  const done = step.done ? `<div class="cert-done">${rankBadge('Gold',64)}<div><div class="cert-done__lock">🔒 Gold rank LOCKED</div><div class="cert-done__sub">Credencial verificável emitida</div></div></div>` : '';
  const rubric = `<div class="cert-rubric">${CERT_RUBRIC.map((r,i)=>{
    const state = i<step.checked ? 'done' : (i===step.active ? 'now' : '');
    const mark = i<step.checked ? '✓' : (i===step.active ? '•' : '');
    return `<div class="rub ${state}"><span class="rub__box">${mark}</span>${r}</div>`;
  }).join('')}</div>`;
  return `<div class="cert-scene">
    <div class="cert-presencial">📍 Presencial · 1-on-1 · sem dispositivos</div>
    <div class="cert-people">
      ${person('teacher','🧑‍🏫','Professor')}
      ${wave}
      ${person('student','🧑‍🎓','Aluno')}
    </div>
    ${done}${rubric}
  </div>`;
}

class Timeline{
  constructor(root){
    this.root = root;
    this.key = root.dataset.tl;
    this.steps = TIMELINES[this.key];
    this.i = 0;
    this.playing = false;
    this.build();
    this.render();
  }
  build(){
    this.root.innerHTML = `
      <div class="tl-stage"></div>
      <div class="tl-cap"></div>
      <div class="tl-ctrl">
        <button class="tl-btn tl-prev" aria-label="Anterior">‹</button>
        <input class="tl-range" type="range" min="0" max="${this.steps.length-1}" value="0" />
        <button class="tl-btn tl-next" aria-label="Seguinte">›</button>
        <button class="tl-btn tl-play" aria-label="Reproduzir">▶</button>
      </div>
      <div class="tl-dots"></div>`;
    this.stage = this.root.querySelector('.tl-stage');
    this.cap   = this.root.querySelector('.tl-cap');
    this.range = this.root.querySelector('.tl-range');
    this.dots  = this.root.querySelector('.tl-dots');
    this.playBtn = this.root.querySelector('.tl-play');

    this.dots.innerHTML = this.steps.map((_,i)=>`<button class="tl-dot" data-i="${i}"></button>`).join('');
    this.range.addEventListener('input',()=>this.go(+this.range.value,false));
    this.root.querySelector('.tl-prev').addEventListener('click',()=>{this.stop();this.go(this.i-1);});
    this.root.querySelector('.tl-next').addEventListener('click',()=>{this.stop();this.go(this.i+1);});
    this.dots.querySelectorAll('.tl-dot').forEach(d=>d.addEventListener('click',()=>{this.stop();this.go(+d.dataset.i);}));
    this.playBtn.addEventListener('click',()=>this.toggle());
  }
  go(i,moveRange=true){
    this.i = Math.max(0, Math.min(this.steps.length-1, i));
    if(moveRange) this.range.value = this.i;
    this.render();
  }
  render(){
    const step = this.steps[this.i];
    this.stage.innerHTML = this.key==='rank' ? renderRankStage(step)
      : this.key==='cert' ? renderCertStage(step)
      : step.stage;
    this.stage.classList.remove('flash'); void this.stage.offsetWidth; this.stage.classList.add('flash');
    this.cap.innerHTML = `<span class="tl-step">Passo ${this.i+1}/${this.steps.length}</span> ${step.cap}`;
    this.dots.querySelectorAll('.tl-dot').forEach((d,i)=>d.classList.toggle('on', i<=this.i));
  }
  toggle(){ this.playing ? this.stop() : this.play(); }
  play(){
    this.playing = true; this.playBtn.textContent='❚❚';
    if(this.i>=this.steps.length-1) this.go(0);
    this.timer = setInterval(()=>{
      if(this.i>=this.steps.length-1){ this.stop(); return; }
      this.go(this.i+1);
    }, 1900);
  }
  stop(){ this.playing=false; this.playBtn.textContent='▶'; clearInterval(this.timer); }
}
document.querySelectorAll('.timeline').forEach(el=>new Timeline(el));

/* ===================================================================== */
/* CALCULADORA DE LUCRO                                                  */
/* ===================================================================== */
(function(){
  const calc = document.querySelector('.calc');
  if(!calc) return;

  // constantes do modelo
  const FREE_COST = 0.90;      // custo IA por aluno grátis
  const PRO_REV   = 12.99;
  const PRO_COST  = 9.70;      // IA + pagamento + infra
  const PROC      = 0.03;      // processamento s/ taxas cobradas

  const fields = [...calc.querySelectorAll('.calc-field')];
  const val = id => +document.getElementById(id).value;
  const nf  = n => Math.round(n).toLocaleString('pt-PT');
  const eur = n => (n<0?'− ':'+ ') + Math.abs(Math.round(n)).toLocaleString('pt-PT') + ' €';

  const el = {};
  ['calcRevPro','calcRevEval','calcRev','calcCost','calcMargin','calcProfit','calcYear'].forEach(id=>el[id]=document.getElementById(id));

  function fmtOut(input){
    const v = +input.value, f = input.dataset.fmt;
    const o = input.closest('.calc-field').querySelector('output');
    o.textContent = f==='eur' ? nf(v)+' €' : f==='pct' ? v+' %' : nf(v);
  }

  function recompute(){
    fields.forEach(f=>fmtOut(f.querySelector('input')));
    const free=val('inFree'), pro=val('inPro');
    const evals=val('inEvals'), flatEval=val('inFlatEval');

    const revPro = pro*PRO_REV;
    const revEval = evals*flatEval;
    const rev = revPro + revEval;
    const cost = free*FREE_COST + pro*PRO_COST + revEval*PROC;
    const profit = rev - cost;

    el.calcRevPro.textContent  = nf(revPro)+' €';
    el.calcRevEval.textContent = nf(revEval)+' €';
    el.calcRev.textContent    = eur(rev);
    el.calcCost.textContent   = '− '+nf(cost)+' €';
    el.calcProfit.textContent = eur(profit);
    el.calcProfit.className    = 'calc-big__num '+(profit>=0?'pos':'neg');
    el.calcYear.textContent   = eur(profit*12)+' / ano';
    el.calcMargin.textContent = rev>0 ? Math.round(profit/rev*100)+'%' : '—';
    el.calcMargin.style.color = profit>=0 ? 'var(--green)' : 'var(--red)';
  }
  fields.forEach(f=>f.querySelector('input').addEventListener('input',recompute));
  recompute();
})();

/* ---- Formulário de contacto (simulado) ---- */
document.getElementById('contactForm').addEventListener('submit',e=>{
  e.preventDefault();
  const btn = e.target.querySelector('button');
  btn.textContent = '✓ Enviado — entraremos em contacto';
  btn.disabled = true;
});
