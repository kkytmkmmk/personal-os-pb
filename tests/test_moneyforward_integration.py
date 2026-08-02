from __future__ import annotations

import sqlite3
import tempfile
import unittest
from contextlib import closing
from pathlib import Path

from personal_os.moneyforward import moneyforward_projection


SCHEMA = """
CREATE TABLE groups(id TEXT PRIMARY KEY,name TEXT,is_current INTEGER,last_scraped_at TEXT,created_at TEXT,updated_at TEXT);
CREATE TABLE group_accounts(id INTEGER PRIMARY KEY,group_id TEXT,account_id INTEGER,created_at TEXT,updated_at TEXT);
CREATE TABLE accounts(id INTEGER PRIMARY KEY,mf_id TEXT,name TEXT,type TEXT,institution TEXT,category_id INTEGER,created_at TEXT,updated_at TEXT,is_active INTEGER);
CREATE TABLE asset_categories(id INTEGER PRIMARY KEY,name TEXT,created_at TEXT,updated_at TEXT);
CREATE TABLE holdings(id INTEGER PRIMARY KEY,mf_id TEXT,account_id INTEGER,category_id INTEGER,name TEXT,code TEXT,type TEXT,liability_category TEXT,created_at TEXT,updated_at TEXT,is_active INTEGER);
CREATE TABLE daily_snapshots(id INTEGER PRIMARY KEY,group_id TEXT,date TEXT,refresh_completed INTEGER,created_at TEXT,updated_at TEXT);
CREATE TABLE holding_values(id INTEGER PRIMARY KEY,holding_id INTEGER,snapshot_id INTEGER,amount INTEGER,quantity REAL,unit_price REAL,avg_cost_price REAL,daily_change INTEGER,unrealized_gain INTEGER,unrealized_gain_pct REAL,created_at TEXT,updated_at TEXT);
CREATE TABLE transactions(id INTEGER PRIMARY KEY,mf_id TEXT,date TEXT,account_id INTEGER,category TEXT,sub_category TEXT,description TEXT,amount INTEGER,type TEXT,is_transfer INTEGER,is_excluded_from_calculation INTEGER,transfer_target TEXT,transfer_target_account_id INTEGER,created_at TEXT,updated_at TEXT);
CREATE TABLE asset_history(id INTEGER PRIMARY KEY,group_id TEXT,date TEXT,total_assets INTEGER,change INTEGER,created_at TEXT,updated_at TEXT);
CREATE TABLE asset_history_categories(id INTEGER PRIMARY KEY,asset_history_id INTEGER,category_name TEXT,amount INTEGER,created_at TEXT,updated_at TEXT);
"""


class MoneyForwardIntegrationTests(unittest.TestCase):
    def create_source(self, path: Path) -> None:
        with closing(sqlite3.connect(path)) as connection:
            connection.executescript(SCHEMA)
            connection.execute("INSERT INTO groups VALUES('old','旧',0,'2026-01-01','','2026-01-01')")
            connection.execute("INSERT INTO groups VALUES('current','現行',1,'2026-07-31','','2026-07-31')")
            connection.execute("INSERT INTO accounts VALUES(1,'a1','口座','bank','bank',NULL,'','',1)")
            connection.execute("INSERT INTO accounts VALUES(2,'a2','旧口座','bank','bank',NULL,'','',1)")
            connection.execute("INSERT INTO group_accounts VALUES(1,'current',1,'','')")
            connection.execute("INSERT INTO group_accounts VALUES(2,'old',2,'','')")
            connection.execute("INSERT INTO asset_categories VALUES(1,'預金','','')")
            connection.execute("INSERT INTO holdings VALUES(1,'h1',1,1,'普通預金',NULL,'asset',NULL,'','',1)")
            connection.execute("INSERT INTO holdings VALUES(2,'h2',2,1,'旧グループ預金',NULL,'asset',NULL,'','',1)")
            connection.execute("INSERT INTO daily_snapshots VALUES(1,'old','2026-07-31',1,'','2026-07-31')")
            connection.execute("INSERT INTO holding_values VALUES(1,2,1,999999,1,999999,999999,0,0,0,'','')")
            connection.execute("INSERT INTO daily_snapshots VALUES(2,'current','2026-07-30',1,'','2026-07-30')")
            connection.execute("INSERT INTO holding_values VALUES(2,1,2,130000,1,130000,130000,0,0,0,'','')")
            connection.execute("INSERT INTO asset_history VALUES(1,'current','2026-07-31',120000,20000,'','')")
            connection.execute("INSERT INTO asset_history_categories VALUES(1,1,'預金',120000,'','')")
            connection.execute("INSERT INTO transactions VALUES(1,'t1','2026-07-20',1,'給与','', '給与',200000,'income',0,0,NULL,NULL,'','')")
            connection.execute("INSERT INTO transactions VALUES(2,'t2','2026-07-21',1,'食費','', '食事',3000,'expense',0,0,NULL,NULL,'','')")
            connection.execute("INSERT INTO transactions VALUES(3,'t3','2026-07-22',1,'振替','', '振替',50000,'transfer',1,0,NULL,NULL,'','')")
            connection.commit()

    def test_unconfigured_source_is_safe(self) -> None:
        result = moneyforward_projection(None)
        self.assertFalse(result["connected"])
        self.assertEqual(result["status"], "not_configured")

    def test_projection_uses_current_group_and_excludes_transfers(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "moneyforward.db"
            self.create_source(path)
            result = moneyforward_projection(path)

        self.assertTrue(result["connected"])
        self.assertTrue(result["read_only"])
        self.assertNotIn("database_path", result)
        self.assertEqual(result["total_assets"], 120000)
        self.assertEqual(result["breakdown"], {"預金": 120000.0})
        self.assertEqual(result["holdings_count"], 1)
        self.assertEqual(result["holdings"][0]["amount"], 130000)
        self.assertNotIn("旧グループ預金", [item["name"] for item in result["holdings"]])
        self.assertEqual(result["snapshot_date"], "2026-07-30")
        self.assertEqual(result["transaction_count"], 2)
        self.assertEqual(result["monthly_cashflow"][0]["balance"], 197000)
        self.assertNotIn("database_path", result)
        self.assertNotIn("group_id", result)
        self.assertNotIn("account_id", result)

    def test_source_database_remains_writable_after_projection_closes(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "moneyforward.db"
            self.create_source(path)
            self.assertTrue(moneyforward_projection(path)["connected"])
            with closing(sqlite3.connect(path)) as connection:
                connection.execute("UPDATE groups SET updated_at='2026-08-01' WHERE id='current'")
                connection.commit()


if __name__ == "__main__":
    unittest.main()
