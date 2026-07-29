import tempfile
import unittest
from pathlib import Path

from tools.build_public_snapshot import ROOT, build_snapshot, local_replacements, validate_public_pwa_assets
from tools.check_public_safety import find_public_safety_issues
from tools.check_public_screenshots import find_screenshot_issues
from tools.check_tracked_private_files import tracked_private_files


class PublicReleaseTests(unittest.TestCase):
    def test_worktree_public_scan_covers_requirements(self):
        self.assertEqual(find_public_safety_issues(ROOT), [])

    def test_no_runtime_or_private_file_is_tracked(self):
        self.assertEqual(tracked_private_files(ROOT), [])

    def test_snapshot_is_source_only_and_sanitized(self):
        with tempfile.TemporaryDirectory() as directory:
            snapshot = Path(directory) / "public"
            self.assertGreater(build_snapshot(snapshot), 0)
            self.assertTrue((snapshot / "app.py").is_file())
            self.assertTrue((snapshot / "requirements" / "00_vision.md").is_file())
            self.assertTrue((snapshot / "PUBLIC_SNAPSHOT_INFO.md").is_file())
            self.assertTrue((snapshot / "static" / "manifest.webmanifest").is_file())
            self.assertTrue((snapshot / "static" / "icon.svg").is_file())
            self.assertIn("generated, sanitized public mirror", (snapshot / "README.md").read_text(encoding="utf-8"))
            self.assertFalse((snapshot / "data").exists())
            self.assertEqual(find_public_safety_issues(snapshot), [])
            self.assertEqual(validate_public_pwa_assets(snapshot), [])
            snapshot_text = "\n".join(
                path.read_text(encoding="utf-8")
                for path in snapshot.rglob("*")
                if path.is_file() and path.suffix.lower() in {".md", ".py", ".json", ".html", ".js", ".ps1"}
            )
            for private_term in local_replacements(ROOT):
                self.assertNotIn(private_term, snapshot_text)

    def test_start_scripts_do_not_depend_on_callers_directory(self):
        for name in ("start_production.ps1", "start_verification.ps1"):
            script = (ROOT / "tools" / name).read_text(encoding="utf-8")
            self.assertIn("$PSScriptRoot", script)
            self.assertIn("Push-Location $projectRoot", script)
            self.assertNotIn("C:\\Users\\", script)

    def test_reviewed_synthetic_screenshots_are_safe_and_public(self):
        self.assertEqual(find_screenshot_issues(ROOT), [])
        with tempfile.TemporaryDirectory() as directory:
            snapshot = Path(directory) / "public"
            build_snapshot(snapshot)
            self.assertTrue((snapshot / "docs" / "screenshots" / "ux-phase5" / "manifest.json").is_file())
            self.assertTrue((snapshot / "docs" / "screenshots" / "ux-phase5" / "desktop-1280-today.png").is_file())
            self.assertTrue((snapshot / "docs" / "ux_phase5_visual_review.md").is_file())


if __name__ == "__main__":
    unittest.main()
