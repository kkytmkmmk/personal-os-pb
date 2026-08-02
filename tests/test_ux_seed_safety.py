import os
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from tools.seed_ux_demo import SeedSafetyError, validate_seed_target


class UxSeedSafetyTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name) / "repo"
        self.root.mkdir()
        self.temp_root = Path(self.temp.name) / "tmp"
        self.temp_root.mkdir()
        self.verification = self.root / "data" / "verification"
        self.verification.mkdir(parents=True)
        self.production = self.root / "data" / "personal_os.db"

    def tearDown(self):
        self.temp.cleanup()

    def target(self, path, environment="verification"):
        return validate_seed_target(path, environment=environment, root=self.root, temporary_directory=self.temp_root, protected_paths={self.production})

    def test_rejects_non_verification_and_production_path_without_mutation(self):
        self.production.parent.mkdir(exist_ok=True)
        self.production.write_bytes(b"production-like-bytes")
        before = self.production.read_bytes()
        for environment in (None, "production"):
            with self.assertRaises(SeedSafetyError):
                self.target(self.temp_root / "ux-synthetic.db", environment)
        with self.assertRaisesRegex(SeedSafetyError, "production database"):
            self.target(self.production)
        self.assertEqual(before, self.production.read_bytes())

    def test_allows_only_named_temp_or_verification_targets(self):
        self.assertEqual(self.target(self.temp_root / "ux-synthetic.db"), (self.temp_root / "ux-synthetic.db").resolve())
        self.assertEqual(self.target(self.verification / "demo.verification.db"), (self.verification / "demo.verification.db").resolve())
        for path in (self.temp_root / "personal_os.db", self.root / "data" / "ux-synthetic.db", self.temp_root / "anything.db"):
            with self.assertRaises(SeedSafetyError):
                self.target(path)

    def test_symlink_resolves_before_production_comparison(self):
        self.production.parent.mkdir(exist_ok=True)
        self.production.write_bytes(b"protected")
        link = self.temp_root / "ux-synthetic.db"
        try:
            os.symlink(self.production, link)
        except (OSError, NotImplementedError):
            self.skipTest("symlink creation is unavailable on this host")
        with self.assertRaisesRegex(SeedSafetyError, "production database"):
            self.target(link)
        self.assertEqual(self.production.read_bytes(), b"protected")

    def test_existing_target_requires_replace_and_production_is_never_replaced(self):
        """Exercise the CLI guard without ever handing it a real production DB."""
        target = self.temp_root / "ux-synthetic.db"
        target.write_bytes(b"existing-verification-data")
        environment = os.environ.copy()
        environment["PERSONAL_OS_ENV"] = "verification"
        command = [sys.executable, str(Path(__file__).parents[1] / "tools" / "seed_ux_demo.py"), "--db", str(target)]
        refused = subprocess.run(command, env=environment, capture_output=True, text=True, check=False)
        self.assertNotEqual(refused.returncode, 0)
        self.assertIn("without --replace", refused.stderr)
        self.assertEqual(target.read_bytes(), b"existing-verification-data")

        replaced = subprocess.run(command + ["--replace"], env=environment, capture_output=True, text=True, check=False)
        self.assertEqual(replaced.returncode, 0, replaced.stderr)
        self.assertNotEqual(target.read_bytes(), b"existing-verification-data")
        self.assertEqual(target.read_bytes()[:16], b"SQLite format 3\x00")

        protected_before = b"protected-production-like-data"
        self.production.parent.mkdir(exist_ok=True)
        self.production.write_bytes(protected_before)
        protected = subprocess.run(
            command[:-1] + [str(self.production), "--replace"], env=environment,
            capture_output=True, text=True, check=False,
        )
        self.assertNotEqual(protected.returncode, 0)
        self.assertEqual(self.production.read_bytes(), protected_before)

    def test_review_backlog_profile_is_large_and_bucketed(self):
        target = self.temp_root / "ux-synthetic.db"
        environment = os.environ.copy()
        environment["PERSONAL_OS_ENV"] = "verification"
        command = [sys.executable, str(Path(__file__).parents[1] / "tools" / "seed_ux_demo.py"),
                   "--db", str(target), "--profile", "review-backlog"]
        result = subprocess.run(command, env=environment, capture_output=True, text=True, check=False)
        self.assertEqual(result.returncode, 0, result.stderr)
        connection = sqlite3.connect(target)
        try:
            pending = connection.execute("SELECT COUNT(*) FROM fact_reviews WHERE state='pending'").fetchone()[0]
            deferred = connection.execute("SELECT COUNT(*) FROM fact_reviews WHERE state='deferred'").fetchone()[0]
            conflicts = connection.execute("SELECT COUNT(*) FROM facts WHERE validation_status='conflict'").fetchone()[0]
        finally:
            connection.close()
        self.assertGreaterEqual(pending + deferred, 50)
        self.assertGreaterEqual(deferred, 15)
        self.assertGreaterEqual(conflicts, 5)
