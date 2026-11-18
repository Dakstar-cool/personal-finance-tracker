"""Локальный замер модели. Запуск из корня: python -m tests.benchmark."""
from statistics import median
from time import perf_counter
from src.main import demo
from src.reports import monthly

if __name__ == "__main__":
    db = demo()
    with db:
        db.executemany(
            """INSERT INTO entry(account_id,category_id,booked_on,amount_minor,status)
               VALUES(1,2,'2026-11-20',?,'posted')""",
            ((i % 10000 + 1,) for i in range(9996)),
        )
    def report():
        return monthly(db,1,"2026-11-01","2026-12-01")
    report()
    samples = []
    for _ in range(30):
        start = perf_counter()
        report()
        samples.append(1000*(perf_counter()-start))
    print(f"SQLite in memory, 10000 entries, 30 runs. Median {median(samples):.2f} ms, P95 {sorted(samples)[28]:.2f} ms")
    db.close()
