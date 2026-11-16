"""Communication module: announcements + direct messages + inbox."""
from mvp import store


def send(conn, sender, sender_role, subject, body, audience="all"):
    if not sender or not sender.strip():
        raise ValueError("sender is required")
    if not subject or not subject.strip():
        raise ValueError("subject is required")
    if not body or not body.strip():
        raise ValueError("body is required")
    cur = conn.execute(
        "INSERT INTO messages(sender, sender_role, audience, subject, body)"
        " VALUES (?, ?, ?, ?, ?)",
        (sender.strip(), sender_role, (audience or "all").strip(),
         subject.strip(), body.strip()),
    )
    conn.commit()
    return dict(conn.execute("SELECT * FROM messages WHERE id = ?",
                             (cur.lastrowid,)).fetchone())


def inbox(conn, audience=None, limit=50):
    if audience:
        cur = conn.execute(
            "SELECT * FROM messages WHERE audience IN ('all', ?) "
            "ORDER BY id DESC LIMIT ?", (audience, limit))
    else:
        cur = conn.execute("SELECT * FROM messages ORDER BY id DESC LIMIT ?",
                           (limit,))
    return [dict(r) for r in cur.fetchall()]
