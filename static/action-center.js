/* Phase B-UX1 stabilization: safe Action Center and bounded Review Inbox. */
(() => {
  'use strict';
  const $ = (selector, root = document) => root.querySelector(selector);
  const $$ = (selector, root = document) => [...root.querySelectorAll(selector)];
  const esc = value => String(value ?? '').replace(/[&<>"']/g, character => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[character]));
  const api = (path, options) => window.apiClient?.request(path, options) || window.fetch(path, options);
  const navigate = route => window.personalOsNavigate?.(route);
  const DRAFT_MAX_AGE = 72 * 60 * 60 * 1000;
  const DRAFT_RESTORE_AGE = 7 * 24 * 60 * 60 * 1000;
  const MASKED_SUMMARY = '機微情報の確認が必要です';
  let inboxBucket = 'urgent';
  let inboxDomain = '';
  let showInboxList = false;
  let inboxItems = [];
  let inboxCursor = null;
  let processedInFocus = 0;
  let focusPaused = false;
  const presented = new Set();
  const revealed = new Map();

  const draftRoutes = [
    [/^personal-os-draft-memo$/, 'home', '書きかけの記録を続ける', '#record-text'],
    [/^personal-os-draft-chat$/, 'chat', '書きかけの相談を続ける', '#chat-message'],
    [/^personal-os-draft-decision-\d+-result$/, 'decisions', '書きかけの結果を続ける', ''],
    [/^personal-os-draft-decision-\d+-evaluation$/, 'decisions', '書きかけの後日評価を続ける', ''],
    [/^personal-os-draft-ux-feedback$/, 'settings', '書きかけのフィードバックを続ける', ''],
  ];

  function parseDraft(key) {
    const raw = sessionStorage.getItem(key);
    if (!raw) return null;
    const matched = draftRoutes.find(([pattern]) => pattern.test(key));
    if (!matched) return null;
    try {
      const data = JSON.parse(raw);
      if (!data || typeof data !== 'object' || typeof data.body !== 'string') throw new Error('legacy');
      return { key, body: data.body, updated_at: data.updated_at || null, save_failed: data.save_failed === true,
        hidden_until: data.hidden_until || null, route: data.route || matched[1], focus: data.focus || matched[3], title: matched[2], legacy: false };
    } catch {
      return { key, body: raw, updated_at: null, save_failed: false, hidden_until: null,
        route: matched[1], focus: matched[3], title: matched[2], legacy: true };
    }
  }

  function draftCandidates() {
    const now = Date.now();
    const drafts = Array.from({ length: sessionStorage.length }, (_, index) => sessionStorage.key(index) || '')
      .map(parseDraft).filter(Boolean).filter(item => item.body.trim().length >= 10);
    const eligible = [];
    const restore = [];
    drafts.forEach(item => {
      const updated = item.updated_at ? Date.parse(item.updated_at) : NaN;
      const hidden = item.hidden_until ? Date.parse(item.hidden_until) : NaN;
      if (Number.isFinite(hidden) && hidden > now) return;
      if (!Number.isFinite(updated) || updated > now + 60000) { restore.push(item); return; }
      const age = now - updated;
      if (item.save_failed) eligible.push({ ...item, priority: 0, reason: '前回の保存に失敗しました。入力内容はこの端末に残っています' });
      else if (age <= DRAFT_MAX_AGE) eligible.push({ ...item, priority: 1, reason: '入力途中の内容がこの端末に残っています' });
      else if (age >= DRAFT_RESTORE_AGE) restore.push(item);
    });
    eligible.sort((a, b) => a.priority - b.priority || Date.parse(b.updated_at) - Date.parse(a.updated_at) || a.key.localeCompare(b.key));
    restore.sort((a, b) => String(b.updated_at || '').localeCompare(String(a.updated_at || '')));
    return { eligible, restore };
  }

  function clientDraftAction() {
    const draft = draftCandidates().eligible[0];
    return draft ? { ...draft, kind: 'client_draft', action_label: draft.save_failed ? '再試行する' : '続ける', can_snooze: false } : null;
  }

  function saveDraftMetadata(draft, patch) {
    sessionStorage.setItem(draft.key, JSON.stringify({ version: 2, body: draft.body, updated_at: draft.updated_at,
      save_failed: draft.save_failed, hidden_until: draft.hidden_until, route: draft.route, focus: draft.focus, ...patch }));
  }

  function actionRoute(action) {
    if (action.kind === 'fact_review' || action.kind === 'memory_proposal') {
      inboxBucket = action.bucket || 'urgent'; navigate('verify'); window.setTimeout(() => refreshReviewInbox(true), 0); return;
    }
    navigate(action.route || 'today');
    if (action.kind === 'decision_result' || action.kind === 'decision_evaluation') {
      window.setTimeout(() => window.personalOsOpenDecisionReplay?.(Number(action.id), null), 0);
    } else if (action.focus) window.setTimeout(() => $(action.focus)?.focus(), 0);
  }

  function bindDraftActions(card, action) {
    if (action.kind !== 'client_draft') return;
    $('[data-draft-hide]', card)?.addEventListener('click', () => {
      saveDraftMetadata(action, { hidden_until: new Date(Date.now() + 24 * 60 * 60 * 1000).toISOString() });
      refreshActionCenter();
    });
    $('[data-draft-discard]', card)?.addEventListener('click', () => {
      if (!window.confirm('この下書きを破棄しますか？')) return;
      sessionStorage.removeItem(action.key); refreshActionCenter();
    });
    $$('[data-old-draft-key]', card).forEach(button => button.addEventListener('click', () => {
      const draft = parseDraft(button.dataset.oldDraftKey || ''); if (draft) actionRoute({ ...draft, kind: 'client_draft' });
    }));
  }

  function renderTopAction(action, counts) {
    const card = $('#today-daily-actions'); if (!card) return;
    const restore = draftCandidates().restore;
    const statusItems = [['今確認', counts.urgent_reviews || 0], ['結果待ち', counts.result_waiting || 0],
      ['後日評価', counts.evaluation_waiting || 0], ['最近の変化', counts.recent_changes || 0]]
      .filter(([, count]) => Number(count) > 0).slice(0, 3);
    const draftButtons = action.kind === 'client_draft'
      ? '<button type="button" class="secondary" data-draft-hide>今回は表示しない</button><button type="button" class="secondary" data-draft-discard>破棄</button>' : '';
    const oldDrafts = restore.length ? `<details class="old-draft-list"><summary>古い下書きを見る（${restore.length}件）</summary>${restore.slice(0, 5).map(item => `<button type="button" class="secondary" data-old-draft-key="${esc(item.key)}">${esc(item.title)}</button>`).join('')}</details>` : '';
    card.className = 'card action-center-card';
    card.innerHTML = `<div class="action-center-kicker">次にすること</div><h2>${esc(action.title || '記録する')}</h2><p class="action-reason">${esc(action.reason || '')}</p><div class="actions action-center-buttons"><button type="button" data-action-primary>${esc(action.action_label || '開く')}</button>${draftButtons}${action.can_snooze ? '<button type="button" class="secondary" data-action-defer>後で</button>' : ''}</div><div class="action-defer-menu hidden" data-action-defer-menu><button type="button" class="secondary" data-defer-for="one_day">1日後</button><button type="button" class="secondary" data-defer-for="one_week">1週間後</button><button type="button" class="secondary" data-defer-for="indefinite">Inboxに残す</button></div>${statusItems.length ? `<div class="action-status" aria-label="現在の件数">${statusItems.map(([label, count]) => `<span><b>${Number(count)}</b>${esc(label)}</span>`).join('')}</div>` : ''}<p class="help action-inbox-link">${Number(counts.normal_reviews || 0) + Number(counts.deferred_reviews || 0) > 0 ? '通常の確認事項は確認Inboxにあります。' : '今すぐ対応する項目を1件だけ表示しています。'}</p>${oldDrafts}<div class="quick-actions"><button type="button" class="secondary" data-quick-route="home">記録する</button><button type="button" class="secondary" data-quick-route="chat">相談する</button><button type="button" class="secondary" data-quick-route="verify">確認Inbox</button></div>`;
    $('[data-action-primary]', card)?.addEventListener('click', () => actionRoute(action));
    $('[data-action-defer]', card)?.addEventListener('click', () => $('[data-action-defer-menu]', card)?.classList.toggle('hidden'));
    $$('[data-defer-for]', card).forEach(button => button.addEventListener('click', async () => {
      button.disabled = true; const deferFor = button.dataset.deferFor;
      const response = action.kind === 'fact_review'
        ? await api(`/api/facts/${Number(action.id)}/review`, { method: 'PATCH', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ state: deferFor === 'indefinite' ? 'deferred' : 'pending', defer_for: deferFor }) })
        : await api('/api/action-center/snooze', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ action_key: action.key, defer_for: deferFor }) });
      if (response.ok) await refreshActionCenter(); else button.disabled = false;
    }));
    $$('[data-quick-route]', card).forEach(button => button.addEventListener('click', () => navigate(button.dataset.quickRoute)));
    bindDraftActions(card, action);
  }

  function renderDigest(data) {
    let digest = $('#today-digest');
    if (!digest) {
      digest = document.createElement('section'); digest.id = 'today-digest'; digest.className = 'card today-digest';
      const actionCard = $('#today-daily-actions'); if (actionCard) actionCard.after(digest); else $('#today')?.append(digest);
    }
    const recent = (data.recent_changes || []).slice(0, 2); const prompts = (data.consultation_prompts || []).slice(0, 3);
    digest.innerHTML = `<section class="digest-headline"><h2>今日の一言</h2><p>${esc(data.headline?.text || '最近の大きな変化はまだありません')}</p></section><section class="digest-section"><div class="digest-section-heading"><h3>最近変わったこと</h3><button type="button" class="secondary" data-digest-timeline>変化を見る</button></div>${recent.map(item => `<div class="timeline-row"><b>${esc(item.text || '記憶の更新')}</b></div>`).join('') || '<p class="help">最近の変化はまだありません。</p>'}</section><details class="digest-secondary"><summary>思い出す・相談候補</summary><div class="digest-prompt-list">${prompts.map(item => `<button type="button" class="secondary" data-digest-prompt="${esc(item.text || '')}">${esc(item.text || '相談する')}</button>`).join('') || '<p class="help">相談候補はまだありません。</p>'}</div></details>`;
    $('[data-digest-timeline]', digest)?.addEventListener('click', () => { navigate('explore'); window.setTimeout(() => $('[data-explore-mode="timeline"]')?.click(), 0); });
    $$('[data-digest-prompt]', digest).forEach(button => button.addEventListener('click', () => { navigate('chat'); window.setTimeout(() => { const field = $('#chat-message'); if (field) { field.value = button.dataset.digestPrompt || ''; field.dispatchEvent(new Event('input', { bubbles: true })); field.focus(); } }, 0); }));
  }

  async function refreshActionCenter() {
    const card = $('#today-daily-actions'); if (!card) return;
    try {
      const response = await api('/api/today/digest'); if (!response.ok) throw new Error('action-center');
      const data = await response.json(); renderTopAction(clientDraftAction() || data.top_action || {}, data.status_counts || {}); renderDigest(data);
      ['today-overview', 'today-next-actions', 'today-next-candidates', 'today-cycle-summary'].forEach(id => { const node = $(`#${id}`); if (node) node.hidden = true; });
    } catch {
      card.innerHTML = '<h2>次にすること</h2><p class="help">いまは次の行動を読み込めません。入力内容は失われていません。</p><div class="quick-actions"><button type="button" class="secondary" data-quick-route="home">記録する</button><button type="button" class="secondary" data-quick-route="chat">相談する</button></div>';
      $$('[data-quick-route]', card).forEach(button => button.addEventListener('click', () => navigate(button.dataset.quickRoute)));
    }
  }

  function itemKey(item) { return `${item.item_kind || 'fact'}:${Number(item.id)}`; }
  function detailFor(item) { return revealed.get(itemKey(item)); }
  function valueLabel(item) { try { const value = JSON.parse(item.value_json || '{}'); return [value.asset, value.amount, value.currency].filter(value => value !== null && value !== undefined && value !== '').join(' ・ '); } catch { return ''; } }

  function reviewActions(item) {
    if (item.item_kind === 'memory_proposal') return item.bucket === 'deferred'
      ? '<button type="button" data-proposal-resume>確認を再開</button>'
      : '<button type="button" data-proposal-apply>保存する</button><button type="button" class="secondary" data-proposal-edit>修正して保存</button><button type="button" class="secondary" data-proposal-discard>保存しない</button>';
    return item.bucket === 'deferred'
      ? '<button type="button" data-review-state="pending">確認を再開</button>'
      : '<button type="button" data-review-state="confirmed">正しい</button><button type="button" class="secondary" data-review-correct>修正</button><button type="button" class="secondary" data-review-state="rejected">違う</button>';
  }

  function reviewCard(item, focus) {
    const detail = detailFor(item); const sensitiveHidden = item.sensitive && !detail;
    const shown = detail || item;
    const heading = sensitiveHidden ? `${item.domain_label || '機微'}情報の確認候補` : (shown.summary || item.summary || '確認が必要な記憶');
    const body = sensitiveHidden
      ? '<p class="help">機微情報のため内容を隠しています。確認操作の後だけ、この画面内に表示します。</p>'
      : `<div class="body">${esc(valueLabel(shown) || shown.summary || '')}</div><details class="review-evidence"><summary>根拠を見る</summary><p class="source">${esc(shown.document_title || '原文')} / Evidence ${Number(shown.evidence_count || 0)}件</p><div class="body">${esc(shown.evidence || shown.source_preview || '確認できる根拠はありません。')}</div></details>`;
    const actions = sensitiveHidden
      ? '<button type="button" data-review-reveal>内容を確認する</button><button type="button" class="secondary" data-review-defer>後で</button>'
      : `${reviewActions(item)}${item.bucket !== 'deferred' ? '<button type="button" class="secondary" data-review-defer>後で</button>' : ''}${item.sensitive ? '<button type="button" class="secondary" data-review-close>内容を閉じる</button>' : ''}`;
    return `<article class="review-card${focus ? ' review-focus-card' : ''}" data-review-id="${Number(item.id)}" data-review-kind="${esc(item.item_kind || 'fact')}"><div class="entry-head"><div><span class="review-domain">${esc(item.domain_label || 'その他')}</span><h3>${esc(heading)}</h3></div><span class="pill">${item.bucket === 'urgent' ? '今確認' : item.bucket === 'deferred' ? 'あとで' : '通常'}</span></div><p class="review-reason">${esc(item.priority_reason || '')}</p>${body}<div class="actions review-actions">${actions}</div><div class="review-defer-menu hidden"><button type="button" class="secondary" data-review-period="one_day">1日後</button><button type="button" class="secondary" data-review-period="one_week">1週間後</button><button type="button" class="secondary" data-review-period="indefinite">Inboxに残す</button></div></article>`;
  }

  async function markPresented(item) {
    const key = itemKey(item); if (presented.has(key)) return; presented.add(key);
    try {
      const response = await api(`/api/review-inbox/${item.item_kind === 'memory_proposal' ? 'memory-proposal' : 'fact'}/${Number(item.id)}/presented`, { method: 'POST' });
      if (!response.ok) presented.delete(key);
    } catch (_error) {
      // Presentation metadata must never break or obscure the review UI.
      presented.delete(key);
    }
  }

  async function completeReview() {
    processedInFocus += 1; revealed.clear();
    if (processedInFocus >= 3) focusPaused = true;
    await refreshReviewInbox(true);
  }

  async function correctFact(item) {
    const source = detailFor(item) || item;
    if (source.summary === MASKED_SUMMARY) return;
    const summary = window.prompt('正しい要約', source.summary || ''); if (summary === null) return;
    let value = {}; try { value = JSON.parse(source.value_json || '{}'); } catch { value = {}; }
    const valueText = window.prompt('正しい値（JSON）', JSON.stringify(value, null, 2)); if (valueText === null) return;
    try { value = JSON.parse(valueText); } catch { window.alert('JSON形式を確認してください'); return; }
    const response = await api(`/api/facts/${Number(item.id)}`, { method: 'PATCH', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ summary, value, reason: '確認Inboxで訂正' }) });
    if (response.ok) await completeReview();
  }

  function bindReviewCards(root) {
    $$('[data-review-state]', root).forEach(button => button.addEventListener('click', async () => {
      const card = button.closest('[data-review-id]');
      const response = await api(`/api/facts/${Number(card.dataset.reviewId)}/review`, { method: 'PATCH', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ state: button.dataset.reviewState }) });
      if (response.ok) { if (button.dataset.reviewState === 'pending') await refreshReviewInbox(true); else await completeReview(); }
    }));
    $$('[data-review-correct]', root).forEach(button => button.addEventListener('click', () => {
      const card = button.closest('[data-review-id]'); const item = inboxItems.find(candidate => candidate.item_kind === 'fact' && Number(candidate.id) === Number(card.dataset.reviewId)); if (item) correctFact(item);
    }));
    $$('[data-review-reveal]', root).forEach(button => button.addEventListener('click', async () => {
      const card = button.closest('[data-review-id]'); const id = Number(card.dataset.reviewId); const kind = card.dataset.reviewKind;
      const path = kind === 'memory_proposal' ? `/api/review-inbox/proposals/${id}/detail?include_sensitive=true` : `/api/review-inbox/${id}/detail?include_sensitive=true`;
      const response = await api(path); if (!response.ok) return; revealed.set(`${kind}:${id}`, await response.json()); renderInbox();
    }));
    $$('[data-review-close]', root).forEach(button => button.addEventListener('click', () => { const card = button.closest('[data-review-id]'); revealed.delete(`${card.dataset.reviewKind}:${Number(card.dataset.reviewId)}`); renderInbox(); }));
    $$('[data-review-defer]', root).forEach(button => button.addEventListener('click', () => $('.review-defer-menu', button.closest('[data-review-id]'))?.classList.toggle('hidden')));
    $$('[data-review-period]', root).forEach(button => button.addEventListener('click', async () => {
      const card = button.closest('[data-review-id]');
      const response = card.dataset.reviewKind === 'fact'
        ? await api(`/api/facts/${Number(card.dataset.reviewId)}/review`, { method: 'PATCH', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ state: button.dataset.reviewPeriod === 'indefinite' ? 'deferred' : 'pending', defer_for: button.dataset.reviewPeriod }) })
        : await api(`/api/review-inbox/memory-proposal/${Number(card.dataset.reviewId)}/snooze`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ defer_for: button.dataset.reviewPeriod }) });
      if (response.ok) await completeReview();
    }));
    $$('[data-proposal-resume]', root).forEach(button => button.addEventListener('click', async () => { const card = button.closest('[data-review-id]'); const response = await api(`/api/review-inbox/memory-proposal/${Number(card.dataset.reviewId)}/snooze`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: '{"defer_for":"resume"}' }); if (response.ok) await refreshReviewInbox(true); }));
    $$('[data-proposal-apply]', root).forEach(button => button.addEventListener('click', async () => { const card = button.closest('[data-review-id]'); const response = await api(`/api/memory-proposals/${Number(card.dataset.reviewId)}/apply`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: '{}' }); if (response.ok) await completeReview(); }));
    $$('[data-proposal-edit]', root).forEach(button => button.addEventListener('click', async () => {
      const card = button.closest('[data-review-id]'); const id = Number(card.dataset.reviewId); let detail = revealed.get(`memory_proposal:${id}`);
      if (!detail) { const response = await api(`/api/review-inbox/proposals/${id}/detail?include_sensitive=true`); if (!response.ok) return; detail = await response.json(); }
      const edited = window.prompt('保存するFact候補をJSON配列で修正', JSON.stringify(detail.facts || [], null, 2)); if (edited === null) return;
      try { const facts = JSON.parse(edited); const response = await api(`/api/memory-proposals/${id}/apply`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ facts }) }); if (response.ok) await completeReview(); } catch { window.alert('JSON形式を確認してください'); }
    }));
    $$('[data-proposal-discard]', root).forEach(button => button.addEventListener('click', async () => { const card = button.closest('[data-review-id]'); const response = await api(`/api/memory-proposals/${Number(card.dataset.reviewId)}/discard`, { method: 'POST' }); if (response.ok) await completeReview(); }));
  }

  function renderInbox() {
    const focus = $('#review-inbox-focus'); const list = $('#review-inbox-list'); if (!focus || !list) return;
    if (focusPaused) {
      focus.innerHTML = '<div class="empty-state review-pause"><h3>3件確認しました</h3><p>今日はここまでにしても、候補の状態は変わりません。</p><div class="actions"><button type="button" data-review-stop>今日はここまで</button><button type="button" class="secondary" data-review-continue>続けて確認する</button></div></div>';
      list.innerHTML = ''; $('[data-review-stop]', focus)?.addEventListener('click', () => navigate('today')); $('[data-review-continue]', focus)?.addEventListener('click', () => { processedInFocus = 0; focusPaused = false; renderInbox(); }); return;
    }
    focus.innerHTML = inboxItems.length ? reviewCard(inboxItems[0], true) : '<div class="empty-state"><p>この区分に確認事項はありません。</p><button type="button" class="secondary" data-review-record>記録する</button></div>';
    list.innerHTML = showInboxList && inboxItems.length > 1 ? inboxItems.slice(1).map(item => reviewCard(item, false)).join('') : '';
    const load = $('#review-inbox-load-more'); if (load) load.hidden = !(showInboxList && inboxCursor);
    bindReviewCards(focus); bindReviewCards(list); $('[data-review-record]', focus)?.addEventListener('click', () => navigate('home'));
    if (inboxItems[0]) markPresented(inboxItems[0]); if (showInboxList) inboxItems.slice(1).forEach(markPresented);
  }

  async function refreshReviewInbox(reset = true) {
    const focus = $('#review-inbox-focus'); if (!focus) return; focus.setAttribute('aria-busy', 'true');
    try {
      const query = new URLSearchParams({ bucket: inboxBucket, limit: '10' }); if (inboxDomain) query.set('domain', inboxDomain); if (!reset && inboxCursor) query.set('cursor', inboxCursor);
      const response = await api(`/api/review-inbox?${query}`); if (!response.ok) throw new Error('review-inbox'); const data = await response.json();
      inboxItems = reset ? (data.items || []) : inboxItems.concat(data.items || []); inboxCursor = data.next_cursor || null; if (reset) revealed.clear();
      const counts = data.counts || {}; $('#review-inbox-counts').innerHTML = `<span><b>${Number(counts.urgent || 0)}</b> 今確認</span><span><b>${Number(counts.normal || 0)}</b> 通常</span><span><b>${Number(counts.deferred || 0)}</b> あとで</span>`;
      $('#review-inbox-list-toggle').textContent = showInboxList ? '1件ずつ確認する' : '一覧を見る'; renderInbox();
    } catch { focus.innerHTML = '<p class="help">確認Inboxを読み込めませんでした。記憶の状態は変更されていません。</p>'; }
    finally { focus.removeAttribute('aria-busy'); }
  }

  function setupReviewInbox() {
    const page = $('#verify'); if (!page) return;
    page.innerHTML = `<header class="page-header"><h2>確認Inbox</h2><p>重要で、自動では解決できない記憶だけを確認します。</p></header><section class="card review-inbox-card"><div class="entry-head"><div><h2>確認する記憶</h2><p class="help">優先度順に1件ずつ表示します。</p></div><div id="review-inbox-counts" class="review-counts"></div></div><div class="review-tabs" role="tablist"><button type="button" data-review-bucket="urgent">今確認したい</button><button type="button" class="secondary" data-review-bucket="normal">通常</button><button type="button" class="secondary" data-review-bucket="deferred">あとで</button><button type="button" class="secondary" data-review-bucket="all">すべて</button></div><div class="review-filter"><label for="review-domain-filter">分野</label><select id="review-domain-filter"><option value="">すべて</option><option value="finance">資産</option><option value="travel">旅行</option><option value="housing">住居</option><option value="relationship">人間関係</option><option value="work">仕事</option><option value="health">健康</option><option value="life">生活</option><option value="other">その他</option></select></div><div id="review-inbox-focus"></div><div class="actions"><button id="review-inbox-list-toggle" type="button" class="secondary">一覧を見る</button><button id="review-inbox-load-more" type="button" class="secondary" hidden>さらに読み込む</button></div><div id="review-inbox-list"></div></section>`;
    $$('[data-review-bucket]', page).forEach(button => button.addEventListener('click', () => { inboxBucket = button.dataset.reviewBucket; processedInFocus = 0; focusPaused = false; $$('[data-review-bucket]', page).forEach(tab => { tab.classList.toggle('secondary', tab !== button); tab.classList.toggle('active', tab === button); }); refreshReviewInbox(true); }));
    $('#review-domain-filter')?.addEventListener('change', event => { inboxDomain = event.target.value; processedInFocus = 0; focusPaused = false; refreshReviewInbox(true); });
    $('#review-inbox-list-toggle')?.addEventListener('click', () => { showInboxList = !showInboxList; renderInbox(); $('#review-inbox-list-toggle').textContent = showInboxList ? '1件ずつ確認する' : '一覧を見る'; });
    $('#review-inbox-load-more')?.addEventListener('click', () => refreshReviewInbox(false)); window.refreshFactReview = () => refreshReviewInbox(true);
  }

  function moveMaintenance() {
    const settings = $('#settings'); if (!settings || $('#memory-maintenance')) return;
    const details = document.createElement('details'); details.id = 'memory-maintenance'; details.className = 'card maintenance-details';
    details.innerHTML = '<summary><b>記憶メンテナンス</b><span class="help">必要なときだけ実行</span></summary><p class="help">自動判定、監査、修復、再解析などの管理操作です。</p><div class="actions" data-maintenance-actions></div><div data-maintenance-status></div>';
    const actions = $('[data-maintenance-actions]', details); ['auto-resolve-facts', 'memory-quality-recheck', 'memory-quality-repair', 'memory-quality-resegment', 'refresh-inferences'].forEach(id => { const button = $(`#${id}`); if (button) actions.append(button); });
    ['fact-review-summary', 'memory-quality-summary', 'inference-summary'].forEach(id => { const node = $(`#${id}`); if (node) $('[data-maintenance-status]', details).append(node); }); settings.append(details);
  }

  function init() {
    moveMaintenance(); setupReviewInbox(); $$('[data-tab="verify"]').forEach(button => { button.textContent = '確認Inbox'; }); $$('[data-tab="review"]').forEach(button => { button.textContent = '週次レビュー'; });
    refreshActionCenter(); window.refreshActionCenter = refreshActionCenter; window.refreshReviewInbox = () => refreshReviewInbox(true); window.refreshTodayDigest = refreshActionCenter;
    window.addEventListener('hashchange', () => { if ((location.hash || '#today') === '#today') refreshActionCenter(); });
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', () => window.setTimeout(init, 1), { once: true }); else init();
})();
