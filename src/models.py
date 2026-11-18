"""Прототип доменных операций. Суммы задаются целыми копейками."""
from datetime import date
from decimal import Decimal
import re
import sqlite3


def connect(path):
    connection = sqlite3.connect(path)
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def parse_amount(raw):
    if not re.fullmatch(r"[0-9]+(?:\.[0-9]{1,2})?", raw):
        raise ValueError("Сумма должна содержать не более двух десятичных знаков.")
    result = int(Decimal(raw) * 100)
    if not 1 <= result <= 1_000_000_000_000:
        raise ValueError("Сумма вне допустимого диапазона.")
    return result


def draft(connection, account, category, day, amount, note="", bank_ref=None):
    if date.fromisoformat(day).isoformat() != day:
        raise ValueError("Используйте дату ГГГГ-ММ-ДД.")
    cursor = connection.execute(
        """INSERT INTO entry(account_id,category_id,booked_on,amount_minor,note,bank_ref)
           VALUES(?,?,?,?,?,?)""",
        (account, category, day, amount, note, bank_ref),
    )
    return cursor.lastrowid


def change_status(connection, entry, revision, target):
    if target not in {"posted", "void"}:
        raise ValueError("Неизвестное целевое состояние.")
    cursor = connection.execute(
        """UPDATE entry SET status=?,revision=revision+1
           WHERE id=? AND revision=? AND status<>?""",
        (target, entry, revision, target),
    )
    if cursor.rowcount != 1:
        raise ValueError("Запись изменилась или уже находится в этом состоянии.")


def correct_amount(connection, entry, revision, amount):
    cursor = connection.execute(
        """UPDATE entry SET amount_minor=?,revision=revision+1
           WHERE id=? AND revision=? AND status IN ('draft','posted')""",
        (amount, entry, revision),
    )
    if cursor.rowcount != 1:
        raise ValueError("Откройте актуальную запись.")
