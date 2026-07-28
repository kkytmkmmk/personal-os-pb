/* Explore is a secondary, local-only view. It deliberately depends on no 3D
   library so the same deterministic Canvas view works on iPhone. */
(function () {
  'use strict';
  const esc = value => String(value ?? '').replace(/[&<>"']/g, char => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[char]));
  const domainNames = { finance: '資産', travel: '旅行', housing: '住居', relationship: '人間関係', work: '仕事', health: '健康', life: '生活', lifestyle: '生活', learning: '学習', hobby: '趣味', food: '食事', shopping: '買い物', other: 'その他' };
  let spaceData = { nodes: [], edges: [], colors: {} };
  let selectedId = null;
  let camera = { yaw: .16, pitch: -.18, zoom: 1 };

  const byId = id => document.getElementById(id);
  const stableNumber = text => { let value = 2166136261; for (const char of String(text)) value = Math.imul(value ^ char.charCodeAt(0), 16777619); return value >>> 0; };
  function coords(node) { const hash = stableNumber(node.id); const group = stableNumber(node.domain) % 12; const angle = group * Math.PI / 6; const radius = .34 + (hash % 29) / 100; return { x: Math.cos(angle) * radius + ((hash >>> 8) % 21 - 10) / 180, y: Math.sin(angle) * radius + ((hash >>> 13) % 21 - 10) / 180, z: ((hash >>> 18) % 100 - 50) / 100 }; }
  function project(node, width, height) { const p = coords(node); const cy = Math.cos(camera.yaw), sy = Math.sin(camera.yaw), cp = Math.cos(camera.pitch), sp = Math.sin(camera.pitch); const x = p.x * cy - p.z * sy; const z = p.x * sy + p.z * cy; const y = p.y * cp - z * sp; const depth = 1.4 + z * .45; return { x: width / 2 + (x / depth) * width * .76 * camera.zoom, y: height / 2 + (y / depth) * height * .76 * camera.zoom, depth }; }
  function activeNodes() {
    const query = (byId('space-search')?.value || '').trim().toLowerCase();
    const domain = byId('space-domain')?.value || '';
    const kind = byId('space-kind')?.value || '';
    const current = byId('space-current')?.checked;
    const history = byId('space-history')?.checked;
    const mobile = matchMedia('(max-width: 767px)').matches;
    return spaceData.nodes.filter(node => {
      const isCurrent = node.status === 'current';
      if ((isCurrent && !current) || (!isCurrent && !history)) return false;
      if (domain && node.domain !== domain) return false;
      if (kind && node.kind !== kind) return false;
      return !query || String(node.label).toLowerCase().includes(query) || String(node.domain).includes(query) || String(node.kind).includes(query);
    }).slice(0, mobile ? 70 : 220);
  }
  function drawShape(ctx, node, radius) {
    if (node.kind === 'decision') { ctx.rotate(Math.PI / 4); ctx.rect(-radius, -radius, radius * 2, radius * 2); return; }
    if (node.kind === 'plan') { ctx.rect(-radius, -radius, radius * 2, radius * 2); return; }
    if (node.kind === 'recommendation') { ctx.arc(0, 0, radius, 0, Math.PI * 2); ctx.stroke(); return; }
    if (node.kind === 'result') { ctx.arc(0, 0, radius, 0, Math.PI * 2); ctx.fill(); ctx.beginPath(); ctx.arc(radius * .45, -radius * .45, Math.max(2, radius * .28), 0, Math.PI * 2); ctx.fill(); return; }
    ctx.arc(0, 0, radius, 0, Math.PI * 2);
  }
  function renderSpace() {
    const canvas = byId('personal-space-canvas'); if (!canvas) return;
    const ratio = Math.min(window.devicePixelRatio || 1, 2), rect = canvas.getBoundingClientRect();
    canvas.width = Math.max(1, Math.floor(rect.width * ratio)); canvas.height = Math.max(1, Math.floor(rect.height * ratio));
    const ctx = canvas.getContext('2d'); ctx.scale(ratio, ratio); const width = rect.width, height = rect.height; ctx.fillStyle = '#070d12'; ctx.fillRect(0, 0, width, height);
    const nodes = activeNodes().map(node => ({ ...node, p: project(node, width, height) })).sort((a, b) => a.p.depth - b.p.depth);
    const lookup = new Map(nodes.map(node => [node.id, node]));
    if (byId('space-edges')?.checked) {
      spaceData.edges.forEach(edge => { const from = lookup.get(edge.from), to = lookup.get(edge.to); if (!from || !to) return; ctx.save(); ctx.globalAlpha = edge.kind === 'lifecycle' ? .55 : .3; ctx.strokeStyle = edge.kind === 'result' ? '#8ce8bb' : '#93a3a0'; ctx.lineWidth = edge.kind === 'lifecycle' ? 1.8 : 1; if (edge.kind === 'contradiction') ctx.setLineDash([4, 4]); ctx.beginPath(); ctx.moveTo(from.p.x, from.p.y); ctx.lineTo(to.p.x, to.p.y); ctx.stroke(); ctx.restore(); });
    }
    nodes.forEach(node => { const color = spaceData.colors[node.domain] || spaceData.colors.other || '#94A3B8'; const radius = 4 + Number(node.strength || .4) * 8; ctx.save(); ctx.translate(node.p.x, node.p.y); ctx.globalAlpha = node.status === 'current' ? .96 : .38; ctx.fillStyle = color; ctx.strokeStyle = color; ctx.lineWidth = 2; ctx.shadowColor = color; ctx.shadowBlur = node.id === selectedId ? 22 : (node.kind === 'result' ? 12 : 6); ctx.beginPath(); drawShape(ctx, node, radius); if (node.kind === 'recommendation') ctx.stroke(); else ctx.fill(); ctx.restore(); if (width > 620 && !node.masked) { ctx.globalAlpha = node.status === 'current' ? .88 : .45; ctx.fillStyle = '#e8efeb'; ctx.font = '11px system-ui'; ctx.fillText(String(node.label).slice(0, 20), node.p.x + radius + 4, node.p.y + 3); } });
    canvas._spaceNodes = nodes;
  }
  function showNode(node) { selectedId = node.id; const detail = byId('personal-space-detail'); if (!detail) return; const safeLabel = esc(node.label); detail.innerHTML = `<b>${safeLabel}</b><div class="meta">${esc(domainNames[node.domain] || node.domain)} ・ ${esc(node.kind)} ・ ${esc(node.status || '')}</div>${node.masked ? '<p>機微情報はマスク中です。表示を明示的に切り替えてください。</p>' : `<p><a href="${esc(node.target)}" target="_blank" rel="noopener">根拠・詳細を確認</a></p>`}`; renderSpace(); }
  function chooseNode(event) { const canvas = event.currentTarget, rect = canvas.getBoundingClientRect(), x = event.clientX - rect.left, y = event.clientY - rect.top; const nearest = (canvas._spaceNodes || []).map(node => ({ node, d: Math.hypot(node.p.x - x, node.p.y - y) })).sort((a, b) => a.d - b.d)[0]; if (nearest && nearest.d <= 30) showNode(nearest.node); }
  async function refreshSpace() { try { const sensitive = byId('space-sensitive')?.checked ? 'true' : 'false'; const response = await fetch(`/api/personal-space?include_sensitive=${sensitive}&limit=220`); if (!response.ok) throw new Error('Personal Space を取得できません'); spaceData = await response.json(); const select = byId('space-domain'); if (select && !select.dataset.ready) { Object.keys(spaceData.colors).filter(key => key !== 'lifestyle').forEach(key => { const option = document.createElement('option'); option.value = key; option.textContent = domainNames[key] || key; select.append(option); }); select.dataset.ready = 'true'; } const legend = byId('personal-space-legend'); if (legend) legend.innerHTML = Object.entries(spaceData.colors).filter(([key]) => key !== 'lifestyle').map(([key, color]) => `<span><i class="space-dot" style="background:${color}"></i>${esc(domainNames[key] || key)}</span>`).join(''); renderSpace(); } catch (error) { const detail = byId('personal-space-detail'); if (detail) detail.textContent = error.message; } }

  function formatNumber(value) { return value == null ? '—' : Number(value).toLocaleString('ja-JP', { maximumFractionDigits: 2 }); }
  function compatibilityText(series) { const c = series.comparison; if (!c) return '<span class="pill">参照のみ</span>'; if (c.compatibility === 'exact' || c.compatibility === 'comparable') return `<span class="pill">${esc(c.compatibility)}</span><br>あなた: <b>${formatNumber(c.personal_value)} ${esc(c.unit || '')}</b><br>差: ${formatNumber(c.absolute_difference)} / ${formatNumber(c.ratio)}x / ${formatNumber((c.percentage_difference || 0) * 100)}%`; return `<span class="pill">${esc(c.compatibility)}</span><br>${esc((c.reasons || []).join(' / '))}`; }
  function percentileBand(observation, comparison) { const d = observation?.distribution || observation?.distribution_json; if (!d || typeof d !== 'object') return ''; const points = ['p10', 'p25', 'p50', 'p75', 'p90'].filter(key => d[key] != null); if (!points.length) return ''; const you = comparison?.personal_value; return `<div class="benchmark-band">${points.map(key => `<span>${key.toUpperCase()}<b>${formatNumber(d[key])}</b></span>`).join('')}${you != null ? `<mark style="left:${Math.max(2, Math.min(96, Number(comparison?.percentile_hint || 50)))}%">あなた</mark>` : ''}</div>`; }
  async function refreshBenchmarks() { const container = byId('benchmark-series'); if (!container) return; try { const response = await fetch('/api/benchmarks'); const payload = await response.json(); byId('benchmark-privacy').textContent = payload.privacy || ''; container.innerHTML = payload.series.length ? payload.series.map(series => { const latest = series.observations?.[0]; const value = latest?.value == null ? '分布データ' : `${formatNumber(latest.value)} ${series.unit}`; return `<article class="benchmark-card"><div class="benchmark-card-head"><h3>${esc(series.metric_name)}</h3>${series.is_demo ? '<span class="pill">DEMO</span>' : ''}</div><div class="benchmark-value">${esc(value)}</div><div class="benchmark-comparison">${compatibilityText(series)}</div>${percentileBand(latest, series.comparison)}<div class="benchmark-meta">${esc(series.statistic_type)} ・ ${esc(latest?.reference_period || '')}<br>${esc(series.population_scope)}<br>出典: <a href="${esc(series.source_url)}" target="_blank" rel="noopener">${esc(series.publisher)}</a><br>定義: ${esc(series.definition)}</div></article>`; }).join('') : '<p class="help">参照データはまだありません。デモデータまたは確認済みのBundleを取り込んでください。</p>'; } catch (error) { container.textContent = error.message; } }
  function parseRawBundle() { const raw = byId('benchmark-import-json')?.value || ''; return { raw_json: raw }; }
  async function previewBundle() { const target = byId('benchmark-preview-result'); target.textContent = '検証中…'; try { const response = await fetch('/api/benchmarks/preview', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(parseRawBundle()) }); const result = await response.json(); if (!response.ok) throw new Error(result.error || '検証できませんでした'); target.innerHTML = `<b>${result.datasets} 件のデータセット / ${result.observations} 件の観測値</b><br>${esc((result.metrics || []).join(' ・ '))}${result.warnings?.length ? `<br>注意: ${esc(result.warnings.join(' / '))}` : ''}`; } catch (error) { target.textContent = error.message; } }
  async function importBundle(event) { event.preventDefault(); const notice = byId('benchmark-import-notice'); notice.textContent = '保存中…'; try { const response = await fetch('/api/benchmarks/import', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(parseRawBundle()) }); const result = await response.json(); if (!response.ok) throw new Error(result.error || '保存できませんでした'); notice.textContent = `保存しました（${result.datasets} データセット、${result.new_observations} 観測値）`; refreshBenchmarks(); } catch (error) { notice.textContent = error.message; } }
  async function loadDemo() { const notice = byId('benchmark-import-notice'); try { const response = await fetch('/api/benchmarks/demo', { method: 'POST' }); const result = await response.json(); if (!response.ok) throw new Error(result.error || 'デモを追加できませんでした'); notice.textContent = 'DEMOデータを追加しました。相談や推薦の根拠には使用されません。'; refreshBenchmarks(); } catch (error) { notice.textContent = error.message; } }
  async function copyPrompt() { const prompt = '日本の公開統計からPopulation Benchmark Bundleを作成してください。個人の情報は入力しません。各datasetに source.publisher, source.source_url, source_type, methodology, series.metric_key, metric_name, unit, statistic_type, definition, population_scope, segment_definition（subject_scope等）, observations.reference_period/value を含めてください。推測値やURL不明の値は入れず、JSONだけを返してください。'; try { await navigator.clipboard.writeText(prompt); byId('benchmark-import-notice').textContent = 'ChatGPT用プロンプトをコピーしました。'; } catch { byId('benchmark-import-notice').textContent = 'コピーできませんでした。'; } }
  function setMode(mode) { ['space', 'benchmark'].forEach(name => { byId(`explore-${name}`)?.classList.toggle('hidden', name !== mode); document.querySelector(`[data-explore-mode="${name}"]`)?.classList.toggle('active', name === mode); }); if (mode === 'space') refreshSpace(); else refreshBenchmarks(); }
  function wire() { document.querySelectorAll('[data-explore-mode]').forEach(button => button.addEventListener('click', () => setMode(button.dataset.exploreMode))); ['space-search', 'space-domain', 'space-kind', 'space-current', 'space-history', 'space-edges'].forEach(id => byId(id)?.addEventListener(id === 'space-search' ? 'input' : 'change', renderSpace)); byId('space-sensitive')?.addEventListener('change', refreshSpace); byId('personal-space-canvas')?.addEventListener('click', chooseNode); byId('benchmark-preview')?.addEventListener('click', previewBundle); byId('benchmark-import-form')?.addEventListener('submit', importBundle); byId('benchmark-load-demo')?.addEventListener('click', loadDemo); byId('benchmark-copy-prompt')?.addEventListener('click', copyPrompt); window.addEventListener('resize', renderSpace); }
  window.refreshPersonalSpace = refreshSpace;
  window.refreshBenchmarks = refreshBenchmarks;
  window.refreshExplore = () => { const active = document.querySelector('[data-explore-mode].active')?.dataset.exploreMode || 'space'; setMode(active); };
  document.addEventListener('DOMContentLoaded', () => { wire(); });
}());
