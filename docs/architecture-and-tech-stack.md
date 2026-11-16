# School Management System — Architecture and Tech Stack

Covers criterion **c3**: architecture and tech stack selected.

## 1. Architecture decision

**Selected: modular monolith with clean module boundaries, single
relational database, multi-tenant by `school_id`.**

- One backend deployable, one module per domain (M1–M16), each with
  its own router/service/repository; cross-module calls go through
  explicit service interfaces, never direct table access.
- REST JSON API; versioned (`/api/v1`); OpenAPI spec generated from
  code and published for frontend/mobile.
- Server-rendered admin UI is out; a separate SPA consumes the API.
- Background jobs (notifications, report exports, reminders) run in
  a worker process sharing the same codebase.
- File uploads (documents, assignments) go to object storage; the
  database stores metadata + object key only.

### Why not microservices now

- Team and scale do not justify the ops cost; module boundaries
  preserve a later split path (Fees, Comms split first if needed).
- Single-database transactions keep enrollment/grading/fee flows
  correct without sagas.

### Why not a monolith without boundaries

- 16 modules would tangle; enforced module interfaces keep the MVP
  shippable and later modules pluggable.

## 2. Tech stack (selected)

| Layer | Choice | Notes |
|---|---|---|
| Backend language/framework | **TypeScript + NestJS (Node.js 22 LTS)** | Modules, DI, validation, OpenAPI generation |
| API style | REST JSON, OpenAPI 3.1 | Versioned `/api/v1`; JWT access + refresh |
| Frontend (web) | **React + Vite + TypeScript + Tailwind** | SPA; React Query, React Hook Form, i18n-ready |
| Database | **PostgreSQL 16** | Row-level multi-tenancy via `school_id`; Prisma or TypeORM migrations |
| Cache/queue | **Redis 7** (cache + BullMQ queue) | Sessions, rate limits, jobs |
| Object storage | **S3-compatible** (MinIO local / cloud S3) | Documents, attachments |
| Auth | JWT (short access + rotating refresh), bcrypt/argon2 | Invite codes for parents; RBAC middleware |
| Notifications | Provider abstraction: email (SMTP/SES), SMS (one vendor), push (FCM) | One provider per channel in MVP |
| Payments | Provider abstraction; one gateway in MVP | Manual/bank-transfer always supported |
| Validation | DTO validation (class-validator/Zod) server-side | Never trust client |
| Audit | Append-only `audit_logs` table + request id | Every write logs actor/action/diff |
| Testing | Vitest/Jest + Supertest, Playwright for E2E | Unit + API + one E2E per MVP flow |
| Lint/format | ESLint + Prettier, strict TS | CI-gated |
| Containers | Docker + Docker Compose for local/dev | One compose for api/worker/web/db/redis/minio |
| CI/CD | GitHub Actions: lint → typecheck → test → build → image | Preview env per PR; staging → prod |
| Hosting | Any container host (Render/Fly/AWS) + managed Postgres/Redis | 12-factor config via env |
| Observability | Structured JSON logs, health/readiness endpoints, Sentry | Metrics endpoint for later Prometheus |

## 3. Data and security principles

- Every tenant table has `school_id`; all queries scoped by the
  authenticated school; Super Admin path is explicit and logged.
- RBAC enforced in API guards; frontend hiding is UX only.
- PII minimization: store only needed student data; encrypt backups;
  signed URLs with expiry for documents.
- Backups: daily Postgres snapshots, 30-day retention; tested restore.
- Rate limiting on auth and broadcast endpoints; idempotency keys on
  payments and bulk imports.

## 4. Repository layout (proposed)

```text
apps/
  api/        # NestJS modular monolith + worker
    src/modules/<m1..m16>/
  web/        # React SPA
packages/
  contracts/  # shared DTOs / OpenAPI types
docs/         # this plan (scope, modules, architecture, milestones)
docker-compose.yml
```

## 5. Alternatives considered and rejected

- Django/Laravel monolith: fine choices, but the team's backend
  direction is TypeScript; NestJS gives the same structure with one
  language across api/web/contracts.
- Microservices + event bus: rejected for MVP (see §1); revisit
  after 50+ schools or a dedicated platform team.
- NoSQL-first: rejected; school data is relational (enrollments,
  grades, invoices) and needs joins/transactions.

## 6. Acceptance for c3

- [x] Architecture style chosen with rationale and split path.
- [x] Full stack table with versions where it matters.
- [x] Security/tenancy principles stated.
- [x] Repo layout and rejected alternatives recorded.
