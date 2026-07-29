/* One browser-side API boundary for Personal OS.
 * It preserves the Response-like contract used by the legacy UI while
 * centralising timeout, request IDs, safe retries, auth/CSRF recovery and
 * structured error diagnostics.  The native fetch reference is captured
 * before the page exposes the compatibility alias in index.html. */
(function () {
  'use strict';
  const nativeFetch = window.fetch.bind(window);
  // Short request timeouts are an E2E-only fault-injection hook.  The flag is
  // injected before this asset loads by the verification runner and is never
  // set by production pages.
  const verificationTimeout = Number(window.__PERSONAL_OS_E2E_REQUEST_TIMEOUT_MS);
  const DEFAULT_TIMEOUT = window.__PERSONAL_OS_E2E_VERIFICATION__ === true
    && Number.isFinite(verificationTimeout) && verificationTimeout >= 100
    ? Math.min(5000, verificationTimeout)
    : 30000;
  const RETRIES = 2;
  let csrfToken = '';
  let authWaiter = null;
  let pendingAuth = null;

  const makeId = prefix => `${prefix}-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 8)}`;
  const classify = (status, error) => {
    if (error?.name === 'AbortError') return 'timeout';
    if (status === 401) return 'authentication_expired';
    if (status === 403) return 'csrf';
    if (status >= 500) return 'http_error';
    if (status >= 400) return 'http_error';
    return 'network_error';
  };
  const isRetryable = (method, status, error, allowRetry) => {
    if (!allowRetry) return false;
    if (!['GET', 'HEAD', 'OPTIONS'].includes(method)) return Boolean(allowRetry && error?.idempotent);
    return Boolean(error || status >= 500 || status === 408 || status === 429);
  };

  function waitForAuthentication() {
    if (authWaiter) return authWaiter;
    authWaiter = new Promise(resolve => {
      const timer = setTimeout(() => { authWaiter = null; resolve(false); }, 60000);
      window.addEventListener('personal-os-authenticated', event => {
        clearTimeout(timer); authWaiter = null; csrfToken = event.detail?.csrf_token || csrfToken; resolve(true);
      }, { once: true });
    });
    return authWaiter;
  }

  async function request(path, options = {}) {
    const url = typeof path === 'string' ? path : path.toString();
    const method = String(options.method || 'GET').toUpperCase();
    const requestId = options.requestId || makeId('req');
    const headers = new Headers(options.headers || {});
    headers.set('X-Request-ID', requestId);
    if (csrfToken && method !== 'GET' && method !== 'HEAD' && method !== 'OPTIONS') headers.set('X-CSRF-Token', csrfToken);
    if (options.body && typeof options.body !== 'string' && !(options.body instanceof FormData) && !headers.has('Content-Type')) {
      headers.set('Content-Type', 'application/json');
      options = { ...options, body: JSON.stringify(options.body) };
    }
    const timeout = Number(options.timeout || DEFAULT_TIMEOUT);
    const allowRetry = options.retry !== false;
    const idempotent = options.idempotencyKey || (method === 'GET' ? '' : '');
    if (idempotent) headers.set('Idempotency-Key', idempotent);
    let authenticatedRetry = false;
    for (let attempt = 0; attempt <= RETRIES; attempt += 1) {
      if (csrfToken && method !== 'GET' && method !== 'HEAD' && method !== 'OPTIONS') headers.set('X-CSRF-Token', csrfToken);
      const controller = new AbortController();
      const timer = setTimeout(() => controller.abort(), timeout);
      let response;
      let failure = null;
      try {
        response = await nativeFetch(url, { ...options, method, headers, signal: options.signal || controller.signal });
      } catch (error) {
        failure = error;
      } finally { clearTimeout(timer); }
      if (failure) {
        const detail = { request_id: requestId, error_type: classify(0, failure), message: failure.message || 'Network request failed', path: url, method };
        window.dispatchEvent(new CustomEvent('personal-os-api-error', { detail }));
        // DOMException.message can be read-only in some browsers.  Do not
        // mutate the browser exception while constructing a retryable error.
        const tagged = Object.assign(new Error(detail.message), detail, { cause: failure, idempotent: Boolean(idempotent) });
        if (isRetryable(method, 0, tagged, allowRetry) && attempt < RETRIES) { await new Promise(resolve => setTimeout(resolve, 250 * (attempt + 1))); continue; }
        throw tagged;
      }
      response.request_id = response.headers.get('X-Request-ID') || requestId;
      if (response.status === 401 && !authenticatedRetry) {
        const info = await response.clone().json().catch(() => ({}));
        if (info.auth_required) {
          pendingAuth = { request_id: requestId, path: url, method };
          window.dispatchEvent(new CustomEvent('personal-os-auth-required', { detail: { request_id: requestId, path: url, method } }));
          authenticatedRetry = await waitForAuthentication();
          if (authenticatedRetry) continue;
        }
      }
      if (!response.ok) {
        const info = await response.clone().json().catch(() => ({}));
        const detail = { request_id: response.request_id, error_type: info.error_type || classify(response.status), message: info.error || info.message || `HTTP ${response.status}`, status: response.status, path: url, method };
        window.dispatchEvent(new CustomEvent('personal-os-api-error', { detail }));
        response.error_info = detail;
      }
      if (new URL(url, window.location.href).pathname.startsWith('/api/') && !new URL(url, window.location.href).pathname.endsWith('/image')) {
        response.clone().json().catch(() => {
          const detail = { request_id: response.request_id, error_type: 'json_parse_error', status: response.status, path: url, method };
          window.dispatchEvent(new CustomEvent('personal-os-api-error', { detail }));
        });
      }
      if (response.ok && new URL(url, window.location.href).pathname === '/api/chat') {
        response.clone().json().then(data => window.dispatchEvent(new CustomEvent('personal-os-chat-response', { detail: data }))).catch(() => {});
      }
      window.dispatchEvent(new CustomEvent('personal-os-api-response', { detail: { request_id: response.request_id, path: new URL(url, window.location.href).pathname, method, status: response.status, ok: response.ok } }));
      if (isRetryable(method, response.status, null, allowRetry) && attempt < RETRIES) { await new Promise(resolve => setTimeout(resolve, 250 * (attempt + 1))); continue; }
      return response;
    }
    throw Object.assign(new Error('Request failed'), { request_id: requestId, error_type: 'unknown' });
  }

  const client = {
    request,
    fetch: request,
    get: (path, options = {}) => request(path, { ...options, method: 'GET' }),
    post: (path, body, options = {}) => request(path, { ...options, method: 'POST', body }),
    patch: (path, body, options = {}) => request(path, { ...options, method: 'PATCH', body }),
    delete: (path, options = {}) => request(path, { ...options, method: 'DELETE' }),
    setCsrfToken(token) { csrfToken = token || ''; },
    getCsrfToken() { return csrfToken; },
    getPendingAuth() { return pendingAuth; },
    clearPendingAuth() { pendingAuth = null; },
    async login(password) {
      const response = await nativeFetch('/api/auth/login', { method: 'POST', headers: { 'Content-Type': 'application/json', 'X-Request-ID': makeId('login') }, body: JSON.stringify({ password }) });
      const data = await response.clone().json().catch(() => ({}));
      if (response.ok) { csrfToken = data.csrf_token || ''; pendingAuth = null; window.dispatchEvent(new CustomEvent('personal-os-authenticated', { detail: data })); }
      return response;
    },
  };
  window.apiClient = client;
  window.personalOsApi = client;
}());
