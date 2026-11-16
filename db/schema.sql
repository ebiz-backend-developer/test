-- Task 5 reference schema: multi-school data model (PostgreSQL 16).
-- Tenancy: shared schema, every tenant table carries school_id + RLS.
-- Application sets: SELECT set_config('app.current_school_id', :school_id, true);

CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ============ Global (no school_id) ============

CREATE TABLE schools (
  id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  code        TEXT NOT NULL UNIQUE,
  name        TEXT NOT NULL,
  timezone    TEXT NOT NULL DEFAULT 'UTC',
  status      TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active','suspended','archived')),
  created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE users (
  id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  email         TEXT NOT NULL UNIQUE,
  password_hash TEXT NOT NULL,
  status        TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active','locked','disabled')),
  created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE roles (
  id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name        TEXT NOT NULL UNIQUE,
  description TEXT NOT NULL DEFAULT ''
);

INSERT INTO roles (name, description) VALUES
  ('admin','System Administrator (cross-school config only)'),
  ('principal','Principal / Head of School'),
  ('registrar','Registrar / Admissions Officer'),
  ('teacher','Teacher'),
  ('class_teacher','Class Teacher / Form Tutor'),
  ('accountant','Accountant / Bursar'),
  ('student','Student'),
  ('parent','Parent / Guardian'),
  ('support','IT Support')
ON CONFLICT (name) DO NOTHING;

-- ============ Tenant link ============

CREATE TABLE user_school_memberships (
  id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id    UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  school_id  UUID NOT NULL REFERENCES schools(id) ON DELETE CASCADE,
  role_id    UUID NOT NULL REFERENCES roles(id) ON DELETE RESTRICT,
  status     TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active','revoked')),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (user_id, school_id, role_id)
);
CREATE INDEX idx_memberships_school ON user_school_memberships(school_id);
CREATE INDEX idx_memberships_user ON user_school_memberships(user_id);

-- ============ Core ============

CREATE TABLE academic_sessions (
  id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  school_id  UUID NOT NULL REFERENCES schools(id) ON DELETE CASCADE,
  label      TEXT NOT NULL,
  starts_on  DATE NOT NULL,
  ends_on    DATE NOT NULL,
  is_active  BOOLEAN NOT NULL DEFAULT FALSE,
  UNIQUE (school_id, label),
  CHECK (starts_on < ends_on)
);

CREATE TABLE terms (
  id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  school_id  UUID NOT NULL REFERENCES schools(id) ON DELETE CASCADE,
  session_id UUID NOT NULL REFERENCES academic_sessions(id) ON DELETE RESTRICT,
  name       TEXT NOT NULL,
  starts_on  DATE NOT NULL,
  ends_on    DATE NOT NULL,
  UNIQUE (school_id, session_id, name),
  CHECK (starts_on < ends_on)
);

CREATE TABLE classes (
  id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  school_id  UUID NOT NULL REFERENCES schools(id) ON DELETE CASCADE,
  code       TEXT NOT NULL,
  name       TEXT NOT NULL,
  level      INTEGER NOT NULL DEFAULT 0,
  UNIQUE (school_id, code)
);

CREATE TABLE sections (
  id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  school_id        UUID NOT NULL REFERENCES schools(id) ON DELETE CASCADE,
  class_id         UUID NOT NULL REFERENCES classes(id) ON DELETE RESTRICT,
  session_id       UUID NOT NULL REFERENCES academic_sessions(id) ON DELETE RESTRICT,
  name             TEXT NOT NULL,
  class_teacher_id UUID REFERENCES users(id) ON DELETE SET NULL,
  UNIQUE (school_id, class_id, session_id, name)
);

CREATE TABLE subjects (
  id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  school_id  UUID NOT NULL REFERENCES schools(id) ON DELETE CASCADE,
  code       TEXT NOT NULL,
  name       TEXT NOT NULL,
  UNIQUE (school_id, code)
);

CREATE TABLE students (
  id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  school_id    UUID NOT NULL REFERENCES schools(id) ON DELETE CASCADE,
  admission_no TEXT NOT NULL,
  first_name   TEXT NOT NULL,
  last_name    TEXT NOT NULL,
  dob          DATE,
  gender       TEXT CHECK (gender IN ('male','female','other')),
  status       TEXT NOT NULL DEFAULT 'enrolled'
               CHECK (status IN ('applicant','enrolled','graduated','transferred','withdrawn')),
  created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (school_id, admission_no)
);
CREATE INDEX idx_students_school ON students(school_id);

CREATE TABLE guardians (
  id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  school_id  UUID NOT NULL REFERENCES schools(id) ON DELETE CASCADE,
  full_name  TEXT NOT NULL,
  phone      TEXT,
  email      TEXT,
  address    TEXT
);
CREATE INDEX idx_guardians_school ON guardians(school_id);

CREATE TABLE student_guardians (
  student_id  UUID NOT NULL REFERENCES students(id) ON DELETE CASCADE,
  guardian_id UUID NOT NULL REFERENCES guardians(id) ON DELETE CASCADE,
  school_id   UUID NOT NULL REFERENCES schools(id) ON DELETE CASCADE,
  relation    TEXT NOT NULL DEFAULT 'parent',
  is_primary  BOOLEAN NOT NULL DEFAULT FALSE,
  PRIMARY KEY (student_id, guardian_id)
);
CREATE INDEX idx_student_guardians_school ON student_guardians(school_id);

-- ============ Admissions ============

CREATE TABLE enquiries (
  id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  school_id     UUID NOT NULL REFERENCES schools(id) ON DELETE CASCADE,
  child_name    TEXT NOT NULL,
  contact_phone TEXT,
  contact_email TEXT,
  class_applied UUID REFERENCES classes(id) ON DELETE SET NULL,
  source        TEXT NOT NULL DEFAULT 'walk-in',
  status        TEXT NOT NULL DEFAULT 'new'
                CHECK (status IN ('new','contacted','applied','closed')),
  created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE applications (
  id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  school_id  UUID NOT NULL REFERENCES schools(id) ON DELETE CASCADE,
  enquiry_id UUID REFERENCES enquiries(id) ON DELETE RESTRICT,
  payload    JSONB NOT NULL DEFAULT '{}',
  status     TEXT NOT NULL DEFAULT 'submitted'
             CHECK (status IN ('submitted','under_review','offered','waitlisted','rejected','accepted','enrolled')),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE application_documents (
  id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  school_id      UUID NOT NULL REFERENCES schools(id) ON DELETE CASCADE,
  application_id UUID NOT NULL REFERENCES applications(id) ON DELETE CASCADE,
  doc_type       TEXT NOT NULL,
  file_key       TEXT NOT NULL
);

CREATE TABLE admission_decisions (
  id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  school_id      UUID NOT NULL REFERENCES schools(id) ON DELETE CASCADE,
  application_id UUID NOT NULL REFERENCES applications(id) ON DELETE RESTRICT,
  decision       TEXT NOT NULL CHECK (decision IN ('offer','waitlist','reject')),
  decided_by     UUID REFERENCES users(id) ON DELETE SET NULL,
  approved_by    UUID REFERENCES users(id) ON DELETE SET NULL,
  decided_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE enrolments (
  id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  school_id  UUID NOT NULL REFERENCES schools(id) ON DELETE CASCADE,
  student_id UUID NOT NULL REFERENCES students(id) ON DELETE RESTRICT,
  section_id UUID NOT NULL REFERENCES sections(id) ON DELETE RESTRICT,
  session_id UUID NOT NULL REFERENCES academic_sessions(id) ON DELETE RESTRICT,
  roll_no    TEXT,
  UNIQUE (school_id, section_id, student_id),
  UNIQUE (school_id, section_id, roll_no)
);

-- ============ Attendance ============

CREATE TABLE attendance_registers (
  id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  school_id  UUID NOT NULL REFERENCES schools(id) ON DELETE CASCADE,
  section_id UUID NOT NULL REFERENCES sections(id) ON DELETE RESTRICT,
  date       DATE NOT NULL,
  status     TEXT NOT NULL DEFAULT 'open' CHECK (status IN ('open','closed')),
  UNIQUE (school_id, section_id, date)
);

CREATE TABLE attendance_entries (
  id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  school_id   UUID NOT NULL REFERENCES schools(id) ON DELETE CASCADE,
  register_id UUID NOT NULL REFERENCES attendance_registers(id) ON DELETE CASCADE,
  student_id  UUID NOT NULL REFERENCES students(id) ON DELETE RESTRICT,
  code        TEXT NOT NULL CHECK (code IN ('present','absent','late','excused')),
  note        TEXT,
  UNIQUE (register_id, student_id)
);

-- ============ Grades ============

CREATE TABLE grade_scales (
  id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  school_id  UUID NOT NULL REFERENCES schools(id) ON DELETE CASCADE,
  label      TEXT NOT NULL,
  min_score  NUMERIC(5,2) NOT NULL,
  max_score  NUMERIC(5,2) NOT NULL,
  grade      TEXT NOT NULL,
  points     NUMERIC(4,2) NOT NULL DEFAULT 0,
  UNIQUE (school_id, label, grade),
  CHECK (min_score <= max_score)
);

CREATE TABLE assessments (
  id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  school_id  UUID NOT NULL REFERENCES schools(id) ON DELETE CASCADE,
  subject_id UUID NOT NULL REFERENCES subjects(id) ON DELETE RESTRICT,
  section_id UUID NOT NULL REFERENCES sections(id) ON DELETE RESTRICT,
  term_id    UUID NOT NULL REFERENCES terms(id) ON DELETE RESTRICT,
  name       TEXT NOT NULL,
  weight     NUMERIC(5,2) NOT NULL CHECK (weight > 0),
  max_score  NUMERIC(7,2) NOT NULL CHECK (max_score > 0)
);

CREATE TABLE scores (
  id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  school_id     UUID NOT NULL REFERENCES schools(id) ON DELETE CASCADE,
  assessment_id UUID NOT NULL REFERENCES assessments(id) ON DELETE RESTRICT,
  student_id    UUID NOT NULL REFERENCES students(id) ON DELETE RESTRICT,
  raw_score     NUMERIC(7,2) NOT NULL CHECK (raw_score >= 0),
  status        TEXT NOT NULL DEFAULT 'draft' CHECK (status IN ('draft','published')),
  UNIQUE (assessment_id, student_id)
);

CREATE TABLE report_cards (
  id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  school_id  UUID NOT NULL REFERENCES schools(id) ON DELETE CASCADE,
  student_id UUID NOT NULL REFERENCES students(id) ON DELETE RESTRICT,
  term_id    UUID NOT NULL REFERENCES terms(id) ON DELETE RESTRICT,
  payload    JSONB NOT NULL DEFAULT '{}',
  published_at TIMESTAMPTZ,
  UNIQUE (school_id, student_id, term_id)
);

-- ============ Timetable ============

CREATE TABLE time_slots (
  id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  school_id  UUID NOT NULL REFERENCES schools(id) ON DELETE CASCADE,
  term_id    UUID NOT NULL REFERENCES terms(id) ON DELETE RESTRICT,
  day_of_week SMALLINT NOT NULL CHECK (day_of_week BETWEEN 1 AND 7),
  starts_at  TIME NOT NULL,
  ends_at    TIME NOT NULL,
  UNIQUE (school_id, term_id, day_of_week, starts_at, ends_at),
  CHECK (starts_at < ends_at)
);

CREATE TABLE lessons (
  id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  school_id  UUID NOT NULL REFERENCES schools(id) ON DELETE CASCADE,
  section_id UUID NOT NULL REFERENCES sections(id) ON DELETE RESTRICT,
  subject_id UUID NOT NULL REFERENCES subjects(id) ON DELETE RESTRICT,
  slot_id    UUID NOT NULL REFERENCES time_slots(id) ON DELETE RESTRICT,
  teacher_id UUID REFERENCES users(id) ON DELETE RESTRICT,
  room       TEXT,
  UNIQUE (school_id, slot_id, section_id),
  UNIQUE (school_id, slot_id, teacher_id),
  UNIQUE (school_id, slot_id, room)
);

-- ============ Fees ============

CREATE TABLE fee_structures (
  id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  school_id  UUID NOT NULL REFERENCES schools(id) ON DELETE CASCADE,
  class_id   UUID NOT NULL REFERENCES classes(id) ON DELETE RESTRICT,
  term_id    UUID NOT NULL REFERENCES terms(id) ON DELETE RESTRICT,
  head       TEXT NOT NULL,
  amount     NUMERIC(12,2) NOT NULL CHECK (amount >= 0),
  currency   TEXT NOT NULL DEFAULT 'NGN',
  UNIQUE (school_id, class_id, term_id, head)
);

CREATE TABLE invoices (
  id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  school_id  UUID NOT NULL REFERENCES schools(id) ON DELETE CASCADE,
  student_id UUID NOT NULL REFERENCES students(id) ON DELETE RESTRICT,
  term_id    UUID NOT NULL REFERENCES terms(id) ON DELETE RESTRICT,
  invoice_no TEXT NOT NULL,
  total      NUMERIC(12,2) NOT NULL CHECK (total >= 0),
  status     TEXT NOT NULL DEFAULT 'issued'
             CHECK (status IN ('issued','partial','paid','void')),
  UNIQUE (school_id, invoice_no)
);
CREATE INDEX idx_invoices_school_student ON invoices(school_id, student_id);

CREATE TABLE invoice_lines (
  id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  school_id  UUID NOT NULL REFERENCES schools(id) ON DELETE CASCADE,
  invoice_id UUID NOT NULL REFERENCES invoices(id) ON DELETE CASCADE,
  head       TEXT NOT NULL,
  amount     NUMERIC(12,2) NOT NULL CHECK (amount >= 0)
);

CREATE TABLE payments (
  id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  school_id    UUID NOT NULL REFERENCES schools(id) ON DELETE CASCADE,
  invoice_id   UUID NOT NULL REFERENCES invoices(id) ON DELETE RESTRICT,
  amount       NUMERIC(12,2) NOT NULL CHECK (amount > 0),
  method       TEXT NOT NULL DEFAULT 'cash',
  provider_ref TEXT,
  received_by  UUID REFERENCES users(id) ON DELETE SET NULL,
  received_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE receipts (
  id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  school_id  UUID NOT NULL REFERENCES schools(id) ON DELETE CASCADE,
  payment_id UUID NOT NULL UNIQUE REFERENCES payments(id) ON DELETE RESTRICT,
  receipt_no TEXT NOT NULL,
  issued_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (school_id, receipt_no)
);

CREATE TABLE fee_waivers (
  id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  school_id  UUID NOT NULL REFERENCES schools(id) ON DELETE CASCADE,
  invoice_id UUID NOT NULL REFERENCES invoices(id) ON DELETE RESTRICT,
  amount     NUMERIC(12,2) NOT NULL CHECK (amount > 0),
  reason     TEXT NOT NULL,
  approved_by UUID REFERENCES users(id) ON DELETE SET NULL
);

-- ============ Communication ============

CREATE TABLE announcements (
  id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  school_id    UUID NOT NULL REFERENCES schools(id) ON DELETE CASCADE,
  audience     TEXT NOT NULL DEFAULT 'school',
  title        TEXT NOT NULL,
  body         TEXT NOT NULL,
  published_by UUID REFERENCES users(id) ON DELETE SET NULL,
  published_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE messages (
  id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  school_id    UUID NOT NULL REFERENCES schools(id) ON DELETE CASCADE,
  sender_id    UUID NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
  recipient_id UUID NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
  subject      TEXT,
  body         TEXT NOT NULL,
  sent_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
  CHECK (sender_id <> recipient_id)
);

CREATE TABLE notification_log (
  id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  school_id  UUID NOT NULL REFERENCES schools(id) ON DELETE CASCADE,
  template   TEXT NOT NULL,
  channel    TEXT NOT NULL CHECK (channel IN ('in_app','email','sms','push')),
  recipient  TEXT NOT NULL,
  payload    JSONB NOT NULL DEFAULT '{}',
  status     TEXT NOT NULL DEFAULT 'queued'
             CHECK (status IN ('queued','sent','failed')),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ============ Shared ============

CREATE TABLE audit_log (
  id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  school_id  UUID NOT NULL REFERENCES schools(id) ON DELETE CASCADE,
  actor_id   UUID REFERENCES users(id) ON DELETE SET NULL,
  entity     TEXT NOT NULL,
  entity_id  UUID,
  action     TEXT NOT NULL,
  before_data JSONB,
  after_data  JSONB,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_audit_school_entity ON audit_log(school_id, entity, created_at);

-- ============ Row-Level Security (tenant isolation) ============
-- Every tenant table enforces school_id = app.current_school_id.

DO $$
DECLARE t TEXT;
BEGIN
  FOR t IN SELECT unnest(ARRAY[
    'user_school_memberships','academic_sessions','terms','classes','sections',
    'subjects','students','guardians','student_guardians','enrolments',
    'enquiries','applications','application_documents','admission_decisions',
    'attendance_registers','attendance_entries','grade_scales','assessments',
    'scores','report_cards','time_slots','lessons','fee_structures','invoices',
    'invoice_lines','payments','receipts','fee_waivers','announcements',
    'messages','notification_log','audit_log'
  ]) LOOP
    EXECUTE format('ALTER TABLE %I ENABLE ROW LEVEL SECURITY', t);
    EXECUTE format(
      'DROP POLICY IF EXISTS tenant_isolation ON %I; ' ||
      'CREATE POLICY tenant_isolation ON %I USING ' ||
      '(school_id = current_setting(''app.current_school_id'', true)::uuid)',
      t, t);
  END LOOP;
END $$;
