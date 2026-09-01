(() => {
  const menu = document.getElementById('menuToggle');
  const sidebar = document.getElementById('sidebar');
  if (menu && sidebar) menu.addEventListener('click', () => sidebar.classList.toggle('open'));

  const tabRoot = document.querySelector('[data-tabs]');
  if (tabRoot) {
    const buttons = [...tabRoot.querySelectorAll('[data-tab]')];
    const panes = [...document.querySelectorAll('[data-pane]')];
    buttons.forEach(btn => btn.addEventListener('click', () => {
      buttons.forEach(x => x.classList.remove('active'));
      panes.forEach(x => x.classList.remove('active'));
      btn.classList.add('active');
      const pane = document.querySelector(`[data-pane="${btn.dataset.tab}"]`);
      if (pane) pane.classList.add('active');
    }));
  }

  const textarea = document.querySelector('.investigate-form textarea');
  document.querySelectorAll('[data-prompt]').forEach(btn => btn.addEventListener('click', () => {
    if (!textarea) return;
    textarea.value = btn.dataset.prompt || '';
    textarea.focus();
  }));
})();

// Zero-config onboarding drag/drop
(() => {
  const dz = document.getElementById('dropzone');
  const input = document.getElementById('fileInput');
  const queue = document.getElementById('uploadQueue');
  if (!dz || !input || !queue) return;
  const render = () => {
    queue.innerHTML = '';
    Array.from(input.files || []).forEach(f => {
      const s = document.createElement('span');
      s.textContent = `${f.name} · ${(f.size/1024).toFixed(1)}KB`;
      queue.appendChild(s);
    });
  };
  input.addEventListener('change', render);
  ['dragenter','dragover'].forEach(ev => dz.addEventListener(ev, e => { e.preventDefault(); dz.classList.add('dragover'); }));
  ['dragleave','drop'].forEach(ev => dz.addEventListener(ev, e => { e.preventDefault(); dz.classList.remove('dragover'); }));
  dz.addEventListener('drop', e => {
    if (!e.dataTransfer?.files?.length) return;
    const dt = new DataTransfer();
    Array.from(e.dataTransfer.files).forEach(f => dt.items.add(f));
    input.files = dt.files;
    render();
  });
})();

// Approval Center filters + bulk selection
(() => {
  const list = document.getElementById('approvalList');
  if (!list) return;
  const search = document.getElementById('approvalSearch');
  const status = document.getElementById('approvalStatusFilter');
  const type = document.getElementById('approvalTypeFilter');
  const empty = document.getElementById('approvalEmpty');
  const count = document.getElementById('selectedApprovalCount');
  const rows = [...list.querySelectorAll('[data-approval-item]')];
  const checks = [...list.querySelectorAll('.approval-checkbox')];
  const refreshCount = () => { if (count) count.textContent = String(checks.filter(x => x.checked).length); };
  const apply = () => {
    const q = (search?.value || '').trim().toLowerCase();
    const st = status?.value || 'all';
    const ty = type?.value || 'all';
    let visible = 0;
    rows.forEach(row => {
      const ok = (!q || (row.dataset.search || '').includes(q)) && (st === 'all' || row.dataset.status === st) && (ty === 'all' || row.dataset.type === ty);
      row.hidden = !ok;
      if (ok) visible++;
    });
    if (empty) empty.hidden = visible !== 0;
  };
  search?.addEventListener('input', apply);
  status?.addEventListener('change', apply);
  type?.addEventListener('change', apply);
  checks.forEach(c => c.addEventListener('change', refreshCount));
  document.getElementById('bulkForm')?.addEventListener('submit', e => {
    if (!checks.some(x => x.checked)) { e.preventDefault(); window.alert('処理する項目を選択してください。'); }
  });
  apply(); refreshCount();
})();

// Interactive file → table → semantic column → JOIN → analysis lineage graph
(() => {
  const dataEl = document.getElementById('lineageData');
  const canvas = document.getElementById('lineageCanvas');
  const nodesEl = document.getElementById('lineageNodes');
  const svg = document.getElementById('lineageEdges');
  const detail = document.getElementById('lineageDetail');
  if (!dataEl || !canvas || !nodesEl || !svg || !detail) return;
  let graph;
  try { graph = JSON.parse(dataEl.textContent || '{}'); } catch { return; }
  const nodes = Array.isArray(graph.nodes) ? graph.nodes : [];
  const edges = Array.isArray(graph.edges) ? graph.edges : [];
  const layers = Array.isArray(graph.layers) ? graph.layers : [];
  const layerLabels = document.getElementById('lineageLayerLabels');
  const search = document.getElementById('lineageSearch');
  const kindFilter = document.getElementById('lineageKindFilter');
  const statusFilter = document.getElementById('lineageStatusFilter');
  const zoomLabel = document.getElementById('lineageZoomLabel');
  const viewport = document.getElementById('lineageViewport');
  let zoom = 1;
  const W = 205, H = 76, XGAP = 80, YGAP = 22, LEFT = 34, TOP = 60;
  const layerX = new Map(layers.map((l, i) => [Number(l.id), LEFT + i * (W + XGAP)]));
  const byLayer = new Map();
  nodes.forEach(n => { const l = Number(n.layer || 0); if (!byLayer.has(l)) byLayer.set(l, []); byLayer.get(l).push(n); });
  const positions = new Map();
  let maxY = 0;
  byLayer.forEach((arr, layer) => {
    arr.sort((a,b) => String(a.label).localeCompare(String(b.label), 'ja'));
    arr.forEach((n, i) => {
      const x = layerX.get(layer) ?? LEFT;
      const y = TOP + i * (H + YGAP);
      positions.set(n.id, {x,y}); maxY = Math.max(maxY, y + H + 40);
    });
  });
  const width = Math.max(1450, LEFT + Math.max(1, layers.length) * (W + XGAP) + 40);
  const height = Math.max(650, maxY);
  canvas.style.width = `${width}px`; canvas.style.height = `${height}px`;
  svg.setAttribute('viewBox', `0 0 ${width} ${height}`);
  svg.setAttribute('width', String(width)); svg.setAttribute('height', String(height));

  const esc = value => String(value ?? '').replace(/[&<>"']/g, ch => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[ch]));
  const humanStatus = s => ({pending:'未承認',approved:'承認済み',held:'保留',rejected:'却下',active:'稼働中',waiting:'データ待ち',waiting_data:'データ待ち',auto:'自動候補',review:'要確認',suggested:'候補'}[s] || s || '—');
  const humanKind = s => ({file:'ファイル',table:'テーブル',column:'列',join:'結合',module:'分析',relationship:'関連',maps:'意味付け',contains:'包含',join_key:'結合キー',join_table:'結合対象',enables:'分析を有効化',supports_analysis:'分析を支援'}[s] || s || '項目');
  const humanKey = s => ({relative_path:'ファイルパス',extension:'形式',size_bytes:'サイズ',sha256:'SHA-256',allowed:'利用可否',table_key:'テーブル識別子',source:'参照元',sheet:'シート',rows:'行数',role:'データ種別',role_score:'データ種別の信頼度',raw:'元の列名',canonical:'AIの解釈',confidence:'信頼度',examples:'サンプル値',reasons:'判断理由',join_id:'結合ID',left:'左側データ',right:'右側データ',key:'結合キー',mode:'結合方式',requires_all:'必須データ',requires_any:'いずれか必要',missing:'不足データ',enrichments:'追加連携',state:'状態',description:'説明',kind:'種類',target:'接続先'}[s] || s);
  const humanTerm = s => ({quality:'品質',process:'工程',equipment_logs:'設備ログ',maintenance:'保全',parts:'部品・ロット',documents:'文書',vision:'画像',acoustic:'音響',vehicle_id:'製品/車両ID',equipment_id:'設備ID',part_lot:'部品ロット',part_no:'部品番号',timestamp:'タイムスタンプ',equi_join:'等価結合',asof_join:'時刻近傍結合',time_window:'時間窓結合',ON:'稼働',DATA_WAIT:'データ待ち'}[s] || s);
  const pretty = (k,v) => {
    if (v === null || v === undefined || v === '') return '—';
    if (Array.isArray(v)) return v.map(x => humanTerm(String(x))).join(' / ');
    if (typeof v === 'object') return Object.entries(v).map(([kk,vv]) => `${humanKey(kk)}: ${typeof vv === 'object' ? JSON.stringify(vv) : humanTerm(String(vv))}`).join(' / ');
    if (String(k).includes('confidence') || String(k).includes('score')) { const n=Number(v); if (Number.isFinite(n) && n >= 0 && n <= 1) return `${Math.round(n*100)}%`; }
    return humanTerm(String(v));
  };
  const nodeMap = new Map(nodes.map(n => [n.id,n]));
  const domNode = new Map();
  nodes.forEach(n => {
    const p = positions.get(n.id); if (!p) return;
    const b = document.createElement('button'); b.type = 'button';
    b.className = `lineage-node kind-${n.kind || 'node'}`; b.dataset.nodeId=n.id; b.dataset.kind=n.kind||''; b.dataset.status=n.status||'';
    b.dataset.search = `${n.label||''} ${n.sub||''}`.toLowerCase(); b.style.left=`${p.x}px`; b.style.top=`${p.y}px`;
    b.innerHTML = `<span class="node-top"><span class="node-kind">${esc(humanKind(n.kind))}</span><i class="node-state"></i></span><b>${esc(n.label)}</b><small>${esc(n.sub)}</small>`;
    b.addEventListener('click', () => selectNode(n.id)); nodesEl.appendChild(b); domNode.set(n.id,b);
  });
  if (layerLabels) layers.forEach(l => { const x=layerX.get(Number(l.id))??LEFT; const e=document.createElement('span'); e.className='lineage-layer-label'; e.style.left=`${x}px`; e.textContent=l.label; layerLabels.appendChild(e); });

  const NS='http://www.w3.org/2000/svg';
  const edgeDom = new Map();
  const pathFor = e => {
    const a=positions.get(e.source), b=positions.get(e.target); if(!a||!b) return '';
    const x1=a.x+W, y1=a.y+H/2, x2=b.x, y2=b.y+H/2, mx=(x1+x2)/2;
    return `M ${x1} ${y1} C ${mx} ${y1}, ${mx} ${y2}, ${x2} ${y2}`;
  };
  edges.forEach(e => {
    const d=pathFor(e); if(!d) return;
    const g=document.createElementNS(NS,'g');
    const p=document.createElementNS(NS,'path'); p.setAttribute('d',d); p.setAttribute('class',`lineage-edge ${e.status||''}`); p.dataset.edgeId=e.id;
    const hit=document.createElementNS(NS,'path'); hit.setAttribute('d',d); hit.setAttribute('class','lineage-edge-hit'); hit.dataset.edgeId=e.id; hit.addEventListener('click',()=>selectEdge(e.id));
    g.appendChild(p); g.appendChild(hit); svg.appendChild(g); edgeDom.set(e.id,{path:p,hit,g});
  });

  const renderDetails = (title, kind, status, sub, detailsObj) => {
    const entries = Object.entries(detailsObj || {}).filter(([k,v]) => !['approval','columns'].includes(k) && v !== '' && v !== null && v !== undefined).slice(0,18);
    const approval = detailsObj?.approval;
    let html = `<span class="section-kicker">${esc(humanKind(kind))}</span><h2>${esc(title)}</h2><p>${esc(sub||'')}</p><div class="lineage-detail-grid"><div class="lineage-detail-row"><small>状態</small><b>${esc(humanStatus(status))}</b></div>`;
    if (approval) html += `<div class="lineage-detail-row"><small>承認ログ</small><b>${esc(approval.actor||'未承認')}</b><span>${approval.updated_at ? ' · '+esc(approval.updated_at) : ''}</span></div>`;
    entries.forEach(([k,v]) => html += `<div class="lineage-detail-row"><small>${esc(humanKey(k))}</small><span>${esc(pretty(k,v))}</span></div>`);
    html += '</div>'; detail.innerHTML=html;
  };
  const clearSelected = () => { domNode.forEach(x=>x.classList.remove('selected')); edgeDom.forEach(x=>x.path.classList.remove('selected')); };
  const selectNode = id => {
    clearSelected(); const n=nodeMap.get(id); const el=domNode.get(id); if(!n||!el)return; el.classList.add('selected');
    renderDetails(n.label,n.kind,n.status,n.sub,n.details||{});
  };
  const selectEdge = id => {
    clearSelected(); const e=edges.find(x=>x.id===id); const ed=edgeDom.get(id); if(!e||!ed)return; ed.path.classList.add('selected');
    const a=nodeMap.get(e.source), b=nodeMap.get(e.target); renderDetails(e.label||humanKind(e.kind),'relationship',e.status,`${a?.label||e.source} → ${b?.label||e.target}`,{kind:e.kind,source:a?.label||e.source,target:b?.label||e.target,...(e.details||{})});
  };
  const applyFilters = () => {
    const q=(search?.value||'').trim().toLowerCase(), k=kindFilter?.value||'all', st=statusFilter?.value||'all';
    const visible=new Set();
    nodes.forEach(n=>{ const el=domNode.get(n.id); if(!el)return; const ok=(!q||el.dataset.search.includes(q))&&(k==='all'||n.kind===k)&&(st==='all'||n.status===st); el.classList.toggle('hidden-node',!ok); if(ok) visible.add(n.id); });
    edgeDom.forEach((ed,id)=>{ const e=edges.find(x=>x.id===id); const show=e&&visible.has(e.source)&&visible.has(e.target); ed.g.style.display=show?'':'none'; });
  };
  search?.addEventListener('input',applyFilters); kindFilter?.addEventListener('change',applyFilters); statusFilter?.addEventListener('change',applyFilters);
  const setZoom = z => { zoom=Math.max(.55,Math.min(1.5,z)); canvas.style.transform=`scale(${zoom})`; canvas.style.marginRight=`${width*(zoom-1)}px`; canvas.style.marginBottom=`${height*(zoom-1)}px`; if(zoomLabel) zoomLabel.textContent=`${Math.round(zoom*100)}%`; };
  document.getElementById('lineageZoomIn')?.addEventListener('click',()=>setZoom(zoom+.1));
  document.getElementById('lineageZoomOut')?.addEventListener('click',()=>setZoom(zoom-.1));
  document.getElementById('lineageReset')?.addEventListener('click',()=>{ setZoom(1); if(viewport){viewport.scrollLeft=0;viewport.scrollTop=0;} });
  applyFilters();
  if(nodes[0]) selectNode(nodes[0].id);
})();
