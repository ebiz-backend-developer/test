"""Fees module: invoices, payments, outstanding balances."""
from mvp import store


def issue_invoice(conn, student_name, term, amount):
    if not student_name or not student_name.strip():
        raise ValueError("student_name is required")
    if not term or not term.strip():
        raise ValueError("term is required")
    amount = float(amount)
    if amount <= 0:
        raise ValueError("amount must be > 0")
    cur = conn.execute(
        "INSERT INTO invoices(student_name, term, amount) VALUES (?, ?, ?)",
        (student_name.strip(), term.strip(), amount),
    )
    conn.commit()
    return get_invoice(conn, cur.lastrowid)


def get_invoice(conn, invoice_id):
    row = conn.execute("SELECT * FROM invoices WHERE id = ?", (invoice_id,)).fetchone()
    if row is None:
        raise KeyError(f"invoice {invoice_id} not found")
    inv = dict(row)
    paid = conn.execute("SELECT COALESCE(SUM(amount), 0) t FROM payments"
                        " WHERE invoice_id = ?", (invoice_id,)).fetchone()["t"]
    inv["paid"] = paid
    inv["balance"] = round(inv["amount"] - paid, 2)
    inv["status"] = "paid" if inv["balance"] <= 0 else (
        "partial" if paid > 0 else "unpaid")
    return inv


def list_invoices(conn, student_name=None):
    if student_name:
        ids = [r["id"] for r in conn.execute(
            "SELECT id FROM invoices WHERE student_name = ? ORDER BY id",
            (student_name,)).fetchall()]
    else:
        ids = [r["id"] for r in conn.execute(
            "SELECT id FROM invoices ORDER BY id").fetchall()]
    return [get_invoice(conn, i) for i in ids]


def record_payment(conn, invoice_id, amount, method="cash"):
    inv = get_invoice(conn, invoice_id)
    amount = float(amount)
    if amount <= 0:
        raise ValueError("amount must be > 0")
    if amount - inv["balance"] > 1e-9:
        raise ValueError(f"payment {amount} exceeds balance {inv['balance']}")
    cur = conn.execute(
        "INSERT INTO payments(invoice_id, amount, method) VALUES (?, ?, ?)",
        (invoice_id, amount, method or "cash"),
    )
    conn.commit()
    pay = dict(conn.execute("SELECT * FROM payments WHERE id = ?",
                            (cur.lastrowid,)).fetchone())
    pay["invoice"] = get_invoice(conn, invoice_id)
    return pay


def list_payments(conn, invoice_id=None):
    if invoice_id:
        cur = conn.execute("SELECT * FROM payments WHERE invoice_id = ? ORDER BY id",
                           (invoice_id,))
    else:
        cur = conn.execute("SELECT * FROM payments ORDER BY id")
    return [dict(r) for r in cur.fetchall()]


def student_balance(conn, student_name):
    invoices = list_invoices(conn, student_name)
    return {"student_name": student_name,
            "invoices": len(invoices),
            "billed": round(sum(i["amount"] for i in invoices), 2),
            "paid": round(sum(i["paid"] for i in invoices), 2),
            "balance": round(sum(i["balance"] for i in invoices), 2)}
