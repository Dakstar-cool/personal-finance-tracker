"""Импорт нормализованной выписки одного счёта."""
import csv
from datetime import date
from .models import draft, parse_amount, change_status

HEADER = ["bank_ref", "booked_on", "kind", "category", "amount"]


def prepare(connection, account, stream):
    reader = csv.DictReader(stream, strict=True)
    if reader.fieldnames != HEADER:
        raise ValueError("Заголовок CSV не соответствует профилю.")
    opening = connection.execute("SELECT opened_on FROM account WHERE id=?", (account,)).fetchone()
    if not opening:
        raise ValueError("Счёт не найден.")
    new = {}
    skipped = 0
    for row in reader:
        try:
            if None in row or any(v is None for v in row.values()):
                raise ValueError("Неверное количество полей.")
            ref = row["bank_ref"].strip()
            day = date.fromisoformat(row["booked_on"]).isoformat()
            if day != row["booked_on"] or day < opening[0] or not ref:
                raise ValueError("Проверьте дату и банковский идентификатор.")
            category = connection.execute(
                "SELECT id FROM category WHERE kind=? AND name=?", (row["kind"], row["category"])
            ).fetchone()
            if not category:
                raise ValueError("Категория и вид операции не согласованы.")
            item = (day, category[0], parse_amount(row["amount"]))
            saved = new.get(ref) or connection.execute(
                "SELECT booked_on,category_id,amount_minor FROM entry WHERE account_id=? AND bank_ref=?",
                (account, ref),
            ).fetchone()
            if saved and tuple(saved) != item:
                raise ValueError("Идентификатор совпал, реквизиты различаются.")
            if saved:
                skipped += 1
            else:
                new[ref] = item
        except (ValueError, TypeError) as error:
            raise ValueError(f"Строка {reader.line_num}. {error}") from error
    return new, skipped


def apply(connection, account, stream):
    # Повторный разбор под блокировкой защищает промежуток между просмотром и записью.
    with connection:
        connection.execute("BEGIN IMMEDIATE")
        rows, skipped = prepare(connection, account, stream)
        for ref, (day, category, amount) in rows.items():
            key = draft(connection, account, category, day, amount, bank_ref=ref)
            change_status(connection, key, 1, "posted")
    return len(rows), skipped
