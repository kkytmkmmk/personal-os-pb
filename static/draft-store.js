/* Shared, session-local Draft v2 contract for every daily workflow. */
(() => {
  'use strict';
  const PREFIX = 'personal-os-draft-';
  const MAX_PRIMARY_AGE = 72 * 60 * 60 * 1000;
  const OLD_AGE = 7 * 24 * 60 * 60 * 1000;
  const routes = [
    [/^personal-os-draft-memo$/, { kind: 'memo', route: 'home', focus: '#record-text', title: '書きかけの記録を続ける' }],
    [/^personal-os-draft-chat$/, { kind: 'chat', route: 'chat', focus: '#chat-message', title: '書きかけの相談を続ける' }],
    [/^personal-os-draft-screenshot-context$/, { kind: 'image_context', route: 'home', focus: '#screenshot-form [name="context"]', title: '書きかけの画像記録を続ける' }],
    [/^personal-os-draft-benchmark-import$/, { kind: 'benchmark_import', route: 'explore', focus: '#benchmark-import-json', title: '書きかけの比較データ取込を続ける' }],
    [/^personal-os-draft-decision-(\d+)-result$/, { kind: 'decision_result', route: 'decisions', focus: '#decision-outcome-text', title: '書きかけの結果を続ける', mode: 'result' }],
    [/^personal-os-draft-decision-(\d+)-(?:evaluation|evaluate)$/, { kind: 'decision_evaluation', route: 'decisions', focus: '#decision-outcome-text', title: '書きかけの後日評価を続ける', mode: 'evaluate' }],
    [/^personal-os-draft-ux-feedback$/, { kind: 'ux_feedback', route: 'settings', focus: '#ux-feedback-body', title: '書きかけのフィードバックを続ける' }],
  ];

  function descriptor(key) {
    for (const [pattern, base] of routes) {
      const match = key.match(pattern);
      if (match) return { ...base, target_id: match[1] ? Number(match[1]) : null };
    }
    return null;
  }

  function normalize(key, raw) {
    const meta = descriptor(key); if (!meta || raw === null || raw === undefined) return null;
    let value; let legacy = false;
    try { value = JSON.parse(raw); } catch { value = { body: String(raw) }; legacy = true; }
    if (!value || typeof value !== 'object') { value = { body: String(raw) }; legacy = true; }
    if (Number(value.version) !== 2) legacy = true;
    const legacyFields = { good: value.good || '', next: value.next || '', score: value.score || '', expected: value.expected || value.expected_behavior || '' };
    const body = typeof value.body === 'string' ? value.body : typeof value.text === 'string' ? value.text : '';
    return {
      version: 2, key, kind: value.kind || meta.kind, body,
      fields: value.fields && typeof value.fields === 'object' ? value.fields : legacyFields,
      target_id: value.target_id ?? meta.target_id, mode: value.mode || meta.mode || null,
      updated_at: value.updated_at || null, save_failed: value.save_failed === true,
      hidden_until: value.hidden_until || null, route: value.route || meta.route,
      focus: value.focus || meta.focus, title: meta.title, legacy,
    };
  }

  function read(key) { return normalize(key, sessionStorage.getItem(key)); }
  function write(key, patch = {}) {
    const meta = descriptor(key); if (!meta) throw new Error('Unsupported draft key');
    const previous = read(key) || { version: 2, key, kind: meta.kind, body: '', fields: {}, target_id: meta.target_id,
      mode: meta.mode || null, updated_at: null, save_failed: false, hidden_until: null, route: meta.route, focus: meta.focus };
    const next = { ...previous, ...patch, version: 2 };
    delete next.key; delete next.title; delete next.legacy;
    if (!Object.prototype.hasOwnProperty.call(patch, 'updated_at')) next.updated_at = new Date().toISOString();
    sessionStorage.setItem(key, JSON.stringify(next));
    return read(key);
  }
  function markFailed(key, patch = {}) { return write(key, { ...patch, save_failed: true, hidden_until: null }); }
  function clear(key) { sessionStorage.removeItem(key); }
  function hide(key, until = new Date(Date.now() + 86400000).toISOString()) { return write(key, { hidden_until: until }); }
  function list() {
    return Array.from({ length: sessionStorage.length }, (_, index) => sessionStorage.key(index) || '')
      .filter(key => key.startsWith(PREFIX)).map(read).filter(Boolean);
  }
  function candidates(at = Date.now()) {
    const eligible = []; const restore = [];
    for (const item of list()) {
      const textLength = item.body.trim().length;
      const updated = item.updated_at ? Date.parse(item.updated_at) : NaN;
      const hidden = item.hidden_until ? Date.parse(item.hidden_until) : NaN;
      const hiddenNow = Number.isFinite(hidden) && hidden > at;
      const age = Number.isFinite(updated) ? at - updated : Infinity;
      if (!hiddenNow && item.save_failed && textLength > 0) eligible.push({ ...item, priority: 0, reason: '前回の保存に失敗しました。入力内容はこの端末に残っています' });
      else if (!hiddenNow && !item.save_failed && textLength >= 10 && age >= 0 && age <= MAX_PRIMARY_AGE) eligible.push({ ...item, priority: 1, reason: '入力途中の内容がこの端末に残っています' });
      else if (textLength > 0 || Object.values(item.fields || {}).some(value => String(value || '').trim())) restore.push({ ...item, old: age >= OLD_AGE, hidden: hiddenNow });
    }
    eligible.sort((a, b) => a.priority - b.priority || String(b.updated_at || '').localeCompare(String(a.updated_at || '')) || a.key.localeCompare(b.key));
    restore.sort((a, b) => String(b.updated_at || '').localeCompare(String(a.updated_at || '')) || a.key.localeCompare(b.key));
    return { eligible, restore };
  }
  window.PersonalOSDraftStore = { read, write, markFailed, clear, hide, list, candidates, descriptor };
})();
