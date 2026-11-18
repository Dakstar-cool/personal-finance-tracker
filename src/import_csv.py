"""Импорт нормализованной выписки одного счёта."""
import csv
from datetime import date
from .models import draft, parse_amount, change_status

HEADER = ["bank_ref", "booked_on", "kind", "category", "amount"]


def numbered_rows(stream):
    parser = csv.reader(stream, strict=True)
    try:
        for fields in parser:
            yield parser.line_num, fields
    except csv.Error as error:
        raise ValueError(f"Строка {parser.line_num}. Нарушен синтаксис CSV.") from error


def prepare(connection, account, stream):
    rows = numbered_rows(stream)
    _, header = next(rows, (0, []))
    if header != HEADER:
        raise ValueError("Заголовок CSV не соответствует профилю.")
    opening = connection.execute("SELECT opened_on FROM account WHERE id=?", (account,)).fetchone()
    if not opening:
        raise ValueError("Счёт не найден.")
    new = {}
    skipped = 0
    for line_number, fields in rows:
        if not fields:
            continue
        try:
            if len(fields) != len(HEADER):
                raise ValueError("Неверное количество полей.")
            row = dict(zip(HEADER, fields))
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
            raise ValueError(f"Строка {line_number}. {error}") from error
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
