"""SQLite storage with migration runner for the Design Hub."""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from .models import (
    ConflictError,
    NewFlow,
    NewMilestone,
    NewModule,
    NewScopeItem,
    NewTechOption,
    NewWireframe,
    NotFoundError,
)

APP_ROOT = Path(__file__).resolve().parent.parent
MIGRATIONS_DIR = APP_ROOT / "migrations"


def _utcnow() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def connect(path: str | Path) -> sqlite3.Connection:
    # check_same_thread=False: the HTTP server serializes requests with a
    # lock (see app/server.py), so one connection is safe to share.
    conn = sqlite3.connect(str(path), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def migrate(conn: sqlite3.Connection) -> list[str]:
    """Apply pending migrations in filename order; return applied names."""
    conn.execute(
        "CREATE TABLE IF NOT EXISTS schema_migrations (name TEXT PRIMARY KEY)"
    )
    applied = {r[0] for r in conn.execute("SELECT name FROM schema_migrations")}
    done: list[str] = []
    for sql_file in sorted(MIGRATIONS_DIR.glob("*.sql")):
        if sql_file.name in applied:
            continue
        with conn:
            conn.executescript(sql_file.read_text())
            conn.execute(
                "INSERT INTO schema_migrations (name) VALUES (?)", (sql_file.name,)
            )
        done.append(sql_file.name)
    return done


class Store:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    # -- generic helpers -------------------------------------------------
    def _rows(self, sql: str, params: tuple = ()) -> list[dict]:
        return [dict(r) for r in self.conn.execute(sql, params)]

    def _one(self, sql: str, params: tuple = ()) -> dict:
        row = self.conn.execute(sql, params).fetchone()
        if row is None:
            raise NotFoundError("record not found")
        return dict(row)

    # -- roles & users (c1) ----------------------------------------------
    def list_roles(self) -> list[dict]:
        from .rbac import ROLE_DESCRIPTIONS, role_permissions

        roles = self._rows("SELECT id, name, description FROM roles ORDER BY id")
        for role in roles:
            role["permissions"] = role_permissions(role["name"])
            role.setdefault("description", ROLE_DESCRIPTIONS.get(role["name"], ""))
        return roles

    def list_users(self) -> list[dict]:
        return self._rows(
            "SELECT u.id, u.username, u.display_name, r.name AS role"
            " FROM users u JOIN roles r ON r.id = u.role_id"
            " ORDER BY u.id"
        )

    def get_user(self, username: str) -> dict | None:
        row = self.conn.execute(
            "SELECT u.id, u.username, u.display_name, r.name AS role"
            " FROM users u JOIN roles r ON r.id = u.role_id"
            " WHERE u.username = ?",
            (username,),
        ).fetchone()
        return dict(row) if row else None

    # -- scope (c1) -------------------------------------------------------
    def list_scope(self) -> list[dict]:
        return self._rows("SELECT * FROM scope_items ORDER BY id")

    def add_scope(self, item: NewScopeItem) -> dict:
        item.validate()
        with self.conn:
            cur = self.conn.execute(
                "INSERT INTO scope_items (title, kind, detail) VALUES (?, ?, ?)",
                (item.title, item.kind, item.detail),
            )
        return self._one("SELECT * FROM scope_items WHERE id = ?", (cur.lastrowid,))

    # -- modules (c2) -----------------------------------------------------
    def list_modules(self, mvp_only: bool = False) -> list[dict]:
        sql = "SELECT * FROM modules"
        if mvp_only:
            sql += " WHERE mvp = 1"
        sql += " ORDER BY sort_order, id"
        return self._rows(sql)

    def get_module(self, module_id: int) -> dict:
        return self._one("SELECT * FROM modules WHERE id = ?", (module_id,))

    def add_module(self, mod: NewModule) -> dict:
        mod.validate()
        try:
            with self.conn:
                cur = self.conn.execute(
                    "INSERT INTO modules (name, description, priority, moscow, mvp,"
                    " status, owner_role, sort_order)"
                    " VALUES (?, ?, ?, ?, ?, ?, ?,"
                    " (SELECT COALESCE(MAX(sort_order), -1) + 1 FROM modules))",
                    (mod.name, mod.description, mod.priority, mod.moscow,
                     int(mod.mvp), mod.status, mod.owner_role),
                )
        except sqlite3.IntegrityError:
            raise ConflictError(f"module '{mod.name}' already exists")
        return self.get_module(cur.lastrowid)

    def update_module_status(self, module_id: int, status: str) -> dict:
        from .models import MODULE_STATUSES, _one_of

        _one_of(status, "status", MODULE_STATUSES)
        self.get_module(module_id)
        with self.conn:
            self.conn.execute(
                "UPDATE modules SET status = ? WHERE id = ?", (status, module_id)
            )
        return self.get_module(module_id)

    def prioritize_module(
        self, module_id: int, priority: str, mvp: bool, sort_order: int | None = None
    ) -> dict:
        from .models import PRIORITIES, _one_of

        _one_of(priority, "priority", PRIORITIES)
        self.get_module(module_id)
        if sort_order is None:
            sort_order = {"P0": 0, "P1": 1, "P2": 2, "P3": 3}[priority]
        with self.conn:
            self.conn.execute(
                "UPDATE modules SET priority = ?, mvp = ?, sort_order = ?"
                " WHERE id = ?",
                (priority, int(bool(mvp)), int(sort_order), module_id),
            )
        return self.get_module(module_id)

    # -- tech stack (c3) --------------------------------------------------
    def list_tech(self, layer: str | None = None) -> list[dict]:
        if layer:
            return self._rows(
                "SELECT * FROM tech_options WHERE layer = ? ORDER BY id", (layer,)
            )
        return self._rows("SELECT * FROM tech_options ORDER BY id")

    def get_tech(self, tech_id: int) -> dict:
        return self._one("SELECT * FROM tech_options WHERE id = ?", (tech_id,))

    def add_tech(self, opt: NewTechOption) -> dict:
        opt.validate()
        with self.conn:
            cur = self.conn.execute(
                "INSERT INTO tech_options (layer, name, description, status, rationale)"
                " VALUES (?, ?, ?, 'proposed', ?)",
                (opt.layer, opt.name, opt.description, opt.rationale),
            )
        return self.get_tech(cur.lastrowid)

    def decide_tech(self, tech_id: int, decision: str, rationale: str = "") -> dict:
        if decision not in ("selected", "rejected"):
            raise ConflictError("decision must be 'selected' or 'rejected'")
        option = self.get_tech(tech_id)
        if option["status"] == decision:
            raise ConflictError(f"option is already {decision}")
        with self.conn:
            if decision == "selected":
                # One selected option per layer: selecting supersedes the old one.
                self.conn.execute(
                    "UPDATE tech_options SET status = 'rejected',"
                    " rationale = 'Superseded by option ' || ?"
                    " WHERE layer = ? AND status = 'selected'",
                    (tech_id, option["layer"]),
                )
            self.conn.execute(
                "UPDATE tech_options SET status = ?, rationale = ? WHERE id = ?",
                (decision, str(rationale or "")[:2000], tech_id),
            )
        return self.get_tech(tech_id)

    # -- milestones (c4) --------------------------------------------------
    def list_milestones(self) -> list[dict]:
        return self._rows("SELECT * FROM milestones ORDER BY id")

    def get_milestone(self, milestone_id: int) -> dict:
        return self._one("SELECT * FROM milestones WHERE id = ?", (milestone_id,))

    def add_milestone(self, ms: NewMilestone) -> dict:
        ms.validate()
        with self.conn:
            cur = self.conn.execute(
                "INSERT INTO milestones (title, description, due_date, status)"
                " VALUES (?, ?, ?, 'draft')",
                (ms.title, ms.description, ms.due_date),
            )
        return self.get_milestone(cur.lastrowid)

    def submit_milestone(self, milestone_id: int) -> dict:
        ms = self.get_milestone(milestone_id)
        if ms["status"] != "draft":
            raise ConflictError(
                f"only draft milestones can be submitted (is {ms['status']})"
            )
        with self.conn:
            self.conn.execute(
                "UPDATE milestones SET status = 'proposed' WHERE id = ?",
                (milestone_id,),
            )
        return self.get_milestone(milestone_id)

    def decide_milestone(
        self, milestone_id: int, decision: str, decided_by: str
    ) -> dict:
        if decision not in ("approved", "rejected"):
            raise ConflictError("decision must be 'approved' or 'rejected'")
        ms = self.get_milestone(milestone_id)
        if ms["status"] != "proposed":
            raise ConflictError(
                f"only proposed milestones can be decided (is {ms['status']})"
            )
        now = _utcnow()
        with self.conn:
            if decision == "approved":
                self.conn.execute(
                    "UPDATE milestones SET status = 'approved', approved_by = ?,"
                    " approved_at = ?, decided_by = ? WHERE id = ?",
                    (decided_by, now, decided_by, milestone_id),
                )
            else:
                self.conn.execute(
                    "UPDATE milestones SET status = 'rejected', decided_by = ?"
                    " WHERE id = ?",
                    (decided_by, milestone_id),
                )
        return self.get_milestone(milestone_id)

    # -- flows ------------------------------------------------------------
    def list_flows(self) -> list[dict]:
        rows = self._rows(
            "SELECT id, name, persona, device, status FROM flows ORDER BY id"
        )
        return rows

    def get_flow(self, flow_id: int) -> dict:
        flow = self._one("SELECT * FROM flows WHERE id = ?", (flow_id,))
        flow["steps"] = json.loads(flow.pop("steps_json") or "[]")
        return flow

    def add_flow(self, flow: NewFlow) -> dict:
        flow.validate()
        with self.conn:
            cur = self.conn.execute(
                "INSERT INTO flows (name, persona, device, status, steps_json)"
                " VALUES (?, ?, ?, 'draft', ?)",
                (flow.name, flow.persona, flow.device, json.dumps(flow.steps)),
            )
        return self.get_flow(cur.lastrowid)

    # -- wireframes -------------------------------------------------------
    def list_wireframes(self) -> list[dict]:
        return self._rows(
            "SELECT w.id, w.title, w.screen, w.device, w.module_id, w.status,"
            " m.name AS module_name FROM wireframes w"
            " LEFT JOIN modules m ON m.id = w.module_id ORDER BY w.id"
        )

    def get_wireframe(self, wireframe_id: int) -> dict:
        wf = self._one("SELECT * FROM wireframes WHERE id = ?", (wireframe_id,))
        wf["blocks"] = json.loads(wf.pop("blocks_json") or "[]")
        return wf

    def add_wireframe(self, wf: NewWireframe) -> dict:
        wf.validate()
        if wf.module_id is not None:
            self.get_module(wf.module_id)
        with self.conn:
            cur = self.conn.execute(
                "INSERT INTO wireframes (title, screen, device, module_id, status,"
                " blocks_json) VALUES (?, ?, ?, ?, 'draft', ?)",
                (wf.title, wf.screen, wf.device, wf.module_id, json.dumps(wf.blocks)),
            )
        return self.get_wireframe(cur.lastrowid)

    # -- dashboard --------------------------------------------------------
    def dashboard(self, role: str) -> dict:
        modules = self.list_modules()
        milestones = self.list_milestones()
        tech = self.list_tech()
        mvp = [m for m in modules if m["mvp"]]
        return {
            "role": role,
            "counts": {
                "modules": len(modules),
                "mvp_modules": len(mvp),
                "milestones": len(milestones),
                "flows": len(self.list_flows()),
                "wireframes": len(self.list_wireframes()),
                "tech_options": len(tech),
                "tech_selected": sum(1 for t in tech if t["status"] == "selected"),
            },
            "mvp_modules": mvp,
            "milestones_by_status": {
                s: [m for m in milestones if m["status"] == s]
                for s in ("draft", "proposed", "approved", "rejected")
            },
            "pending_approvals": [
                m for m in milestones if m["status"] == "proposed"
            ],
            "selected_tech": [t for t in tech if t["status"] == "selected"],
        }
