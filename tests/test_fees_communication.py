"""Fees + communication behavior through the roleified API."""
from tests.helpers import DbTestCase


class FeesTest(DbTestCase):
    def test_invoice_pay_balance(self):
        _, inv = self.call("POST", "/api/invoices", role="accountant", body={
            "student_name": "Amina", "term": "2026-T1", "amount": 50000})
        self.assertEqual(inv["status"], "unpaid")
        _, pay = self.call("POST", "/api/payments", role="accountant", body={
            "invoice_id": inv["id"], "amount": 20000, "method": "transfer"})
        self.assertEqual(pay["invoice"]["status"], "partial")
        self.call("POST", "/api/payments", role="accountant", body={
            "invoice_id": inv["id"], "amount": 30000})
        s, done = self.call("GET", f"/api/invoices/{inv['id']}",
                            role="accountant")
        self.assertEqual(done["status"], "paid")
        self.assertEqual(done["balance"], 0)
        s, bal = self.call("GET", "/api/balance?student_name=Amina",
                           role="parent")
        self.assertEqual((bal["billed"], bal["paid"], bal["balance"]),
                         (50000, 50000, 0))

    def test_overpayment_rejected(self):
        _, inv = self.call("POST", "/api/invoices", role="accountant", body={
            "student_name": "B", "term": "2026-T1", "amount": 1000})
        s, err = self.call("POST", "/api/payments", role="accountant", body={
            "invoice_id": inv["id"], "amount": 1001})
        self.assertEqual(s, 400)

    def test_teacher_cannot_issue_invoice(self):
        s, _ = self.call("POST", "/api/invoices", role="teacher", body={
            "student_name": "B", "term": "2026-T1", "amount": 1000})
        self.assertEqual(s, 403)


class CommunicationTest(DbTestCase):
    def test_broadcast_and_inbox(self):
        s, msg = self.call("POST", "/api/messages", role="teacher", body={
            "sender": "Mr Ade", "subject": "Mid-term date",
            "body": "Mid-term starts Monday", "audience": "all"})
        self.assertEqual(s, 201)
        s, inbox = self.call("GET", "/api/messages", role="student")
        self.assertEqual(len(inbox), 1)
        self.assertEqual(inbox[0]["subject"], "Mid-term date")

    def test_direct_message_audience_filter(self):
        self.call("POST", "/api/messages", role="admin", body={
            "sender": "Admin", "subject": "Staff only", "body": "x",
            "audience": "teachers"})
        s, inbox = self.call("GET", "/api/messages?audience=students",
                             role="student")
        self.assertEqual(inbox, [])
        s, inbox = self.call("GET", "/api/messages?audience=teachers",
                             role="teacher")
        self.assertEqual(len(inbox), 1)

    def test_student_cannot_send(self):
        s, _ = self.call("POST", "/api/messages", role="student", body={
            "sender": "Kid", "subject": "hi", "body": "hello"})
        self.assertEqual(s, 403)
