"""Delivery milestones (criterion c4) as code.

Milestones map to the prioritized modules in mvp.catalog. Status flow:
planned -> approved -> in_progress -> done. Approval requires the
admin.milestones permission and is enforced by the API + store.
"""

MILESTONES = [
    {
        "id": "M1",
        "name": "Foundation + Admissions & Communication",
        "modules": ["admissions", "communication"],
        "deliverables": ["roleified API + data layer",
                         "admissions pipeline working end to end",
                         "announcements/inbox UI"],
        "acceptance": "Apply->admit flow and broadcast message pass automated tests.",
    },
    {
        "id": "M2",
        "name": "Daily school ops: Attendance & Timetable",
        "modules": ["attendance", "timetable"],
        "deliverables": ["attendance marking + summaries",
                         "weekly timetable with clash detection"],
        "acceptance": "Marking a class and detecting a room clash pass tests.",
    },
    {
        "id": "M3",
        "name": "Academic + financials: Grades & Fees",
        "modules": ["grades", "fees"],
        "deliverables": ["gradebook with averages",
                         "invoicing, payments, balances"],
        "acceptance": "Averages and balances computed correctly in tests.",
    },
    {
        "id": "M4",
        "name": "MVP hardening & pilot",
        "modules": ["admissions", "attendance", "grades", "timetable",
                    "fees", "communication"],
        "deliverables": ["full UI pass", "seed demo data", "pilot sign-off"],
        "acceptance": "Full test suite green, pilot school onboarded.",
    },
]

STATUSES = ("planned", "approved", "in_progress", "done")

# allowed status transitions
TRANSITIONS = {
    "planned": ("approved",),
    "approved": ("in_progress",),
    "in_progress": ("done",),
    "done": (),
}


def get_milestone(milestone_id):
    for m in MILESTONES:
        if m["id"] == milestone_id:
            return m
    raise KeyError(f"unknown milestone: {milestone_id}")


def check_transition(old, new):
    if new not in TRANSITIONS.get(old, ()):
        raise ValueError(f"illegal milestone transition {old!r} -> {new!r}")
    return True
