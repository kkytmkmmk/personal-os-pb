/* Adaptive shell for the Personal OS.  Domain/business handlers remain in
   index.html for API compatibility; this file owns navigation, sheets and
   small-screen interaction state. */
(function () {
  'use strict';
  const draftFields = {
    chat: '#chat-message',
    memo: '#record-text',
    capture: '#capture-body',
    decision: '#decision-form'
  };
  let lastFocus = null;

  const $ = (selector, root = document) => root.querySelector(selector);
  const $$ = (selector, root = document) => Array.from(root.querySelectorAll(selector));
  const escapeHtml = value => String(value ?? '').replace(/[&<>"']/g, character => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[character]));
  const announce = (message) => { const node = $('#ui-live'); if (node) node.textContent = message || ''; };
  const FRONTEND_VERSION = '2026.07.26-reliability-1';
  const frontendErrors = [];
  const pushFrontendError = detail => {
    const item = {
      at: new Date().toISOString(), route: location.hash || '#today',
      type: String(detail?.error_type || detail?.type || 'frontend_error'),
      stage: String(detail?.stage || 'ui'), status: Number(detail?.status || 0) || null,
      request_id: String(detail?.request_id || '').slice(0, 120),
      endpoint: String(detail?.path || '').slice(0, 160),
      viewport: `${window.innerWidth}x${window.innerHeight}`,
      online: navigator.onLine !== false, app_version: FRONTEND_VERSION,
    };
    frontendErrors.push(item); while (frontendErrors.length > 20) frontendErrors.shift();
    window.personalOsFrontendErrors = frontendErrors;
  };
  function setupDiagnosticsUI() {
    const settings = $('#settings'); if (!settings || $('#diagnostics-card')) return;
    const card = document.createElement('section'); card.id = 'diagnostics-card'; card.className = 'card';
    card.innerHTML = '<div class="entry-head"><div><h2>診断・信頼性</h2><p class="help">個人データ、本文、Fact、APIキーを含めず、接続と処理状態だけを確認します。</p></div><span class="pill">Diagnostics</span></div><div id="diagnostics-summary" class="help">未実行</div><div class="actions"><button type="button" class="secondary" id="refresh-diagnostics">診断を更新</button><button type="button" class="secondary" id="copy-diagnostics">診断結果をコピー</button></div><details><summary>技術詳細</summary><pre id="diagnostics-details" class="diagnostics-pre"></pre></details>';
    settings.append(card);
    $('#refresh-diagnostics', card).addEventListener('click', refreshDiagnostics);
    $('#copy-diagnostics', card).addEventListener('click', async () => {
      const text = $('#diagnostics-details', card)?.textContent || '';
      try { await navigator.clipboard.writeText(text); announce('個人情報を含まない診断結果をコピーしました'); } catch { announce('コピーできませんでした'); }
    });
    refreshDiagnostics();
  }
  async function refreshDiagnostics() {
    const summary = $('#diagnostics-summary'), details = $('#diagnostics-details'); if (!summary || !details) return;
    const storageAvailable = name => { try { return Boolean(window[name]); } catch { return false; } };
    const local = { frontend_version: FRONTEND_VERSION, viewport: `${window.innerWidth}x${window.innerHeight}`, user_agent: navigator.userAgent.slice(0, 180), route: location.hash || '#today', online: navigator.onLine !== false, display_mode: window.matchMedia?.('(display-mode: standalone)').matches ? 'standalone' : 'browser', service_worker: Boolean(navigator.serviceWorker?.controller), local_storage: storageAvailable('localStorage'), session_storage: storageAvailable('sessionStorage'), frontend_errors: frontendErrors };
    try {
      const response = await window.apiClient.get('/api/diagnostics', { retry: true });
      const server = await response.json();
      const payload = { ...local, ...server };
      summary.textContent = `API: ${server.api_reachable ? '到達' : '未到達'} ／ 認証: ${server.auth?.authenticated ? '済み' : (server.auth?.required ? '必要' : '不要')} ／ 解析: ${server.analysis?.status_label || '-'} ／ エラー履歴: ${frontendErrors.length}`;
      details.textContent = JSON.stringify(payload, null, 2);
    } catch (error) {
      pushFrontendError(error); summary.textContent = `診断APIに接続できません（${error.error_type || 'network_error'}）`; details.textContent = JSON.stringify(local, null, 2);
    }
  }
  function wireActionReliability() {
    window.addEventListener('error', () => pushFrontendError({ type: 'window_error' }));
    window.addEventListener('unhandledrejection', () => pushFrontendError({ type: 'unhandled_rejection' }));
    window.addEventListener('personal-os-api-error', event => { pushFrontendError(event.detail); announce(`処理に失敗しました（${event.detail?.error_type || 'unknown'}）。入力内容は保持されています。詳細は診断を確認してください。`); });
    window.addEventListener('personal-os-api-response', event => {
      const path = event.detail?.path || '';
      const selector = path === '/api/chat' ? '#chat-form' : path === '/api/providers' ? '#provider-form' : path === '/api/decisions' ? '#decision-form' : path === '/api/entries' ? '#capture' : '';
      const form = selector && $(selector); if (!form || form.dataset.actionState !== 'submitting') return;
      form.dataset.actionState = event.detail.ok ? 'success' : 'error';
      form.querySelectorAll('button:disabled').forEach(button => { button.disabled = false; if (button.dataset.previousLabel) button.textContent = button.dataset.previousLabel; });
    });
    window.addEventListener('personal-os-llm-stage', event => pushFrontendError({ ...event.detail, stage: event.detail?.stage || 'llm' }));
    document.addEventListener('submit', event => {
      const form = event.target; if (!(form instanceof HTMLFormElement)) return;
      if (!form.matches('#chat-form,#record-form,#capture,#decision-form,#provider-form,#import-form')) return;
      if (form.dataset.actionState === 'submitting') { event.preventDefault(); return; }
      form.dataset.actionState = 'submitting';
      form.querySelectorAll('button[type="submit"],button:not([type])').forEach(button => { button.disabled = true; button.dataset.previousLabel = button.textContent || ''; button.textContent = '処理中…'; });
      window.setTimeout(() => { if (form.dataset.actionState === 'submitting') { form.dataset.actionState = 'idle'; form.querySelectorAll('button:disabled').forEach(button => { button.disabled = false; if (button.dataset.previousLabel) button.textContent = button.dataset.previousLabel; }); } }, 45000);
    }, true);
    window.addEventListener('personal-os-chat-response', () => { const form = $('#chat-form'); if (form) { form.dataset.actionState = 'success'; form.querySelectorAll('button:disabled').forEach(button => { button.disabled = false; if (button.dataset.previousLabel) button.textContent = button.dataset.previousLabel; }); } });
  }

  const pageAliases = { memory: 'home', admin: 'settings' };
  const pageNames = { today: '今日', chat: '相談', home: '記憶', money: '資産', travel: '旅行', housing: '住居', people: '人間関係', decisions: '判断', explore: '探索', settings: '管理', import: '取込', visualize: '記憶状況', verify: '記憶品質', review: 'レビュー', checkin: 'チェックイン', questions: '質問セット' };

  function setActiveTab(tab) {
    if (!tab) return;
    const canonical = pageAliases[tab] || tab;
    $$('.tab').forEach(section => section.classList.toggle('hidden', section.id !== canonical));
    $$('[data-tab]').forEach(button => {
      const active = (pageAliases[button.dataset.tab] || button.dataset.tab) === canonical;
      button.classList.toggle('active', active);
      if (active) button.setAttribute('aria-current', 'page');
      else button.removeAttribute('aria-current');
    });
  }

  function refreshForTab(tab) {
    const canonical = pageAliases[tab] || tab;
    if (canonical === 'checkin' && typeof refreshCheckins === 'function') refreshCheckins();
    if (canonical === 'review' && typeof refreshReview === 'function') refreshReview();
    if (canonical === 'visualize' && typeof refreshInsights === 'function') refreshInsights();
    if (canonical === 'visualize' && typeof refreshPersonalSpace === 'function') refreshPersonalSpace();
    if (canonical === 'explore' && typeof refreshExplore === 'function') refreshExplore();
    if (canonical === 'benchmark' && typeof refreshBenchmarks === 'function') refreshBenchmarks();
    if (canonical === 'verify' && typeof refreshFactReview === 'function') refreshFactReview();
    if (canonical === 'today' && typeof refreshToday === 'function') refreshToday();
    if (canonical === 'today') refreshTodayCycleSummary();
    if (canonical === 'settings' && typeof refreshSettings === 'function') refreshSettings();
    const renderDomain = window.personalOsRenderDomain || window.refreshDomain;
    if (['money', 'travel', 'housing', 'people'].includes(canonical) && typeof renderDomain === 'function') renderDomain(canonical);
    if (canonical === 'decisions' && typeof refreshDecisions === 'function') refreshDecisions();
  }

  function navigateTo(tab, options = {}) {
    const canonical = pageAliases[tab] || tab;
    if (!document.getElementById(canonical)) return;
    setActiveTab(canonical);
    if (options.push !== false) {
      const hash = `#${canonical === 'home' ? 'memory' : canonical}`;
      if (location.hash !== hash) history.pushState({ page: canonical }, '', hash);
    }
    $$('.ui-sheet').forEach(sheet => closeSheet(sheet));
    window.scrollTo({ top: 0, behavior: 'auto' });
    refreshForTab(canonical);
    announce(`${pageNames[canonical] || canonical}を表示しました`);
  }

  function openSheet(id, opener) {
    if (window.personalOsSheets?.open) return window.personalOsSheets.open(id, opener);
    const sheet = document.getElementById(id);
    if (!sheet) return;
    lastFocus = opener || document.activeElement;
    sheet.hidden = false;
    sheet.classList.remove('hidden');
    document.body.classList.add('sheet-open');
    const first = $('button:not([data-sheet-close])', sheet);
    first?.focus();
  }

  function closeSheet(sheet) {
    if (window.personalOsSheets?.close) return window.personalOsSheets.close(sheet);
    if (!sheet) return;
    sheet.hidden = true;
    sheet.classList.add('hidden');
    document.body.classList.remove('sheet-open');
    if (lastFocus && document.contains(lastFocus)) lastFocus.focus();
    lastFocus = null;
  }

  function activate(tab) { navigateTo(tab); }

  function wireNavigation() {
    $$('[data-tab]').forEach(button => button.addEventListener('click', (event) => {
      event.preventDefault();
      const tab = event.currentTarget.dataset.tab;
      if (!tab) return;
      navigateTo(tab);
    }));
    $$('[data-action="quick"]').forEach(button => button.addEventListener('click', event => openSheet('quick-sheet', event.currentTarget)));
    $$('[data-action="more"]').forEach(button => button.addEventListener('click', event => openSheet('more-sheet', event.currentTarget)));
    $$('[data-action="admin"]').forEach(button => button.addEventListener('click', event => {
      const nav = $('#legacy-nav');
      if (!nav) return;
      const expanded = nav.classList.toggle('admin-open');
      nav.style.display = expanded ? 'flex' : 'none';
      event.currentTarget.setAttribute('aria-expanded', String(expanded));
      announce(expanded ? '管理メニューを開きました' : '管理メニューを閉じました');
    }));
    $$('[data-sheet-close]').forEach(button => button.addEventListener('click', () => closeSheet(button.closest('.ui-sheet'))));
    document.addEventListener('keydown', event => {
      if (event.key === 'Escape') $$('.ui-sheet:not([hidden])').forEach(sheet => closeSheet(sheet));
    });
    window.addEventListener('popstate', () => navigateTo(location.hash.slice(1) || 'today', { push: false }));
    window.addEventListener('hashchange', () => navigateTo(location.hash.slice(1) || 'today', { push: false }));
    window.personalOsNavigate = navigateTo;
  }

  function ensureExploreNavigation() {
    if (!document.getElementById('explore')) return;
    const primary = document.getElementById('os-nav');
    if (primary && !document.getElementById('explore-primary-nav')) {
      const button = document.createElement('button');
      button.id = 'explore-primary-nav'; button.type = 'button'; button.className = 'secondary';
      button.dataset.tab = 'explore'; button.textContent = '探索';
      const admin = primary.querySelector('[data-action="admin"]');
      if (admin) primary.insertBefore(button, admin); else primary.append(button);
    }
    const more = document.querySelector('#more-sheet .secondary-grid');
    if (more && !document.querySelector('#more-sheet [data-tab="explore"]')) {
      const button = document.createElement('button');
      button.id = 'explore-mobile-nav'; button.type = 'button'; button.className = 'secondary';
      button.dataset.tab = 'explore'; button.textContent = '探索'; more.prepend(button);
    }
  }

  function wireQuickActions() {
    $$('[data-quick]').forEach(button => button.addEventListener('click', () => {
      const action = button.dataset.quick;
      $$('.ui-sheet').forEach(sheet => closeSheet(sheet));
      if (action === 'chat') { activate('chat'); setTimeout(() => $('#chat-message')?.focus(), 0); return; }
      if (action === 'memo') { activate('home'); setTimeout(() => $('#record-text')?.focus(), 0); return; }
      if (action === 'screenshot') {
        activate('home');
        setTimeout(() => { const target = $('#screenshot-import') || $('#record-text'); target?.scrollIntoView({ behavior: 'smooth', block: 'center' }); target?.focus?.(); }, 0);
        return;
      }
      if (action === 'decision') { activate('today'); setTimeout(() => $('#decision-form [name="title"]')?.focus(), 0); }
    }));
  }

  function setupRecordUI() {
    const home = $('#home');
    if (!home || $('#record-card')) return;
    const globalStats = $('.stats');
    if (globalStats) { globalStats.classList.add('memory-stats'); home.prepend(globalStats); }
    const legacyCards = Array.from(home.querySelectorAll(':scope > section.card')).slice(0, 2);
    const card = document.createElement('section');
    card.id = 'record-card'; card.className = 'card record-primary';
    card.innerHTML = '<h2>記録する</h2><p class="help">メモ、会話、支出、旅行などを自然文で保存します。分類やタグは後からAIが整理します。</p><form id="record-form"><label for="record-text">記録内容</label><textarea id="record-text" required placeholder="例: 今日、Sample City Aの温泉に行った。次は車なしで移動を短くしたい"></textarea><div class="actions"><button class="secondary voice" type="button" data-target="record-text">音声入力</button><button>保存する</button><span id="record-notice" class="help" aria-live="polite"></span></div></form><details class="record-advanced"><summary>詳細設定・過去の入力</summary><p class="help">通常は使いません。従来の構造化抽出・Raw保存・スクリーンショット入力を利用できます。</p></details>';
    home.prepend(card);
    const advanced = card.querySelector('.record-advanced');
    legacyCards.forEach(legacy => advanced.append(legacy));
    card.querySelector('#record-form').addEventListener('submit', async event => {
      event.preventDefault();
      const field = $('#record-text'), notice = $('#record-notice'), button = event.currentTarget.querySelector('button:not(.voice)');
      const text = field.value.trim(); if (!text) return;
      button.disabled = true; notice.textContent = '保存しています…';
      try {
        const response = await fetch('/api/ingest', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ text }) });
        const data = await response.json().catch(() => ({}));
        notice.textContent = response.ok
          ? '保存しました。AIがバックグラウンドで整理します。'
          : (data.error || '保存できませんでした。入力内容は保持しています。');
        if (response.ok) { field.value = ''; sessionStorage.removeItem('personal-os-draft-memo'); if (typeof refresh === 'function') refresh(); }
      } catch (error) { notice.textContent = '保存できませんでした。入力内容は保持しています。'; }
      finally { button.disabled = false; }
    });
  }

  function cleanupLegacyToday() {
    $('#today-ask-form')?.remove();
    $('#recommendation-panel')?.remove();
    $('#today-overview .quick-actions')?.remove();
    const today = $('#today');
    if (today) {
      today.querySelector(':scope > #cycle-board')?.remove();
      // The legacy Today refresh still owns historical cards. Keep only the
      // read-only overview/candidate/summary projections in the daily view.
      today.querySelectorAll(':scope > section.card').forEach(section => {
        const keep = ['today-daily-actions', 'today-overview', 'today-next-actions', 'today-next-candidates', 'today-cycle-summary'].includes(section.id);
        if (!keep) section.hidden = true;
      });
    }
  }

  function addPageHeaders() {
    const headers = {
      today: ['今日', '今の状態と、次に考えること'],
      chat: ['相談', '自分の記憶を使って一緒に考える'],
      home: ['記憶', '記録したことを残す・探す'],
      money: ['資産', '現在の資産と変化を見る'],
      travel: ['旅行', '訪問履歴と次の候補を見る'],
      housing: ['住居', '現在の住まいと比較材料を見る'],
      people: ['人間関係', '明示されたやりとりと予定を見る'],
      decisions: ['判断', 'DecisionとResultの履歴を見る'],
      settings: ['管理', '取込・AI・バックアップを管理する'],
    };
    Object.entries(headers).forEach(([id, [title, subtitle]]) => {
      const page = $(`#${id}`); if (!page || page.querySelector(':scope > .page-header')) return;
      const header = document.createElement('header'); header.className = 'page-header'; header.innerHTML = `<h2>${title}</h2><p>${subtitle}</p>`; page.prepend(header);
    });
  }

  function wireDrafts() {
    Object.entries(draftFields).forEach(([key, selector]) => {
      const field = $(selector); if (!field) return;
      const storageKey = `personal-os-draft-${key}`;
      const saved = sessionStorage.getItem(storageKey);
      if (saved && (field.value || '').trim() === '') field.value = saved;
      field.addEventListener('input', () => sessionStorage.setItem(storageKey, field.value || ''));
      field.closest('form')?.addEventListener('reset', () => sessionStorage.removeItem(storageKey));
      const clearWhenVisible = () => {
        if (key === 'chat' && !$('#chat-result')?.classList.contains('hidden')) sessionStorage.removeItem(storageKey);
        if (key === 'memo' && $('#ingest-notice')?.textContent.includes('保存')) sessionStorage.removeItem(storageKey);
        if (key === 'capture' && $('#notice')?.textContent.includes('保存')) sessionStorage.removeItem(storageKey);
        if (key === 'decision' && $('#decision-notice')?.textContent.includes('保存')) sessionStorage.removeItem(storageKey);
      };
      new MutationObserver(clearWhenVisible).observe(field.closest('section') || document.body, { subtree: true, childList: true, characterData: true });
    });
  }

  function improveConsultation() {
    const result = $('#chat-result');
    if (!result || $('#chat-context-toggle')) return;
    const heading = result.querySelector('h3');
    const memoryList = $('#chat-memories');
    if (!heading || !memoryList) return;
    heading.textContent = '参照した根拠';
    const toggle = document.createElement('button');
    toggle.id = 'chat-context-toggle'; toggle.type = 'button'; toggle.className = 'secondary context-toggle'; toggle.textContent = '根拠を見る';
    heading.before(toggle);
    memoryList.classList.add('chat-context-body');
    toggle.addEventListener('click', () => {
      const open = memoryList.classList.toggle('is-open');
      toggle.textContent = open ? '根拠を閉じる' : '根拠を見る';
      announce(open ? '参照した根拠を表示しました' : '参照した根拠を閉じました');
    });
  }

  function cycleTrack(stage) {
    const labels = [['recommended', '提案'], ['planned', '計画'], ['decided', '決定'], ['executed', '実行'], ['result', '結果']];
    const order = { recommended: 0, planned: 1, decided: 2, executed: 3, result: 4, evaluated: 4 };
    const current = order[stage] ?? 0;
    return labels.map(([key, label], index) => `<span class="${index <= current ? 'active' : ''}">${index <= current ? '✓ ' : ''}${label}</span>`).join('');
  }

  function resultSheet(cycle, mode) {
    const id = `cycle-result-sheet-${cycle.cycle_id}`;
    document.getElementById(id)?.remove();
    const isEvaluation = mode === 'evaluate';
    const sheet = document.createElement('div');
    sheet.id = id; sheet.className = 'ui-sheet'; sheet.role = 'dialog'; sheet.ariaModal = 'true';
    sheet.innerHTML = `<div class="ui-sheet-backdrop" data-cycle-close></div><section class="ui-sheet-panel"><div class="ui-sheet-grabber"></div><h2>${isEvaluation ? '後日評価を記録' : '結果を記録'}</h2><form><label>${isEvaluation ? '後日評価' : 'どうだった？'}</label><textarea name="comment" required placeholder="良かった点、微妙だった点、次回に活かすこと"></textarea>${isEvaluation ? '' : '<label>満足度（任意）</label><select name="rating"><option value="">未選択</option><option>良かった</option><option>普通</option><option>微妙</option></select>'}<div class="actions"><button>${isEvaluation ? '評価を保存' : '結果を保存'}</button><button type="button" class="secondary" data-cycle-close>キャンセル</button><span class="help" data-cycle-notice></span></div></form></section>`;
    document.body.append(sheet);
    const close = () => sheet.remove();
    sheet.querySelectorAll('[data-cycle-close]').forEach(button => button.addEventListener('click', close));
    sheet.querySelector('textarea')?.focus();
    sheet.querySelector('form').addEventListener('submit', async event => {
      event.preventDefault();
      const data = Object.fromEntries(new FormData(event.currentTarget));
      const endpoint = isEvaluation ? `/api/decisions/${cycle.decision.id}/evaluate` : `/api/decisions/${cycle.decision.id}/result`;
      const payload = isEvaluation ? { later_evaluation: data.comment } : { comment: data.comment, rating: data.rating };
      const response = await fetch(endpoint, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) });
      const result = await response.json().catch(() => ({}));
      const notice = sheet.querySelector('[data-cycle-notice]');
      notice.textContent = response.ok ? '保存しました。' : (result.error || '保存できませんでした。');
      if (response.ok) { close(); refreshCycleBoard(); refreshTodayCycleSummary(); announce('サイクルを更新しました'); }
    });
  }

  function legacyDecisionSheet(id, mode) {
    const sheetId = `decision-edit-sheet-${id}-${mode}`;
    document.getElementById(sheetId)?.remove();
    const isEvaluation = mode === 'evaluate';
    const sheet = document.createElement('div');
    sheet.id = sheetId; sheet.className = 'ui-sheet'; sheet.role = 'dialog'; sheet.ariaModal = 'true';
    sheet.innerHTML = `<div class="ui-sheet-backdrop" data-modal-close></div><section class="ui-sheet-panel"><div class="ui-sheet-grabber"></div><h2>${isEvaluation ? '後日評価を記録' : '結果を記録'}</h2><form><label for="decision-edit-text">${isEvaluation ? '評価' : '実際の結果'}</label><textarea id="decision-edit-text" name="text" required></textarea><div class="actions"><button>${isEvaluation ? '評価を保存' : '結果を保存'}</button><button type="button" class="secondary" data-modal-close>キャンセル</button><span class="help" data-modal-notice></span></div></form></section>`;
    document.body.append(sheet);
    const close = () => sheet.remove();
    sheet.querySelectorAll('[data-modal-close]').forEach(button => button.addEventListener('click', close));
    sheet.querySelector('textarea')?.focus();
    sheet.querySelector('form').addEventListener('submit', async event => {
      event.preventDefault();
      const text = new FormData(event.currentTarget).get('text')?.toString().trim();
      if (!text) return;
      const payload = isEvaluation ? { later_evaluation: text, status: 'revisited' } : { result: text };
      const response = await fetch(`/api/decisions/${id}`, { method: 'PATCH', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) });
      const data = await response.json().catch(() => ({}));
      const notice = sheet.querySelector('[data-modal-notice]');
      notice.textContent = response.ok ? '保存しました。' : (data.error || '更新できませんでした。');
      if (response.ok) { close(); if (typeof refreshDecisions === 'function') refreshDecisions(); if (typeof refreshToday === 'function') refreshToday(); }
    });
  }

  function factCorrectionSheet(id, summary, amount) {
    const sheetId = `fact-correction-sheet-${id}`;
    document.getElementById(sheetId)?.remove();
    const sheet = document.createElement('div');
    sheet.id = sheetId; sheet.className = 'ui-sheet'; sheet.role = 'dialog'; sheet.ariaModal = 'true';
    sheet.innerHTML = `<div class="ui-sheet-backdrop" data-modal-close></div><section class="ui-sheet-panel"><div class="ui-sheet-grabber"></div><h2>記憶を訂正</h2><form><label for="fact-correction-summary">正しい内容</label><textarea id="fact-correction-summary" name="summary" required></textarea><label for="fact-correction-amount">金額（任意）</label><input id="fact-correction-amount" name="amount" inputmode="decimal"><div class="actions"><button>訂正を保存</button><button type="button" class="secondary" data-modal-close>キャンセル</button><span class="help" data-modal-notice></span></div></form></section>`;
    document.body.append(sheet);
    sheet.querySelector('[name="summary"]').value = summary || '';
    sheet.querySelector('[name="amount"]').value = amount || '';
    const close = () => sheet.remove();
    sheet.querySelectorAll('[data-modal-close]').forEach(button => button.addEventListener('click', close));
    sheet.querySelector('[name="summary"]')?.focus();
    sheet.querySelector('form').addEventListener('submit', async event => {
      event.preventDefault();
      const form = new FormData(event.currentTarget);
      const corrected = String(form.get('summary') || '').trim();
      if (!corrected) return;
      const rawAmount = String(form.get('amount') || '').trim();
      const payload = { summary: corrected, reason: '専用画面から訂正' };
      if (!rawAmount) payload.amount = null;
      else if (!Number.isNaN(Number(rawAmount.replaceAll(',', '')))) payload.amount = Number(rawAmount.replaceAll(',', ''));
      const response = await fetch(`/api/facts/${id}`, { method: 'PATCH', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) });
      const data = await response.json().catch(() => ({}));
      const notice = sheet.querySelector('[data-modal-notice]');
      notice.textContent = response.ok ? '訂正を保存しました。' : (data.error || '訂正できませんでした。');
      if (response.ok) { close(); ['money', 'travel', 'housing', 'people'].forEach(domain => { if (!document.querySelector(`#${domain}`)?.classList.contains('hidden') && typeof refreshDomain === 'function') refreshDomain(domain); }); if (typeof refreshToday === 'function') refreshToday(); }
    });
  }

  function overrideLegacyPrompts() {
    window.recordDecisionResult = id => legacyDecisionSheet(Number(id), 'result');
    window.evaluateDecision = id => legacyDecisionSheet(Number(id), 'evaluate');
    window.correctDomainFact = (id, encodedSummary, encodedAmount = '') => factCorrectionSheet(Number(id), decodeURIComponent(encodedSummary || ''), decodeURIComponent(encodedAmount || ''));
  }

  function openLoginSheet() {
    if ($('#auth-login-sheet')) return;
    const sheet = document.createElement('div');
    sheet.id = 'auth-login-sheet'; sheet.className = 'ui-sheet'; sheet.role = 'dialog'; sheet.ariaModal = 'true';
    sheet.innerHTML = '<div class="ui-sheet-backdrop" data-auth-close></div><section class="ui-sheet-panel"><div class="ui-sheet-grabber"></div><h2>Personal OSにログイン</h2><p class="help">LAN接続の認証が必要です。入力内容は保存しません。</p><form><label for="auth-password">パスワード</label><input id="auth-password" name="password" type="password" autocomplete="current-password" required><div class="actions"><button>ログイン</button><span class="help" data-auth-notice></span></div></form></section>';
    document.body.append(sheet);
    const close = () => sheet.remove();
    sheet.querySelectorAll('[data-auth-close]').forEach(button => button.addEventListener('click', close));
    sheet.querySelector('form').addEventListener('submit', async event => {
      event.preventDefault();
      const form = event.currentTarget, button = form.querySelector('button'), notice = sheet.querySelector('[data-auth-notice]');
      button.disabled = true; notice.textContent = '認証しています…';
      const response = await window.apiClient.login(new FormData(form).get('password')?.toString() || '');
      if (response.ok) { close(); announce('ログインしました。処理を再開します。'); }
      else { button.disabled = false; const data = await response.json().catch(() => ({})); notice.textContent = data.error || 'ログインできませんでした。'; }
    });
    sheet.querySelector('#auth-password')?.focus();
  }

  function wireAuthentication() {
    window.addEventListener('personal-os-auth-required', openLoginSheet);
    const api = window.apiClient;
    if (!api) return;
    api.get('/api/auth/status').then(response => response.json().catch(() => ({}))).then(info => {
      if (info.required && !info.authenticated) openLoginSheet();
    }).catch(() => {});
    if (api.getPendingAuth?.()) openLoginSheet();
  }

  async function refreshCycleBoard() {
    const consultation = $('#chat');
    if (!consultation) return;
    let board = $('#cycle-board');
    if (!board) { board = document.createElement('section'); board.id = 'cycle-board'; board.className = 'card'; consultation.append(board); }
    try {
      const recommendations = await fetch('/api/recommendations').then(response => response.json());
      const cycles = [];
      for (const recommendation of (recommendations || []).slice(0, 8)) {
        const cycle = await fetch(`/api/cycles/${Number(recommendation.id)}`).then(response => response.ok ? response.json() : null);
        if (cycle && !['dismissed', 'evaluated'].includes(cycle.cycle_stage)) cycles.push(cycle);
      }
      board.innerHTML = '<div class="entry-head"><div><h2>進行中のサイクル</h2><p class="help">相談から結果まで、現在の位置と次の操作を表示します。</p></div><span class="pill">Cycle</span></div>' + (cycles.length ? cycles.slice(0, 3).map(renderCycle).join('') : '<p class="help">進行中のサイクルはありません。相談から提案を作成できます。</p>');
      board.querySelectorAll('[data-cycle-action]').forEach(button => button.addEventListener('click', () => handleCycleAction(button.dataset.cycleAction, Number(button.dataset.cycleId))));
    } catch (error) { board.innerHTML = '<h2>進行中のサイクル</h2><p class="help">サイクルを読み込めませんでした。</p>'; }
  }

  async function refreshTodayCycleSummary() {
    const today = $('#today');
    if (!today) return;
    let summary = $('#today-cycle-summary');
    if (!summary) {
      summary = document.createElement('section');
      summary.id = 'today-cycle-summary';
      summary.className = 'card cycle-summary';
      today.append(summary);
    }
    try {
      const response = await fetch('/api/today');
      const data = response.ok ? await response.json() : {};
      const cycles = (data.cycles || []).filter(cycle => !['dismissed', 'evaluated'].includes(cycle.cycle_stage));
      summary.innerHTML = '<div class="entry-head"><div><h2>判断サイクル</h2><p class="help">進行中の判断だけを要約しています。</p></div><button type="button" class="secondary" data-open-cycle-detail>続きを見る</button></div>' + (cycles.length ? cycles.slice(0, 3).map(cycle => `<div class="cycle-summary-row"><strong>${escapeHtml(cycle.title || cycle.question || '判断')}</strong><span class="pill">${escapeHtml(cycle.cycle_stage || 'recommended')}</span></div>`).join('') : '<p class="help">進行中の判断はありません。</p>');
      summary.querySelector('[data-open-cycle-detail]')?.addEventListener('click', () => navigateTo('chat'));
    } catch (error) {
      summary.innerHTML = '<h2>判断サイクル</h2><p class="help">要約を読み込めませんでした。</p>';
    }
  }

  function renderCycle(cycle) {
    const rec = cycle.recommendation || {}, plan = cycle.plan, decision = cycle.decision;
    const stage = cycle.cycle_stage;
    let action = '';
    if (stage === 'recommended') action = `<button type="button" data-cycle-action="plan" data-cycle-id="${cycle.cycle_id}">この案を計画にする</button>`;
    else if (stage === 'planned') {
      if (decision && decision.decision_state === 'candidate') {
        const options = (decision.options || rec.options || []).map(option => `<option value="${escapeHtml(option)}">${escapeHtml(option)}</option>`).join('');
        action = `<select data-cycle-option="${cycle.cycle_id}">${options || '<option value="未確定">未確定</option>'}</select><button type="button" data-cycle-action="confirm" data-cycle-id="${cycle.cycle_id}">この判断で記録</button>`;
      } else if (plan) action = `<button type="button" data-cycle-action="decision" data-cycle-id="${plan.id}">この計画で進める</button>`;
    } else if (stage === 'decided') action = `<button type="button" data-cycle-action="execute" data-cycle-id="${decision.id}">実行した</button>`;
    else if (stage === 'executed') action = `<button type="button" data-cycle-action="result" data-cycle-id="${cycle.cycle_id}">結果を記録</button>`;
    else if (stage === 'result') action = `<button type="button" data-cycle-action="evaluate" data-cycle-id="${cycle.cycle_id}">後日評価を記録</button>`;
    const steps = plan?.steps?.slice(0, 5).map(step => `<div class="plan-step"><b>□</b><div>${escapeHtml(step.title || step.detail || step)}</div></div>`).join('') || '';
    return `<article class="cycle-card"><div class="entry-head"><div><h3>${escapeHtml(rec.title || 'サイクル')}</h3><div class="meta">現在: ${stage === 'recommended' ? '提案' : stage === 'planned' ? '計画' : stage === 'decided' ? '決定済み' : stage === 'executed' ? '実行済み' : '結果待ち'}</div></div><span class="pill">${escapeHtml(stage)}</span></div><div class="cycle-track">${cycleTrack(stage)}</div>${steps}<div class="cycle-actions">${action}</div></article>`;
  }

  async function handleCycleAction(action, id) {
    let endpoint = '', payload = {};
    if (action === 'plan') { endpoint = `/api/recommendations/${id}/plan`; }
    if (action === 'decision') { endpoint = `/api/plans/${id}/decision`; }
    if (action === 'confirm') {
      const button = document.querySelector(`[data-cycle-action="confirm"][data-cycle-id="${id}"]`);
      const option = button?.parentElement?.querySelector('[data-cycle-option]')?.value || '';
      const cycle = await fetch(`/api/cycles/${id}`).then(response => response.json());
      if (!cycle.decision) return;
      endpoint = `/api/decisions/${cycle.decision.id}`; payload = { selected_option: option, decision_state: 'decided' };
    }
    if (action === 'execute') { endpoint = `/api/decisions/${id}/execute`; payload = { note: 'ユーザーが実行した' }; }
    if (action === 'result' || action === 'evaluate') {
      const cycle = await fetch(`/api/cycles/${id}`).then(response => response.json());
      if (cycle.decision) resultSheet(cycle, action === 'evaluate' ? 'evaluate' : 'result');
      return;
    }
    if (!endpoint) return;
    const response = await fetch(endpoint, { method: action === 'confirm' ? 'PATCH' : 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) });
    if (!response.ok && action !== 'confirm') { announce('サイクルを更新できませんでした'); return; }
    await refreshCycleBoard(); refreshTodayCycleSummary(); announce('サイクルを更新しました');
  }

  function legacyCandidateObserverDisabled() {
    return;
    /* legacy candidate observer retained below for reference; API responses
       are now delivered through personalOsHandleChatResponse. */
    /* const originalFetch = window.fetch.bind(window);
    // legacy global fetch hook removed; api-client.js owns requests.
      const response = await originalFetch(input, init);
      const url = typeof input === 'string' ? input : input?.url || '';
      if (url.endsWith('/api/chat') && response.ok) {
        response.clone().json().then(data => {
          window.personalOsLastConsultation = data;
          const candidate = data.recommendation_candidate;
          if (!candidate || $('#chat-recommendation-candidate')) return;
          const result = $('#chat-result'); if (!result) return;
          const card = document.createElement('section'); card.id = 'chat-recommendation-candidate'; card.className = 'summary-card';
          card.innerHTML = `<h3>提案候補</h3><p>${escapeHtml(candidate.summary || '保存済みの文脈から提案候補を作成しました。')}</p><div class="options">${(candidate.options || []).slice(0, 3).map(option => `<span class="pill">${escapeHtml(option)}</span>`).join('')}</div><div class="actions"><button type="button" data-save-consultation>提案として保存</button></div>`;
          result.prepend(card);
          card.querySelector('[data-save-consultation]').addEventListener('click', async () => {
            const save = await fetch('/api/recommendations/generate', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ domain: candidate.domain, question: candidate.title }) });
            if (save.ok) { card.querySelector('[data-save-consultation]').textContent = '保存しました'; refreshCycleBoard(); refreshTodayCycleSummary(); }
          });
        }).catch(() => {});
      }
      return response;
    }; */
  }

  function renderConsultationCandidate(data) {
    window.dispatchEvent(new CustomEvent('personal-os-llm-stage', { detail: { stage: 'ui_rendered', provider: data?.provider || '', model: data?.model || '', request_id: data?.request_id || '' } }));
    window.personalOsLastConsultation = data;
    const candidate = data?.recommendation_candidate;
    if (!candidate || $('#chat-recommendation-candidate')) return;
    const result = $('#chat-result'); if (!result) return;
    const card = document.createElement('section'); card.id = 'chat-recommendation-candidate'; card.className = 'summary-card';
    card.innerHTML = `<h3>提案候補</h3><p>${escapeHtml(candidate.summary || '相談内容から提案候補を作成しました。')}</p><div class="options">${(candidate.options || []).slice(0, 3).map(option => `<span class="pill">${escapeHtml(option)}</span>`).join('')}</div><div class="actions"><button type="button" data-save-consultation>提案として保存</button><span class="help" data-candidate-notice></span></div>`;
    result.prepend(card);
    card.querySelector('[data-save-consultation]').addEventListener('click', async event => {
      const button = event.currentTarget, notice = card.querySelector('[data-candidate-notice]');
      button.disabled = true; button.textContent = '保存しています…';
      const save = await fetch('/api/recommendations/generate', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ candidate }) });
      if (save.ok) { button.textContent = '保存しました'; refreshCycleBoard(); refreshTodayCycleSummary(); }
      else { button.disabled = false; button.textContent = '提案として保存'; notice.textContent = save.error_info?.message || '提案を保存できませんでした。'; }
    });
  }

  function init() {
    wireActionReliability();
    setupRecordUI();
    addPageHeaders();
    ensureExploreNavigation();
    wireNavigation();
    wireQuickActions();
    wireDrafts();
    window.personalOsHandleChatResponse = renderConsultationCandidate;
    window.addEventListener('personal-os-chat-response', event => renderConsultationCandidate(event.detail || {}));
    wireAuthentication();
    setupDiagnosticsUI();
    overrideLegacyPrompts();
    improveConsultation();
    refreshCycleBoard();
    cleanupLegacyToday();
    const active = location.hash.slice(1) || 'today';
    navigateTo(active, { push: false });
    const todayObserver = new MutationObserver(cleanupLegacyToday);
    todayObserver.observe($('#today') || document.body, { subtree: true, childList: true });
    // Result is inserted by the existing chat handler; enhance it after each update.
    new MutationObserver(improveConsultation).observe($('#chat') || document.body, { subtree: true, childList: true });
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init, { once: true });
  else init();
})();
