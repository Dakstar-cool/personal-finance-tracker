from io import StringIO
import sqlite3
import tempfile
from pathlib import Path
import unittest
from src.main import demo
from src.models import change_status, connect, correct_amount, draft, parse_amount
from src.reports import monthly
from src.import_csv import apply, prepare

header = "bank_ref,booked_on,kind,category,amount\r\n"
row = "B-008,2026-11-18,expense,Продукты,230.10\r\n"


class FinanceTests(unittest.TestCase):
    def setUp(self):
        self.db = demo()
        self.addCleanup(self.db.close)

    def totals(self):
        return monthly(self.db, 1, "2026-11-01", "2026-12-01")

    def test_month(self):
        self.assertEqual(self.totals(), (3000000, 140000, 3860000, {"Продукты":125040,"Транспорт":14960}))

    def test_period_boundary(self):
        key = draft(self.db,1,2,"2026-12-01",100)
        change_status(self.db,key,1,"posted")
        self.assertEqual(self.totals()[2],3860000)
        self.assertEqual(monthly(self.db,1,"2026-12-01","2027-01-01")[1:3],(100,3859900))

    def test_draft_void_and_restore_prevention(self):
        change_status(self.db,4,1,"void")
        self.assertEqual(self.totals()[2],3860000)
        with self.assertRaises(sqlite3.IntegrityError):
            change_status(self.db,4,2,"posted")

    def test_void_posted(self):
        change_status(self.db,3,2,"void")
        self.assertEqual(self.totals()[1:3],(125040,3874960))

    def test_edit_and_stale_revision(self):
        correct_amount(self.db,2,2,120040)
        with self.assertRaises(ValueError):
            correct_amount(self.db,2,2,100)
        self.assertEqual(self.totals()[2],3865000)

    def test_money(self):
        self.assertEqual(parse_amount("0.01"),1)
        for value in ["0","-1","1.001","1e2","10000000000.01"]:
            with self.subTest(value=value), self.assertRaises(ValueError):
                parse_amount(value)

    def test_foreign_key(self):
        with self.assertRaises(sqlite3.IntegrityError):
            draft(self.db,999,2,"2026-11-13",19)

    def test_preview_and_reimport(self):
        data = header+row+row
        rows,repeats=prepare(self.db,1,StringIO(data))
        self.assertEqual((len(rows),repeats),(1,1))
        self.assertEqual(self.totals()[1],140000)
        self.assertEqual(apply(self.db,1,StringIO(data)),(1,1))
        self.assertEqual(apply(self.db,1,StringIO(data)),(0,2))
        self.assertEqual(self.totals()[1],163010)

    def test_conflict_aborts_batch(self):
        with self.assertRaisesRegex(ValueError,"Строка 3"):
            apply(self.db,1,StringIO(header+row+row.replace("230.10","231.10")))
        self.assertEqual(self.totals()[1],140000)

    def test_invalid_date(self):
        with self.assertRaises(ValueError):
            apply(self.db,1,StringIO(header+row.replace("11-18","11-31")))

    def test_backup(self):
        with tempfile.TemporaryDirectory() as tmp:
            copy = connect(Path(tmp)/"copy.db")
            try:
                self.db.backup(copy)
                self.assertEqual(copy.execute("PRAGMA integrity_check").fetchone()[0],"ok")
                self.assertEqual(monthly(copy,1,"2026-11-01","2026-12-01"),self.totals())
            finally:
                copy.close()


if __name__=="__main__":
    unittest.main()
