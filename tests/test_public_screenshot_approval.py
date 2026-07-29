import json
import shutil
import tempfile
import unittest
from pathlib import Path

from tools.approve_public_screenshots import CONFIRMATION, approve
from tools.check_public_screenshots import SCREENSHOT_DIR, find_screenshot_issues


class PublicScreenshotApprovalTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.directory = self.root / SCREENSHOT_DIR
        self.directory.mkdir(parents=True)
        source_root = Path(__file__).parents[1] / SCREENSHOT_DIR
        self.image_name = "desktop-1280-today.png"
        shutil.copy2(source_root / self.image_name, self.directory / self.image_name)
        self.manifest = {
            "version": "1",
            "environment": "verification",
            "data_type": "synthetic",
            "screenshots": [{
                "file": self.image_name,
                "viewport": {"width": 1280, "height": 720},
                "route": "#today",
                "state": "default",
                "data_type": "synthetic",
                "contains_sensitive_data": False,
                "reviewed": False,
                "reviewed_at": None,
                "reviewed_by": None,
                "sha256": None,
            }],
        }
        (self.directory / "manifest.json").write_text(json.dumps(self.manifest), encoding="utf-8")

    def tearDown(self):
        self.temp.cleanup()

    def test_unapproved_images_are_rejected_then_approval_records_hash(self):
        self.assertTrue(find_screenshot_issues(self.root))
        self.assertEqual(approve(self.root, "test-reviewer", CONFIRMATION, True), 1)
        self.assertEqual(find_screenshot_issues(self.root), [])
        item = json.loads((self.directory / "manifest.json").read_text(encoding="utf-8"))["screenshots"][0]
        self.assertTrue(item["reviewed"])
        self.assertEqual(item["reviewed_by"], "test-reviewer")
        self.assertRegex(item["sha256"], r"^[0-9a-f]{64}$")

    def test_changed_png_and_invalid_approval_inputs_are_rejected(self):
        with self.assertRaisesRegex(ValueError, "confirmation"):
            approve(self.root, "test-reviewer", "not reviewed", True)
        with self.assertRaisesRegex(ValueError, "reviewer"):
            approve(self.root, "", CONFIRMATION, True)
        approve(self.root, "test-reviewer", CONFIRMATION, True)
        image = self.directory / self.image_name
        image.write_bytes(image.read_bytes() + b"changed")
        self.assertTrue(any("sha256 does not match" in issue for issue in find_screenshot_issues(self.root)))
