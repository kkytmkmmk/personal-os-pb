/* Phase B-UX1: one next action on Today and a deterministic Review Inbox. */
(() => {
  'use strict';
  const $ = (selector, root = document) => root.querySelector(selector);
  const $$ = (selector, root = document) => [...root.querySelectorAll(selector)];
  const esc = value => String(value ?? '').replace(/[&<>"']/g, character => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[character]));
  const api = (path, options) => window.apiClient?.request(path, options) || window.fetch(path, options);
  const navigate = route => window.personalOsNavigate?.(route);
  let inboxBucket = 'urgent';
  let inboxDomain = '';
  let showInboxList = false;

  const draftRoutes = [
    [/^personal-os-draft-memo$/, 'home', '書きかけの記録を続ける', '#record-text'],
    [/^personal-os-draft-chat$/, 'chat', '書きかけの相談を続ける', '#chat-message'],
    [/^personal-os-draft-decision-\d+-result$/, 'decisions', '書きかけの結果を続ける', ''],
    [/^personal-os-draft-decision-\d+-evaluation$/, 'decisions', '書きかけの後日評価を続ける', ''],
    [/^personal-os-draft-ux-feedback$/, 'settings', '書きかけのフィードバックを続ける', ''],
  ];

  function clientDraftAction() {
    const keys = Array.from({ length: sessionStorage.length }, (_, index) => sessionStorage.key(index) || '');
    for (const match of draftRoutes) {
      const key = keys.find(candidate => match[0].test(candidate));
      const value = key ? sessionStorage.getItem(key) || '' : '';
      if (!value.trim()) continue;
      return { key, kind: 'client_draft', title: match[2], reason: '入力途中の内容がこの端末に残っています', action_label: '続ける', route: match[1], focus: match[3], can_snooze: false };
    }
    const failed = sessionStorage.getItem('personal-os-failed-action');
    if (failed) return { key: 'failed:retry', kind: 'failed_retry', title: '保存できなかった入力を再試行する', reason: '前回の入力内容はこの端末に保持されています', action_label: '入力を確認する', route: failed, can_snooze: false };
    return null;
  }

  function actionRoute(action) {
    if (action.kind === 'fact_review') {
      inboxBucket = action.bucket || 'urgent';
      navigate('verify');
      window.setTimeout(refreshReviewInbox, 0);
      return;
    }
    navigate(action.route || 'today');
    if (action.kind === 'decision_result' || action.kind === 'decision_evaluation') {
      window.setTimeout(() => window.personalOsOpenDecisionReplay?.(Number(action.id), null), 0);
    } else if (action.focus) {
      window.setTimeout(() => $(action.focus)?.focus(), 0);
    }
  }

  function renderTopAction(action, counts) {
    const card = $('#today-daily-actions');
    if (!card) return;
    const statusItems = [
      ['今確認', counts.urgent_reviews || 0], ['結果待ち', counts.result_waiting || 0],
      ['後日評価', counts.evaluation_waiting || 0], ['最近の変化', counts.recent_changes || 0],
    ].filter(([, count]) => Number(count) > 0).slice(0, 3);
    card.className = 'card action-center-card';
    card.innerHTML = `<div class="action-center-kicker">次にすること</div><h2>${esc(action.title || '記録する')}</h2><p class="action-reason">${esc(action.reason || '')}</p><div class="actions action-center-buttons"><button type="button" data-action-primary>${esc(action.action_label || '開く')}</button>${action.can_snooze ? '<button type="button" class="secondary" data-action-defer>後で</button>' : ''}</div><div class="action-defer-menu hidden" data-action-defer-menu><button type="button" class="secondary" data-defer-for="one_day">1日後</button><button type="button" class="secondary" data-defer-for="one_week">1週間後</button><button type="button" class="secondary" data-defer-for="indefinite">Inboxに残す</button></div>${statusItems.length ? `<div class="action-status" aria-label="現在の件数">${statusItems.map(([label, count]) => `<span><b>${Number(count)}</b>${esc(label)}</span>`).join('')}</div>` : ''}<p class="help action-inbox-link">${Number(counts.normal_reviews || 0) + Number(counts.deferred_reviews || 0) > 0 ? 'ほかの確認事項は確認Inboxにあります。' : '今すぐ対応する項目を1件だけ表示しています。'}</p><div class="quick-actions"><button type="button" class="secondary" data-quick-route="home">記録する</button><button type="button" class="secondary" data-quick-route="chat">相談する</button><button type="button" class="secondary" data-quick-route="verify">確認Inbox</button></div>`;
    $('[data-action-primary]', card)?.addEventListener('click', () => actionRoute(action));
    $('[data-action-defer]', card)?.addEventListener('click', () => $('[data-action-defer-menu]', card)?.classList.toggle('hidden'));
    $$('[data-defer-for]', card).forEach(button => button.addEventListener('click', async () => {
      const deferFor = button.dataset.deferFor;
      button.disabled = true;
      const response = action.kind === 'fact_review'
        ? await api(`/api/facts/${Number(action.id)}/review`, { method: 'PATCH', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ state: 'deferred', defer_for: deferFor }) })
        : await api('/api/action-center/snooze', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ action_key: action.key, defer_for: deferFor }) });
      if (response.ok) await refreshActionCenter();
      else button.disabled = false;
    }));
    $$('[data-quick-route]', card).forEach(button => button.addEventListener('click', () => navigate(button.dataset.quickRoute)));
  }

  async function refreshActionCenter() {
    const card = $('#today-daily-actions');
    if (!card) return;
    try {
      const response = await api('/api/today/digest');
      if (!response.ok) throw new Error('action-center');
      const data = await response.json();
      renderTopAction(clientDraftAction() || data.top_action || {}, data.status_counts || {});
      const digest = $('#today-digest');
      if (digest) {
        const recent = (data.recent_changes || []).slice(0, 2);
        const prompts = (data.consultation_prompts || []).slice(0, 3);
        digest.innerHTML = `<section class="digest-headline"><h2>今日の一言</h2><p>${esc(data.headline?.text || '最近の大きな変化はまだありません')}</p></section><section class="digest-section"><div class="digest-section-heading"><h3>最近変わったこと</h3><button type="button" class="secondary" data-digest-timeline>変化を見る</button></div>${recent.map(item => `<div class="timeline-row"><b>${esc(item.text || '記憶の更新')}</b></div>`).join('') || '<p class="help">最近の変化はまだありません。</p>'}</section><details class="digest-secondary"><summary>思い出す・相談候補</summary><div class="digest-prompt-list">${prompts.map(item => `<button type="button" class="secondary" data-digest-prompt="${esc(item.text || '')}">${esc(item.text || '相談する')}</button>`).join('') || '<p class="help">相談候補はまだありません。</p>'}</div></details>`;
        $('[data-digest-timeline]', digest)?.addEventListener('click', () => { navigate('explore'); window.setTimeout(() => $('[data-explore-mode="timeline"]')?.click(), 0); });
        $$('[data-digest-prompt]', digest).forEach(button => button.addEventListener('click', () => { navigate('chat'); window.setTimeout(() => { const field = $('#chat-message'); if (field) { field.value = button.dataset.digestPrompt || ''; field.dispatchEvent(new Event('input', { bubbles: true })); field.focus(); } }, 0); }));
      }
      ['today-overview', 'today-next-actions', 'today-next-candidates', 'today-cycle-summary'].forEach(id => { const node = $(`#${id}`); if (node) node.hidden = true; });
    } catch {
      card.innerHTML = '<h2>次にすること</h2><p class="help">いまは次の行動を読み込めません。入力内容は失われていません。</p><div class="quick-actions"><button type="button" class="secondary" data-quick-route="home">記録する</button><button type="button" class="secondary" data-quick-route="chat">相談する</button></div>';
      $$('[data-quick-route]', card).forEach(button => button.addEventListener('click', () => navigate(button.dataset.quickRoute)));
    }
  }

  function reviewCard(item, focus) {
    const technical = `<details class="review-technical"><summary>技術情報</summary><p class="source">抽出: ${esc(item.extractor || '不明')} / ${esc(item.extractor_model || '')} / ${esc(item.prompt_version || '')}</p></details>`;
    const evidence = item.sensitive ? '<p class="help">機微情報のため、一覧では原文を表示しません。</p>' : `<details class="review-evidence"><summary>根拠を見る</summary><p class="source">${esc(item.document_title || '原文')} / Evidence ${Number(item.evidence_count || 0)}件</p><div class="body">${esc(item.evidence || '確認できる根拠がありません。')}</div></details>`;
    return `<article class="review-card${focus ? ' review-focus-card' : ''}" data-review-id="${Number(item.id)}"><div class="entry-head"><div><span class="review-domain">${esc(item.domain_label || 'その他')}</span><h3>${esc(item.summary || '確認が必要な記憶')}</h3></div><span class="pill">${item.bucket === 'urgent' ? '今確認' : item.bucket === 'deferred' ? 'あとで' : '通常'}</span></div><p class="review-reason">${esc(item.priority_reason || '')}</p>${evidence}${technical}<div class="actions review-actions">${item.bucket === 'deferred' ? '<button type="button" data-review-state="pending">確認を再開</button>' : '<button type="button" data-review-state="confirmed">正しい</button><button type="button" class="secondary" data-review-correct>修正</button><button type="button" class="secondary" data-review-state="rejected">違う</button><button type="button" class="secondary" data-review-defer>後で</button>'}</div><div class="review-defer-menu hidden"><button type="button" class="secondary" data-review-period="one_day">1日後</button><button type="button" class="secondary" data-review-period="one_week">1週間後</button><button type="button" class="secondary" data-review-period="indefinite">Inboxに残す</button></div></article>`;
  }

  function bindReviewCards(root) {
    $$('[data-review-state]', root).forEach(button => button.addEventListener('click', async () => {
      const card = button.closest('[data-review-id]');
      const response = await api(`/api/facts/${Number(card.dataset.reviewId)}/review`, { method: 'PATCH', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ state: button.dataset.reviewState }) });
      if (response.ok) await refreshReviewInbox();
    }));
    $$('[data-review-correct]', root).forEach(button => button.addEventListener('click', () => window.correctFactFromReview?.(Number(button.closest('[data-review-id]').dataset.reviewId))));
    $$('[data-review-defer]', root).forEach(button => button.addEventListener('click', () => $('.review-defer-menu', button.closest('[data-review-id]'))?.classList.toggle('hidden')));
    $$('[data-review-period]', root).forEach(button => button.addEventListener('click', async () => {
      const card = button.closest('[data-review-id]');
      const response = await api(`/api/facts/${Number(card.dataset.reviewId)}/review`, { method: 'PATCH', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ state: 'deferred', defer_for: button.dataset.reviewPeriod }) });
      if (response.ok) await refreshReviewInbox();
    }));
  }

  async function refreshReviewInbox() {
    const focus = $('#review-inbox-focus');
    const list = $('#review-inbox-list');
    if (!focus || !list) return;
    focus.setAttribute('aria-busy', 'true');
    try {
      const query = new URLSearchParams({ bucket: inboxBucket, limit: '30' });
      if (inboxDomain) query.set('domain', inboxDomain);
      const response = await api(`/api/review-inbox?${query}`);
      if (!response.ok) throw new Error('review-inbox');
      const data = await response.json();
      const items = data.items || [];
      window.reviewFactsById = Object.fromEntries(items.map(item => [item.id, item]));
      const counts = data.counts || {};
      $('#review-inbox-counts').innerHTML = `<span><b>${Number(counts.urgent || 0)}</b> 今確認</span><span><b>${Number(counts.normal || 0)}</b> 通常</span><span><b>${Number(counts.deferred || 0)}</b> あとで</span>`;
      focus.innerHTML = items.length ? reviewCard(items[0], true) : '<div class="empty-state"><p>この区分に確認事項はありません。</p><button type="button" class="secondary" data-review-record>記録する</button></div>';
      list.innerHTML = showInboxList && items.length > 1 ? items.slice(1).map(item => reviewCard(item, false)).join('') : '';
      $('#review-inbox-list-toggle').textContent = showInboxList ? '1件ずつ確認する' : `一覧を見る${items.length > 1 ? `（${items.length}件）` : ''}`;
      bindReviewCards(focus); bindReviewCards(list);
      $('[data-review-record]', focus)?.addEventListener('click', () => navigate('home'));
    } catch {
      focus.innerHTML = '<p class="help">確認Inboxを読み込めませんでした。記憶の状態は変更されていません。</p>';
    } finally { focus.removeAttribute('aria-busy'); }
  }

  function setupReviewInbox() {
    const page = $('#verify');
    if (!page) return;
    page.innerHTML = `<header class="page-header"><h2>確認Inbox</h2><p>重要で、自動では解決できない記憶だけを確認します。</p></header><section class="card review-inbox-card"><div class="entry-head"><div><h2>確認する記憶</h2><p class="help">優先度順に1件ずつ表示します。</p></div><div id="review-inbox-counts" class="review-counts"></div></div><div class="review-tabs" role="tablist"><button type="button" data-review-bucket="urgent">今確認したい</button><button type="button" class="secondary" data-review-bucket="normal">通常</button><button type="button" class="secondary" data-review-bucket="deferred">あとで</button><button type="button" class="secondary" data-review-bucket="all">すべて</button></div><div class="review-filter"><label for="review-domain-filter">分野</label><select id="review-domain-filter"><option value="">すべて</option><option value="finance">資産</option><option value="travel">旅行</option><option value="housing">住居</option><option value="relationship">人間関係</option><option value="work">仕事</option><option value="health">健康</option><option value="life">生活</option><option value="other">その他</option></select></div><div id="review-inbox-focus"></div><div class="actions"><button id="review-inbox-list-toggle" type="button" class="secondary">一覧を見る</button></div><div id="review-inbox-list"></div></section>`;
    $$('[data-review-bucket]', page).forEach(button => button.addEventListener('click', () => {
      inboxBucket = button.dataset.reviewBucket;
      $$('[data-review-bucket]', page).forEach(tab => { tab.classList.toggle('secondary', tab !== button); tab.classList.toggle('active', tab === button); });
      refreshReviewInbox();
    }));
    $('#review-domain-filter')?.addEventListener('change', event => { inboxDomain = event.target.value; refreshReviewInbox(); });
    $('#review-inbox-list-toggle')?.addEventListener('click', () => { showInboxList = !showInboxList; refreshReviewInbox(); });
    window.refreshFactReview = refreshReviewInbox;
  }

  function moveMaintenance() {
    const settings = $('#settings');
    if (!settings || $('#memory-maintenance')) return;
    const details = document.createElement('details');
    details.id = 'memory-maintenance'; details.className = 'card maintenance-details';
    details.innerHTML = '<summary><b>記憶メンテナンス</b><span class="help">必要なときだけ実行</span></summary><p class="help">自動判定、監査、修復、再解析などの管理操作です。</p><div class="actions" data-maintenance-actions></div><div data-maintenance-status></div>';
    const actions = $('[data-maintenance-actions]', details);
    ['auto-resolve-facts', 'memory-quality-recheck', 'memory-quality-repair', 'memory-quality-resegment', 'refresh-inferences'].forEach(id => { const button = $(`#${id}`); if (button) actions.append(button); });
    ['fact-review-summary', 'memory-quality-summary', 'inference-summary'].forEach(id => { const node = $(`#${id}`); if (node) $('[data-maintenance-status]', details).append(node); });
    const relocateCategoryAudit = () => { const categoryAudit = $('#category-audit'); if (categoryAudit && categoryAudit.parentElement !== details) details.append(categoryAudit); };
    relocateCategoryAudit();
    details.addEventListener('click', event => {
      const destructive = event.target.closest('#memory-quality-repair,#memory-quality-resegment');
      if (destructive && !window.confirm('記憶全体を再評価します。検証内容を確認してから実行してください。続けますか？')) {
        event.preventDefault(); event.stopImmediatePropagation();
      }
    }, true);
    settings.append(details);
    const verify = $('#verify');
    if (verify) new MutationObserver(relocateCategoryAudit).observe(verify, { childList: true });
  }

  function relabelNavigation() {
    $$('[data-tab="verify"]').forEach(button => { button.textContent = '確認Inbox'; });
    $$('[data-tab="review"]').forEach(button => { button.textContent = '週次レビュー'; });
  }

  function init() {
    moveMaintenance();
    setupReviewInbox();
    relabelNavigation();
    refreshActionCenter();
    window.refreshActionCenter = refreshActionCenter;
    window.refreshReviewInbox = refreshReviewInbox;
    window.addEventListener('personal-os-api-error', event => {
      const route = event.detail?.path === '/api/chat' ? 'chat' : event.detail?.path === '/api/ingest' ? 'home' : '';
      if (route) sessionStorage.setItem('personal-os-failed-action', route);
    });
    window.addEventListener('personal-os-api-response', event => {
      if (event.detail?.ok && ['/api/chat', '/api/ingest'].includes(event.detail?.path)) sessionStorage.removeItem('personal-os-failed-action');
    });
    window.addEventListener('hashchange', () => { if ((location.hash || '#today') === '#today') refreshActionCenter(); });
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', () => window.setTimeout(init, 1), { once: true });
  else init();
})();
