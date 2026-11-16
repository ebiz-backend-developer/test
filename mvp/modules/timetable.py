"""Timetable module: weekly slots with teacher/room/class clash detection."""
from mvp import store

WEEKDAYS = ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat")


class ClashError(ValueError):
    pass


def _overlaps(a_start, a_end, b_start, b_end):
    return a_start < b_end and b_start < a_end


def list_slots(conn, weekday=None, class_name=None):
    sql, params = "SELECT * FROM slots", []
    clauses = []
    if weekday:
        clauses.append("weekday = ?")
        params.append(weekday)
    if class_name:
        clauses.append("class_name = ?")
        params.append(class_name)
    if clauses:
        sql += " WHERE " + " AND ".join(clauses)
    sql += " ORDER BY weekday, starts_at"
    return [dict(r) for r in conn.execute(sql, params).fetchall()]


def find_clashes(conn, weekday, starts_at, ends_at, class_name, teacher, room,
                 exclude_id=None):
    """Return existing slots conflicting on class, teacher, or room overlap."""
    clashes = []
    for s in list_slots(conn, weekday=weekday):
        if exclude_id is not None and s["id"] == exclude_id:
            continue
        if not _overlaps(starts_at, ends_at, s["starts_at"], s["ends_at"]):
            continue
        reasons = []
        if s["class_name"] == class_name:
            reasons.append("class")
        if s["teacher"] == teacher:
            reasons.append("teacher")
        if s["room"] == room:
            reasons.append("room")
        if reasons:
            clash = dict(s)
            clash["conflicts_on"] = reasons
            clashes.append(clash)
    return clashes


def add_slot(conn, weekday, starts_at, ends_at, class_name, subject,
             teacher, room):
    for name, val in (("weekday", weekday), ("starts_at", starts_at),
                      ("ends_at", ends_at), ("class_name", class_name),
                      ("subject", subject), ("teacher", teacher), ("room", room)):
        if not val or not str(val).strip():
            raise ValueError(f"{name} is required")
    if weekday not in WEEKDAYS:
        raise ValueError(f"weekday must be one of {WEEKDAYS}")
    if not starts_at < ends_at:
        raise ValueError("starts_at must be before ends_at")
    clashes = find_clashes(conn, weekday, starts_at, ends_at, class_name,
                           teacher, room)
    if clashes:
        raise ClashError(f"slot clashes with {len(clashes)} existing slot(s): "
                         f"{[(c['id'], c['conflicts_on']) for c in clashes]}")
    cur = conn.execute(
        "INSERT INTO slots(weekday, starts_at, ends_at, class_name, subject,"
        " teacher, room) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (weekday, starts_at, ends_at, class_name, subject, teacher, room),
    )
    conn.commit()
    return dict(conn.execute("SELECT * FROM slots WHERE id = ?",
                             (cur.lastrowid,)).fetchone())


def delete_slot(conn, slot_id):
    cur = conn.execute("DELETE FROM slots WHERE id = ?", (slot_id,))
    conn.commit()
    if cur.rowcount == 0:
        raise KeyError(f"slot {slot_id} not found")
    return {"deleted": slot_id}
