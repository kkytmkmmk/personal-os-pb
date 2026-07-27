/* Secondary exploration surfaces.  Canvas is intentionally used instead of a
   heavyweight 3D dependency so the same local-first view works on iPhone. */
(function () {
  'use strict';
  const esc = value => String(value ?? '').replace(/[&<>"']/g, char => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[char]));
  const domainNames = { finance: '資産', travel: '旅行', housing: '住居', relationship: '人間関係', work: '仕事', health: '健康', life: '生活', lifestyle: '生活', learning: '学習', hobby: '趣味', food: '食事', shopping: '買い物', other: 'その他' };
  let spaceData = null;
  let selectedId = null;
  let camera = { yaw: 0.15, pitch: -0.2, zoom: 1 };

  function addStyles() {
    const style = document.createElement('style');
    style.textContent = '.space-wrap{position:relative;min-height:420px;background:#070d12;border:1px solid var(--line);border-radius:12px;overflow:hidden}.space-canvas{display:block;width:100%;height:420px;touch-action:none}.space-overlay{position:absolute;inset:12px auto auto 12px;max-width:calc(100% - 24px);display:flex;gap:6px;flex-wrap:wrap}.space-overlay label{margin:0;padding:6px 8px;background:rgba(7,13,18,.82);border:1px solid var(--line);border-radius:8px;color:var(--text);font-size:.78rem}.space-overlay input{width:auto;min-height:0;vertical-align:middle}.space-detail{padding:11px;border-top:1px solid var(--line);min-height:58px}.space-legend{display:flex;gap:8px;flex-wrap:wrap;margin:10px 0;font-size:.8rem}.space-dot{display:inline-block;width:10px;height:10px;border-radius:50%;margin-right:4px}.benchmark-series{display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:10px}.benchmark-card{padding:12px;background:#101716;border:1px solid var(--line);border-radius:10px}.benchmark-card h3{margin:0 0 6px;font-size:1rem}.benchmark-value{font-size:1.3rem;color:var(--accent);font-weight:700}.benchmark-meta{font-size:.78rem;color:var(--muted);margin-top:7px}@media(max-width:767px){.space-wrap,.space-canvas{min-height:330px;height:330px}.space-overlay{right:10px}.space-overlay label{font-size:.72rem}}';
    document.head.append(style);
  }

  function appendSurface() {
    const visual = document.getElementById('visualize');
    if (!visual || document.getElementById('personal-space-card')) return;
    const section = document.createElement('section');
    section.id = 'personal-space-card'; section.className = 'card';
    section.innerHTML = '<h2>Personal Space</h2><p class="help">記憶・判断を探索する補助画面です。日常操作や検索の代わりにはしません。クリックで根拠を確認できます。</p><div class="space-wrap"><canvas id="personal-space-canvas" class="space-canvas" aria-label="Personal Space 記憶マップ"></canvas><div class="space-overlay"><label><input id="space-current" type="checkbox" checked> 現在</label><label><input id="space-history" type="checkbox" checked> 履歴</label><label><input id="space-sensitive" type="checkbox"> 機微情報を表示</label></div></div><div id="personal-space-legend" class="space-legend"></div><div id="personal-space-detail" class="space-detail help">ノードを選ぶと詳細を表示します。</div>';
    visual.append(section);
    ['space-current', 'space-history', 'space-sensitive'].forEach(id => document.getElementById(id).addEventListener('change', refreshSpace));
    const canvas = document.getElementById('personal-space-canvas');
    let dragging = false, point = null;
    canvas.addEventListener('pointerdown', event => { dragging = true; point = { x: event.clientX, y: event.clientY }; canvas.setPointerCapture?.(event.pointerId); });
    canvas.addEventListener('pointermove', event => { if (!dragging || !point) return; camera.yaw += (event.clientX - point.x) / 250; camera.pitch = Math.max(-1, Math.min(1, camera.pitch + (event.clientY - point.y) / 250)); point = { x: event.clientX, y: event.clientY }; renderSpace(); });
    canvas.addEventListener('pointerup', () => { dragging = false; point = null; });
    canvas.addEventListener('wheel', event => { event.preventDefault(); camera.zoom = Math.max(.55, Math.min(1.8, camera.zoom - event.deltaY / 900)); renderSpace(); }, { passive: false });
    canvas.addEventListener('click', event => chooseSpaceNode(event));
  }

  function stableNumber(text) { let value = 2166136261; for (const char of String(text)) value = Math.imul(value ^ char.charCodeAt(0), 16777619); return value >>> 0; }
  function coords(node) { const hash = stableNumber(node.id); const group = stableNumber(node.domain) % 12; const angle = (group / 12) * Math.PI * 2; const radius = 0.36 + (hash % 29) / 100; return { x: Math.cos(angle) * radius + ((hash >>> 8) % 21 - 10) / 180, y: Math.sin(angle) * radius + ((hash >>> 13) % 21 - 10) / 180, z: ((hash >>> 18) % 100 - 50) / 100 }; }
  function projected(node, width, height) { const p = coords(node); const cy = Math.cos(camera.yaw), sy = Math.sin(camera.yaw), cp = Math.cos(camera.pitch), sp = Math.sin(camera.pitch); const x = p.x * cy - p.z * sy; const z = p.x * sy + p.z * cy; const y = p.y * cp - z * sp; const depth = 1.4 + z * .45; return { x: width / 2 + (x / depth) * width * .76 * camera.zoom, y: height / 2 + (y / depth) * height * .76 * camera.zoom, depth }; }
  function visibleNodes() { if (!spaceData) return []; const current = document.getElementById('space-current')?.checked; const history = document.getElementById('space-history')?.checked; const mobile = matchMedia('(max-width: 767px)').matches; return spaceData.nodes.filter(node => (node.status === 'current' ? current : history)).slice(0, mobile ? 70 : 180); }
  function renderSpace() {
    const canvas = document.getElementById('personal-space-canvas'); if (!canvas || !spaceData) return;
    const ratio = Math.min(window.devicePixelRatio || 1, 2), rect = canvas.getBoundingClientRect(); canvas.width = Math.max(1, Math.floor(rect.width * ratio)); canvas.height = Math.max(1, Math.floor(rect.height * ratio));
    const ctx = canvas.getContext('2d'); ctx.scale(ratio, ratio); const width = rect.width, height = rect.height; ctx.clearRect(0, 0, width, height);
    const nodes = visibleNodes().map(node => ({ ...node, p: projected(node, width, height) })).sort((a, b) => a.p.depth - b.p.depth);
    ctx.fillStyle = '#070d12'; ctx.fillRect(0, 0, width, height);
    nodes.forEach(node => { const color = spaceData.colors[node.domain] || spaceData.colors.other; const radius = 4 + node.strength * 8; ctx.globalAlpha = node.status === 'current' ? .95 : .36; ctx.beginPath(); ctx.fillStyle = color; ctx.shadowColor = color; ctx.shadowBlur = node.id === selectedId ? 20 : 8; if (node.kind === 'decision') ctx.rect(node.p.x - radius, node.p.y - radius, radius * 2, radius * 2); else ctx.arc(node.p.x, node.p.y, radius, 0, Math.PI * 2); ctx.fill(); ctx.shadowBlur = 0; if (width > 520 && !node.masked) { ctx.font = '11px system-ui'; ctx.fillStyle = '#e8efeb'; ctx.globalAlpha *= .82; ctx.fillText(node.label.slice(0, 18), node.p.x + radius + 4, node.p.y + 3); } });
    canvas._spaceNodes = nodes;
  }
  function chooseSpaceNode(event) { const canvas = event.currentTarget, rect = canvas.getBoundingClientRect(); const x = event.clientX - rect.left, y = event.clientY - rect.top; const selected = (canvas._spaceNodes || []).map(node => ({ node, d: Math.hypot(node.p.x - x, node.p.y - y) })).sort((a,b) => a.d - b.d)[0]; if (!selected || selected.d > 28) return; selectedId = selected.node.id; const detail = document.getElementById('personal-space-detail'); detail.innerHTML = '<b>' + esc(selected.node.label) + '</b><div class="meta">' + esc(domainNames[selected.node.domain] || selected.node.domain) + ' ・ ' + esc(selected.node.kind) + ' ・ ' + esc(selected.node.status || '') + '</div>' + (selected.node.masked ? '<div>機微情報はマスク中です。表示を明示的に切り替えてください。</div>' : '<div>根拠: <a href="' + esc(selected.node.target) + '" target="_blank" rel="noopener">確認する</a></div>'); renderSpace(); }
  async function refreshSpace() { const showSensitive = document.getElementById('space-sensitive')?.checked ? 'true' : 'false'; try { const response = await fetch('/api/personal-space?include_sensitive=' + showSensitive); if (!response.ok) throw new Error('Personal Space を取得できません'); spaceData = await response.json(); const legend = document.getElementById('personal-space-legend'); legend.innerHTML = Object.entries(spaceData.colors).filter(([key]) => key !== 'lifestyle').map(([key, color]) => '<span><i class="space-dot" style="background:' + color + '"></i>' + esc(domainNames[key] || key) + '</span>').join(''); renderSpace(); } catch (error) { const detail = document.getElementById('personal-space-detail'); if (detail) detail.textContent = error.message; } }

  function appendBenchmark() {
    if (document.getElementById('benchmark')) return;
    const section = document.createElement('section'); section.id = 'benchmark'; section.className = 'tab hidden';
    section.innerHTML = '<section class="card"><h2>人口ベンチマーク</h2><p class="help">公的統計など、手元に保存した参照値を表示します。個人データは統計提供元や外部サービスへ送信しません。</p><div id="benchmark-privacy" class="help"></div><div id="benchmark-series" class="benchmark-series"></div></section><section class="card"><h2>参照データを追加</h2><p class="help">出典・定義・対象集団を必須にしてローカルへ保存します。API取得は行いません。</p><form id="benchmark-import-form"><label>参照データ JSON</label><textarea id="benchmark-import-json" required placeholder="source / series / observations を含むJSON"></textarea><div class="actions"><button type="submit">ローカルに保存</button><span id="benchmark-import-notice" class="help"></span></div></form></section>';
    document.getElementById('visualize')?.before(section);
    const nav = document.getElementById('legacy-nav'); if (nav) { const button = document.createElement('button'); button.className = 'secondary'; button.textContent = '比較'; button.addEventListener('click', () => window.personalOsNavigate?.('benchmark')); nav.append(button); }
    document.getElementById('benchmark-import-form').addEventListener('submit', async event => { event.preventDefault(); const notice = document.getElementById('benchmark-import-notice'); try { const payload = JSON.parse(document.getElementById('benchmark-import-json').value); const response = await fetch('/api/benchmarks/import', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) }); const result = await response.json(); if (!response.ok) throw new Error(result.error || '保存できませんでした'); notice.textContent = `保存しました（新規 ${result.new_observations} 件、改訂 ${result.revised_observations} 件）`; refreshBenchmarks(); } catch (error) { notice.textContent = error.message; } });
  }
  async function refreshBenchmarks() { const container = document.getElementById('benchmark-series'); if (!container) return; try { const response = await fetch('/api/benchmarks'); const payload = await response.json(); document.getElementById('benchmark-privacy').textContent = payload.privacy || ''; container.innerHTML = payload.series.length ? payload.series.map(series => { const latest = series.observations?.[0]; return '<article class="benchmark-card"><h3>' + esc(series.metric_name) + '</h3><div class="benchmark-value">' + (latest?.value == null ? '分布データ' : esc(Number(latest.value).toLocaleString('ja-JP')) + ' ' + esc(series.unit)) + '</div><div class="benchmark-meta">' + esc(series.statistic_type) + ' ・ ' + esc(latest?.reference_period || '') + '<br>' + esc(series.population_scope) + '<br>出典: <a href="' + esc(series.source_url) + '" target="_blank" rel="noopener">' + esc(series.publisher) + '</a><br>定義: ' + esc(series.definition) + '</div></article>'; }).join('') : '<p class="help">参照データはまだありません。出典を確認したJSONを追加してください。</p>'; } catch (error) { container.textContent = error.message; } }
  async function refreshBenchmarks() {
    const container = document.getElementById('benchmark-series');
    if (!container) return;
    try {
      const response = await fetch('/api/benchmarks');
      const payload = await response.json();
      document.getElementById('benchmark-privacy').textContent = payload.privacy || '';
      container.innerHTML = payload.series.length ? payload.series.map(series => {
        const latest = series.observations?.[0];
        const reference = latest?.value == null ? 'Distribution data' : `${Number(latest.value).toLocaleString('ja-JP')} ${series.unit}`;
        const own = series.personal;
        const comparison = own && series.compatibility === 'exact' && own.value != null
          ? `<br>あなた: <b>${Number(own.value).toLocaleString('ja-JP')} ${esc(own.unit)}</b> <span class="pill">exact match</span><br><a href="/api/facts/${own.fact_id}/evidence" target="_blank" rel="noopener">Fact の根拠</a>`
          : own ? '<br>あなたのFactはありますが、単位または定義が一致しないため数値比較はしません。'
          : '<br>同じ metric key の確認済みCurrent Factがないため、参照値のみを表示しています。';
        return `<article class="benchmark-card"><h3>${esc(series.metric_name)}</h3><div class="benchmark-value">${esc(reference)}</div><div class="benchmark-meta">${esc(series.statistic_type)} ・ ${esc(latest?.reference_period || '')}<br>${esc(series.population_scope)}<br>出典: <a href="${esc(series.source_url)}" target="_blank" rel="noopener">${esc(series.publisher)}</a><br>定義: ${esc(series.definition)}${comparison}</div></article>`;
      }).join('') : '<p class="help">参照データはまだありません。出典を確認したJSONを追加してください。</p>';
    } catch (error) { container.textContent = error.message; }
  }
  window.refreshPersonalSpace = refreshSpace; window.refreshBenchmarks = refreshBenchmarks;
  document.addEventListener('DOMContentLoaded', () => { addStyles(); appendSurface(); appendBenchmark(); window.addEventListener('resize', renderSpace); });
}());
