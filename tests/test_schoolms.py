"""Real-behavior API tests for the SchoolMS MVP (M1–M3)."""

from __future__ import annotations

import datetime as dt

from tests.conftest import auth_headers


def test_health_and_ui(client):
    assert client.get("/health").json()["status"] == "ok"
    res = client.get("/")
    assert res.status_code == 200 and "SchoolMS" in res.text


def test_plan_endpoints_cover_c1_to_c4(client):
    scope = client.get("/api/v1/plan/scope").json()
    assert scope["in_scope"] and scope["out_of_scope_mvp"]  # c1 scope
    roles = client.get("/api/v1/plan/roles").json()
    assert set(roles) == {"admin", "staff", "teacher", "student", "parent"}  # c1 roles
    modules = client.get("/api/v1/plan/modules").json()
    assert modules["mvp"] == ["users", "students", "teachers", "classes",
                              "enrollments", "attendance", "grades"]  # c2
    arch = client.get("/api/v1/plan/architecture").json()
    assert arch["stack"]["api"] == "FastAPI + Starlette"  # c3
    milestones = client.get("/api/v1/plan/milestones").json()["milestones"]
    assert [m["id"] for m in milestones] == ["M1", "M2", "M3", "M4", "M5"]  # c4
    full = client.get("/api/v1/plan").json()
    assert {"scope", "roles", "modules", "architecture", "milestones"} <= set(full)


def test_auth_flow_and_guards(client):
    res = client.post("/api/v1/auth/register", json={
        "username": "alice", "full_name": "Alice", "email": "a@t.local",
        "password": "Password123", "role": "teacher"})
    assert res.status_code == 201
    dup = client.post("/api/v1/auth/register", json={
        "username": "alice", "full_name": "A", "email": "other@t.local",
        "password": "Password123", "role": "teacher"})
    assert dup.status_code == 409
    bad_role = client.post("/api/v1/auth/register", json={
        "username": "x", "full_name": "X", "email": "x@t.local",
        "password": "Password123", "role": "nope"})
    assert bad_role.status_code in (400, 422)
    priv = client.post("/api/v1/auth/register", json={
        "username": "root", "full_name": "R", "email": "r@t.local",
        "password": "Password123", "role": "admin"})
    assert priv.status_code == 403
    login = client.post("/api/v1/auth/login", json={"username": "alice", "password": "Password123"})
    assert login.status_code == 200
    assert client.post("/api/v1/auth/login",
                        json={"username": "alice", "password": "wrong"}).status_code == 401
    me = client.get("/api/v1/auth/me", headers=auth_headers(login.json()["access_token"]))
    assert me.json()["username"] == "alice"
    assert client.get("/api/v1/auth/me").status_code == 401


def test_rbac_admin_users_and_denials(admin_client, client, student_token):
    created = admin_client.post("/api/v1/users", json={
        "username": "boss2", "full_name": "B", "email": "b2@t.local",
        "password": "Password123", "role": "staff"})
    assert created.status_code == 201
    assert admin_client.get("/api/v1/users").status_code == 200
    denied = client.get("/api/v1/users", headers=auth_headers(student_token))
    assert denied.status_code == 403
    assert client.get("/api/v1/users").status_code == 401


def _student(admin_client, adm="S-100"):
    res = admin_client.post("/api/v1/students", json={
        "admission_no": adm, "first_name": "Ann", "last_name": "Lee"})
    assert res.status_code == 201, res.text
    return res.json()


def _teacher(admin_client, staff_no="T-100"):
    res = admin_client.post("/api/v1/teachers", json={
        "staff_no": staff_no, "first_name": "Tom", "last_name": "Kay", "subject": "Math"})
    assert res.status_code == 201, res.text
    return res.json()


def _class(admin_client, code="C-100", capacity=30, teacher_id=None):
    res = admin_client.post("/api/v1/classes", json={
        "code": code, "name": f"Class {code}", "capacity": capacity, "teacher_id": teacher_id})
    assert res.status_code == 201, res.text
    return res.json()


def test_student_teacher_crud(admin_client, client, teacher_token, student_token):
    s = _student(admin_client)
    assert admin_client.get(f"/api/v1/students/{s['id']}").json()["admission_no"] == "S-100"
    upd = admin_client.patch(f"/api/v1/students/{s['id']}", json={"status": "inactive"})
    assert upd.json()["status"] == "inactive"
    assert admin_client.get("/api/v1/students?status_filter=inactive").json()
    # duplicate admission number rejected
    dup = admin_client.post("/api/v1/students", json={
        "admission_no": "S-100", "first_name": "B", "last_name": "C"})
    assert dup.status_code == 409
    # teacher can read students but student role cannot
    assert client.get("/api/v1/students", headers=auth_headers(teacher_token)).status_code == 200
    assert client.get("/api/v1/students", headers=auth_headers(student_token)).status_code == 403
    t = _teacher(admin_client)
    assert admin_client.get(f"/api/v1/teachers/{t['id']}").json()["staff_no"] == "T-100"
    assert admin_client.delete(f"/api/v1/students/{s['id']}").status_code == 204
    assert admin_client.get(f"/api/v1/students/{s['id']}").status_code == 404


def test_classes_enrollments_roster_capacity(admin_client):
    t = _teacher(admin_client)
    cls = _class(admin_client, code="C-CAP", capacity=1, teacher_id=t["id"])
    s1, s2 = _student(admin_client, "S-1"), _student(admin_client, "S-2")
    e1 = admin_client.post("/api/v1/enrollments",
                           json={"student_id": s1["id"], "class_id": cls["id"]})
    assert e1.status_code == 201
    dup = admin_client.post("/api/v1/enrollments",
                            json={"student_id": s1["id"], "class_id": cls["id"]})
    assert dup.status_code == 409
    full = admin_client.post("/api/v1/enrollments",
                             json={"student_id": s2["id"], "class_id": cls["id"]})
    assert full.status_code == 409  # capacity enforced
    roster = admin_client.get(f"/api/v1/classes/{cls['id']}/roster").json()
    assert [r["id"] for r in roster] == [s1["id"]]
    assert admin_client.get(f"/api/v1/classes/{cls['id']}").json()["enrolled"] == 1
    assert admin_client.delete(f"/api/v1/enrollments/{e1.json()['id']}").status_code == 204
    e2 = admin_client.post("/api/v1/enrollments",
                           json={"student_id": s2["id"], "class_id": cls["id"]})
    assert e2.status_code == 201  # seat freed after unenroll


def test_attendance_upsert_and_summary(admin_client, client, teacher_token):
    cls = _class(admin_client)
    s = _student(admin_client)
    day = dt.date.today().isoformat()
    mark = client.post("/api/v1/attendance", headers=auth_headers(teacher_token), json=[
        {"student_id": s["id"], "class_id": cls["id"], "day": day, "status": "absent"}])
    assert mark.status_code == 200
    fix = client.post("/api/v1/attendance", headers=auth_headers(teacher_token), json=[
        {"student_id": s["id"], "class_id": cls["id"], "day": day, "status": "present"}])
    assert fix.json()[0]["status"] == "present"  # upsert, not duplicate
    summary = client.get(f"/api/v1/attendance/summary?class_id={cls['id']}&day={day}",
                         headers=auth_headers(teacher_token)).json()
    assert (summary["total"], summary["present"], summary["rate"]) == (1, 1, 1.0)
    bad = client.post("/api/v1/attendance", headers=auth_headers(teacher_token), json=[
        {"student_id": 999, "class_id": cls["id"], "day": day, "status": "present"}])
    assert bad.status_code == 400


def test_grades_report_card_and_self_service(admin_client, client, teacher_token,
                                             student_token, db_session):
    from schoolms import models
    from schoolms.security import decode_access_token
    cls, s = _class(admin_client), _student(admin_client)
    student_user_id = int(decode_access_token(student_token)["sub"])
    db_session.query(models.Student).filter(models.Student.id == s["id"]).update(
        {"user_id": student_user_id})
    db_session.commit()
    a1 = client.post("/api/v1/assignments", headers=auth_headers(teacher_token), json={
        "class_id": cls["id"], "title": "Midterm", "max_score": 100}).json()
    g = client.post("/api/v1/grades", headers=auth_headers(teacher_token), json={
        "assignment_id": a1["id"], "student_id": s["id"], "score": 85})
    assert g.status_code == 201
    over = client.post("/api/v1/grades", headers=auth_headers(teacher_token), json={
        "assignment_id": a1["id"], "student_id": s["id"], "score": 500})
    assert over.status_code == 400  # exceeds max_score
    card = client.get(f"/api/v1/report-cards/{s['id']}",
                      headers=auth_headers(teacher_token)).json()
    assert card["average_pct"] == 85.0 and card["letter"] == "B"
    own = client.get(f"/api/v1/report-cards/{s['id']}",
                     headers=auth_headers(student_token)).json()
    assert own["average_pct"] == 85.0  # self-service allowed
    other = _student(admin_client, "S-OTHER")
    forbidden = client.get(f"/api/v1/report-cards/{other['id']}",
                           headers=auth_headers(student_token))
    assert forbidden.status_code == 403  # cannot view others


def test_dashboard_stats(admin_client):
    _student(admin_client)
    _teacher(admin_client)
    stats = admin_client.get("/api/v1/dashboard/stats").json()
    assert stats["students"] >= 1 and stats["teachers"] >= 1
    assert any(r["role"] == "admin" for r in stats["users_by_role"])
