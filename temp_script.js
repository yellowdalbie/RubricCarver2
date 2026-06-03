
let DATA = {};
let charts = {}; // To store chart instances

async function fetchData() {
    try {
        const res = await fetch('/api/data');
        DATA = await res.json();
        document.getElementById('gen-time').textContent = '생성: ' + DATA.generated_at;
        
        buildLive();
        buildOverview();
        buildDetail();
        buildBoundary();
        buildRubric();
        buildFI();
    } catch(e) {
        console.error("Failed to fetch data:", e);
    }
}

document.addEventListener('DOMContentLoaded', fetchData);



// ── 유틸 ─────────────────────────────────────────────────────────────────────
function showSection(name, btn) {
  document.querySelectorAll('.section').forEach(s=>s.classList.remove('active'));
  document.querySelectorAll('nav button').forEach(b=>b.classList.remove('active'));
  document.getElementById('sec-'+name).classList.add('active');
  if(btn) btn.classList.add('active');
}

function kappaBadge(k){
  if(k==null) return '<span style="color:var(--muted)">—</span>';
  const cls = k>=0.95?'k-high':k>=0.80?'k-mid':'k-low';
  return `<span class="kappa-badge ${cls}">${k.toFixed(3)}</span>`;
}

function decisionBadge(d){
  const map={APPROVED:'b-approved',REJECTED:'b-rejected',
    ANALYST_INVALID:'b-invalid',FAILED_ALL:'b-failed'};
  return `<span class="badge ${map[d]||'b-pending'}">${d||'진행중'}</span>`;
}

function pct(v){ return v!=null?Math.round(v*100)+'%':'—'; }

function accuracyColor(v){
  if(v==null) return 'var(--muted)';
  if(v>=0.85) return 'var(--green)';
  if(v>=0.70) return 'var(--yellow)';
  return 'var(--red)';
}

function closeModal(e){
  if(e.target===document.getElementById('modal'))
    document.getElementById('modal').style.display='none';
}

function switchTab(base, which, options){
  options.forEach(t=>{
    const tab = document.getElementById(`tab-${base}-${t}`);
    const pane = document.getElementById(`pane-${base}-${t}`);
    if(tab) tab.classList.toggle('active', t===which);
    if(pane) pane.style.display = t===which?'block':'none';
  });
}

// ── ① 실시간 진행 ────────────────────────────────────────────────────────────
function buildLive(){
  const live = DATA.live;
  const progress = live.progress || {};
  const cycle = live.current_cycle;

  // 진행 바
  let html = `<div class="grid4" style="margin-bottom:16px;">`;
  DATA.teachers.forEach(tid=>{
    const done = progress[tid] || 0;
    const total = DATA.students.length;
    const pctVal = Math.round(done/total*100);
    const statusColor = done===total?'var(--green)':done===0?'var(--muted)':'var(--yellow)';
    const statusLabel = done===total?'완료':done===0?'대기중':'채점중';
    html += `<div class="card">
      <div style="font-size:12px;font-weight:700;color:#fff;margin-bottom:4px;">${tid}</div>
      <div style="font-size:11px;color:var(--muted);margin-bottom:8px;">${DATA.teacher_labels[tid]}</div>
      <div class="progress-bar-label">
        <span style="color:${statusColor}">${statusLabel}</span>
        <span style="color:#fff;font-weight:700;">${done}/${total}</span>
      </div>
      <div class="progress-bar"><div class="progress-bar-fill" style="width:${pctVal}%"></div></div>
    </div>`;
  });
  html += `</div>`;

  if(cycle){
    html += `<div style="font-size:12px;color:var(--muted);margin-bottom:8px;">
      사이클 ${cycle} 진행 중 — ${new Date().toLocaleTimeString('ko-KR')} 기준
    </div>`;
  }

  document.getElementById('live-progress').innerHTML = html;

  // 학생 × 교사 그리드
  const grid = live.student_grid || {};
  const LEVEL_CLASS = {A:'sc-a',B:'sc-b',C:'sc-c',D:'sc-d',E:'sc-e',F:'sc-e',I:'sc-e'};

  let tableHtml = `<table class="sg-table">
    <thead><tr>
      <th style="text-align:left;">학생</th>`;
  DATA.teachers.forEach(t=>{ tableHtml += `<th>${t}</th>`; });
  tableHtml += `</tr></thead><tbody>`;

  DATA.students.forEach(sid=>{
    const sg = grid[sid] || {};
    tableHtml += `<tr><td style="text-align:left;font-weight:600;color:var(--text);">${sid}</td>`;
    DATA.teachers.forEach(tid=>{
      if(sg[tid]){
        const g = sg[tid];
        const lvl = (g.level||'?')[0];
        const cls = LEVEL_CLASS[lvl] || 'sc-c';
        const checklistText = Object.entries(g.checklist||{}).map(([code,ans])=>{
          const basis = (g.basis||{})[code]||'';
          return `${code}: ${ans}  ${basis?'→ '+basis.slice(0,60):''}`;
        }).join('\n');
        tableHtml += `<td>
          <div class="sg-cell ${cls}" onclick="showChecklist('${sid}', '${tid}')">
            <span style="font-size:13px;">${g.total}</span>
            <span style="font-size:9px;opacity:.8;">${g.level||'?'}</span>
          </div>
        </td>`;
      } else {
        tableHtml += `<td><div class="sg-cell sc-pending">…</div></td>`;
      }
    });
    tableHtml += `</tr>`;
  });
  tableHtml += `</tbody></table>`;

  document.getElementById('student-grid').innerHTML = tableHtml;
}

function showChecklist(sid, tid){
  const g = DATA.live.student_grid[sid][tid];
  document.getElementById('modal').style.display='flex';
  document.getElementById('modal-title').textContent = `${sid} × ${tid} — 총점 ${g.total}점 (${g.level})`;
  const checklist = g.checklist || {};
  const basis = g.basis || {};
  const codes = Object.keys(checklist);

  window._currentModalData = { codes, checklist, basis };

  let listHtml = codes.map((code, idx) => {
    const ans = checklist[code];
    const color = ans === 'YES' ? 'var(--green)' : 'var(--red)';
    return `<div id="modal-list-item-${idx}" onclick="selectChecklistItem(${idx})" 
                 style="padding:10px 12px; margin-bottom:6px; border-radius:6px; cursor:pointer; 
                        display:flex; justify-content:space-between; align-items:center; border:1px solid transparent;
                        background:var(--surface2); transition:all .15s;">
              <span style="font-weight:700; color:var(--text); font-size:12px;">${code}</span>
              <span style="font-weight:700; color:${color}; font-size:11px;">${ans}</span>
            </div>`;
  }).join('');

  let html = `
    <div style="display:flex; gap:20px; flex:1; overflow:hidden;">
      <div style="flex: 0 0 160px; overflow-y:auto; border-right:1px solid var(--border); padding-right:16px;">
        ${listHtml}
      </div>
      <div id="modal-detail-container" style="flex: 1; overflow-y:auto; padding-left:10px; padding-right:10px;">
        <div style="color:var(--muted); font-size:12px; margin-top:40px; text-align:center;">왼쪽 목록에서 기준을 선택하세요.</div>
      </div>
    </div>
  `;
  document.getElementById('modal-body').innerHTML = html;
  
  if(codes.length > 0) {
    selectChecklistItem(0);
  }
}

function selectChecklistItem(idx) {
  const data = window._currentModalData;
  const code = data.codes[idx];
  const ans = data.checklist[code];
  const b = data.basis[code] || '내용 없음';
  const color = ans === 'YES' ? 'var(--green)' : 'var(--red)';
  
  data.codes.forEach((c, i) => {
    const el = document.getElementById(`modal-list-item-${i}`);
    if(el) {
      el.style.borderColor = (i === idx) ? 'var(--accent)' : 'transparent';
      el.style.background = (i === idx) ? 'rgba(124,131,255,0.1)' : 'var(--surface2)';
    }
  });

  const detailHtml = `
    <div style="display:flex; align-items:center; gap:12px; margin-bottom:20px;">
      <div style="font-size:20px; font-weight:700; color:var(--accent);">${code}</div>
      <span style="display:inline-block; padding:4px 10px; border-radius:6px; font-weight:700; font-size:12px; 
                   background:rgba(${ans==='YES'?'74,222,128':'248,113,113'}, 0.1); color:${color};">
        ${ans}
      </span>
    </div>
    <div style="font-size:14px; font-weight:600; color:var(--text); margin-bottom:10px;">채점 근거</div>
    <div style="font-size:13px; line-height:1.7; color:var(--text); background:var(--surface2); padding:18px; border-radius:8px; white-space:pre-wrap;">${b}</div>
  `;
  document.getElementById('modal-detail-container').innerHTML = detailHtml;
}

// ── ② 사이클 개요 ────────────────────────────────────────────────────────────
function buildOverview(){
  const done = DATA.cycles.filter(c=>c.status==='done');
  if(!done.length){
    document.getElementById('overview-stats').innerHTML =
      '<div style="color:var(--muted);font-size:13px;">완료된 사이클 없음 — 첫 번째 사이클이 끝나면 여기에 표시됩니다.</div>';
    return;
  }

  const last = done[done.length-1];
  const gsa = last.gold_std || {};

  // 통계 카드
  document.getElementById('overview-stats').innerHTML = `
    <div class="stat"><div class="stat-val">${done.length}</div><div class="stat-lbl">완료 사이클</div></div>
    <div class="stat">
      <div class="stat-val" style="color:${accuracyColor(gsa.overall_accuracy)}">${pct(gsa.overall_accuracy)}</div>
      <div class="stat-lbl">최신 참조 표준 일치율</div>
    </div>
    <div class="stat">
      <div class="stat-val" style="color:${accuracyColor(gsa.boundary_accuracy)}">${pct(gsa.boundary_accuracy)}</div>
      <div class="stat-lbl">최신 경계케이스 일치율</div>
    </div>
    <div class="stat">
      <div class="stat-val">${last.kappa!=null?last.kappa.toFixed(3):'—'}</div>
      <div class="stat-lbl">최신 Fleiss κ</div>
    </div>
    <div class="stat">
      <div class="stat-val">${last.proc_count}:[절차] / ${last.conc_count}:[개념]</div>
      <div class="stat-lbl">최신 루브릭 구성</div>
    </div>
    <div class="stat">
      <div class="stat-val">${done.filter(c=>c.criteria_changed&&c.criteria_changed.length>0).length}</div>
      <div class="stat-lbl">루브릭 수정 사이클</div>
    </div>
  `;

  const labels = done.map(c=>`C${String(c.cycle).padStart(2,'0')}`);
  const chartOpts = (yLabel) => ({
    responsive:true, maintainAspectRatio:false,
    scales:{
      y:{grid:{color:'rgba(255,255,255,.05)'},ticks:{color:'#8892b0'},title:{display:true,text:yLabel,color:'#8892b0',font:{size:11}}},
      x:{grid:{color:'rgba(255,255,255,.05)'},ticks:{color:'#8892b0'}}
    },
    plugins:{legend:{labels:{color:'#e2e8f0',font:{size:11}}},
             tooltip:{backgroundColor:'#1a1d2e',borderColor:'#2e3155',borderWidth:1}}
  });

  
  // 참조 표준 일치율 차트
  if(charts['gold']) charts['gold'].destroy();
  charts['gold'] = new Chart(document.getElementById('chart-gold'),{

    type:'line',
    data:{labels, datasets:[
      {label:'전체 일치율',
       data:done.map(c=>c.gold_std&&c.gold_std.overall_accuracy!=null?Math.round(c.gold_std.overall_accuracy*100):null),
       borderColor:'#7c83ff',backgroundColor:'rgba(124,131,255,.15)',tension:.3,fill:true,pointRadius:4},
      {label:'경계케이스 일치율',
       data:done.map(c=>c.gold_std&&c.gold_std.boundary_accuracy!=null?Math.round(c.gold_std.boundary_accuracy*100):null),
       borderColor:'#f87171',backgroundColor:'rgba(248,113,113,.1)',tension:.3,fill:false,pointRadius:4,borderDash:[4,3]},
      {label:'[개념] 기준 일치율',
       data:done.map(c=>{const t=c.gold_std&&c.gold_std.tag_accuracy&&c.gold_std.tag_accuracy['개념'];return t?Math.round(t.accuracy*100):null;}),
       borderColor:'#4ade80',backgroundColor:'transparent',tension:.3,fill:false,pointRadius:4,borderDash:[2,2]},
    ]},
    options:{...chartOpts('일치율 (%)'),scales:{...chartOpts('%').scales,y:{...chartOpts('%').scales.y,min:0,max:100}}}
  });

  
  // κ 차트
  if(charts['kappa']) charts['kappa'].destroy();
  charts['kappa'] = new Chart(document.getElementById('chart-kappa'),{

    type:'line',
    data:{labels, datasets:[
      {label:'Fleiss κ (전체)',
       data:done.map(c=>c.kappa),
       borderColor:'#60a5fa',backgroundColor:'rgba(96,165,250,.15)',tension:.3,fill:true,pointRadius:4},
    ]},
    options:{...chartOpts('κ'),scales:{...chartOpts('κ').scales,y:{...chartOpts('κ').scales.y,min:0,max:1}}}
  });

  
  // [절차]/[개념] 태그 차트
  if(charts['tags']) charts['tags'].destroy();
  charts['tags'] = new Chart(document.getElementById('chart-tags'),{

    type:'bar',
    data:{labels:['초기',...labels], datasets:[
      {label:'[절차] 기준 수',data:[DATA.init_proc,...done.map(c=>c.proc_count)],backgroundColor:'rgba(96,165,250,.7)',borderRadius:3},
      {label:'[개념] 기준 수',data:[DATA.init_conc,...done.map(c=>c.conc_count)],backgroundColor:'rgba(74,222,128,.7)',borderRadius:3},
    ]},
    options:{...chartOpts('기준 수'),plugins:{...chartOpts().plugins},scales:{...chartOpts('기준 수').scales,y:{...chartOpts('기준 수').scales.y,min:0,max:10,stacked:false}}}
  });

  
  // 불일치 차트
  if(charts['dis']) charts['dis'].destroy();
  charts['dis'] = new Chart(document.getElementById('chart-dis'),{

    type:'bar',
    data:{labels, datasets:[
      {label:'불일치 쌍 수',data:done.map(c=>c.disagreements),backgroundColor:'rgba(251,191,36,.7)',borderRadius:3},
    ]},
    options:chartOpts('불일치 쌍 수')
  });

  // 요약 테이블
  let rows = done.map(c=>{
    const gsa = c.gold_std||{};
    const chg = (c.criteria_changed||[]).join(', ')||'—';
    const ptAcc = gsa.per_teacher_accuracy||{};
    return `<tr>
      <td><b>C${String(c.cycle).padStart(2,'0')}</b></td>
      <td>${kappaBadge(c.kappa)}</td>
      <td style="color:${accuracyColor(gsa.overall_accuracy)};font-weight:700;">${pct(gsa.overall_accuracy)}</td>
      <td style="color:${accuracyColor(gsa.boundary_accuracy)};">${pct(gsa.boundary_accuracy)}</td>
      <td>${c.disagreements}</td>
      <td style="font-size:11px;color:var(--accent);">${chg}</td>
      <td>${decisionBadge(c.auditor_decision)}</td>
      <td style="font-size:11px;">
        ${DATA.teachers.map(t=>`${t}:<span style="color:${accuracyColor(ptAcc[t])}">${ptAcc[t]!=null?Math.round(ptAcc[t]*100)+'%':'—'}</span>`).join(' ')}
      </td>
    </tr>`;
  }).join('');
  document.getElementById('overview-table').innerHTML = `
    <table><thead><tr>
      <th>사이클</th><th>κ</th><th>전체 일치율</th><th>경계케이스</th>
      <th>불일치</th><th>변경 기준</th><th>Auditor</th><th>교사별 일치율</th>
    </tr></thead><tbody>${rows}</tbody></table>`;
}

// ── ③ 사이클 상세 아코디언 ──────────────────────────────────────────────────
function buildDetail(){
  const container = document.getElementById('cycle-accordion');
  const done = DATA.cycles.filter(c=>c.status==='done');
  if(!done.length){
    container.innerHTML='<div style="color:var(--muted);font-size:13px;">완료된 사이클 없음</div>';
    return;
  }
  done.forEach(c=>{
    const gsa = c.gold_std||{};
    const chgBadges = (c.criteria_changed||[]).map(x=>
      `<span style="background:#1e2d5f;color:var(--blue);padding:1px 6px;border-radius:4px;font-size:10px;">${x}</span>`
    ).join('');

    const head = document.createElement('div');
    head.className='acc-head';
    head.innerHTML=`
      <span style="font-weight:700;color:#fff;min-width:80px;">Cycle ${String(c.cycle).padStart(2,'0')}</span>
      ${kappaBadge(c.kappa)}
      <span style="color:${accuracyColor(gsa.overall_accuracy)};font-weight:700;font-size:12px;">
        일치율 ${pct(gsa.overall_accuracy)}</span>
      <span style="color:var(--muted);font-size:11px;">불일치 ${c.disagreements}건</span>
      ${chgBadges||'<span style="font-size:10px;color:var(--muted)">변경없음</span>'}
      ${decisionBadge(c.auditor_decision)}
      <span style="margin-left:auto;color:var(--muted);">▾</span>`;

    const body = document.createElement('div');
    body.className='acc-body';

    // 기준별 κ
    const kappaByHtml = DATA.criterion_codes.map(code=>{
      const k = c.kappa_by&&c.kappa_by[code]!=null?c.kappa_by[code]:null;
      const pctV = k!==null?Math.min(100,Math.max(0,(k+1)/2*100)):0;
      const col = k>=0.95?'var(--green)':k>=0.80?'var(--yellow)':'var(--red)';
      return `<div class="kbar-wrap">
        <div class="kbar-label"><span>${code}</span><span>${k!==null?k.toFixed(3):'—'}</span></div>
        <div class="kbar"><div class="kbar-fill" style="width:${pctV}%;background:${col}"></div></div>
      </div>`;
    }).join('');

    // 참조 표준 상세
    const gsHtml = (function(){
      const gsa = c.gold_std||{};
      const ks = gsa.key_students||{};
      let h = `<div class="grid2" style="gap:8px;">`;
      ['B2','C3'].forEach(sid=>{
        const ks_data = ks[sid];
        if(!ks_data){ h+=`<div style="color:var(--muted);font-size:11px;">${sid} 데이터 없음</div>`; return; }
        h+=`<div>
          <div style="font-weight:700;color:var(--accent);font-size:12px;margin-bottom:4px;">${sid}</div>
          <div style="font-size:11px;color:var(--green);">✓ ${(ks_data.correct_criteria||[]).join(', ')||'없음'}</div>
          <div style="font-size:11px;color:var(--red);">✗ ${(ks_data.wrong_criteria||[]).join(', ')||'없음'}</div>
          <div style="font-size:11px;color:var(--muted);">일치율: ${pct(ks_data.accuracy)}</div>
        </div>`;
      });
      h+=`</div>`;
      const ta = gsa.tag_accuracy||{};
      h+=`<div style="margin-top:8px;font-size:11px;display:flex;gap:12px;flex-wrap:wrap;">
        <span>[절차] 기준 일치율: <b style="color:${accuracyColor(ta['절차']&&ta['절차'].accuracy)}">${ta['절차']?pct(ta['절차'].accuracy):'—'}</b></span>
        <span>[개념] 기준 일치율: <b style="color:${accuracyColor(ta['개념']&&ta['개념'].accuracy)}">${ta['개념']?pct(ta['개념'].accuracy):'—'}</b></span>
        <span>분할(SPLIT): <b>${gsa.split_count||0}건</b></span>
      </div>`;
      return h;
    })();

    // Analyst / Auditor 이력
    let auditHtml = '';
    if(c.audit_history&&c.audit_history.length){
      auditHtml = c.audit_history.map(a=>{
        const base=`c${c.cycle}r${a.revision}`;
        const aEsc=(a.analyst_text||'').replace(/</g,'&lt;').replace(/>/g,'&gt;');
        const uEsc=(a.auditor_text||'').replace(/</g,'&lt;').replace(/>/g,'&gt;');
        return `<div style="margin-bottom:10px;padding:10px;background:var(--surface2);border-radius:6px;">
          <div style="display:flex;gap:8px;align-items:center;margin-bottom:8px;">
            <span style="font-size:11px;color:var(--muted);">Revision ${a.revision}</span>
            ${decisionBadge(a.status)}
          </div>
          <div class="tabs">
            <div class="tab active" id="tab-${base}-analyst" onclick="switchTab('${base}','analyst',['analyst','auditor'])">분석관 문건</div>
            <div class="tab" id="tab-${base}-auditor" onclick="switchTab('${base}','auditor',['analyst','auditor'])">심의관 검토</div>
          </div>
          <div id="pane-${base}-analyst" class="excerpt">${aEsc||'<span style="color:var(--muted)">없음</span>'}</div>
          <div id="pane-${base}-auditor" class="excerpt" style="display:none;">${uEsc||'<span style="color:var(--muted)">없음</span>'}</div>
        </div>`;
      }).join('');
    }

    // Diff
    let diffHtml = '';
    if(c.diff_items&&c.diff_items.length){
      diffHtml = c.diff_items.map(d=>`
        <div style="margin-bottom:10px;padding:8px;background:var(--surface2);border-radius:6px;">
          <div class="diff-code">${d.code}</div>
          <div class="diff-old">이전: ${d.old}</div>
          <div class="diff-new">이후: ${d.new}</div>
        </div>`).join('');
    }

    body.innerHTML = `
      <div class="grid3" style="margin-bottom:14px;">
        <div><h3>기준별 Fleiss κ</h3>${kappaByHtml}</div>
        <div><h3>참조 표준 상세</h3>${gsHtml}</div>
        <div>
          <h3>루브릭 태그 구성</h3>
          <div style="margin-bottom:4px;font-size:11px;color:var(--muted);">[절차] ${c.proc_count} / [개념] ${c.conc_count}</div>
          <div class="tag-bar">
            <div class="tag-proc" style="width:${c.proc_count*10}%">[절차]×${c.proc_count}</div>
            <div class="tag-conc" style="width:${c.conc_count*10}%">[개념]×${c.conc_count}</div>
          </div>
        </div>
      </div>
      ${auditHtml?`<div style="margin-bottom:14px;"><h3>Auditor 심의 이력</h3>${auditHtml}</div>`:''}
      ${diffHtml?`<div><h3>루브릭 변경 내역</h3>${diffHtml}</div>`:''}
    `;

    head.onclick=()=>{
      const isOpen=body.classList.contains('open');
      document.querySelectorAll('#cycle-accordion .acc-body').forEach(b=>b.classList.remove('open'));
      if(!isOpen) body.classList.add('open');
    };

    const wrap=document.createElement('div');
    wrap.className='accordion';
    wrap.appendChild(head);
    wrap.appendChild(body);
    container.appendChild(wrap);
  });
}

// ── ④ 경계 케이스 ────────────────────────────────────────────────────────────
function buildBoundary(){
  const done = DATA.cycles.filter(c=>c.status==='done');
  const bm = DATA.boundary_meta;
  let html = '';

  // B2 / C3 그룹별로 묶어서 표시
  const groups = {B2:[], C3:[]};
  DATA.boundary_cases.forEach(key=>{
    const [sid] = key.split('_');
    if(groups[sid]) groups[sid].push(key);
  });

  Object.entries(groups).forEach(([sid, keys])=>{
    const gsRow = DATA.gold_standard[sid]||{};
    html += `<div class="card" style="margin-bottom:16px;">
      <div style="font-size:15px;font-weight:700;color:#fff;margin-bottom:4px;">${sid}</div>
      <div style="font-size:12px;color:var(--muted);margin-bottom:12px;">${
        sid==='B2'?'수식 없는 서술 답안 — 참조 표준 전 기준 YES (T1/T2의 NO 판정이 경계)':
        '자기 수정 답안 — 참조 표준 전 기준 YES (T2의 연쇄 NO가 경계)'
      }</div>
      <div style="overflow-x:auto;"><table style="min-width:500px;">
        <thead><tr>
          <th>기준</th><th>골드</th><th>분쟁유형</th>
          ${done.map(c=>`<th>C${String(c.cycle).padStart(2,'0')}</th>`).join('')}
          ${done.length?'':'<th style="color:var(--muted);">사이클 없음</th>'}
        </tr></thead><tbody>`;
    keys.forEach(key=>{
      const code = key.split('_').slice(1).join('_');
      const meta = bm[key]||{};
      const gsVal = gsRow[code]||'?';
      const dispType = meta.dispute_type||'?';
      html += `<tr>
        <td style="font-weight:700;color:var(--accent);">${code}</td>
        <td><span class="${gsVal==='YES'?'yes':'no'}">${gsVal}</span></td>
        <td><span class="dispute-badge ${dispType==='규범적'?'d-normative':'d-factual'}">${dispType}</span></td>`;
      done.forEach(c=>{
        const votes = (c.boundary||{})[key]||{};
        const yesN = Object.values(votes).filter(v=>v==='YES').length;
        const noN  = Object.values(votes).filter(v=>v==='NO').length;
        let cls='split', sym='⚡';
        if(yesN>=3){cls='correct';sym='✓';}
        else if(noN>=3){cls='wrong';sym='✗';}
        const tip = DATA.teachers.map(t=>`${t}:${votes[t]||'?'}`).join(' ');
        html += `<td title="${tip}" style="text-align:center;cursor:default;">
          <span class="${cls}" style="font-size:14px;">${sym}</span>
          <div style="font-size:9px;color:var(--muted);">${yesN}Y/${noN}N</div>
        </td>`;
      });
      if(!done.length) html+=`<td style="color:var(--muted);text-align:center;">—</td>`;
      html+=`</tr>`;
    });
    html+=`</tbody></table></div></div>`;
  });

  html += `<div style="font-size:12px;color:var(--muted);margin-top:4px;">
    ✓ = 다수결 YES (≥3표) &nbsp; ✗ = 다수결 NO (≥3표) &nbsp; ⚡ = 분할(2:2 또는 혼재)
  </div>`;

  document.getElementById('boundary-content').innerHTML = html;
}

// ── ⑤ 루브릭 진화 ────────────────────────────────────────────────────────────
function buildRubric(){
  const done = DATA.cycles.filter(c=>c.status==='done');
  if(!done.length){
    document.getElementById('rubric-content').innerHTML=
      '<div style="color:var(--muted);font-size:13px;">완료된 사이클 없음</div>';
    return;
  }
  let html = `<div class="card" style="margin-bottom:16px;">
    <h3>[절차] / [개념] 기준 구성 추이</h3>`;

  const allData = [{cycle:0, label:'초기', proc:DATA.init_proc, conc:DATA.init_conc},
    ...done.map(c=>({cycle:c.cycle, label:`C${String(c.cycle).padStart(2,'0')}`, proc:c.proc_count, conc:c.conc_count}))];

  allData.forEach(row=>{
    const total = row.proc + row.conc || 10;
    html+=`<div style="display:flex;align-items:center;gap:10px;margin-bottom:6px;">
      <span style="font-size:11px;color:var(--muted);min-width:36px;">${row.label}</span>
      <div class="tag-bar" style="flex:1;">
        <div class="tag-proc" style="width:${row.proc/total*100}%">[절차]×${row.proc}</div>
        <div class="tag-conc" style="width:${row.conc/total*100}%">[개념]×${row.conc}</div>
      </div>
    </div>`;
  });
  html += `</div>`;

  // 사이클별 변경 이력
  html += `<div class="card"><h3>사이클별 루브릭 변경 이력</h3>`;
  let anyChange = false;
  done.forEach(c=>{
    if(!c.diff_items||!c.diff_items.length) return;
    anyChange = true;
    html+=`<div style="margin-bottom:14px;">
      <div style="font-size:12px;font-weight:700;color:var(--accent);margin-bottom:6px;">
        Cycle ${String(c.cycle).padStart(2,'0')} — ${c.diff_items.length}개 기준 변경
      </div>`;
    c.diff_items.forEach(d=>{
      html+=`<div style="margin-bottom:8px;padding:8px;background:var(--surface2);border-radius:5px;">
        <div class="diff-code">${d.code}</div>
        <div class="diff-old">이전: ${d.old}</div>
        <div class="diff-new">이후: ${d.new}</div>
      </div>`;
    });
    html+=`</div>`;
  });
  if(!anyChange) html+=`<div style="color:var(--muted);font-size:13px;">아직 루브릭 변경 없음</div>`;
  html+=`</div>`;

  document.getElementById('rubric-content').innerHTML = html;
}

// ── ⑥ F/I 분석 ───────────────────────────────────────────────────────────────
function buildFI(){
  const FI = ['F1','F2','I1','I2'];
  const LABEL = {
    F1:'권위 호소형 Prompt Injection',
    F2:'기술적 조작형 Prompt Injection',
    I1:'풀이 없는 정답 나열',
    I2:'완전 무응답',
  };
  const live = DATA.live.student_grid||{};
  let html = '';

  FI.forEach(sid=>{
    const sg = live[sid]||{};
    const scores = DATA.teachers.map(t=>sg[t]?sg[t].total:null);
    const hasData = scores.some(s=>s!==null);
    const bypass = scores.some(s=>s>0);

    html+=`<div class="card" style="margin-bottom:16px;">
      <div style="display:flex;align-items:center;gap:12px;margin-bottom:10px;">
        <span style="font-size:16px;font-weight:700;color:#fff;">${sid}</span>
        <span style="font-size:12px;color:${sid.startsWith('F')?'var(--red)':'var(--blue)'};">${LABEL[sid]}</span>
        ${hasData?(bypass
          ?'<span class="badge b-failed">PG-1 우회 감지</span>'
          :'<span class="badge b-approved">PG-1 차단 확인</span>'
        ):'<span class="badge b-pending">채점 대기중</span>'}
      </div>`;

    if(hasData){
      html+=`<table style="width:auto;"><thead><tr>
        ${DATA.teachers.map(t=>`<th style="text-align:center">${t}</th>`).join('')}
      </tr></thead><tbody><tr>
        ${DATA.teachers.map(t=>{
          const s = sg[t];
          if(!s) return `<td style="text-align:center;color:var(--muted);">—</td>`;
          const c = s.total>0?'var(--red)':'var(--green)';
          return `<td style="text-align:center;font-weight:700;color:${c};">${s.total}</td>`;
        }).join('')}
      </tr></tbody></table>`;
    }
    html+=`</div>`;
  });

  // 완료된 사이클이 있으면 사이클별 히스토리도 표시 가능 (향후 확장)
  const done = DATA.cycles.filter(c=>c.status==='done');
  if(done.length){
    html+=`<div style="font-size:12px;color:var(--muted);">
      * 사이클별 F/I 점수 추이는 각 사이클 상세에서 확인 가능합니다.
    </div>`;
  }

  document.getElementById('fi-content').innerHTML = html;
}

