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
  const domainLabels = { finance: '資産', money: '資産', travel: '旅行', housing: '住居', relationship: '人間関係', people: '人間関係', work: '仕事', health: '健康', life: '生活', learning: '学習', hobby: '趣味', food: '食事', shopping: '買い物', technology: '技術', other: 'その他' };
  const domainLabel = domain => domainLabels[String(domain || '').toLowerCase()] || 'その他';
  window.personalOsDomainLabel = domainLabel;
  const sheetOpeners = new Map();
  let activeSheet = null;

  const focusableIn = sheet => $$('button:not([disabled]), [href], input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])', sheet)
    .filter(element => visible(element));

  function openSheet(id, opener) {
    const sheet = $(`#${id}`);
    if (!sheet) return;
    if (activeSheet && activeSheet !== sheet) closeSheet(activeSheet, false);
    if (opener) sheetOpeners.set(id, opener);
    sheet.hidden = false;
    sheet.classList.remove('hidden');
    document.body.classList.add('sheet-open');
    activeSheet = sheet;
    window.setTimeout(() => focusableIn(sheet)[0]?.focus(), 0);
  }

  function closeSheet(sheet, restoreFocus = true) {
    if (!sheet) return;
    sheet.hidden = true;
    sheet.classList.add('hidden');
    if (activeSheet === sheet) activeSheet = null;
    if (!$$('.ui-sheet:not([hidden])').length) document.body.classList.remove('sheet-open');
    const opener = sheetOpeners.get(sheet.id);
    if (restoreFocus && opener && document.contains(opener)) opener.focus();
  }

  function wireStaticSheets() {
    $$('[data-action="domains"]').forEach(button => button.addEventListener('click', () => openSheet('domains-sheet', button)));
    $$('[data-sheet-close]').forEach(button => button.addEventListener('click', () => closeSheet(button.closest('.ui-sheet'))));
    document.addEventListener('keydown', event => {
      if (!activeSheet) return;
      if (event.key === 'Escape') { event.preventDefault(); closeSheet(activeSheet); return; }
      if (event.key !== 'Tab') return;
      const targets = focusableIn(activeSheet);
      if (!targets.length) { event.preventDefault(); return; }
      const first = targets[0], last = targets[targets.length - 1];
      if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last.focus(); }
      if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first.focus(); }
    });
    window.personalOsSheets = { open: openSheet, close: closeSheet };
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

  const mutationConfig = {
    'record-form': { path: '/api/ingest', method: 'POST', notice: '#record-notice', success: '保存しました。AIがバックグラウンドで整理します。' },
    'screenshot-form': { path: '/api/import/screenshot', method: 'POST', notice: '#screenshot-notice', success: '保存しました。AIがバックグラウンドで整理します。' },
    'benchmark-import-form': { path: '/api/benchmarks/import', method: 'POST', notice: '#benchmark-import-notice', success: '保存しました。' },
    'decision-outcome-form': { path: '/api/decisions/', method: 'PATCH', notice: '#decision-outcome-notice', success: '保存しました。' },
  };

  function mutationFor(form) { return mutationConfig[form?.id] || null; }
  function setMutationState(form, state, message = '') {
    const config = mutationFor(form); if (!config) return;
    form.dataset.submitting = state === 'submitting' ? 'true' : 'false';
    form.dataset.mutationState = state;
    const submit = form.querySelector('button[type="submit"], button:not([type])');
    if (submit) {
      if (!submit.dataset.label) submit.dataset.label = submit.textContent || '保存する';
      submit.disabled = state === 'submitting';
      submit.textContent = state === 'submitting' ? '保存しています…' : submit.dataset.label;
    }
    const notice = $(config.notice);
    if (notice && message) notice.textContent = message;
  }
  function matchesMutation(form, detail) {
    const config = mutationFor(form);
    return Boolean(config && detail && detail.method === config.method
      && (config.path.endsWith('/') ? String(detail.path || '').startsWith(config.path) : detail.path === config.path));
  }

  function wireMutationState() {
    document.addEventListener('submit', event => {
      const form = event.target;
      if (!(form instanceof HTMLFormElement) || !mutationFor(form)) return;
      if (form.dataset.submitting === 'true') { event.preventDefault(); return; }
      setMutationState(form, 'submitting', '保存しています…');
      window.setTimeout(() => {
        if (form.dataset.submitting !== 'true') return;
        setMutationState(form, 'error', '保存できませんでした。入力内容は保持しています。再試行してください。');
      }, 45000);
    }, true);
    window.addEventListener('personal-os-api-response', event => {
      $$('#record-form,#screenshot-form,#benchmark-import-form,#decision-outcome-form').forEach(form => {
        if (form.dataset.submitting !== 'true' || !matchesMutation(form, event.detail)) return;
        if (!event.detail.ok) { setMutationState(form, 'error', '保存できませんでした。入力内容は保持しています。'); return; }
        setMutationState(form, 'success', mutationFor(form).success);
        clearDraftFor(form);
      });
    });
    window.addEventListener('personal-os-api-error', event => {
      $$('#record-form,#screenshot-form,#benchmark-import-form,#decision-outcome-form').forEach(form => {
        if (form.dataset.submitting === 'true' && matchesMutation(form, event.detail)) {
          setMutationState(form, 'error', '保存できませんでした。入力内容は保持しています。');
        }
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
      if (notice) notice.textContent = '保存しています…';
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
    const digest = $('#today-digest'); if (digest && card.nextElementSibling !== digest) card.after(digest);
    const overview = $('#today-overview'); if (overview && (digest || card).nextElementSibling !== overview) (digest || card).after(overview);
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

  function digestEmpty() {
    return '<div class="empty-state"><p>まだ今日のダイジェストを作れる記録がありません。</p><span class="help">記録や相談を始めると、ここに今の状態が表示されます。</span><div class="actions"><button type="button" class="secondary" data-digest-record>記録する</button><button type="button" class="secondary" data-digest-chat>相談する</button></div></div>';
  }

  function digestBasis(item) {
    const basis = Array.isArray(item?.basis) ? item.basis : [];
    const first = basis[0] || {};
    return basis.length ? `<details class="digest-basis"><summary>根拠を見る</summary><p class="help">確認済みの記録・判断をもとに表示しています。</p><button type="button" class="secondary" data-digest-evidence-kind="${escapeHtml(first.kind || '')}">関連する記録を見る</button></details>` : '';
  }

  function bindDigestActions(card) {
    $$('[data-digest-record]', card).forEach(button => button.addEventListener('click', () => { navigate('home'); window.setTimeout(() => $('#record-text')?.focus(), 0); }));
    $$('[data-digest-chat]', card).forEach(button => button.addEventListener('click', () => { navigate('chat'); window.setTimeout(() => $('#chat-message')?.focus(), 0); }));
    $$('[data-digest-decision]', card).forEach(button => button.addEventListener('click', () => navigate('decisions')));
    $$('[data-digest-evidence-kind]', card).forEach(button => button.addEventListener('click', () => navigate(button.dataset.digestEvidenceKind === 'decision' ? 'decisions' : 'home')));
    $$('[data-digest-timeline]', card).forEach(button => button.addEventListener('click', () => {
      navigate('explore');
      window.setTimeout(() => document.querySelector('[data-explore-mode="timeline"]')?.click(), 0);
    }));
    $$('[data-digest-prompt]', card).forEach(button => button.addEventListener('click', () => {
      const prompt = button.dataset.digestPrompt || '';
      navigate('chat');
      window.setTimeout(() => { const input = $('#chat-message'); if (input) { input.value = prompt; input.focus(); input.dispatchEvent(new Event('input', { bubbles: true })); } }, 0);
    }));
  }

  async function refreshDailyDigest() {
    const page = $('#today');
    if (!page) return;
    let card = $('#today-digest');
    if (!card) { card = document.createElement('section'); card.id = 'today-digest'; card.className = 'card today-digest'; const actions = $('#today-daily-actions'); (actions || page.firstElementChild)?.after(card); }
    card.setAttribute('aria-busy', 'true');
    try {
      const response = await fetch('/api/today/digest');
      if (!response.ok) throw new Error('今日のダイジェストを取得できません');
      const digest = await response.json();
      const next = Array.isArray(digest.next_actions) ? digest.next_actions.slice(0, 3) : [];
      const recent = Array.isArray(digest.recent_changes) ? digest.recent_changes.slice(0, 3) : [];
      const remember = Array.isArray(digest.remember) ? digest.remember.slice(0, 2) : [];
      const prompts = Array.isArray(digest.consultation_prompts) ? digest.consultation_prompts.slice(0, 3) : [];
      const hasContent = next.length || recent.length || remember.length || prompts.length;
      if (!hasContent) {
        card.innerHTML = `<h2>今日のダイジェスト</h2>${digestEmpty()}`;
        bindDigestActions(card);
        return;
      }
      const rows = (items, renderer, emptyText) => items.length ? items.map(renderer).join('') : `<p class="help">${emptyText}</p>`;
      card.innerHTML = `<section class="digest-headline"><h2>今日の一言</h2><p>${escapeHtml(digest.headline?.text || '最近の大きな変化はまだありません')}</p>${digestBasis(digest.headline)}</section><section class="digest-section"><h3>次にやること</h3>${rows(next, item => `<article class="timeline-row"><div><b>${escapeHtml(item.title || '確認すること')}</b><span class="source">${escapeHtml(item.state_label || '')}</span></div><button type="button" class="secondary" data-digest-decision="${Number(item.id)}">${escapeHtml(item.action || '確認する')}</button></article>`, '今すぐ対応が必要なことはありません。')}</section><section class="digest-section"><div class="digest-section-heading"><h3>最近変わったこと</h3><button type="button" class="secondary" data-digest-timeline>すべての変化を見る</button></div>${rows(recent, item => `<article class="timeline-row"><b>${escapeHtml(item.text || '記憶の更新')}</b><span>${escapeHtml(item.change_type || '更新')}</span>${digestBasis(item)}</article>`, '最近の変化はまだありません。')}</section><section class="digest-section"><h3>思い出しておくこと</h3>${rows(remember, item => `<article class="timeline-row"><b>${escapeHtml(item.text || '確認済みの記録')}</b>${digestBasis(item)}</article>`, '確認できる記憶はまだありません。')}</section><section class="digest-section"><h3>相談候補</h3>${rows(prompts, item => `<button type="button" class="secondary digest-prompt" data-digest-prompt="${escapeHtml(item.text || '')}">${escapeHtml(item.text || '相談する')}</button>`, '今の記録から作れる相談候補はまだありません。')}</section>`;
      bindDigestActions(card);
    } catch { card.innerHTML = '<h2>今日のダイジェスト</h2><p class="help">いまはダイジェストを確認できません。入力内容は失われていません。</p>'; }
    finally { card.removeAttribute('aria-busy'); }
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
        const priority = item => item.later_evaluation ? 5 : ({ executed: 0, decided: 1, considered: 2, result: 3, candidate: 4 }[item.decision_state] ?? 4);
        items.sort((left, right) => priority(left) - priority(right)
          || String(left.updated_at || left.created_at || '').localeCompare(String(right.updated_at || right.created_at || ''))
          || String(left.created_at || '').localeCompare(String(right.created_at || ''))
          || Number(left.id || 0) - Number(right.id || 0));
        target.innerHTML = items.length ? items.map(item => {
          const rationale = item.rationale || item.decision || '理由は未記録です。';
          return `<article class="cycle-card"><div class="entry-head"><div><h3>${escapeHtml(item.title || '判断')}</h3><p class="meta">${escapeHtml(decisionState(item))} · 更新 ${escapeHtml(item.updated_at || item.decided_on || item.created_at || '')}</p></div><span class="pill">${domainLabel(item.domain)}</span></div><p>${escapeHtml(rationale)}</p>${item.result ? `<p class="source">結果: ${escapeHtml(item.result)}</p>` : ''}${item.later_evaluation ? `<p class="source">後日評価: ${escapeHtml(item.later_evaluation)}</p>` : ''}<div class="cycle-actions">${actionFor(item)}</div></article>`;
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
    if (window.refreshDomain?.dailyUxWrapped) return;
    const categoryAliases = { money: ['finance'], people: ['relationship'], travel: ['travel'], housing: ['housing'] };
    const labels = { money: '資産', travel: '旅行', housing: '住居', people: '人間関係' };
    const empty = (message, action = true) => `<div class="empty-state"><p>${escapeHtml(message)}</p>${action ? '<button type="button" class="secondary" data-domain-record>記録する</button>' : ''}</div>`;
    const value = fact => {
      try {
        const data = JSON.parse(fact.value_json || '{}');
        return [data.asset, data.amount !== undefined && data.amount !== null ? `${Number(data.amount).toLocaleString('ja-JP')} ${data.currency || ''}`.trim() : '', data.value].filter(Boolean).join(' / ');
      } catch { return ''; }
    };
    const factCard = (fact, compact = false) => {
      const amount = (() => { try { return JSON.parse(fact.value_json || '{}').amount ?? ''; } catch { return ''; } })();
      const evidence = Number(fact.evidence_count || 0) > 0
        ? `<p class="source">根拠あり・${Number(fact.evidence_count)}件</p>`
        : '<p class="help">確認できる根拠がまだありません。</p>';
      return `<article class="domain-fact ${fact.status === 'current' ? 'current-card' : ''}"><b>${escapeHtml(fact.summary || '記録')}</b>${compact ? '' : `<div>${escapeHtml(value(fact) || fact.fact_key || '')}</div>`}<div class="source">${fact.status === 'current' ? '現在の情報' : '過去の記録'} ・ 確からしさ ${Math.round((Number(fact.truth_confidence ?? fact.confidence) || 0) * 100)}%</div>${compact ? '' : `<div class="actions"><button type="button" class="secondary" data-domain-correct="${Number(fact.id)}" data-domain-summary="${encodeURIComponent(fact.summary || '')}" data-domain-amount="${encodeURIComponent(String(amount))}">訂正する</button></div>`}${evidence}</article>`;
    };
    const currentSummary = (domain, summary = {}) => {
      if (domain === 'money') return `<div class="summary-grid"><div><span>総資産</span><b>${summary.total_assets === null || summary.total_assets === undefined ? '未登録' : `${Number(summary.total_assets).toLocaleString('ja-JP')}円`}</b></div><div><span>月間積立</span><b>${summary.monthly_investment === null || summary.monthly_investment === undefined ? '未登録' : `${Number(summary.monthly_investment).toLocaleString('ja-JP')}円`}</b></div><div><span>構成</span><b>${Object.keys(summary.breakdown || {}).length}種</b></div><div><span>実取引</span><b>${Number(summary.transaction_count || 0)}件</b></div></div>`;
      if (domain === 'travel') return `<div class="summary-grid"><div><span>次の旅行</span><b>${escapeHtml((summary.upcoming || []).join('、') || '未定')}</b></div><div><span>訪問地</span><b>${Number((summary.visited_places || []).length)}件</b></div><div><span>行きたい場所</span><b>${Number((summary.wanted_places || []).length)}件</b></div><div><span>旅行傾向</span><b>${escapeHtml((summary.preferences || []).slice(0, 2).join(' / ') || '未登録')}</b></div></div>`;
      if (domain === 'housing') return `<div class="summary-grid"><div><span>現住居</span><b>${Number((summary.current || []).length) ? '登録済み' : '未登録'}</b></div><div><span>希望条件</span><b>${Number((summary.preferences || []).length)}件</b></div><div><span>更新時期</span><b>${escapeHtml(summary.renewal || '未登録')}</b></div><div><span>検討候補</span><b>${Number((summary.candidates || []).length)}件</b></div></div>`;
      return `<div class="summary-grid"><div><span>最近の人物</span><b>${Number(summary.people_count || 0)}人</b></div><div><span>次の予定</span><b>${Number(summary.next_plans || 0)}件</b></div><div><span>結果待ち</span><b>${Number(summary.pending_results || 0)}件</b></div><div><span>タイムライン</span><b>${Number(summary.timeline_count || 0)}件</b></div></div>`;
    };
    const wrapped = async domain => {
      const root = $(`#${domain}-content`); if (!root) return;
      root.setAttribute('aria-busy', 'true');
      try {
        const [projectionResponse, changesResponse] = await Promise.all([fetch(`/api/domains/${domain}`), fetch('/api/memory-changes')]);
        if (!projectionResponse.ok) throw new Error('domain fetch failed');
        const data = await projectionResponse.json();
        const changes = changesResponse.ok ? await changesResponse.json() : [];
        const aliases = categoryAliases[domain] || [domain];
        const recent = (changes || []).filter(change => aliases.includes(change.category)).slice(0, 3);
        const decisions = (data.decisions || []).slice(0, 8);
        const history = [...(data.history || [])];
        if (domain === 'money') history.push(...(data.transactions || []).map(transaction => ({ id: `transaction-${transaction.fact_id}`, summary: `${transaction.asset || transaction.summary || '実取引'} ${Number(transaction.normalized_amount ?? transaction.amount ?? 0).toLocaleString('ja-JP')} ${transaction.currency || ''}`, status: 'historical', confidence: transaction.confidence, evidence: transaction.evidence, document_title: transaction.document_title, extractor: '取引集計', value_json: '{}' })));
        const rootEvidence = [...(data.current || [])].filter((item, index, items) => items.findIndex(other => String(other.evidence_id || other.id) === String(item.evidence_id || item.id)) === index);
        root.innerHTML = `<section class="domain-current"><h3>現在の要約</h3><div class="summary-card">${currentSummary(domain, data.summary || {})}</div><div class="domain-grid">${(data.current || []).map(item => factCard(item)).join('') || empty('現在の情報がまだありません')}</div></section><section class="domain-recent"><h3>最近の変化</h3><div class="domain-recent-changes summary-card">${recent.length ? recent.map(change => `<div class="summary-line"><span>${escapeHtml(change.fact_summary || '記憶の更新')}</span><b>${escapeHtml(change.change_type || '更新')}</b></div>`).join('') : empty('最近の変化はまだありません', false)}</div></section><section class="domain-decisions"><h3>関連する判断</h3>${decisions.length ? decisions.map(decision => `<article class="domain-fact"><b>${escapeHtml(decision.title || decision.decision || '判断')}</b><div class="source">${domainLabel(decision.domain)} ・ ${escapeHtml(decision.status || decision.decision_state || '')}</div>${decision.result ? `<details><summary>結果を表示</summary><div class="body">${escapeHtml(decision.result)}</div></details>` : '<p class="help">結果待ちです</p>'}</article>`).join('') : empty('この領域の進行中の判断はありません', false)}</section><section class="domain-history"><h3>履歴</h3>${history.length ? history.map(item => factCard(item, true)).join('') : empty('まだ履歴はありません')}</section><section class="domain-evidence"><h3>根拠</h3>${rootEvidence.length ? rootEvidence.map(item => `<details class="technical-detail"><summary>${escapeHtml(item.summary || '記憶')} の根拠</summary><p class="source">${escapeHtml(item.document_title || '原文')} / ${escapeHtml(item.extractor || '')} ${escapeHtml(item.extractor_model || '')} / Evidence ${Number(item.evidence_count || 0)}件</p><div class="body">${escapeHtml(String(item.evidence || '確認できる根拠がまだありません。').slice(0, 1200))}</div></details>`).join('') : empty('確認できる根拠がまだありません')}</section>`;
        $$('[data-domain-record]', root).forEach(button => button.addEventListener('click', () => { navigate('home'); window.setTimeout(() => $('#record-text')?.focus(), 0); }));
        $$('[data-domain-correct]', root).forEach(button => button.addEventListener('click', () => window.correctDomainFact?.(Number(button.dataset.domainCorrect), button.dataset.domainSummary || '', button.dataset.domainAmount || '')));
      } catch {
        root.innerHTML = `<section class="domain-current"><h3>${labels[domain] || '領域'}の情報</h3>${empty('情報を読み込めませんでした。入力内容は失われていません。')}</section>`;
      } finally { root.removeAttribute('aria-busy'); }
    };
    wrapped.dailyUxWrapped = true;
    window.personalOsRenderDomain = wrapped;
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
    refreshDailyDigest();
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

  // Register before app.js handles the initial hash route so direct Domain
  // links never produce a legacy-only first render.
  standardizeDomainViews();
  // app.js has a few legacy DOMContentLoaded initialisers.  Defer this final
  // UX composition one task so its unified renderers remain the active ones.
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', () => window.setTimeout(init, 0), { once: true });
  else init();
  // Legacy inline scripts can finish their own first render after the deferred
  // bundle. Re-apply the decision renderer once the document is fully ready.
  window.addEventListener('load', streamlineDecisions, { once: true });
  window.refreshTodayDigest = refreshDailyDigest;
})();
