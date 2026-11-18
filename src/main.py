"""Воспроизведение ноябрьского примера без обращения к личным данным."""
from pathlib import Path
from .models import connect, draft, change_status
from .reports import monthly


def demo():
    db = connect(":memory:")
    db.executescript((Path(__file__).resolve().parents[1] / "docs/schema.sql").read_text(encoding="utf-8-sig"))
    with db:
        db.execute("INSERT INTO account VALUES(1,'Основной','2026-11-01',1000000)")
        db.executemany("INSERT INTO category VALUES(?,?,?)", [
            (1,'Зарплата','income'), (2,'Продукты','expense'),
            (3,'Транспорт','expense'), (4,'Досуг','expense')
        ])
        for day, cat, amount, posted in [
            ('2026-11-05',1,3000000,True), ('2026-11-07',2,125040,True),
            ('2026-11-08',3,14960,True), ('2026-11-12',4,60000,False)
        ]:
            key = draft(db, 1, cat, day, amount)
            if posted:
                change_status(db, key, 1, "posted")
    return db


if __name__ == "__main__":
    with demo() as db:
        print("Доход, расход, остаток и расходы по категориям (копейки)")
        print(monthly(db, 1, "2026-11-01", "2026-12-01"))
