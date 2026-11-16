-- 002: milestone approval audit trail (c4).
ALTER TABLE milestones ADD COLUMN approved_by TEXT NOT NULL DEFAULT '';
ALTER TABLE milestones ADD COLUMN approved_at TEXT NOT NULL DEFAULT '';
ALTER TABLE milestones ADD COLUMN decided_by TEXT NOT NULL DEFAULT '';
