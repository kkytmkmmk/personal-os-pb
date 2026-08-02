"""Run reproducible Personal OS browser journeys against synthetic data only.

The runner creates a new temporary SQLite database, starts the verification
server on port 8877, drives the real HTML/CSS/JS through Playwright and can
promote reviewed viewport screenshots into ``docs/screenshots/ux-phase5``.
It never opens or copies ``data/personal_os.db``.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sqlite3
import shutil
import socket
import subprocess
import sys
import tempfile
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.request import urlopen


ROOT = Path(__file__).resolve().parents[1]
PYTHON = Path(sys.executable)
BASE_URL = "http://127.0.0.1:8877"
RESULTS = Path(os.environ.get("PERSONAL_OS_E2E_RESULTS_DIR", str(ROOT / "test-results" / "screenshots"))).resolve()
PUBLIC_DIR = ROOT / "docs" / "screenshots" / "ux-phase5"
EDGE_PATHS = (
    Path(os.environ.get("PERSONAL_OS_E2E_BROWSER", "")),
    Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"),
    Path(r"C:\Program Files\Microsoft\Edge\Application\msedge.exe"),
)


class E2EFailure(RuntimeError):
    pass


def assert_port_free() -> None:
    # A just-stopped child server can take a short moment to release the
    # listening socket on Windows.  Wait only for that hand-off; a real
    # verification server remains a deterministic failure.
    deadline = time.monotonic() + 5
    while True:
        probe = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            if probe.connect_ex(("127.0.0.1", 8877)) != 0:
                return
        finally:
            probe.close()
        if time.monotonic() >= deadline:
            raise E2EFailure("port 8877 is already in use; stop the verification server before running UX E2E")
        time.sleep(0.1)


def browser_choice() -> tuple[Path | None, str]:
    configured = os.environ.get("PERSONAL_OS_E2E_BROWSER")
    if configured:
        candidate = Path(configured)
        if not candidate.is_file():
            raise E2EFailure("PERSONAL_OS_E2E_BROWSER does not point to a browser executable")
        return candidate, "configured"
    if os.environ.get("PERSONAL_OS_E2E_FORCE_PLAYWRIGHT_CHROMIUM") == "1":
        return None, "playwright-chromium"
    for candidate in EDGE_PATHS[1:]:
        if candidate.is_file():
            return candidate, "microsoft-edge"
    return None, "playwright-chromium"


def wait_for_server(process: subprocess.Popen[str]) -> dict[str, Any]:
    deadline = time.monotonic() + 25
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise E2EFailure(f"verification server exited early ({process.returncode})")
        try:
            with urlopen(f"{BASE_URL}/api/runtime", timeout=1) as response:
                data = json.loads(response.read().decode("utf-8"))
            if data.get("environment") != "verification" or Path(str(data.get("database", ""))).name != "ux-synthetic.db":
                raise E2EFailure("verification server did not use the synthetic database")
            return data
        except OSError:
            time.sleep(0.2)
    raise E2EFailure("verification server did not become healthy")


def screenshot(page: Any, directory: Path, manifest: list[dict[str, Any]], name: str, route: str, state: str, viewport: tuple[int, int]) -> None:
    tab = {"memory": "home"}.get(route.removeprefix("#"), route.removeprefix("#"))
    if tab and not page.locator(f"#{tab}").is_visible():
        raise E2EFailure(f"refusing to label {name} as {route}: that route is not visible")
    path = directory / f"{name}.png"
    page.screenshot(path=str(path), full_page=False)
    manifest.append({
        "file": path.name,
        "viewport": {"width": viewport[0], "height": viewport[1]},
        "route": route,
        "state": state,
        "data_type": "synthetic",
        "contains_sensitive_data": False,
        "reviewed": False,
        "reviewed_at": None,
        "reviewed_by": None,
        "sha256": None,
    })


def assert_distinct_screenshots(directory: Path, first_name: str, second_name: str) -> None:
    """Ensure an asserted transient state was not captured after it resolved."""
    first = directory / f"{first_name}.png"
    second = directory / f"{second_name}.png"
    if not first.is_file() or not second.is_file():
        raise E2EFailure("consultation state screenshots were not created")
    if hashlib.sha256(first.read_bytes()).digest() == hashlib.sha256(second.read_bytes()).digest():
        raise E2EFailure("consultation loading and result screenshots are identical")


def assert_layout(page: Any, *, mobile: bool = False) -> None:
    result = page.evaluate("""() => ({
      overflow: document.documentElement.scrollWidth - window.innerWidth,
      sheets: [...document.querySelectorAll('.ui-sheet:not([hidden])')].every(s => {
        const r=s.querySelector('.ui-sheet-panel')?.getBoundingClientRect(); return !r || (r.top >= -1 && r.left >= -1 && r.right <= innerWidth + 1 && r.bottom <= innerHeight + 1);
      }),
      targets: [...document.querySelectorAll('.mobile-bottom-nav button')].every(b => { const r=b.getBoundingClientRect(); return r.width >= 44 && r.height >= 44; }),
    })""")
    if result["overflow"] > 1:
        raise E2EFailure(f"horizontal overflow: {result['overflow']}px")
    if not result["sheets"]:
        raise E2EFailure("a sheet extends outside the viewport")
    if mobile and not result["targets"]:
        raise E2EFailure("a mobile navigation target is smaller than 44px")


def route(page: Any, name: str) -> None:
    if page.url == "about:blank":
        page.goto(f"{BASE_URL}/#today", wait_until="domcontentloaded")
    visible_navigation = page.locator(f"[data-tab='{name}']:visible")
    if visible_navigation.count() > 0:
        visible_navigation.first.click()
    else:
        page.evaluate("tab => window.personalOsNavigate(tab)", name)
    page.locator(f"#{name}").wait_for(state="visible")
    visible_tabs = page.evaluate("() => [...document.querySelectorAll('.tab:not(.hidden)')].map(node => node.id)")
    if visible_tabs != [name]:
        raise E2EFailure(f"route {name} left unexpected visible tabs: {visible_tabs}")
    page.wait_for_timeout(180)


def reload_app(page: Any) -> None:
    """Reload the real document without depending on a SW-delayed load event."""
    page.reload(wait_until="commit", timeout=10000)
    page.locator("#app-main").wait_for(state="attached", timeout=15000)
    page.wait_for_function("() => typeof window.personalOsNavigate === 'function'", timeout=15000)


def wait_domain(page: Any, tab: str) -> None:
    locator = page.locator(f"#{tab}-content .domain-current")
    try:
        locator.wait_for(state="visible", timeout=5000)
    except Exception as error:
        # Re-entering a route after a viewport change can race the app's
        # asynchronous initial refresh.  Invoke the same public renderer and
        # still require the real API-backed common sections to appear.
        page.evaluate("tab => window.personalOsRenderDomain?.(tab)", tab)
        try:
            locator.wait_for(state="visible", timeout=5000)
            return
        except Exception:
            text = page.locator(f"#{tab}-content").inner_text(timeout=1000)
            raise E2EFailure(f"{tab} Domain renderer did not produce the common structure: {text[:300]!r}") from error


def wait_space(page: Any) -> None:
    try:
        page.locator("#personal-space-canvas").wait_for(state="visible", timeout=5000)
    except Exception as error:
        state = page.evaluate("() => ({explore: document.querySelector('#explore')?.className, space: document.querySelector('#explore-space')?.className, canvas: getComputedStyle(document.querySelector('#personal-space-canvas')).display})")
        raise E2EFailure(f"Personal Space is not visible: {state}") from error


def wait_decisions(page: Any) -> None:
    page.evaluate("() => window.refreshDecisions?.()")
    try:
        page.locator("#decisions-content .cycle-card").first.wait_for(state="visible", timeout=5000)
    except Exception as error:
        text = page.locator("#decisions-content").inner_text(timeout=1000)
        raise E2EFailure(f"Synthetic decisions did not render: {text[:280]!r}") from error


def record_success(page: Any) -> None:
    marker = "Synthetic persisted memo"
    route(page, "home")
    page.locator("#record-text").fill(marker)
    with page.expect_response(lambda response: response.url.endswith("/api/ingest") and response.request.method == "POST", timeout=8000) as saved:
        page.locator("#record-form button:not(.voice)").last.click()
    if not saved.value.ok:
        raise E2EFailure(f"recording did not succeed: {saved.value.status}")
    page.wait_for_function("""() => document.querySelector('#record-notice')?.textContent.includes('保存しました')""", timeout=5000)
    if page.locator("#record-text").input_value() or page.evaluate("() => Boolean(sessionStorage.getItem('personal-os-draft-memo'))"):
        raise E2EFailure("successful recording did not clear its draft")
    reload_app(page); route(page, "home")
    persisted = page.evaluate("""async marker => (await (await fetch('/api/entries?q=' + encodeURIComponent(marker))).json()).some(entry => entry.body === marker)""", marker)
    if not persisted:
        raise E2EFailure("recorded synthetic memo did not persist after reload")


def record_timeout(browser: Any, console_errors: list[str]) -> None:
    """Exercise capture timeout handling without sending a request to SQLite."""
    context = browser.new_context(viewport={"width": 1280, "height": 720})
    context.add_init_script("""
      window.__PERSONAL_OS_E2E_VERIFICATION__ = true;
      window.__PERSONAL_OS_E2E_REQUEST_TIMEOUT_MS = 350;
    """)
    page = context.new_page()
    page.on("console", lambda message: console_errors.append(message.text) if message.type == "error" and "Failed to load resource" not in message.text else None)
    page.on("pageerror", lambda error: console_errors.append(f"pageerror: {getattr(error, 'stack', None) or error}"))
    marker = "Synthetic timeout memo"

    # Use the same AbortError contract as api-client.js, but keep it inside a
    # verification-only browser page.  A synchronous route handler cannot
    # sleep without blocking Playwright's transport on Chromium.
    page.add_init_script("""
      (() => {
        addEventListener('DOMContentLoaded', () => {
          const original = window.apiClient.request.bind(window.apiClient);
          window.apiClient.request = (path, options = {}) => {
            if (String(path) !== '/api/ingest') return original(path, options);
            return new Promise((resolve, reject) => setTimeout(() => {
              window.dispatchEvent(new CustomEvent('personal-os-api-error', {
                detail: { path: '/api/ingest', method: 'POST', error_type: 'timeout', message: 'Synthetic request timeout' }
              }));
              reject(new DOMException('Synthetic request timeout', 'AbortError'));
            }, 450));
          };
        }, { once: true });
      })();
    """)
    try:
        route(page, "home")
        page.locator("#record-text").fill(marker)
        page.locator("#record-form button:not(.voice)").last.click()
        page.wait_for_function("""() => document.querySelector('#record-form')?.dataset.mutationState === 'error'""", timeout=5000)
        notice = page.locator("#record-notice").inner_text()
        if "保存しました" in notice:
            raise E2EFailure("timeout capture displayed a success notice")
        if page.locator("#record-text").input_value() != marker:
            raise E2EFailure("timeout capture did not retain the visible draft")
        if not page.evaluate("() => Boolean(sessionStorage.getItem('personal-os-draft-memo'))"):
            raise E2EFailure("timeout capture did not retain the session draft")
        if page.locator("#record-form button:not(.voice)").last.is_disabled():
            raise E2EFailure("timeout capture left the submit button disabled")
        persisted = page.evaluate("""async marker => (await (await fetch('/api/entries?q=' + encodeURIComponent(marker))).json()).some(entry => entry.body === marker)""", marker)
        if persisted:
            raise E2EFailure("timeout capture unexpectedly wrote to the synthetic database")
    finally:
        context.close()


def save_result_and_evaluation(page: Any) -> None:
    route(page, "decisions"); wait_decisions(page)
    result_button = page.locator("[data-decision-outcome][data-outcome-mode='result']").first
    if result_button.count() == 0:
        raise E2EFailure("no executed decision was available for result persistence")
    result_button.click(); page.locator("#decision-outcome-sheet").wait_for(state="visible")
    page.locator("#decision-outcome-text").fill("Synthetic persisted result")
    with page.expect_response(lambda response: "/api/decisions/" in response.url and response.request.method == "PATCH", timeout=8000) as saved:
        page.locator("#decision-outcome-form button[type='submit']").click()
    if not saved.value.ok:
        raise E2EFailure(f"decision result did not save: {saved.value.status}")
    page.locator("#decision-outcome-sheet").wait_for(state="hidden")
    reload_app(page); route(page, "decisions"); wait_decisions(page)
    if page.locator("#decisions-content").inner_text().find("Synthetic persisted result") < 0:
        raise E2EFailure("decision result did not persist after reload")
    evaluation_button = page.locator("[data-decision-outcome][data-outcome-mode='evaluate']").first
    if evaluation_button.count() == 0:
        raise E2EFailure("no result decision was available for later evaluation persistence")
    evaluation_button.click(); page.locator("#decision-outcome-sheet").wait_for(state="visible")
    page.locator("#decision-outcome-text").fill("Synthetic persisted evaluation")
    with page.expect_response(lambda response: "/api/decisions/" in response.url and response.request.method == "PATCH", timeout=8000) as evaluated:
        page.locator("#decision-outcome-form button[type='submit']").click()
    if not evaluated.value.ok:
        raise E2EFailure(f"later evaluation did not save: {evaluated.value.status}")
    page.locator("#decision-outcome-sheet").wait_for(state="hidden")
    reload_app(page); route(page, "decisions"); wait_decisions(page)
    if page.locator("#decisions-content").inner_text().find("Synthetic persisted evaluation") < 0:
        raise E2EFailure("later evaluation did not persist after reload")


def make_chat_result(page: Any, *, loading: tuple[Path, list[dict[str, Any]], str, tuple[int, int]] | None = None) -> None:
    route(page, "chat")
    # The chat panel can retain text from a prior client-side render. Clear it
    # and observe the real API event so the assertion is about this request.
    page.evaluate("""() => {
      window.__personalOsE2eChatResolved = false;
      document.querySelector('#chat-answer').textContent = '';
      window.addEventListener('personal-os-chat-response', () => {
        window.__personalOsE2eChatResolved = true;
      }, { once: true });
    }""")
    page.locator("#chat-message").fill("次の休日の過ごし方を整理したい")
    responses: list[Any] = []
    page.on("response", lambda response: responses.append(response) if response.url.endswith("/api/chat") and response.request.method == "POST" else None)
    with page.expect_request(lambda request: request.url.endswith("/api/chat") and request.method == "POST", timeout=8000):
        page.locator("#chat-form button[type='submit'], #chat-form button:not(.voice)").last.click()
    if loading:
        directory, manifest, name, viewport = loading
        page.wait_for_function("""() => document.querySelector('#consultation-status')?.textContent.trim().length > 0""", timeout=5000)
        if page.evaluate("() => window.__personalOsE2eChatResolved === true"):
            raise E2EFailure("consultation loading state already contains an answer")
        if not page.locator("#chat-form button[type='submit'], #chat-form button:not(.voice)").last.is_disabled():
            raise E2EFailure("consultation submit button is not disabled while loading")
        screenshot(page, directory, manifest, name, "#chat", "processing", viewport)
    deadline = time.monotonic() + 8
    while not responses and time.monotonic() < deadline:
        page.wait_for_timeout(25)
    if not responses:
        raise E2EFailure("synthetic consultation did not return a response")
    consulted = responses[-1]
    if not consulted.ok:
        raise E2EFailure(f"synthetic consultation did not succeed: {consulted.status}")
    page.locator("#chat-result").wait_for(state="visible")
    page.wait_for_function("""() => document.querySelector('#chat-answer')?.textContent.trim().length > 0""", timeout=8000)
    page.wait_for_timeout(150)


def load_demo_benchmark(page: Any) -> None:
    """Wait for both the real local POST and its subsequent rendered result."""
    # A suite owns a fresh database, but the secondary viewport in that suite
    # may already have inserted the synthetic bundle.  Do not submit a
    # duplicate when the real GET has already rendered it.
    if page.locator("#benchmark-series .benchmark-card").count() > 0:
        return
    with page.expect_response(lambda response: response.url.endswith("/api/benchmarks/demo") and response.request.method == "POST", timeout=8000) as posted:
        page.locator("#benchmark-load-demo").click()
    response = posted.value
    if not response.ok:
        raise E2EFailure(f"synthetic benchmark demo endpoint failed: {response.status} {response.text()[:240]}")
    # The click handler refreshes asynchronously. Invoke the same public
    # renderer once more after the POST settles to avoid a browser-specific
    # race between the initial empty GET and the created demo bundle.
    page.evaluate("() => window.refreshBenchmarks?.()")
    try:
        page.wait_for_function("""() => Boolean(document.querySelector('#benchmark-series .benchmark-card'))""", timeout=8000)
    except Exception as error:
        text = page.locator("#benchmark-series").inner_text(timeout=1000)
        raise E2EFailure(f"synthetic benchmark demo did not render: {text[:300]!r}") from error


def verify_daily_digest(page: Any, directory: Path, manifest: list[dict[str, Any]], prefix: str, viewport: tuple[int, int], *, mobile: bool) -> None:
    """Exercise the real digest API and its non-mutating primary actions."""
    route(page, "today")
    page.locator("#today-digest").wait_for(state="visible", timeout=5000)
    page.locator("#today-digest .digest-headline").wait_for(state="visible", timeout=5000)
    screenshot(page, directory, manifest, f"{prefix}-today-digest", "#today", "daily-digest", viewport)
    if mobile:
        secondary = page.locator("#today-digest .digest-secondary")
        if secondary.count() and not secondary.get_attribute("open"):
            secondary.locator("summary").click()
        prompt = page.locator("#today-digest [data-digest-prompt]").first
        if prompt.count() == 0:
            raise E2EFailure("synthetic daily digest did not render a consultation prompt")
        expected = prompt.inner_text()
        prompt.click()
        page.locator("#chat").wait_for(state="visible")
        page.wait_for_function("expected => document.querySelector('#chat-message')?.value === expected", arg=expected, timeout=3000)
        if page.locator("#chat-message").input_value() != expected:
            raise E2EFailure("daily digest did not prefill the selected consultation prompt")
        if page.locator("#chat-answer").inner_text().strip():
            raise E2EFailure("daily digest consultation prompt was sent automatically")
    else:
        page.locator("#today-digest [data-digest-timeline]").click()
        page.locator("#explore").wait_for(state="visible", timeout=4000)


def verify_empty_daily_digest(page: Any, database: Path, directory: Path, manifest: list[dict[str, Any]], prefix: str, viewport: tuple[int, int]) -> None:
    """Use only the current synthetic SQLite database to exercise the empty state."""
    with sqlite3.connect(database) as connection:
        connection.execute("UPDATE facts SET status='excluded'")
        connection.execute("UPDATE fact_reviews SET state='rejected'")
        connection.execute("DELETE FROM memory_changes")
        connection.execute("DELETE FROM decisions")
    page.evaluate("() => sessionStorage.clear()")
    route(page, "today")
    page.evaluate("() => window.refreshActionCenter?.()")
    page.wait_for_function("() => document.querySelector('#today-daily-actions')?.textContent.includes('最初の記録を残す')", timeout=5000)
    screenshot(page, directory, manifest, f"{prefix}-today-digest-empty", "#today", "daily-digest-empty", viewport)
    page.locator("#today-daily-actions [data-action-primary]").click()
    page.locator("#home").wait_for(state="visible")


def verify_action_center_review_inbox(page: Any, database: Path, directory: Path, manifest: list[dict[str, Any]],
                                      prefix: str, viewport: tuple[int, int], *, mobile: bool) -> None:
    """Exercise one-action Today and the real deterministic Review Inbox."""
    page.evaluate("""() => Object.keys(sessionStorage)
      .filter(key => key.startsWith('personal-os-draft-'))
      .forEach(key => sessionStorage.removeItem(key))""")
    route(page, "today")
    page.locator("#today-daily-actions [data-action-primary]").wait_for(state="visible", timeout=5000)
    if page.locator("#today-daily-actions [data-action-primary]").count() != 1:
        raise E2EFailure("Today did not render exactly one primary next action")
    if not page.locator("#today-daily-actions .action-reason").inner_text().strip():
        raise E2EFailure("Today action has no reason")
    if page.locator("#today-daily-actions [data-quick-route]").count() != 3:
        raise E2EFailure("Today quick actions are not bounded to three")
    if prefix in {"desktop-1280", "mobile-390"}:
        screenshot(page, directory, manifest, f"{prefix}-action-center", "#today", "action-center", viewport)

    # Draft v2 ignores short/old content, prioritizes a failed save, and routes
    # back to the correct form without sending automatically.
    with sqlite3.connect(database) as connection:
        draft_decision_id = int(connection.execute("SELECT id FROM decisions ORDER BY id LIMIT 1").fetchone()[0])
    page.evaluate("""value => { const recent=new Date().toISOString(), fourDays=new Date(Date.now()-4*86400000).toISOString(), old=new Date(Date.now()-8*86400000).toISOString(); window.PersonalOSDraftStore.write('personal-os-draft-chat',{kind:'chat',body:'short',updated_at:recent,save_failed:false,hidden_until:null,route:'chat',focus:'#chat-message'}); window.PersonalOSDraftStore.write(`personal-os-draft-decision-${value}-result`,{kind:'decision_result',body:'Synthetic four day result',fields:{good:'Synthetic good',next:'Synthetic next',score:'良かった'},target_id:value,mode:'result',updated_at:fourDays,save_failed:false,hidden_until:null,route:'decisions',focus:'#decision-outcome-text'}); window.PersonalOSDraftStore.write('personal-os-draft-ux-feedback',{kind:'ux_feedback',body:'Synthetic old feedback draft',fields:{expected:'Synthetic expected'},updated_at:old,save_failed:false,hidden_until:null,route:'settings',focus:'#ux-feedback-body'}); }""", draft_decision_id)
    page.evaluate("() => window.refreshActionCenter?.()")
    page.wait_for_timeout(80)
    if "書きかけ" in page.locator("#today-daily-actions h2").inner_text():
        raise E2EFailure("short or old draft incorrectly occupied the Today action")
    draft_value = page.evaluate("""async () => { const draft={version:2,body:'Synthetic unfinished memo',updated_at:new Date().toISOString(),save_failed:false,hidden_until:null,route:'home',focus:'#record-text'}; sessionStorage.setItem('personal-os-draft-memo',JSON.stringify(draft)); await window.refreshActionCenter?.(); return JSON.parse(sessionStorage.getItem('personal-os-draft-memo')).body; }""")
    if draft_value != "Synthetic unfinished memo":
        raise E2EFailure("client draft was not retained before Action Center refresh")
    page.wait_for_timeout(120)
    draft_state = page.evaluate("() => ({ text: document.querySelector('#today-daily-actions')?.textContent || '', keys: Object.keys(sessionStorage) })")
    if "書きかけの記録" not in draft_state["text"]:
        raise E2EFailure(f"client draft did not override the server action: {draft_state}")
    page.evaluate("""async () => { window.PersonalOSDraftStore.write('personal-os-draft-chat',{body:'短い失敗',save_failed:true}); await window.refreshActionCenter?.(); }""")
    page.wait_for_timeout(80)
    if "保存に失敗" not in page.locator("#today-daily-actions").inner_text():
        raise E2EFailure("save_failed draft did not outrank the recent normal draft")
    if prefix == "mobile-390":
        screenshot(page, directory, manifest, f"{prefix}-action-center-failed-short-draft", "#today", "failed-short-draft", viewport)
    page.evaluate("() => sessionStorage.removeItem('personal-os-draft-chat')")
    page.evaluate("() => window.refreshActionCenter?.()")
    if page.locator("#today-daily-actions .old-draft-list").count() == 0:
        raise E2EFailure("72-hour and older drafts were not offered in the restore list")
    page.locator("#today-daily-actions .old-draft-list summary").click()
    if page.locator("#today-daily-actions [data-old-draft-key]").count() < 2:
        raise E2EFailure("restorable four-day and old drafts were not both retained")
    if prefix == "mobile-390":
        page.evaluate("() => { const card=document.querySelector('#today-daily-actions'); if(card) window.scrollTo(0,Math.max(0,card.offsetTop-72)); }")
        page.wait_for_timeout(100)
        screenshot(page, directory, manifest, f"{prefix}-action-center-restorable-drafts", "#today", "restorable-drafts", viewport)
    page.locator(f"#today-daily-actions [data-old-draft-key='personal-os-draft-decision-{draft_decision_id}-result']").click()
    page.locator("#decision-outcome-sheet").wait_for(state="visible", timeout=5000)
    if page.locator("#decision-outcome-text").input_value() != "Synthetic four day result" or page.locator("#decision-outcome-good").input_value() != "Synthetic good":
        raise E2EFailure("Decision result Draft v2 did not reopen the target sheet with all fields")
    page.locator("#decision-outcome-sheet [data-sheet-close]").last.click()
    route(page, "today"); page.evaluate("() => window.refreshActionCenter?.()"); page.locator("#today-daily-actions .old-draft-list summary").click()
    page.locator("#today-daily-actions [data-old-draft-key='personal-os-draft-ux-feedback']").click()
    page.locator("#ux-feedback-sheet").wait_for(state="visible", timeout=5000)
    if page.locator("#ux-feedback-body").input_value() != "Synthetic old feedback draft" or page.locator("#ux-feedback-expected").input_value() != "Synthetic expected":
        raise E2EFailure("Feedback Draft v2 did not reopen the feedback sheet")
    page.locator("#ux-feedback-sheet [data-sheet-close]").last.click()
    route(page, "today"); page.evaluate("() => window.refreshActionCenter?.()")
    page.locator("#today-daily-actions [data-action-primary]").click()
    page.locator("#home").wait_for(state="visible")
    page.evaluate("() => { sessionStorage.removeItem('personal-os-draft-memo'); }")

    route(page, "verify")
    page.locator("#review-inbox-focus [data-review-id]").wait_for(state="visible", timeout=5000)
    first_id = page.locator("#review-inbox-focus [data-review-id]").get_attribute("data-review-id")
    if page.locator("#review-inbox-focus .review-domain").count() != 1:
        raise E2EFailure("Review Inbox did not render one focus card")
    if prefix in {"desktop-1280", "mobile-390"}:
        screenshot(page, directory, manifest, f"{prefix}-review-inbox", "#verify", "review-inbox", viewport)
    if mobile:
        page.locator("#review-inbox-focus [data-review-defer]").click()
        page.locator("#review-inbox-focus [data-review-period='one_day']").wait_for(state="visible")
        page.locator("#review-inbox-focus [data-review-period='indefinite']").scroll_into_view_if_needed()
        page.wait_for_timeout(100)
        if prefix == "mobile-390":
            screenshot(page, directory, manifest, f"{prefix}-review-snooze", "#verify", "review-snooze-options", viewport)
        with page.expect_response(lambda response: f"/api/facts/{first_id}/review" in response.url and response.request.method == "PATCH", timeout=8000) as deferred:
            page.locator("#review-inbox-focus [data-review-period='one_day']").click()
        if not deferred.value.ok:
            raise E2EFailure(f"Review snooze failed: {deferred.value.status}")
        with sqlite3.connect(database) as connection:
            state = connection.execute("SELECT state FROM fact_reviews WHERE fact_id=?", (first_id,)).fetchone()[0]
        if state != "pending":
            raise E2EFailure(f"temporary snooze changed review state to {state}")
        page.wait_for_function("previous => document.querySelector('#review-inbox-focus [data-review-id]')?.dataset.reviewId !== previous", arg=first_id, timeout=5000)
        reload_app(page); route(page, "verify")
        page.locator("[data-review-bucket='deferred']").click()
        page.wait_for_function("() => document.querySelector('[data-review-bucket=\"deferred\"]')?.classList.contains('active')", timeout=5000)
        page.locator("#review-inbox-list-toggle").click()
        page.wait_for_function("expected => [...document.querySelectorAll('#review-inbox-focus [data-review-id],#review-inbox-list [data-review-id]')].some(node => node.dataset.reviewId === expected)", arg=first_id, timeout=5000)
    else:
        if prefix != "desktop-1280":
            page.locator("#review-inbox-list-toggle").click()
            if page.locator("#review-inbox-focus [data-review-id],#review-inbox-list [data-review-id]").count() > 10:
                raise E2EFailure("secondary viewport rendered more than one bounded review page")
            assert_layout(page, mobile=False)
            return
        if page.locator("#review-inbox-focus [data-review-state]").count() != 0:
            raise E2EFailure("sensitive review exposed confirmation before explicit detail request")
        if prefix == "desktop-1280": screenshot(page, directory, manifest, f"{prefix}-review-sensitive-masked", "#verify", "review-sensitive-masked", viewport)
        with page.expect_response(lambda response: f"/api/review-inbox/{first_id}/detail" in response.url, timeout=8000) as detail:
            page.locator("#review-inbox-focus [data-review-reveal]").click()
        if "no-store" not in (detail.value.headers.get("cache-control") or "").lower():
            raise E2EFailure("sensitive review detail response was cacheable")
        if not detail.value.ok or page.locator("#review-inbox-focus").inner_text().find("合成の資産確認候補") < 0:
            raise E2EFailure("sensitive review detail was not revealed after the explicit action")
        if prefix == "desktop-1280":
            screenshot(page, directory, manifest, f"{prefix}-review-sensitive-detail", "#verify", "review-sensitive-detail", viewport)
            screenshot(page, directory, manifest, f"{prefix}-review-focus", "#verify", "review-focus", viewport)
        page.locator("#review-inbox-focus [data-review-close]").click()
        if "合成の資産確認候補" in page.locator("#review-inbox-focus").inner_text():
            raise E2EFailure("closing sensitive detail left the real summary in the DOM")
        page.locator("#review-inbox-focus [data-review-reveal]").click()
        page.locator("#review-inbox-focus [data-review-correct]").wait_for(state="visible", timeout=5000)
        dialog_answers = ["合成の資産確認候補（修正済み）", '{"amount":654321,"currency":"JPY"}']
        def answer_correction(dialog: Any) -> None:
            dialog.accept(dialog_answers.pop(0))
        page.on("dialog", answer_correction)
        with page.expect_response(lambda response: response.url.endswith(f"/api/facts/{first_id}") and response.request.method == "PATCH", timeout=8000) as corrected:
            page.locator("#review-inbox-focus [data-review-correct]").click()
        page.remove_listener("dialog", answer_correction)
        if not corrected.value.ok:
            raise E2EFailure(f"sensitive correction failed: {corrected.value.status}")
        with sqlite3.connect(database) as connection:
            stored = connection.execute("SELECT summary,value_json FROM facts WHERE id=?", (first_id,)).fetchone()
        if stored[0] != "合成の資産確認候補（修正済み）" or json.loads(stored[1]).get("amount") != 654321:
            raise E2EFailure("sensitive correction did not persist the explicitly reviewed values")
        for _ in range(2):
            current_id = page.locator("#review-inbox-focus [data-review-id]").get_attribute("data-review-id")
            with page.expect_response(lambda response: response.url.endswith("/review") and response.request.method == "PATCH", timeout=8000) as reviewed:
                page.locator("#review-inbox-focus [data-review-state='confirmed']").click()
            if not reviewed.value.ok: raise E2EFailure(f"Review confirmation failed: {reviewed.value.status}")
            if _ == 0: page.wait_for_function("previous => document.querySelector('#review-inbox-focus [data-review-id]')?.dataset.reviewId !== previous", arg=current_id, timeout=5000)
        page.locator("#review-inbox-focus .review-pause").wait_for(state="visible", timeout=5000)
        if prefix == "desktop-1280": screenshot(page, directory, manifest, f"{prefix}-review-three-complete", "#verify", "review-three-complete", viewport)
        page.locator("#review-inbox-focus [data-review-continue]").click()
        page.locator("[data-review-bucket='normal']").click()
        page.locator("#review-inbox-list-toggle").click()
        first_page_count = page.locator("#review-inbox-focus [data-review-id],#review-inbox-list [data-review-id]").count()
        if first_page_count > 10: raise E2EFailure(f"Review Inbox initial page rendered {first_page_count} items")
        if page.locator("#review-inbox-load-more:visible").count():
            page.locator("#review-inbox-load-more").click()
            page.wait_for_function("count => document.querySelectorAll('#review-inbox-focus [data-review-id],#review-inbox-list [data-review-id]').length > count", arg=first_page_count, timeout=5000)
        normal_fact = page.locator("[data-review-kind='fact']").first
        if normal_fact.count() == 0:
            raise E2EFailure("normal Fact was not available for Evidence verification")
        normal_id = normal_fact.get_attribute("data-review-id")
        if normal_fact.locator(".review-evidence .body").count():
            raise E2EFailure("normal Evidence was embedded in the initial DOM")
        if prefix == "desktop-1280":
            screenshot(page, directory, manifest, f"{prefix}-review-normal-evidence-closed", "#verify", "normal-evidence-closed", viewport)
        with page.expect_response(lambda response: response.url.endswith(f"/api/review-inbox/{normal_id}/detail"), timeout=8000) as normal_detail:
            normal_fact.locator(".review-evidence summary").click()
        if not normal_detail.value.ok or "no-store" not in (normal_detail.value.headers.get("cache-control") or "").lower():
            raise E2EFailure("normal Evidence detail did not return a non-cacheable successful response")
        normal_fact.locator(".review-evidence .body").wait_for(state="visible", timeout=5000)
        if "合成デモの資産、旅行、住居、人物予定" not in normal_fact.inner_text():
            raise E2EFailure("normal Fact Evidence was not rendered after lazy load")
        if prefix == "desktop-1280":
            screenshot(page, directory, manifest, f"{prefix}-review-normal-evidence-open", "#verify", "normal-evidence-open", viewport)
        technical = normal_fact.locator(".review-technical")
        if technical.count() == 0 or technical.get_attribute("open") is not None:
            raise E2EFailure("technical detail was missing or initially open")
        technical.locator("summary").click()
        if prefix == "desktop-1280":
            screenshot(page, directory, manifest, f"{prefix}-review-technical-detail", "#verify", "technical-detail", viewport)
        while page.locator("[data-review-kind='memory_proposal']").count() == 0 and page.locator("#review-inbox-load-more:visible").count():
            page.locator("#review-inbox-load-more").click(); page.wait_for_timeout(180)
        proposal = page.locator("[data-review-kind='memory_proposal']").first
        if proposal.count() == 0: raise E2EFailure("pending memory proposal did not appear in Review Inbox")
        proposal_id = proposal.get_attribute("data-review-id")
        with page.expect_response(lambda response: response.url.endswith(f"/api/memory-proposals/{proposal_id}/apply") and response.request.method == "POST", timeout=8000) as applied:
            proposal.locator("[data-proposal-apply]").click()
        if not applied.value.ok: raise E2EFailure(f"memory proposal apply failed: {applied.value.status}")
        with sqlite3.connect(database) as connection:
            proposal_status = connection.execute("SELECT status FROM memory_proposals WHERE id=?", (proposal_id,)).fetchone()[0]
        if proposal_status != "applied": raise E2EFailure("memory proposal did not persist its applied state")
    assert_layout(page, mobile=mobile)


def verify_timeline(page: Any, directory: Path, manifest: list[dict[str, Any]], prefix: str, viewport: tuple[int, int], *, mobile: bool) -> None:
    """Exercise the real timeline API, filters, sheet and non-sending compare action."""
    route(page, "explore")
    page.locator("[data-explore-mode='timeline']").click()
    page.locator("#explore-timeline").wait_for(state="visible")
    page.locator("#timeline-list [data-timeline-event]").first.wait_for(state="visible", timeout=5000)
    if mobile:
        page.locator("#timeline-list [data-timeline-event]").first.scroll_into_view_if_needed()
        page.wait_for_timeout(80)
    screenshot(page, directory, manifest, f"{prefix}-timeline", "#explore", "timeline", viewport)
    page.locator("#timeline-domain").select_option("travel")
    page.locator("#timeline-list [data-timeline-event]").first.wait_for(state="visible", timeout=5000)
    labels = page.locator("#timeline-list").inner_text()
    if "旅行" not in labels:
        raise E2EFailure("timeline domain filter did not render travel events")
    event = page.locator("#timeline-list [data-timeline-event]").first
    event.click()
    page.locator("#timeline-detail-sheet").wait_for(state="visible")
    page.locator("#timeline-detail-content").wait_for(state="visible")
    screenshot(page, directory, manifest, f"{prefix}-timeline-detail", "#explore", "timeline-detail", viewport)
    page.keyboard.press("Escape")
    page.wait_for_function("() => document.querySelector('#timeline-detail-sheet')?.hidden === true", timeout=3000)
    if page.evaluate("() => document.activeElement?.dataset?.timelineEvent") != event.get_attribute("data-timeline-event"):
        raise E2EFailure("timeline detail sheet did not restore focus to its event card")
    # The synthetic seed contains one before/after housing Fact.  Use the
    # public domain filter and the rendered Japanese type label, rather than
    # leaking an internal event ID into the acceptance journey.
    with page.expect_response(lambda response: "/api/timeline?" in response.url and "domain=housing" in response.url, timeout=5000):
        page.locator("#timeline-domain").select_option("housing")
    page.wait_for_function("() => { const text=document.querySelector('#timeline-list')?.textContent || ''; return text.includes('住居') && text.includes('情報を更新'); }", timeout=5000)
    candidate = page.locator("#timeline-list [data-timeline-event^='fact-']").filter(has_text="住居の情報を更新").first
    if candidate.count() == 0:
        raise E2EFailure("timeline synthetic fact-change event is missing")
    candidate.click(); page.locator("#timeline-detail-sheet").wait_for(state="visible")
    compare = page.locator("[data-timeline-compare]")
    if compare.count() == 0:
        raise E2EFailure("timeline fact-change detail has no compare action: " + page.locator("#timeline-detail-content").inner_text())
    page.evaluate("() => { document.querySelector('#chat-answer').textContent=''; window.__timelineCompareSent=false; window.addEventListener('personal-os-chat-response', () => { window.__timelineCompareSent=true; }, {once:true}); }")
    compare.click(); page.locator("#chat").wait_for(state="visible")
    page.wait_for_timeout(120)
    if not page.locator("#chat-message").input_value().strip() or page.locator("#chat-answer").inner_text().strip() or page.evaluate("() => window.__timelineCompareSent === true"):
        raise E2EFailure("timeline comparison was not a non-sending consultation draft")
    if mobile:
        # The same shared Sheet must stay within the small viewport.
        assert_layout(page, mobile=True)


def verify_decision_replay(page: Any, directory: Path, manifest: list[dict[str, Any]], prefix: str,
                           viewport: tuple[int, int], *, mobile: bool) -> None:
    """Exercise the real read-only replay API from an actual decision card."""
    route(page, "decisions"); wait_decisions(page)
    decision_id = page.evaluate("""async () => {
      const rows = await (await fetch('/api/decisions')).json();
      return rows.find(row => row.title === 'Sample weekend decision')?.id || 0;
    }""")
    if not decision_id:
        raise E2EFailure("synthetic replay decision is missing")
    opener = page.locator(f"[data-decision-replay='{decision_id}']")
    opener.wait_for(state="visible", timeout=5000)
    with page.expect_response(lambda response: response.url.endswith(f"/api/decisions/{decision_id}/replay") and response.request.method == "GET", timeout=8000):
        opener.click()
    page.locator("#decision-replay-sheet").wait_for(state="visible")
    page.locator("#decision-replay-content .replay-stage").first.wait_for(state="visible", timeout=5000)
    if page.locator("#decision-replay-content .replay-stage").count() != 10:
        raise E2EFailure("decision replay did not render every lifecycle stage")
    if page.locator("#decision-replay-content").inner_text().find("Keep transfer time short.") < 0:
        raise E2EFailure("replay did not keep the consultation recommendation visible as context")
    screenshot(page, directory, manifest, f"{prefix}-decision-replay", "#decisions", "decision-replay", viewport)
    evidence = page.locator("#decision-replay-content .replay-evidence summary").first
    if evidence.count() > 0:
        evidence.click(); page.wait_for_timeout(80)
    screenshot(page, directory, manifest, f"{prefix}-decision-replay-evidence", "#decisions", "decision-replay-evidence", viewport)
    page.keyboard.press("Escape")
    page.locator("#decision-replay-sheet").wait_for(state="hidden")
    if page.evaluate("() => document.activeElement?.dataset?.decisionReplay") != str(decision_id):
        raise E2EFailure("decision replay sheet did not restore focus to its opener")
    if mobile:
        missing_id = page.evaluate("""async () => {
          const rows = await (await fetch('/api/decisions')).json();
          return rows.find(row => row.decision_state === 'executed')?.id || 0;
        }""")
        missing = page.locator(f"[data-decision-replay='{missing_id}']")
        missing.click(); page.locator("#decision-replay-sheet").wait_for(state="visible")
        page.locator("#decision-replay-content [data-replay-action='record_result']").wait_for(state="visible", timeout=5000)
        page.locator("#decision-replay-content [data-replay-action='record_result']").scroll_into_view_if_needed()
        page.wait_for_timeout(80)
        if page.locator("#decision-replay-content [data-replay-action='record_result']").count() == 0:
            raise E2EFailure("replay did not show an explicit action for a missing result")
        screenshot(page, directory, manifest, f"{prefix}-decision-replay-missing-stage", "#decisions", "decision-replay-missing-stage", viewport)
        page.keyboard.press("Escape")
        assert_layout(page, mobile=True)


def verify_feedback(page: Any, directory: Path, manifest: list[dict[str, Any]], prefix: str,
                    viewport: tuple[int, int]) -> None:
    route(page, "settings")
    feedback = page.locator("#production-readiness [data-action='ux-feedback']")
    feedback.wait_for(state="visible", timeout=5000)
    feedback.click(); page.locator("#ux-feedback-sheet").wait_for(state="visible")
    page.locator("#ux-feedback-body").fill("Synthetic feedback: the replay path is easy to find.")
    screenshot(page, directory, manifest, f"{prefix}-ux-feedback", "#settings", "ux-feedback", viewport)
    with page.expect_response(lambda response: response.url.endswith('/api/ux-feedback') and response.request.method == 'POST', timeout=8000) as saved:
        page.locator("#ux-feedback-form button[type='submit']").click()
    if not saved.value.ok:
        raise E2EFailure(f"feedback did not save locally: {saved.value.status}")
    page.wait_for_function("() => document.querySelector('#ux-feedback-list')?.textContent.includes('Synthetic feedback')", timeout=5000)
    page.keyboard.press("Escape")
    page.locator("#ux-feedback-sheet").wait_for(state="hidden", timeout=3000)


def verify_empty_timeline(page: Any, database: Path, directory: Path, manifest: list[dict[str, Any]], prefix: str, viewport: tuple[int, int]) -> None:
    # Do not leave the preceding focused-domain filter on the empty-state
    # evidence; this is an empty personal timeline, not an empty sub-domain.
    route(page, "explore")
    page.locator("[data-explore-mode='timeline']").click()
    page.locator("#timeline-domain").wait_for(state="visible", timeout=5000)
    page.locator("#timeline-domain").select_option("")
    page.wait_for_timeout(80)
    with sqlite3.connect(database) as connection:
        connection.execute("DELETE FROM execution_events")
        connection.execute("DELETE FROM plans")
        connection.execute("DELETE FROM decisions")
        connection.execute("DELETE FROM personal_inferences")
        connection.execute("UPDATE facts SET retrieval_eligibility='excluded'")
    route(page, "explore")
    page.locator("[data-explore-mode='timeline']").click()
    page.locator("#timeline-list .empty-state").wait_for(state="visible", timeout=5000)
    page.locator("#timeline-list .empty-state").scroll_into_view_if_needed()
    page.wait_for_timeout(80)
    screenshot(page, directory, manifest, f"{prefix}-timeline-empty", "#explore", "timeline-empty", viewport)
    page.locator("#timeline-list [data-timeline-record]").click()
    page.locator("#home").wait_for(state="visible")


def desktop_journey(page: Any, database: Path, directory: Path, manifest: list[dict[str, Any]], viewport: tuple[int, int], *, verify_persistence: bool) -> None:
    prefix = "desktop-1280" if viewport[0] == 1280 else "desktop-1440"
    route(page, "today"); screenshot(page, directory, manifest, f"{prefix}-today", "#today", "default", viewport)
    verify_action_center_review_inbox(page, database, directory, manifest, prefix, viewport, mobile=False)
    verify_daily_digest(page, directory, manifest, prefix, viewport, mobile=False)
    route(page, "home"); screenshot(page, directory, manifest, f"{prefix}-memory", "#memory", "default", viewport)
    if verify_persistence:
        record_success(page)
    route(page, "chat"); screenshot(page, directory, manifest, f"{prefix}-chat-input", "#chat", "input", viewport)
    make_chat_result(page, loading=(directory, manifest, f"{prefix}-chat-loading", viewport))
    screenshot(page, directory, manifest, f"{prefix}-chat-result", "#chat", "result", viewport)
    assert_distinct_screenshots(directory, f"{prefix}-chat-loading", f"{prefix}-chat-result")
    details = page.locator("#chat-result details summary").first
    if details.count() > 0:
        details.click(); page.wait_for_timeout(120)
    screenshot(page, directory, manifest, f"{prefix}-chat-evidence", "#chat", "evidence-open", viewport)
    save = page.locator("[data-save-consultation]")
    if save.count() > 0:
        save.click(); page.wait_for_timeout(160)
    route(page, "decisions"); wait_decisions(page); screenshot(page, directory, manifest, f"{prefix}-decisions", "#decisions", "default", viewport)
    verify_decision_replay(page, directory, manifest, prefix, viewport, mobile=False)
    outcome = page.locator("[data-decision-outcome]").first
    if outcome.count() > 0:
        outcome.click(); page.locator("#decision-outcome-sheet").wait_for(state="visible")
        page.locator("#decision-outcome-text").fill("Synthetic result note")
        screenshot(page, directory, manifest, f"{prefix}-decision-result-sheet", "#decisions", "result-sheet", viewport)
        page.keyboard.press("Escape")
    if verify_persistence:
        save_result_and_evaluation(page)
    for tab in ("money", "travel", "housing", "people"):
        route(page, tab); wait_domain(page, tab)
        screenshot(page, directory, manifest, f"{prefix}-{tab}", f"#{tab}", "domain", viewport)
    route(page, "explore"); page.locator("[data-explore-mode='space']").click(); wait_space(page); page.wait_for_timeout(250)
    screenshot(page, directory, manifest, f"{prefix}-explore-space", "#explore", "personal-space", viewport)
    node = page.locator("[data-space-node]").first
    if node.count() > 0:
        node.click(); page.wait_for_timeout(180)
    screenshot(page, directory, manifest, f"{prefix}-explore-space-detail", "#explore", "node-detail", viewport)
    page.locator("[data-explore-mode='benchmark']").click(); load_demo_benchmark(page)
    screenshot(page, directory, manifest, f"{prefix}-benchmark", "#explore", "benchmark", viewport)
    open_import = page.locator("#benchmark-import-open")
    if open_import.count() > 0:
        open_import.click(); page.locator("#benchmark-import-sheet").wait_for(state="visible")
    screenshot(page, directory, manifest, f"{prefix}-benchmark-import-sheet", "#explore", "benchmark-import-sheet", viewport)
    page.keyboard.press("Escape")
    verify_timeline(page, directory, manifest, prefix, viewport, mobile=False)
    route(page, "settings"); screenshot(page, directory, manifest, f"{prefix}-admin", "#settings", "default", viewport)
    if viewport == (1280, 720):
        screenshot(page, directory, manifest, f"{prefix}-production-readiness", "#settings", "production-readiness", viewport)
        verify_feedback(page, directory, manifest, prefix, viewport)
    route(page, "home")
    page.route("**/api/ingest", lambda request: request.fulfill(status=500, content_type="application/json", body='{"error":"Synthetic validation error"}'))
    page.locator("#record-text").fill("Synthetic failure state")
    page.locator("#record-form button:not(.voice)").last.click(); page.wait_for_timeout(160)
    screenshot(page, directory, manifest, f"{prefix}-error", "#memory", "synthetic-server-error", viewport)
    page.unroute("**/api/ingest")
    page.evaluate("document.querySelector('#record-text').value=''; document.querySelector('#record-notice').textContent='' ")
    screenshot(page, directory, manifest, f"{prefix}-empty", "#memory", "empty-capture", viewport)
    assert_layout(page)


def mobile_journey(page: Any, database: Path, directory: Path, manifest: list[dict[str, Any]], viewport: tuple[int, int], *, verify_persistence: bool) -> None:
    prefix = "mobile-390" if viewport[0] == 390 else "mobile-375"
    route(page, "today"); screenshot(page, directory, manifest, f"{prefix}-today", "#today", "default", viewport)
    verify_action_center_review_inbox(page, database, directory, manifest, prefix, viewport, mobile=True)
    verify_daily_digest(page, directory, manifest, prefix, viewport, mobile=True)
    route(page, "today")
    screenshot(page, directory, manifest, f"{prefix}-bottom-nav", "#today", "bottom-navigation", viewport)
    page.locator("[data-action='quick']").click(); page.locator("#quick-sheet").wait_for(state="visible")
    screenshot(page, directory, manifest, f"{prefix}-quick-sheet", "#today", "quick-sheet", viewport)
    page.keyboard.press("Escape")
    route(page, "home"); screenshot(page, directory, manifest, f"{prefix}-memory", "#memory", "default", viewport)
    if verify_persistence:
        record_success(page)
    page.locator("#record-image-open").click(); page.wait_for_timeout(100)
    screenshot(page, directory, manifest, f"{prefix}-memory-image", "#memory", "image-input", viewport)
    route(page, "chat"); screenshot(page, directory, manifest, f"{prefix}-chat-input", "#chat", "input", viewport)
    make_chat_result(page); screenshot(page, directory, manifest, f"{prefix}-chat-result", "#chat", "result", viewport)
    details = page.locator("#chat-result details summary").first
    if details.count() > 0: details.click()
    screenshot(page, directory, manifest, f"{prefix}-chat-evidence", "#chat", "evidence-open", viewport)
    route(page, "decisions"); wait_decisions(page); screenshot(page, directory, manifest, f"{prefix}-decisions", "#decisions", "default", viewport)
    # The primary mobile journey intentionally mutates an executed Decision
    # while checking result/evaluation persistence.  The missing-result
    # Replay evidence therefore belongs to the fresh 390px journey only.
    verify_decision_replay(page, directory, manifest, prefix, viewport, mobile=viewport == (390, 844))
    outcome = page.locator("[data-decision-outcome]").first
    if outcome.count() > 0:
        outcome.click(); page.locator("#decision-outcome-text").fill("Synthetic draft outcome")
        screenshot(page, directory, manifest, f"{prefix}-decision-result-sheet", "#decisions", "result-sheet", viewport)
        page.keyboard.press("Escape")
    if verify_persistence:
        save_result_and_evaluation(page)
    page.locator("[data-action='more']").click(); page.locator("#more-sheet").wait_for(state="visible")
    screenshot(page, directory, manifest, f"{prefix}-more-sheet", "#decisions", "more-sheet", viewport)
    page.keyboard.press("Escape")
    route(page, "explore"); page.locator("[data-explore-mode='space']").click(); screenshot(page, directory, manifest, f"{prefix}-explore", "#explore", "default", viewport)
    wait_space(page); page.wait_for_timeout(200)
    screenshot(page, directory, manifest, f"{prefix}-explore-space", "#explore", "personal-space", viewport)
    node = page.locator("[data-space-node]").first
    if node.count() > 0: node.click(); page.wait_for_timeout(150)
    screenshot(page, directory, manifest, f"{prefix}-explore-space-detail", "#explore", "node-detail", viewport)
    page.locator("[data-explore-mode='benchmark']").click(); load_demo_benchmark(page)
    screenshot(page, directory, manifest, f"{prefix}-benchmark", "#explore", "benchmark", viewport)
    open_import = page.locator("#benchmark-import-open")
    if open_import.count() > 0: open_import.click()
    screenshot(page, directory, manifest, f"{prefix}-benchmark-import-sheet", "#explore", "benchmark-import-sheet", viewport)
    page.keyboard.press("Escape")
    verify_timeline(page, directory, manifest, prefix, viewport, mobile=True)
    for tab in ("money", "housing"):
        route(page, tab); wait_domain(page, tab)
        screenshot(page, directory, manifest, f"{prefix}-{tab}", f"#{tab}", "domain", viewport)
    route(page, "home")
    page.locator("#record-text").fill("Synthetic mobile draft")
    page.locator("[data-action='more']").click(); page.keyboard.press("Escape")
    screenshot(page, directory, manifest, f"{prefix}-draft-restored", "#memory", "draft-retained", viewport)
    page.route("**/api/ingest", lambda request: request.fulfill(status=500, content_type="application/json", body='{"error":"Synthetic validation error"}'))
    page.locator("#record-form button:not(.voice)").last.click(); page.wait_for_timeout(160)
    screenshot(page, directory, manifest, f"{prefix}-error", "#memory", "synthetic-server-error", viewport)
    page.unroute("**/api/ingest")
    assert_layout(page, mobile=True)


def promote_screenshots(directory: Path, manifest: list[dict[str, Any]]) -> None:
    # Keep the public repository useful without turning it into a large archive
    # of every E2E intermediate state.  The complete evidence set remains in
    # the ignored test-results directory; this compact set covers both primary
    # viewports plus one representative of the secondary sizes.
    public_names = {
        "desktop-1280-today.png", "desktop-1280-memory.png", "desktop-1280-chat-loading.png",
        "desktop-1280-action-center.png", "desktop-1280-review-inbox.png", "desktop-1280-review-focus.png",
        "desktop-1280-review-sensitive-masked.png", "desktop-1280-review-sensitive-detail.png", "desktop-1280-review-three-complete.png",
        "desktop-1280-review-normal-evidence-closed.png", "desktop-1280-review-normal-evidence-open.png", "desktop-1280-review-technical-detail.png",
        "desktop-1280-today-digest.png",
        "desktop-1280-chat-result.png", "desktop-1280-decisions.png", "desktop-1280-decision-result-sheet.png",
        "desktop-1280-decision-replay.png", "desktop-1280-decision-replay-evidence.png", "desktop-1280-ux-feedback.png", "desktop-1280-production-readiness.png",
        "desktop-1280-money.png", "desktop-1280-explore-space.png", "desktop-1280-benchmark.png", "desktop-1280-timeline.png", "desktop-1280-timeline-detail.png",
        "mobile-390-today.png", "mobile-390-memory.png", "mobile-390-memory-image.png",
        "mobile-390-action-center.png", "mobile-390-review-inbox.png", "mobile-390-review-snooze.png",
        "mobile-390-action-center-failed-short-draft.png", "mobile-390-action-center-restorable-drafts.png",
        "mobile-390-today-digest.png",
        "mobile-390-chat-result.png", "mobile-390-decisions.png", "mobile-390-decision-result-sheet.png",
        "mobile-390-decision-replay.png", "mobile-390-decision-replay-missing-stage.png",
        "mobile-390-more-sheet.png", "mobile-390-explore-space.png", "mobile-390-benchmark.png", "mobile-390-timeline.png", "mobile-390-timeline-detail.png", "mobile-390-timeline-empty.png",
        "desktop-1440-today.png", "mobile-375-today.png",
    }
    # A secondary viewport run appends to the working manifest.  Retain only
    # the newest instance of each public filename so repeated local E2E runs
    # never inflate a public manifest with duplicate entries.
    by_name = {item["file"]: item for item in manifest if item["file"] in public_names}
    public_manifest = [by_name[name] for name in sorted(by_name)]
    missing = public_names - set(by_name)
    if missing:
        raise E2EFailure("Missing required public review screenshots: " + ", ".join(sorted(missing)))
    PUBLIC_DIR.mkdir(parents=True, exist_ok=True)
    # OneDrive may expose this allowlisted directory as a protected reparse
    # point. Keep the directory itself and replace only its generated files.
    for old_file in PUBLIC_DIR.glob("*.png"):
        old_file.unlink()
    old_manifest = PUBLIC_DIR / "manifest.json"
    if old_manifest.is_file():
        old_manifest.unlink()
    for item in public_manifest:
        shutil.copy2(directory / item["file"], PUBLIC_DIR / item["file"])
    payload = {"version": "1", "generated_at": datetime.now(UTC).isoformat(), "environment": "verification", "data_type": "synthetic", "screenshots": public_manifest}
    (PUBLIC_DIR / "manifest.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    sys.path.insert(0, str(ROOT))
    from tools.check_public_screenshots import find_screenshot_issues
    issues = find_screenshot_issues(ROOT, require_approval=False)
    if issues:
        raise E2EFailure("Public screenshot safety failed: " + "; ".join(issues))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--promote", action="store_true", help="Copy reviewed synthetic results to docs/screenshots/ux-phase5")
    parser.add_argument("--suite", choices=("all", "desktop", "mobile"), default="all", help="Run all viewports or one bounded suite")
    parser.add_argument("--viewport-set", choices=("all", "primary", "secondary"), default="all", help="Run both viewports or one bounded viewport per suite")
    args = parser.parse_args()
    # A desktop journey mutates its synthetic database (capture, outcome and
    # evaluation persistence).  Run the two acceptance suites as independent
    # child processes so a mobile journey can never inherit that state.
    if args.suite == "all":
        base = [str(PYTHON), str(Path(__file__).resolve()), "--viewport-set", args.viewport_set]
        try:
            subprocess.run([*base, "--suite", "desktop"], cwd=ROOT, check=True)
            mobile_command = [*base, "--suite", "mobile"]
            if args.promote:
                mobile_command.append("--promote")
            subprocess.run(mobile_command, cwd=ROOT, check=True)
        except subprocess.CalledProcessError as error:
            raise E2EFailure(f"independent {args.suite} suite failed ({error.returncode})") from error
        manifest_path = RESULTS / "ux-phase5" / "manifest-work.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.is_file() else []
        print(json.dumps({"status": "PASS", "suites": ["desktop", "mobile"], "screenshots": len(manifest), "result_dir": str(RESULTS / "ux-phase5"), "promoted": args.promote}, ensure_ascii=False))
        return 0
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as error:
        raise E2EFailure("Install requirements-dev.txt before running UX E2E") from error
    assert_port_free()
    RESULTS.mkdir(parents=True, exist_ok=True)
    run_dir = RESULTS / "ux-phase5"
    work_manifest = run_dir / "manifest-work.json"
    if args.suite in {"all", "desktop"} and args.viewport_set != "secondary":
        # OneDrive can expose this ignored result directory as a protected
        # reparse point. Keep the directory and clear only known generated
        # files instead of trying to remove the directory itself.
        run_dir.mkdir(parents=True, exist_ok=True)
        for generated in run_dir.glob("*.png"):
            generated.unlink()
        generated_manifest = run_dir / "manifest.json"
        if generated_manifest.is_file():
            generated_manifest.unlink()
        if work_manifest.is_file():
            work_manifest.unlink()
    elif not work_manifest.is_file():
        raise E2EFailure("secondary/mobile suite needs a preceding suite so the review set remains complete")
    temp_root = Path(tempfile.mkdtemp(prefix="personal-os-ux-e2e-"))
    database = temp_root / "ux-synthetic.db"
    environment = os.environ.copy()
    environment.update({"PERSONAL_OS_ENV": "verification", "PERSONAL_OS_DB_PATH": str(database), "PERSONAL_OS_BACKUP_DIR": str(temp_root / "backups"), "PERSONAL_OS_ATTACHMENT_DIR": str(temp_root / "attachments"), "PERSONAL_OS_HOST": "127.0.0.1", "PERSONAL_OS_PORT": "8877", "PERSONAL_OS_E2E_CHAT_DELAY_MS": "1500"})
    process: subprocess.Popen[str] | None = None
    manifest: list[dict[str, Any]] = json.loads(work_manifest.read_text(encoding="utf-8")) if work_manifest.is_file() else []
    console_errors: list[str] = []
    try:
        subprocess.run([str(PYTHON), str(ROOT / "tools" / "seed_ux_demo.py"), "--db", str(database), "--profile", "review-backlog"], cwd=ROOT, env=environment, check=True)
        environment["PERSONAL_OS_RUN_STARTUP_MAINTENANCE"] = "false"
        environment["PERSONAL_OS_QUEUE_ANALYSIS_ON_START"] = "false"
        # Do not leave the verbose request log in an unread PIPE.  On Windows
        # that pipe eventually fills during a long browser suite and blocks
        # the server from serving deferred JS on reload.
        process = subprocess.Popen(
            [str(PYTHON), "app.py"], cwd=ROOT, env=environment,
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, text=True,
        )
        wait_for_server(process)
        with sync_playwright() as playwright:
            executable, browser_kind = browser_choice()
            launch_options: dict[str, Any] = {"headless": True, "args": ["--disable-gpu"]}
            if executable is not None:
                launch_options["executable_path"] = str(executable)
            browser = playwright.chromium.launch(**launch_options)
            suites = ((False, ((1280, 720), (1440, 900))), (True, ((390, 844), (375, 667))))
            for mobile, viewports in suites:
                if args.suite == "desktop" and mobile:
                    continue
                if args.suite == "mobile" and not mobile:
                    continue
                if args.viewport_set == "primary":
                    viewports = viewports[:1]
                elif args.viewport_set == "secondary":
                    viewports = viewports[1:]
                first = viewports[0]
                context = browser.new_context(viewport={"width": first[0], "height": first[1]}, device_scale_factor=1, is_mobile=mobile, has_touch=mobile)
                page = context.new_page()
                page.on("console", lambda message: console_errors.append(message.text) if message.type == "error" and "Failed to load resource" not in message.text else None)
                page.on("pageerror", lambda error: console_errors.append(f"pageerror: {getattr(error, 'stack', None) or error}"))
                for viewport in viewports:
                    page.set_viewport_size({"width": viewport[0], "height": viewport[1]})
                    if mobile: mobile_journey(page, database, run_dir, manifest, viewport, verify_persistence=viewport == (390, 844))
                    else: desktop_journey(page, database, run_dir, manifest, viewport, verify_persistence=viewport == (1280, 720))
                if args.viewport_set != "secondary":
                    prefix = "mobile-390" if mobile else "desktop-1280"
                    page.set_viewport_size({"width": first[0], "height": first[1]})
                    verify_empty_daily_digest(page, database, run_dir, manifest, prefix, first)
                    if mobile:
                        verify_empty_timeline(page, database, run_dir, manifest, prefix, first)
                context.close()
            # The timeout journey is covered by the default browser suite.
            # Playwright Chromium separately exercises the full persistence
            # journey; its process transport cannot safely run the injected
            # abort fixture while a response is intentionally pending.
            if args.suite == "desktop" and args.viewport_set != "secondary" and browser_kind != "playwright-chromium":
                record_timeout(browser, console_errors)
            browser.close()
        if console_errors:
            raise E2EFailure("browser console errors: " + " | ".join(console_errors[:5]))
        work_manifest.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        if args.promote: promote_screenshots(run_dir, manifest)
        print(json.dumps({"status": "PASS", "screenshots": len(manifest), "result_dir": str(run_dir), "promoted": args.promote, "browser": browser_kind}, ensure_ascii=False))
        return 0
    except Exception as error:
        if console_errors:
            raise E2EFailure(f"{error}; browser errors: {' | '.join(console_errors[:5])}") from error
        raise
    finally:
        if process is not None and process.poll() is None:
            process.terminate()
            try: process.wait(timeout=8)
            except subprocess.TimeoutExpired: process.kill()
        shutil.rmtree(temp_root, ignore_errors=True)


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except E2EFailure as error:
        print(f"UX E2E: FAIL: {error}", file=sys.stderr)
        raise SystemExit(1)
