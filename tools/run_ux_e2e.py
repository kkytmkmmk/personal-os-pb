"""Run reproducible Personal OS browser journeys against synthetic data only.

The runner creates a new temporary SQLite database, starts the verification
server on port 8877, drives the real HTML/CSS/JS through Playwright and can
promote reviewed viewport screenshots into ``docs/screenshots/ux-phase5``.
It never opens or copies ``data/personal_os.db``.
"""
from __future__ import annotations

import argparse
import json
import os
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
RESULTS = ROOT / "test-results" / "screenshots"
PUBLIC_DIR = ROOT / "docs" / "screenshots" / "ux-phase5"
EDGE_PATHS = (
    Path(os.environ.get("PERSONAL_OS_E2E_BROWSER", "")),
    Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"),
    Path(r"C:\Program Files\Microsoft\Edge\Application\msedge.exe"),
)


class E2EFailure(RuntimeError):
    pass


def assert_port_free() -> None:
    probe = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        if probe.connect_ex(("127.0.0.1", 8877)) == 0:
            raise E2EFailure("port 8877 is already in use; stop the verification server before running UX E2E")
    finally:
        probe.close()


def browser_choice() -> tuple[Path | None, str]:
    configured = os.environ.get("PERSONAL_OS_E2E_BROWSER")
    if configured:
        candidate = Path(configured)
        if not candidate.is_file():
            raise E2EFailure("PERSONAL_OS_E2E_BROWSER does not point to a browser executable")
        return candidate, "configured"
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
        page.goto(f"{BASE_URL}/#today", wait_until="load")
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
    page.reload(wait_until="load"); route(page, "home")
    persisted = page.evaluate("""async marker => (await (await fetch('/api/entries?q=' + encodeURIComponent(marker))).json()).some(entry => entry.body === marker)""", marker)
    if not persisted:
        raise E2EFailure("recorded synthetic memo did not persist after reload")


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
    page.reload(wait_until="load"); route(page, "decisions"); wait_decisions(page)
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
    page.reload(wait_until="load"); route(page, "decisions"); wait_decisions(page)
    if page.locator("#decisions-content").inner_text().find("Synthetic persisted evaluation") < 0:
        raise E2EFailure("later evaluation did not persist after reload")


def make_chat_result(page: Any, *, loading: tuple[Path, list[dict[str, Any]], str, tuple[int, int]] | None = None) -> None:
    route(page, "chat")
    page.locator("#chat-message").fill("次の休日の過ごし方を整理したい")
    with page.expect_response(lambda response: response.url.endswith("/api/chat") and response.request.method == "POST", timeout=8000) as consulted:
        page.locator("#chat-form button[type='submit'], #chat-form button:not(.voice)").last.click()
    if not consulted.value.ok:
        raise E2EFailure(f"synthetic consultation did not succeed: {consulted.value.status}")
    if loading:
        directory, manifest, name, viewport = loading
        page.wait_for_function("""() => document.querySelector('#consultation-status')?.textContent.trim().length > 0""", timeout=5000)
        screenshot(page, directory, manifest, name, "#chat", "processing", viewport)
    page.locator("#chat-result").wait_for(state="visible")
    page.wait_for_function("""() => document.querySelector('#chat-answer')?.textContent.trim().length > 0""", timeout=8000)
    page.wait_for_timeout(150)


def load_demo_benchmark(page: Any) -> None:
    """Wait for both the real local POST and its subsequent rendered result."""
    # A previous Desktop journey may already have inserted the synthetic bundle
    # into this same temporary DB.  First let the real GET render that state;
    # do not submit a duplicate just to obtain a screenshot.
    page.wait_for_function("""() => document.querySelector('#benchmark-series')?.textContent.trim().length > 0""", timeout=8000)
    if page.locator("#benchmark-series .benchmark-card").count() > 0:
        return
    with page.expect_response(lambda response: response.url.endswith("/api/benchmarks/demo") and response.request.method == "POST", timeout=8000) as posted:
        page.locator("#benchmark-load-demo").click()
    response = posted.value
    if not response.ok:
        raise E2EFailure(f"synthetic benchmark demo endpoint failed: {response.status} {response.text()[:240]}")
    page.wait_for_function("""() => Boolean(document.querySelector('#benchmark-series .benchmark-card'))""", timeout=8000)


def desktop_journey(page: Any, directory: Path, manifest: list[dict[str, Any]], viewport: tuple[int, int], *, verify_persistence: bool) -> None:
    prefix = "desktop-1280" if viewport[0] == 1280 else "desktop-1440"
    route(page, "today"); screenshot(page, directory, manifest, f"{prefix}-today", "#today", "default", viewport)
    route(page, "home"); screenshot(page, directory, manifest, f"{prefix}-memory", "#memory", "default", viewport)
    if verify_persistence:
        record_success(page)
    route(page, "chat"); screenshot(page, directory, manifest, f"{prefix}-chat-input", "#chat", "input", viewport)
    make_chat_result(page, loading=(directory, manifest, f"{prefix}-chat-loading", viewport)); screenshot(page, directory, manifest, f"{prefix}-chat-result", "#chat", "result", viewport)
    details = page.locator("#chat-result details summary").first
    if details.count() > 0:
        details.click(); page.wait_for_timeout(120)
    screenshot(page, directory, manifest, f"{prefix}-chat-evidence", "#chat", "evidence-open", viewport)
    save = page.locator("[data-save-consultation]")
    if save.count() > 0:
        save.click(); page.wait_for_timeout(160)
    route(page, "decisions"); wait_decisions(page); screenshot(page, directory, manifest, f"{prefix}-decisions", "#decisions", "default", viewport)
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
    route(page, "settings"); screenshot(page, directory, manifest, f"{prefix}-admin", "#settings", "default", viewport)
    route(page, "home")
    page.route("**/api/ingest", lambda request: request.fulfill(status=500, content_type="application/json", body='{"error":"Synthetic validation error"}'))
    page.locator("#record-text").fill("Synthetic failure state")
    page.locator("#record-form button:not(.voice)").last.click(); page.wait_for_timeout(160)
    screenshot(page, directory, manifest, f"{prefix}-error", "#memory", "synthetic-server-error", viewport)
    page.unroute("**/api/ingest")
    page.evaluate("document.querySelector('#record-text').value=''; document.querySelector('#record-notice').textContent='' ")
    screenshot(page, directory, manifest, f"{prefix}-empty", "#memory", "empty-capture", viewport)
    assert_layout(page)


def mobile_journey(page: Any, directory: Path, manifest: list[dict[str, Any]], viewport: tuple[int, int], *, verify_persistence: bool) -> None:
    prefix = "mobile-390" if viewport[0] == 390 else "mobile-375"
    route(page, "today"); screenshot(page, directory, manifest, f"{prefix}-today", "#today", "default", viewport)
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
        "desktop-1280-chat-result.png", "desktop-1280-decisions.png", "desktop-1280-decision-result-sheet.png",
        "desktop-1280-money.png", "desktop-1280-explore-space.png", "desktop-1280-benchmark.png",
        "mobile-390-today.png", "mobile-390-memory.png", "mobile-390-memory-image.png",
        "mobile-390-chat-result.png", "mobile-390-decisions.png", "mobile-390-decision-result-sheet.png",
        "mobile-390-more-sheet.png", "mobile-390-explore-space.png", "mobile-390-benchmark.png",
        "desktop-1440-today.png", "mobile-375-today.png",
    }
    public_manifest = [item for item in manifest if item["file"] in public_names]
    missing = public_names - {item["file"] for item in public_manifest}
    if missing:
        raise E2EFailure("Missing required public review screenshots: " + ", ".join(sorted(missing)))
    if PUBLIC_DIR.exists():
        shutil.rmtree(PUBLIC_DIR)
    PUBLIC_DIR.mkdir(parents=True)
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
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as error:
        raise E2EFailure("Install requirements-dev.txt before running UX E2E") from error
    assert_port_free()
    RESULTS.mkdir(parents=True, exist_ok=True)
    run_dir = RESULTS / "ux-phase5"
    work_manifest = run_dir / "manifest-work.json"
    if args.suite in {"all", "desktop"} and args.viewport_set != "secondary":
        if run_dir.exists(): shutil.rmtree(run_dir)
        run_dir.mkdir(parents=True)
    elif not work_manifest.is_file():
        raise E2EFailure("secondary/mobile suite needs a preceding suite so the review set remains complete")
    temp_root = Path(tempfile.mkdtemp(prefix="personal-os-ux-e2e-"))
    database = temp_root / "ux-synthetic.db"
    environment = os.environ.copy()
    environment.update({"PERSONAL_OS_ENV": "verification", "PERSONAL_OS_DB_PATH": str(database), "PERSONAL_OS_BACKUP_DIR": str(temp_root / "backups"), "PERSONAL_OS_ATTACHMENT_DIR": str(temp_root / "attachments"), "PERSONAL_OS_HOST": "127.0.0.1", "PERSONAL_OS_PORT": "8877", "PERSONAL_OS_E2E_CHAT_DELAY_MS": "700"})
    process: subprocess.Popen[str] | None = None
    manifest: list[dict[str, Any]] = json.loads(work_manifest.read_text(encoding="utf-8")) if work_manifest.is_file() else []
    console_errors: list[str] = []
    try:
        subprocess.run([str(PYTHON), str(ROOT / "tools" / "seed_ux_demo.py"), "--db", str(database)], cwd=ROOT, env=environment, check=True)
        process = subprocess.Popen([str(PYTHON), "app.py"], cwd=ROOT, env=environment, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
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
                page.on("pageerror", lambda error: console_errors.append(f"pageerror: {error}"))
                for viewport in viewports:
                    page.set_viewport_size({"width": viewport[0], "height": viewport[1]})
                    if mobile: mobile_journey(page, run_dir, manifest, viewport, verify_persistence=viewport == (390, 844))
                    else: desktop_journey(page, run_dir, manifest, viewport, verify_persistence=viewport == (1280, 720))
                context.close()
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
