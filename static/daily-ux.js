/* Daily-use UX layer.  It deliberately keeps the local API and data model
   unchanged while making the existing screens behave as one coherent app. */
(() => {
  'use strict';
  const $ = (selector, root = document) => root.querySelector(selector);
  const $$ = (selector, root = document) => [...root.querySelectorAll(selector)];
  const escapeHtml = value => String(value ?? '').replace(/[&<>"']/g, character => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[character]));
  const announce = message => { const live = $('#ui-live'); if (live) live.textContent = message; };
  const visible = element => Boolean(element && (element.offsetWidth || element.offsetHeight || element.getClientRects().length));
  const navigate = tab => window.personalOsNavigate?.(tab);
  const sheetOpeners = new Map();

  function openSheet(id, opener) {
    const sheet = $(`#${id}`);
    if (!sheet) return;
    if (opener) sheetOpeners.set(id, opener);
    sheet.hidden = false;
    sheet.classList.remove('hidden');
    $('.ui-sheet-panel button, .ui-sheet-panel input, .ui-sheet-panel textarea', sheet)?.focus();
  }

  function closeSheet(sheet) {
    if (!sheet) return;
    sheet.hidden = true;
    sheet.classList.add('hidden');
    const opener = sheetOpeners.get(sheet.id);
    opener?.focus();
  }

  function wireStaticSheets() {
    $$('[data-action="domains"]').forEach(button => button.addEventListener('click', () => openSheet('domains-sheet', button)));
    $$('[data-sheet-close]').forEach(button => button.addEventListener('click', () => closeSheet(button.closest('.ui-sheet'))));
    document.addEventListener('keydown', event => {
      if (event.key === 'Escape') $$('.ui-sheet:not([hidden])').forEach(closeSheet);
    });
  }

  function addDraft(field, key) {
    if (!field) return;
    const storageKey = `personal-os-draft-${key}`;
    if (!field.value && sessionStorage.getItem(storageKey)) field.value = sessionStorage.getItem(storageKey);
    field.addEventListener('input', () => sessionStorage.setItem(storageKey, field.value));
    field.closest('form')?.addEventListener('submit', () => field.closest('form').dataset.draftKey = storageKey);
  }

  function clearDraftFor(form) {
    const key = form?.dataset.draftKey;
    if (key) sessionStorage.removeItem(key);
  }

  function wireMutationState() {
    document.addEventListener('submit', event => {
      const form = event.target;
      if (!(form instanceof HTMLFormElement) || !form.matches('#record-form,#screenshot-form,#benchmark-import-form,#decision-outcome-form')) return;
      if (form.dataset.submitting === 'true') { event.preventDefault(); return; }
      form.dataset.submitting = 'true';
      const submit = form.querySelector('button[type="submit"], button:not([type])');
      if (submit) { submit.dataset.label = submit.textContent; submit.disabled = true; submit.textContent = '保存中…'; }
      window.setTimeout(() => {
        if (form.dataset.submitting !== 'true') return;
        form.dataset.submitting = 'false';
        if (submit) { submit.disabled = false; submit.textContent = submit.dataset.label || '保存する'; }
      }, 45000);
    }, true);
    window.addEventListener('personal-os-api-response', event => {
      if (!event.detail?.ok) return;
      $$('#record-form,#screenshot-form,#benchmark-import-form,#decision-outcome-form').forEach(form => {
        if (form.dataset.submitting !== 'true') return;
        form.dataset.submitting = 'false';
        const submit = form.querySelector('button[type="submit"], button:not([type])');
        if (submit) { submit.disabled = false; submit.textContent = submit.dataset.label || '保存する'; }
        clearDraftFor(form);
      });
    });
  }

  function unifyCapture() {
    const home = $('#home'), record = $('#record-card');
    if (!home || !record || record.dataset.dailyReady) return;
    record.dataset.dailyReady = 'true';
    $('h2', record).textContent = '覚えておいてほしいこと';
    $('.help', record).textContent = '今日あったこと、予定、買ったもの、気になったことを、そのまま残せます。AIがあとから整理します。';
    const form = $('#record-form', record), actions = $('.actions', form);
    if (actions && !$('#record-image-open')) actions.insertAdjacentHTML('afterbegin', '<button id="record-image-open" class="secondary" type="button">画像を追加</button>');
    const advanced = $('.record-advanced', record);
    if (advanced) {
      advanced.querySelectorAll('#ingest-form,#capture').forEach(form => form.closest('.card')?.remove());
      advanced.querySelector('p.help')?.remove();
      advanced.querySelector('summary').textContent = '詳細設定';
    }
    const screenshot = $('#screenshot-import');
    if (screenshot) {
      const attachment = document.createElement('details');
      attachment.id = 'record-image-details';
      attachment.className = 'record-advanced';
      attachment.innerHTML = '<summary>画像から記録する</summary>';
      attachment.append(screenshot);
      advanced?.after(attachment);
      $('#record-image-open')?.addEventListener('click', () => { attachment.open = true; attachment.scrollIntoView({ block: 'center' }); $('#screenshot-form input[type="file"]')?.focus(); });
    }
    form?.addEventListener('submit', () => {
      const notice = $('#record-notice');
      if (notice) notice.textContent = '保存しました。AIがバックグラウンドで整理します。';
    });
    addDraft($('#record-text'), 'memo');
    addDraft($('#screenshot-form [name="context"]'), 'screenshot-context');
  }

  function positionToday() {
    const page = $('#today');
    const card = $('#today-daily-actions');
    if (!page || !card) return;
    const header = $('.page-header', page);
    if (header && header.nextElementSibling !== card) header.after(card);
    const overview = $('#today-overview'); if (overview && card.nextElementSibling !== overview) card.after(overview);
    const cycle = $('#today-cycle-summary'); if (cycle && overview?.nextElementSibling !== cycle) overview?.after(cycle);
  }

  function prepareToday() {
    const page = $('#today');
    if (!page || $('#today-daily-actions')) { positionToday(); return; }
    const card = document.createElement('section');
    card.id = 'today-daily-actions'; card.className = 'card daily-actions-card';
    card.innerHTML = '<h2>いま、何をする？</h2><p class="help">相談するか、覚えておきたいことを記録します。</p><div class="actions"><button type="button" data-daily-action="chat">相談する</button><button type="button" class="secondary" data-daily-action="record">記録する</button></div>';
    page.prepend(card);
    $('[data-daily-action="chat"]', card).addEventListener('click', () => { navigate('chat'); window.setTimeout(() => $('#chat-message')?.focus(), 0); });
    $('[data-daily-action="record"]', card).addEventListener('click', () => { navigate('home'); window.setTimeout(() => $('#record-text')?.focus(), 0); });
    positionToday();
    new MutationObserver(positionToday).observe(page, { childList: true });
  }

  async function refreshNextActions() {
    const page = $('#today');
    if (!page) return;
    let card = $('#today-next-actions');
    if (!card) { card = document.createElement('section'); card.id = 'today-next-actions'; card.className = 'card'; const cycle = $('#today-cycle-summary'); (cycle || $('#today-overview') || page.lastElementChild)?.after(card); }
    try {
      const snapshot = await fetch('/api/today').then(response => response.json());
      const items = (snapshot.next_candidates || []).slice(0, 3);
      card.innerHTML = `<h2>次に対応すること</h2>${items.length ? items.map(item => `<article class="timeline-row"><b>${escapeHtml(item.title || '確認すること')}</b><span>${escapeHtml(item.reason || '')}</span></article>`).join('') : '<div class="empty-state"><p>今すぐ対応が必要なことはありません。</p><button type="button" class="secondary" data-empty-chat>相談する</button></div>'}`;
      $('[data-empty-chat]', card)?.addEventListener('click', () => navigate('chat'));
    } catch { card.innerHTML = '<h2>次に対応すること</h2><p class="help">いまは確認できません。入力内容は失われていません。</p>'; }
  }

  function streamlineConsultation() {
    const page = $('#chat'), result = $('#chat-result');
    if (!page || !result) return;
    const form = $('#chat-form');
    if (!form || form.dataset.consultationReady) return;
    form.dataset.consultationReady = 'true';
    const examples = document.createElement('div');
    examples.className = 'consultation-examples';
    examples.innerHTML = '<p class="help">例: 「次の旅行を決めたい」「この判断を整理したい」</p><p id="consultation-status" class="help" role="status" aria-live="polite"></p>';
    form.after(examples);
    const status = $('#consultation-status');
    const collapseEvidence = () => {
      const memories = $('#chat-memories');
      if (!memories || memories.closest('details')) return;
      const details = document.createElement('details'); details.className = 'chat-context';
      details.innerHTML = '<summary>参照した根拠を見る</summary>';
      memories.before(details); details.append(memories);
      result.querySelector('h3')?.remove();
    };
    const renderResponseContext = data => {
      window.setTimeout(() => {
        collapseEvidence();
        result.querySelector('#consultation-missing')?.remove();
        const missing = Array.isArray(data?.missing_context) ? data.missing_context.slice(0, 3) : [];
        if (missing.length) {
          const section = document.createElement('section');
          section.id = 'consultation-missing'; section.className = 'consultation-missing';
          section.innerHTML = `<h3>確認できると、より良く答えられること</h3><ul>${missing.map(item => `<li><b>${escapeHtml(item.label || '追加情報')}</b>${item.reason ? `<span>${escapeHtml(item.reason)}</span>` : ''}</li>`).join('')}</ul>`;
          const context = result.querySelector('.chat-context');
          (context || result.lastElementChild)?.before(section);
        }
        const responseType = { answer_only: '回答', recommendation: '提案', planning: '計画', decision_review: '判断の整理' }[data?.response_type] || '回答';
        if (status) status.textContent = `${responseType}を表示しました。根拠は必要なときだけ開けます。`;
        announce(`${responseType}を表示しました`);
      }, 0);
    };
    form.addEventListener('submit', () => {
      result.querySelector('#chat-recommendation-candidate')?.remove();
      result.querySelector('#consultation-missing')?.remove();
      if (status) status.textContent = '記憶と過去の判断を確認しています…';
      window.setTimeout(() => { if (form.dataset.actionState === 'submitting' && status) status.textContent = '関連する情報を選んでいます…'; }, 300);
    }, true);
    window.addEventListener('personal-os-chat-response', event => renderResponseContext(event.detail || {}));
    window.addEventListener('personal-os-api-error', event => {
      if (event.detail?.path === '/api/chat' && status) status.textContent = '相談を完了できませんでした。入力内容はそのままです。';
    });
    new MutationObserver(collapseEvidence).observe(result, { childList: true, subtree: true });
    collapseEvidence();
    addDraft($('#chat-message'), 'chat');
  }

  function outcomeSheet() {
    let sheet = $('#decision-outcome-sheet');
    if (sheet) return sheet;
    sheet = document.createElement('div');
    sheet.id = 'decision-outcome-sheet'; sheet.className = 'ui-sheet hidden'; sheet.hidden = true;
    sheet.setAttribute('role', 'dialog'); sheet.setAttribute('aria-modal', 'true');
    sheet.innerHTML = '<div class="ui-sheet-backdrop" data-sheet-close></div><section class="ui-sheet-panel"><div class="ui-sheet-grabber"></div><h2 id="decision-outcome-title">結果を記録する</h2><form id="decision-outcome-form"><label for="decision-outcome-text">どうだったか</label><textarea id="decision-outcome-text" required></textarea><label for="decision-outcome-good">良かった点（任意）</label><textarea id="decision-outcome-good"></textarea><label for="decision-outcome-next">次回に活かすこと（任意）</label><textarea id="decision-outcome-next"></textarea><label for="decision-outcome-score">満足度（任意）</label><select id="decision-outcome-score"><option value="">選ばない</option><option>良かった</option><option>微妙だった</option><option>悪かった</option></select><div class="actions"><button type="submit">保存する</button><button type="button" class="secondary" data-sheet-close>閉じる</button></div><p id="decision-outcome-notice" class="help" aria-live="polite"></p></form></section>';
    document.body.append(sheet);
    $$('[data-sheet-close]', sheet).forEach(button => button.addEventListener('click', () => closeSheet(sheet)));
    return sheet;
  }

  function streamlineDecisions() {
    const page = $('#decisions');
    if (!page) return;
    const board = $('#cycle-board');
    if (board && board.parentElement !== page) page.append(board);
    const existing = $('#decisions-content');
    if (existing && !$('#decision-filters')) {
      const controls = document.createElement('div');
      controls.id = 'decision-filters'; controls.className = 'decision-filters';
      controls.innerHTML = '<label>領域<select id="decision-domain-filter"><option value="">すべて</option><option value="money">資産</option><option value="travel">旅行</option><option value="housing">住居</option><option value="people">人間関係</option><option value="other">その他</option></select></label><label>状態<select id="decision-state-filter"><option value="">すべて</option><option value="actionable">対応が必要</option><option value="candidate">候補</option><option value="decided">決定済み</option><option value="executed">実行済み</option><option value="result">結果待ち・振り返り</option></select></label>';
      existing.before(controls);
      $$('#decision-filters select').forEach(select => select.addEventListener('change', () => window.refreshDecisions?.()));
    }
    const openOutcome = (id, mode) => {
      const sheet = outcomeSheet(), form = $('#decision-outcome-form', sheet), title = $('#decision-outcome-title', sheet);
      title.textContent = mode === 'evaluate' ? '後日評価を記録する' : '結果を記録する';
      form.dataset.decisionId = String(id); form.dataset.mode = mode;
      const draftKey = `personal-os-draft-decision-${id}-${mode}`;
      const saved = sessionStorage.getItem(draftKey);
      if (saved) { try { const data = JSON.parse(saved); $('#decision-outcome-text', sheet).value = data.text || ''; $('#decision-outcome-good', sheet).value = data.good || ''; $('#decision-outcome-next', sheet).value = data.next || ''; $('#decision-outcome-score', sheet).value = data.score || ''; } catch { /* ignore corrupt local draft */ } }
      form.dataset.draftKey = draftKey; openSheet(sheet.id, document.activeElement instanceof HTMLElement ? document.activeElement : undefined);
    };
    window.recordDecisionResult = id => openOutcome(id, 'result');
    window.evaluateDecision = id => openOutcome(id, 'evaluate');
    window.personalOsOpenDecisionOutcome = openOutcome;
    const sheet = outcomeSheet(), form = $('#decision-outcome-form', sheet);
    ['#decision-outcome-text','#decision-outcome-good','#decision-outcome-next','#decision-outcome-score'].forEach(selector => $(selector, sheet)?.addEventListener('input', () => sessionStorage.setItem(form.dataset.draftKey || '', JSON.stringify({ text: $('#decision-outcome-text', sheet).value, good: $('#decision-outcome-good', sheet).value, next: $('#decision-outcome-next', sheet).value, score: $('#decision-outcome-score', sheet).value }))));
    form.addEventListener('submit', async event => {
      event.preventDefault();
      const id = form.dataset.decisionId, mode = form.dataset.mode, text = $('#decision-outcome-text', sheet).value.trim();
      const next = $('#decision-outcome-next', sheet).value.trim(), score = $('#decision-outcome-score', sheet).value;
      if (!id || !text) return;
      const value = [text, $('#decision-outcome-good', sheet).value.trim() && `良かった点: ${$('#decision-outcome-good', sheet).value.trim()}`, next && `次回: ${next}`, score && `満足度: ${score}`].filter(Boolean).join('\n');
      const payload = mode === 'evaluate' ? { later_evaluation: value, status: 'revisited' } : { result: value };
      const response = await fetch(`/api/decisions/${id}`, { method: 'PATCH', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) });
      const notice = $('#decision-outcome-notice', sheet);
      if (!response.ok) { notice.textContent = '保存できませんでした。入力内容は保持しています。'; return; }
      notice.textContent = '保存しました。'; sessionStorage.removeItem(form.dataset.draftKey || ''); form.reset(); closeSheet(sheet);
      window.refreshDecisions?.(); window.refreshToday?.(); announce('判断の結果を保存しました');
    });
    const decisionState = item => {
      if (item.later_evaluation) return '振り返り済み';
      return ({ candidate: '候補', considered: '検討中', decided: '決定済み', executed: '結果待ち', result: '後日評価待ち' }[item.decision_state] || (item.result ? '後日評価待ち' : '決定済み'));
    };
    const actionFor = item => {
      const id = Number(item.id);
      if (item.later_evaluation) return '<span class="pill">振り返り済み</span>';
      if (item.decision_state === 'candidate' || item.decision_state === 'considered') {
        let options = []; try { options = JSON.parse(item.options_json || '[]'); } catch { /* no options */ }
        const select = options.length ? `<select data-decision-option="${id}">${options.map(option => `<option value="${escapeHtml(option)}">${escapeHtml(option)}</option>`).join('')}</select>` : '';
        return `${select}<button type="button" data-decision-action="confirm" data-decision-id="${id}">この判断で決定する</button>`;
      }
      if (item.decision_state === 'decided') return `<button type="button" data-decision-action="execute" data-decision-id="${id}">実行した</button>`;
      if (item.decision_state === 'executed') return `<button type="button" data-decision-outcome="${id}" data-outcome-mode="result">結果を記録する</button>`;
      if (item.decision_state === 'result' || item.result) return `<button type="button" data-decision-outcome="${id}" data-outcome-mode="evaluate">後日評価を記録する</button>`;
      return `<button type="button" data-decision-outcome="${id}" data-outcome-mode="result">結果を記録する</button>`;
    };
    window.refreshDecisions = async () => {
      const target = $('#decisions-content');
      if (!target) return;
      try {
        const allItems = await fetch('/api/decisions').then(response => response.json());
        const domain = $('#decision-domain-filter')?.value || '', state = $('#decision-state-filter')?.value || '';
        const domainAliases = { money: ['money', 'finance'], people: ['people', 'relationship'] };
        const items = allItems.filter(item => (!domain || (domainAliases[domain] || [domain]).includes(item.domain)) && (!state || (state === 'actionable' ? ['candidate', 'considered', 'decided', 'executed', 'result'].includes(item.decision_state) && !item.later_evaluation : item.decision_state === state || (state === 'result' && Boolean(item.result)))));
        const priority = { candidate: 0, considered: 0, decided: 1, executed: 2, result: 3 };
        items.sort((left, right) => (priority[left.decision_state] ?? 4) - (priority[right.decision_state] ?? 4));
        target.innerHTML = items.length ? items.map(item => {
          const rationale = item.rationale || item.decision || '理由は未記録です。';
          return `<article class="cycle-card"><div class="entry-head"><div><h3>${escapeHtml(item.title || '判断')}</h3><p class="meta">${escapeHtml(decisionState(item))} · 更新 ${escapeHtml(item.updated_at || item.decided_on || item.created_at || '')}</p></div><span class="pill">${escapeHtml(item.domain || 'other')}</span></div><p>${escapeHtml(rationale)}</p>${item.result ? `<p class="source">結果: ${escapeHtml(item.result)}</p>` : ''}${item.later_evaluation ? `<p class="source">後日評価: ${escapeHtml(item.later_evaluation)}</p>` : ''}<div class="cycle-actions">${actionFor(item)}</div></article>`;
        }).join('') : '<div class="empty-state"><p>条件に合う判断はありません。相談から提案を残すと、結果まで追跡できます。</p><button type="button" class="secondary" data-decision-empty-chat>相談する</button></div>';
        $$('[data-decision-outcome]', target).forEach(button => button.addEventListener('click', () => openOutcome(button.dataset.decisionOutcome, button.dataset.outcomeMode)));
        $$('[data-decision-action="confirm"]', target).forEach(button => button.addEventListener('click', async () => {
          const id = Number(button.dataset.decisionId), selected = $(`[data-decision-option="${id}"]`, target)?.value || '';
          button.disabled = true;
          const response = await fetch(`/api/decisions/${id}`, { method: 'PATCH', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ selected_option: selected, decision_state: 'decided' }) });
          if (!response.ok) announce('判断を決定できませんでした。');
          await window.refreshDecisions(); window.refreshToday?.();
        }));
        $$('[data-decision-action="execute"]', target).forEach(button => button.addEventListener('click', async () => {
          button.disabled = true;
          const response = await fetch(`/api/decisions/${Number(button.dataset.decisionId)}/execute`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ note: 'ユーザーが実行した' }) });
          if (!response.ok) announce('実行済みに更新できませんでした。');
          await window.refreshDecisions(); window.refreshToday?.();
        }));
        $('[data-decision-empty-chat]', target)?.addEventListener('click', () => navigate('chat'));
      } catch { target.innerHTML = '<p class="help">判断を読み込めませんでした。再試行してください。</p>'; }
    };
    window.refreshDecisions();
  }

  function streamlineExplore() {
    const panel = $('#explore-benchmark'), firstCard = panel?.querySelector(':scope > section.card');
    const importCard = panel?.querySelectorAll(':scope > section.card')[1];
    if (!panel || !firstCard || !importCard || importCard.dataset.moved) return;
    importCard.dataset.moved = 'true';
    const open = document.createElement('button'); open.id = 'benchmark-import-open'; open.type = 'button'; open.className = 'secondary'; open.textContent = '比較データを追加する';
    $('.actions', firstCard)?.append(open);
    $('#benchmark-import-sheet-content')?.append(importCard);
    open.addEventListener('click', () => openSheet('benchmark-import-sheet', open));
    addDraft($('#benchmark-import-json'), 'benchmark-import');
  }

  function standardizeDomainViews() {
    const legacyRefresh = window.refreshDomain;
    if (typeof legacyRefresh !== 'function' || legacyRefresh.dailyUxWrapped) return;
    const categoryAliases = { money: ['finance'], people: ['relationship'], travel: ['travel'], housing: ['housing'] };
    const wrapped = async domain => {
      await legacyRefresh(domain);
      const root = $(`#${domain}-content`);
      if (!root) return;
      root.querySelectorAll('.domain-recent-changes').forEach(node => node.remove());
      root.querySelectorAll('.domain-fact > .source').forEach(source => {
        if (!source.textContent.trim().startsWith('根拠:') || source.parentElement?.querySelector(':scope > details.technical-detail')) return;
        const evidence = source.nextElementSibling?.matches('details') ? source.nextElementSibling : null;
        const details = document.createElement('details'); details.className = 'technical-detail';
        details.innerHTML = '<summary>根拠と抽出情報</summary>';
        source.before(details); details.append(source);
        if (evidence) details.append(evidence);
      });
      try {
        const aliases = categoryAliases[domain] || [domain];
        const changes = await fetch('/api/memory-changes').then(response => response.ok ? response.json() : []);
        const relevant = (changes || []).filter(change => aliases.includes(change.category)).slice(0, 3);
        if (!relevant.length) return;
        const section = document.createElement('section'); section.className = 'domain-recent-changes summary-card';
        section.innerHTML = `<h3>最近の変化</h3>${relevant.map(change => `<div class="summary-line"><span>${escapeHtml(change.fact_summary || '記憶の更新')}</span><b>${escapeHtml(change.change_type || '更新')}</b></div>`).join('')}`;
        (root.querySelector('.domain-grid') || root.querySelector('h3'))?.before(section);
      } catch { /* Changes are supplementary. Domain facts remain available. */ }
    };
    wrapped.dailyUxWrapped = true;
    window.refreshDomain = wrapped;
  }

  function simplifyDomainCopy() {
    const copy = {
      money: '現在の要約、最近の変化、関連する判断と履歴を確認できます。',
      travel: '現在の要約、最近の変化、関連する判断と履歴を確認できます。',
      housing: '現在の要約、最近の変化、関連する判断と履歴を確認できます。',
      people: '明示された人物との記録、予定、関連する判断を確認できます。'
    };
    Object.entries(copy).forEach(([id, text]) => { const page = $(`#${id}`); const intro = page?.querySelector(':scope > section.card > p.help'); if (intro) intro.textContent = text; });
  }

  function init() {
    wireStaticSheets();
    unifyCapture();
    prepareToday();
    refreshNextActions();
    streamlineConsultation();
    streamlineDecisions();
    streamlineExplore();
    standardizeDomainViews();
    simplifyDomainCopy();
    wireMutationState();
    document.addEventListener('click', event => {
      const action = event.target.closest('[data-today-action]')?.dataset.todayAction;
      if (action === 'chat') navigate('chat');
      if (action === 'record') navigate('home');
    });
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init, { once: true });
  else init();
})();
