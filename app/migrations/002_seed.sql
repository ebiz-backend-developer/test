-- 002: seed users (one per role), notification templates, planning data.
INSERT INTO users (email, name, role, api_key) VALUES
    ('admin@example.com', 'Ada Admin', 'admin', 'dev-admin-key'),
    ('finance@example.com', 'Finn Finance', 'finance', 'dev-finance-key'),
    ('support@example.com', 'Sue Support', 'support', 'dev-support-key'),
    ('auditor@example.com', 'Al Auditor', 'auditor', 'dev-auditor-key'),
    ('dev@example.com', 'Dee Developer', 'developer', 'dev-developer-key'),
    ('user@example.com', 'Uma User', 'user', 'dev-user-key');

INSERT INTO notification_templates (name, channel, subject, body) VALUES
    ('payment_receipt', 'email', 'Receipt for your payment {{payment_id}}',
     'Hi {{name}}, we received {{amount}} {{currency}} for {{payment_id}}. Thank you!'),
    ('payment_failed', 'email', 'Your payment {{payment_id}} failed',
     'Hi {{name}}, payment {{payment_id}} ({{amount}} {{currency}}) failed: {{reason}}.'),
    ('otp_code', 'sms', '', 'Your verification code is {{code}}. It expires in 10 minutes.'),
    ('refund_issued', 'email', 'Refund issued for {{payment_id}}',
     'Hi {{name}}, a refund of {{amount}} {{currency}} was issued for {{payment_id}}.');

-- c1: scope
INSERT INTO scope_items (area, title, in_scope, notes) VALUES
    ('payments', 'Card + bank payment intents with confirm/refund lifecycle', 1, 'MVP: mock providers with provider interface for Stripe/adapters'),
    ('payments', 'In-person / terminal payments', 0, 'Out of scope for MVP'),
    ('notifications', 'Transactional SMS and email with templates + delivery log', 1, 'MVP: mock gateways with provider interface for Twilio/SES'),
    ('notifications', 'Marketing campaigns / bulk sends', 0, 'Out of scope for MVP'),
    ('analytics', 'Event ingest + revenue/funnel aggregates', 1, 'MVP scope'),
    ('reports', 'Compliance reports: transactions, refunds, notifications, access audit, revenue', 1, 'CSV + JSON export, every run audited'),
    ('reports', 'E-filing with regulators', 0, 'Out of scope for MVP');

-- c1: user roles
INSERT INTO role_definitions (name, description, permissions_json) VALUES
    ('admin', 'Full access incl. milestone approval and user management',
     '["payments:*","notify:*","analytics:*","reports:*","planning:*","admin:*"]'),
    ('finance', 'Payments operations + financial reports',
     '["payments:create","payments:read","payments:refund","reports:run","reports:read","analytics:read"]'),
    ('support', 'Customer operations: payment lookup, notifications',
     '["payments:create","payments:read","notify:*","reports:read"]'),
    ('auditor', 'Read-only compliance access',
     '["payments:read","reports:run","reports:read","analytics:read","audit:read"]'),
    ('developer', 'Integration config, analytics ingest, planning proposals',
     '["analytics:*","notify:templates","planning:propose","reports:read"]'),
    ('user', 'Customer: own payments and receipts only', '["payments:own"]');

-- c2: core modules + MVP priority
INSERT INTO modules (name, description, priority, mvp, status, owner_role) VALUES
    ('payments', 'Payment intents, provider adapters, refunds, webhooks', 'P0', 1, 'shipped', 'finance'),
    ('notifications', 'SMS/email templates, sending, delivery tracking', 'P0', 1, 'shipped', 'support'),
    ('reports', 'Compliance report generation + export + audit trail', 'P0', 1, 'shipped', 'auditor'),
    ('analytics', 'Event ingest + revenue/usage aggregates', 'P1', 1, 'shipped', 'developer'),
    ('planning', 'Scope/roles/modules/milestones API + approvals', 'P1', 1, 'shipped', 'admin'),
    ('dashboard-ui', 'Operator dashboard for integrations and reports', 'P1', 1, 'shipped', 'developer'),
    ('real-psp-adapters', 'Live Stripe/bank adapters behind provider interface', 'P2', 0, 'planned', 'developer'),
    ('scheduled-reports', 'Cron delivery of compliance reports', 'P2', 0, 'planned', 'auditor');

-- c3: architecture / tech stack decisions
INSERT INTO tech_decisions (area, choice, rationale, status) VALUES
    ('language-runtime', 'Python 3.12', 'Team standard; fast API delivery, strong data/reporting libs', 'selected'),
    ('api-framework', 'FastAPI + Pydantic v2', 'Typed endpoints, auto docs, test client', 'selected'),
    ('datastore', 'SQLite (WAL) with versioned SQL migrations', 'Zero-ops MVP; migrate to Postgres when multi-writer needed', 'selected'),
    ('auth', 'API keys + role-based access control', 'Simple service-to-service + operator auth; JWT/SSO later', 'selected'),
    ('payments', 'Provider interface + mock PSP adapters', 'Ship lifecycle now; swap in Stripe/bank SDKs without API change', 'selected'),
    ('messaging', 'Provider interface + mock SMS/email gateways', 'Ship templates/delivery log now; Twilio/SES adapters later', 'selected'),
    ('reporting', 'Synchronous CSV/JSON report runs with audit trail', 'Deterministic compliance exports; async/scheduled later', 'selected');

-- c4: delivery milestones (one pre-approved to show the approval flow; rest proposed)
INSERT INTO milestones (title, description, due_date, status) VALUES
    ('M1: Payments + notifications MVP', 'Intents, refunds, webhooks, SMS/email templates + delivery log', '2026-12-15', 'proposed'),
    ('M2: Analytics + compliance reports', 'Event ingest, aggregates, audited CSV/JSON report runs', '2027-01-15', 'proposed'),
    ('M3: Dashboard + RBAC hardening', 'Operator UI, role-scoped endpoints, audit coverage', '2027-02-01', 'proposed'),
    ('M4: Live PSP/messaging adapters', 'Stripe/bank + Twilio/SES behind existing interfaces', '2027-03-01', 'proposed');
