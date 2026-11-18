"""Расчёт в целых копейках по одному счёту и полуоткрытому периоду."""
from datetime import date


def monthly(connection, account_id, start, end):
    """Получить обороты за [start, end) и остаток на конец периода."""
    if date.fromisoformat(start) >= date.fromisoformat(end):
        raise ValueError("Конец периода должен быть позже начала.")
    account = connection.execute(
        "SELECT opened_on, opening_minor FROM account WHERE id=?", (account_id,)
    ).fetchone()
    if account is None or end <= account[0]:
        raise ValueError("Счёт не существовал в выбранном периоде.")
    rows = connection.execute(
        """SELECT e.booked_on, c.kind, c.name, e.amount_minor
           FROM entry AS e JOIN category AS c ON c.id=e.category_id
           WHERE e.account_id=? AND e.status='posted' AND e.booked_on<?""",
        (account_id, end),
    )
    income = expense = 0
    balance = account[1]
    expenses = {}
    for day, kind, category, amount in rows:
        balance += amount if kind == "income" else -amount
        if day >= start:
            if kind == "income":
                income += amount
            else:
                expense += amount
                expenses[category] = expenses.get(category, 0) + amount
    return income, expense, balance, expenses
