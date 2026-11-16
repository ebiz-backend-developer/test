# Task 6 — UI/UX Flows: Dashboards, Portals, Mobile Needs & Wireframes

- Status: proposed for review (sign-off table in C4).
- Scope: dashboards, portals, mobile needs, wireframes.
- No verified project knowledge was supplied with this task, so
  assumptions are marked `[ASSUMPTION]` and kept generic to a
  data-driven business portal. Confirm or replace them at M1 review.
- Acceptance mapping: `C1` scope & roles, `C2` modules & MVP,
  `C3` architecture & tech stack, `C4` milestones & approval.

## C1 — Scope and user roles defined

### C1.1 Objectives

1. Give each role one clear home (dashboard or portal landing) with no
   dead ends: every screen has a primary action, a way back, and
   visible system status.
2. Make the MVP demo-able end to end: sign in → dashboard → portal
   list → detail → action → confirmation → notification.
3. Ship mobile-usable from day one (responsive web); native apps are
   explicitly post-MVP.

### C1.2 In scope

- Information architecture (IA), navigation model, and core user flows.
- Dashboard module: layout, widgets, filters, empty/loading/error states.
- Portal module: browse/search list, detail, record actions, activity.
- Mobile needs: breakpoints, navigation, touch targets, readability,
  performance budget, offline fallbacks for read paths.
- Low-fidelity wireframes (ASCII in this doc) for every MVP screen.
- RBAC-aware UI: what each role sees, and what is hidden vs disabled.
- Design-system foundations: tokens, core components, form/empty-state
  patterns (visual polish is a later task).

### C1.3 Out of scope

- Final visual design, branding, illustrations, marketing site.
- Native iOS/Android apps (responsive web + PWA-ready shell only).
- Admin analytics warehouse / BI tooling; only in-app widgets.
- Multi-tenant white-labelling beyond theme tokens.

### C1.4 User roles

| Role | Description | Home | Key capabilities |
|------|-------------|------|------------------|
| Admin | Platform owner `[ASSUMPTION]` | Admin dashboard | Manage users/roles, all records, settings, audit |
| Manager | Team/ops lead | Team dashboard | Approve actions, team reports, manage own team |
| Operator / Staff | Day-to-day worker | Work queue dashboard | Create/edit assigned records, bulk actions |
| Portal user (customer/vendor) | External self-serve user | Portal home | View own records, submit requests, track status |
| Viewer / Auditor | Read-only oversight | Reports dashboard | Read dashboards/reports, export |
| Guest | Unauthenticated visitor | Login / request access | Sign in, password reset, request access |

### C1.5 Permission matrix (UI enforcement)

| Capability | Admin | Manager | Operator | Portal user | Viewer | Guest |
|------------|:-----:|:-------:|:--------:|:-----------:|:------:|:-----:|
| View own dashboard | Y | Y | Y | Y | Y | – |
| View team dashboard | Y | Y | – | – | – | – |
| Browse portal records | Y (all) | Y (team) | Y (assigned) | Y (own) | Y (read) | – |
| Create record / request | Y | Y | Y | Y | – | – |
| Edit record | Y | Y (team) | Y (assigned) | Y (own draft) | – | – |
| Approve / reject | Y | Y | – | – | – | – |
| Manage users & roles | Y | – (invite only) | – | – | – | – |
| App settings | Y | – | – | – | – | – |
| Export reports | Y | Y | – | Y (own) | Y | – |
| View audit log | Y | Y (team) | – | – | Y | – |

Rules:

- Server is the source of truth; the UI mirrors permissions by hiding
  forbidden navigation and disabling (with tooltip) forbidden actions.
- Hidden when the user can never use it here (e.g. Guest nav);
  disabled + reason when it may unlock (e.g. "Submit for approval").
- Every disabled action exposes its reason to assistive tech (`aria-disabled`
  + visible hint), never silence.

### C1.6 Personas (short)

- **Asha, Admin:** needs user/role control and audit confidence.
- **Marco, Manager:** needs team status at a glance and fast approvals.
- **Priya, Operator:** needs a queue with keyboard speed and bulk edits.
- **Chen, Portal user:** needs mobile-friendly self-serve and tracking.
- **Dana, Viewer:** needs read-only reports she can export.

## C2 — Core modules and MVP prioritized

### C2.1 Module catalogue

| ID | Module | Owns | MVP? |
|----|--------|------|------|
| M1 | Auth & access | Login, logout, reset, invite, RBAC shell, 403/404 | P0 |
| M2 | Dashboards | Role home, KPI cards, charts, queues, filters | P0 |
| M3 | Portal records | List (search/filter/sort/paginate), detail, actions, timeline | P0 |
| M4 | Request workflow | Submit → review → approve/reject → notify | P0 |
| M5 | Notifications | Bell, list, read/unread, email fallback flag | P0 (basic) |
| M6 | User management | Users list, invite, role assign, deactivate | P0 (admin-lite) |
| M7 | Reports & export | Saved views, CSV export | P1 |
| M8 | Settings | Profile, team, app preferences, theme tokens | P1 |
| M9 | Audit log | Filterable actor/action/record trail | P1 |
| M10 | Mobile PWA shell | Installable shell, offline read cache | P1 |
| M11 | Advanced analytics | Custom dashboards, scheduled reports | P2 |
| M12 | White-labelling | Per-tenant themes/domains | P2 |

### C2.2 MVP definition (P0)

Must ship together; removing any one breaks the demo journey:

1. M1 sign-in + role shell (nav adapts per C1.5).
2. M2 one dashboard per role with ≥3 widgets each.
3. M3 portal list + detail with search, filter, pagination.
4. M4 one approval workflow end to end with confirmation + timeline entry.
5. M5 notification bell + list marking the workflow outcome.
6. M6 admin invites a user and assigns a role.

MoSCoW for MVP: Must = P0 above; Should = M7/M8-lite; Could = M9 read-only;
Won't (this milestone) = M11/M12, native apps.

### C2.3 Core user flows (MVP)

Conventions: `→` happy path, `(alt)` alternative, `(err)` error path.
Every flow ends in a confirmation or a recoverable state.

F1 — Sign in → role home (M1→M2):

```text
Guest → Login → (err) invalid creds: inline error, retry, reset link
      → success → role shell + home dashboard (per C1.4)
      → (alt) first login via invite: set password → home
```

F2 — Portal browse → detail → action (M3→M4, primary demo):

```text
Home → Portal list → search/filter/sort → select record → Detail
     → primary action (e.g. Submit for approval)
     → confirm dialog → success toast + timeline entry
     → (err) validation: inline field errors, focus first error
     → (err) 409 conflict: reload banner, keep draft
```

F3 — Approve / reject (Manager/Admin):

```text
Dashboard queue → Detail → Approve | Reject (+reason required)
→ confirm → status chip updates → notify requester (M5)
```

F4 — Admin invites user (M6):

```text
Users → Invite → email + role → validate → send invite
→ pending row → (alt) resend / revoke → activated on first login
```

F5 — Track status as portal user (mobile-first):

```text
Portal home → My requests → status chips → Detail → timeline
→ (alt) withdraw draft → confirm → status updates
```

F6 — Notifications (M5):

```text
Bell badge → list → select → deep-link to record → mark read
→ (alt) mark all read → empty state ("You're caught up")
```

Global cross-cutting flows: loading skeletons on every fetch >300ms;
empty states with one CTA; 403 → "Request access" CTA; 404 → home link;
offline (mobile) → cached read + "You're offline" banner, actions queued
as drafts only (no fake success).

## C3 — Architecture and tech stack selected

### C3.1 UX architecture decisions

1. **One responsive web app**, mobile-first CSS, PWA-ready shell
   (manifest + service worker for read caching in M10). No separate
   mobile codebase for MVP.
2. **Route-per-module** IA: `/login`, `/dashboard`, `/portal`,
   `/portal/:id`, `/approvals`, `/users`, `/reports`, `/settings`,
   `/notifications`. Deep-linkable; back button always works.
3. **Design tokens first**: spacing, color (light/dark), type scale,
   radius, elevation; components consume tokens, never raw values.
4. **State split**: server state (fetch/cache) vs UI state (filters,
   dialogs) vs session (role/permissions). Permissions load once per
   session and gate nav + actions per C1.5.
5. **Accessibility target WCAG 2.2 AA**: keyboard-complete flows,
   visible focus, 44px touch targets, contrast ≥ 4.5:1, live regions
   for toasts and async updates.

### C3.2 Selected tech stack (MVP)

| Layer | Choice | Why / notes |
|-------|--------|-------------|
| App framework | Next.js (React + TypeScript) | Routes, SSR for first paint, API proxy; alt: Vite SPA |
| Language | TypeScript (strict) | Typed contracts with backend DTOs |
| Styling | Tailwind CSS + tokens | Responsive + theming speed; alt: CSS modules |
| Server state | TanStack Query | Cache, retry, skeleton/empty/error patterns |
| UI/session state | Zustand (tiny stores) | Role, filters, toasts; alt: Context |
| Forms | React Hook Form + Zod | Inline errors, focus management |
| Tables/lists | TanStack Table (or native + pagination) | Sort/filter/paginate parity desktop/mobile |
| Charts | Recharts (dashboard widgets) | Lightweight KPI/trend widgets |
| Auth | Backend session/JWT via httpOnly cookie `[ASSUMPTION]` | UI stores role/permissions only, never tokens in JS |
| PWA/mobile | Responsive + manifest + service worker (read cache) | Installable, offline banner; native deferred |
| i18n | next-intl, English first | Strings externalized from day one |
| Quality gates | ESLint + Prettier + tsc + axe checks in CI | No merge on red |

Explicit non-goals: no component framework lock-in beyond tokens (MUI/
shadcn-style primitives swappable); no charting BI suite; no native
push in MVP (email fallback flag only).

### C3.3 API/UI contract (minimal)

- `GET /me` → `{ id, name, roles[], permissions[] }` drives shell + matrix.
- `GET /dashboard?role=` → widgets array (type, title, data, link).
- `GET /records?...` → paged `{ items[], page, pageSize, total }`.
- `GET /records/:id`, `POST /records`, `PATCH /records/:id`,
  `POST /records/:id/submit|approve|reject` with problem-details errors.
- UI maps 400→field errors, 401→login, 403→request-access, 404→not-found,
  409→reload banner, 5xx→retry panel. No silent failures.

### C3.4 Information architecture (nav)

```text
[Logo] Dashboard | Portal | Approvals (Mgr/Admin) | Users (Admin)
       | Reports | Settings   ........   [Search] [Bell(n)] [Avatar▾]
Avatar▾: Profile, Preferences, Sign out
Mobile:  bottom tab bar [Home][Portal][Alerts][More] + top contextual back
```

## C4 — Delivery milestones approved

### C4.1 Milestones

| ID | Milestone | Deliverables | Exit criteria | Owner |
|----|-----------|--------------|---------------|-------|
| M1 | IA & roles agreed (wk 1) | C1 + nav map + permission matrix | Roles/permissions signed off; assumptions resolved | Design + PM |
| M2 | Flows & wireframes (wk 2) | C2 flows F1–F6 + all §5 wireframes | Clickable low-fi walkthrough of F2+F3 passes review | Design |
| M3 | Dashboard MVP (wk 3–4) | M1+M2+M5 + tokens + shell | Each role home renders real API data; a11y smoke passes | Frontend |
| M4 | Portal + mobile + handoff (wk 5–6) | M3+M4+M6, responsive, PWA shell | F1–F6 e2e on desktop + 360px mobile; docs handed off | Frontend+QA |

Each milestone ends in a review against its exit criteria; scope
changes re-enter via C2 MoSCoW, never silently.

### C4.2 Approval record

| Criterion | Approver | Decision | Date |
|-----------|----------|----------|------|
| C1 scope & roles | _pending_ | _pending_ | _pending_ |
| C2 modules & MVP | _pending_ | _pending_ | _pending_ |
| C3 architecture & stack | _pending_ | _pending_ | _pending_ |
| C4 milestones | _pending_ | _pending_ | _pending_ |

Sign-off = row marked approved with name + date. This doc is the
single approval surface: approving it approves C1–C4 together.

## 5 — Dashboards, portals, mobile needs, wireframes

### 5.1 Dashboard spec

- Layout: header (title + date/filter) → KPI row (3–4 cards) →
  main grid (chart + queue) → side rail (activity/upcoming).
- Widgets (MVP): KPI card, trend chart, work queue table (top 5 + View
  all), approvals inbox (managers), my-requests (portal users),
  activity feed, alert banner slot.
- States per widget: loading skeleton, empty ("No items — CTA"),
  error with Retry, filtered-no-result with Clear filters.
- Filters persist per session; charts link to the filtered portal list.

### 5.2 Portal spec

- List: search input, filter chips (status/mine/all), sort select,
  responsive table→cards, pagination (20/page), row → detail.
- Detail: title + status chip, key-value summary, tabs
  (Overview | Timeline | Files/notes), primary action bar, audit
  timeline entries on every transition.
- Actions always: confirm destructive/irreversible ones; toast +
  timeline entry on success; inline errors on failure.

### 5.3 Mobile needs

- Breakpoints: 360 / 768 / 1024 / 1440; design starts at 360px.
- Nav: bottom tabs (Home, Portal, Alerts, More); content max 1 column
  <768px; tables collapse to cards; filters become a bottom sheet.
- Touch: ≥44px targets, 8px gaps, sticky primary action on detail.
- Readability: 16px base, line length ≤ 65ch, chips wrap, no h-scroll.
- Performance budget: <200KB critical JS/route, LCP < 2.5s on
  mid-tier Android, skeletons for all fetches >300ms.
- Offline: cached dashboard + last-visited records readable; banner
  "You're offline — showing saved data"; writes become drafts, never
  fake-confirmed.

### 5.4 Wireframes (low-fidelity, MVP screens)

W1 — Desktop dashboard (Manager):

```text
+------------------------------------------------------------------+
| Logo  Dashboard Portal Approvals Users Reports Settings  🔔(3) 👤 |
+------------------------------------------------------------------+
| Team dashboard                      [This week ▾] [Export]         |
| +-----------+ +-----------+ +-----------+ +-----------+            |
| | Active:12 | | Pending:5 | | appr rate | | SLA risk:2|  KPI row   |
| +-----------+ +-----------+ +-----------+ +-----------+            |
| +-------------------------------+ +----------------------------+ |
| | Approvals inbox (top 5)       | | Requests trend  [chart]    | |
| | ☐ REQ-101 Chen  $400 [Review] | |   /\                       | |
| | ☐ REQ-102 …          [Review] | | _/  \__                     | |
| | [View all approvals]          | +----------------------------+ |
| +-------------------------------+ +----------------------------+ |
| | My team queue                 | | Activity                   | |
| | …                       empty/loading/error states per 5.1    | |
+------------------------------------------------------------------+
```

W2 — Desktop portal list:

```text
+------------------------------------------------------------------+
| Portal                              [+ New request]                |
| [Search records…] [Status: All ▾] [Mine ▾] [Sort: Updated ▾]       |
| ID      | Title        | Status   | Owner | Updated |        →     |
| REQ-101 | Laptop req.  | ⏳Pending| Chen  | 2h ago  | [Open]       |
| REQ-102 | Access req.  | ✅Approv.| Priya | 1d ago  | [Open]       |
| …empty: "No records match — [Clear filters]" / skeleton while load |
| < Prev  1 2 3 … 12  Next >              20/page  (184 results)     |
+------------------------------------------------------------------+
```

W3 — Desktop record detail + approval:

```text
+------------------------------------------------------------------+
| < Back to Portal      REQ-101 · Laptop request   [⏳ Pending]      |
| Owner: Chen · Team: Ops · Updated 2h ago                           |
| [Overview] [Timeline (3)] [Notes]                                  |
| Summary: key/value grid …                                          |
| Files/notes list …                                                 |
| Timeline: Submitted → Reviewed → (you are here)                    |
| +---------------------------------------------------------------+  |
| | [Approve] [Reject…(reason)] [Comment]   Manager/Admin only    |  |
| +---------------------------------------------------------------+  |
| Portal-user view: [Withdraw draft] only on own drafts; else track. |
+------------------------------------------------------------------+
```

W4 — Mobile dashboard + portal (360px):

```text
+----------------------------------+
| ☰ Team dashboard        🔔(3) 👤 |
| [This week ▾]                    |
| +----------+ +----------+        |
| |Active:12 | |Pending:5 | KPI 2col
| +----------+ +----------+        |
| Approvals inbox                  |
| [REQ-101 Chen $400]  [Review >]  |
| [REQ-102 …]          [Review >]  |
| [View all >]                     |
| Trend [mini chart]               |
+----------------------------------+
| Home | Portal | Alerts | More    |  bottom tabs
+----------------------------------+

+----------------------------------+
| Portal               [+ New]     |
| [Search…] [Filter ⏷]             |
| +------------------------------+ |
| | REQ-101 ⏳Pending      [>]   | |
| | Laptop req. · Chen · 2h      | |
| +------------------------------+ |
| | REQ-102 ✅Approved     [>]   | |
| +------------------------------+ |
| < Prev 1 2 … Next >              |
+----------------------------------+
| Home | Portal | Alerts | More    |
+----------------------------------+
```

W5 — Mobile detail + admin users (DIA-lite):

```text
+----------------------------------+
| < REQ-101            [⏳Pending]  |
| Laptop request · Chen            |
| [Overview|Timeline|Notes]        |
| Summary rows…                    |
| Timeline entries…                |
| +------------------------------+ |
| | [Approve] [Reject] sticky    | |
+----------------------------------+
| Home | Portal | Alerts | More    |
+----------------------------------+

+----------------------------------+
| Users              [+ Invite]    |
| [Search…] [Role: All ▾]          |
| Ana · Admin · Active    […]      |
| Marco · Manager · Pending […]    |
| Invite dialog: email + role ▾    |
|  [Send invite] [Cancel]          |
+----------------------------------+
```

## 6 — Traceability (criterion → section)

- c1 scope & roles → §C1 (+ nav §C3.4, approvals §C4.2).
- c2 modules & MVP → §C2 (+ specs §5.1–5.2, flows F1–F6).
- c3 architecture & stack → §C3 (+ mobile needs §5.3).
- c4 milestones approved → §C4 (+ sign-off table; pending = needs review).

## 7 — Open questions for reviewers

1. Confirm role list (C1.4): any missing external role (vendor vs
   customer split)?
2. Confirm auth assumption (httpOnly cookie session) or supply the
   real identity provider.
3. Confirm stack (Next.js+TS+Tailwind) or mandate an existing one.
4. Approve milestones M1–M4 dates/owners, or propose replacements.

