# PFC — Patient Flow Controller Backend

Production-oriented backend for the Patient Flow Controller (PFC) front-end. It
provides authenticated queue issuance, inter-department transfers, attendance
sessions, live floor/room displays and PDF attendance reports for a single
on-premises facility.

The repository also contains the existing browser front-end (`index.html`,
`app.js`, `styles.css`). The front-end is intentionally unchanged; the
[frontend integration](#frontend-integration) section maps its current
localStorage flows onto this API.

---

## Contents

1. [Architecture](#architecture)
2. [Repository layout](#repository-layout)
3. [Quick start with Docker](#quick-start-with-docker)
4. [First login and API examples](#first-login-and-api-examples)
5. [Data model](#data-model)
6. [Business rules](#business-rules)
7. [HTTP API](#http-api)
8. [Realtime WebSocket API](#realtime-websocket-api)
9. [Attendance and PDF reports](#attendance-and-pdf-reports)
10. [Local development](#local-development)
11. [Tests](#tests)
12. [Operations](#operations)
13. [Configuration reference](#configuration-reference)
14. [Security notes](#security-notes)
15. [Frontend integration](#frontend-integration)
16. [Troubleshooting](#troubleshooting)

---

## Architecture

| Layer | Technology |
| --- | --- |
| HTTP API | FastAPI (ASGI, async) |
| Realtime | Native WebSocket endpoint with subscription rooms |
| Data access | SQLAlchemy 2.0 async ORM + `asyncmy` MySQL driver |
| Database | MySQL 8.0 with InnoDB, `utf8mb4_0900_ai_ci` |
| Migrations | Alembic (async `env.py`, offline `--sql` supported) |
| Auth | JWT bearer tokens (PyJWT, HS256 by default) |
| Passwords | Argon2id (`argon2-cffi`) with transparent rehash |
| Reports | ReportLab PDF generation |
| Deployment | Docker Compose with persistent MySQL volume and health checks |

All operations run inside a private Compose network. Only the API port is
published to the LAN; MySQL is not exposed.

### Why some extra tables exist

The brief requires four core tables. Two small auxiliary tables make the
requirements enforceable rather than aspirational:

- `rooms` — maps departments to physical floors and door/room codes so
  WebSocket subscriptions can be scoped by `floor:<n>` and `room:<CODE>`.
- `ticket_sequence` — a single-row allocator for the circular 1–999 ticket
  code. It is locked with `SELECT ... FOR UPDATE`, so concurrent kiosks cannot
  receive the same code.

---

## Repository layout

```text
.
├── app.js                     # existing front-end (not modified)
├── index.html
├── styles.css
├── docker-compose.yml
├── .env.example
├── README.md
└── backend/
    ├── Dockerfile             # production image (Python 3.12, non-root)
    ├── Dockerfile.test        # test image used by the `test` Compose profile
    ├── entrypoint.sh          # wait → migrate → seed → uvicorn
    ├── requirements.txt
    ├── requirements-dev.txt
    ├── pyproject.toml         # pytest / ruff configuration
    ├── alembic.ini
    ├── alembic/
    │   ├── env.py
    │   └── versions/20261110_0001_initial_schema.py
    ├── app/
    │   ├── main.py            # app factory, middleware, error handlers
    │   ├── api/               # dependencies, router, route modules, WS gateway
    │   ├── core/              # settings, security, time, constants, logging
    │   ├── db/                # engine/session, seed, readiness check
    │   ├── models/            # SQLAlchemy models and enums
    │   ├── schemas/           # Pydantic request/response contracts
    │   └── services/          # auth, users, sessions, tickets, realtime, reports
    └── tests/
        ├── conftest.py
        ├── helpers.py
        ├── test_*.py          # unit + integration suites
```

---

## Quick start with Docker

### Prerequisites

- Docker Desktop / Docker Engine with the Compose plugin (`docker compose`)
- A host on the facility LAN with a static IP or DNS name

### 1. Create the environment file

```bash
cp .env.example .env
```

Edit `.env` and replace every `CHANGE_ME` value. At minimum:

```dotenv
JWT_SECRET_KEY=<output of the command below>
MYSQL_PASSWORD=<strong database password>
MYSQL_ROOT_PASSWORD=<strong root password>
DATABASE_URL=mysql+asyncmy://pfc_user:<same database password>@mysql_db:3306/pfc
SEED_ADMIN_PASSWORD=<strong administrator password>
CORS_ORIGINS=http://<server-ip-or-hostname>:8000
```

Generate a JWT secret:

```bash
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

> **Passwords containing URL-reserved characters** (`@`, `:`, `/`, `?`, `#`,
> `%`) must be percent-encoded inside `DATABASE_URL`. The simplest option is a
> long alphanumeric password. Keep `MYSQL_PASSWORD` and the password in
> `DATABASE_URL` identical.

### 2. Validate the Compose configuration

```bash
docker compose config
```

### 3. Build and start

```bash
docker compose up -d --build
docker compose ps
```

Startup sequence inside `backend_api`:

1. Wait for MySQL to accept connections.
2. `alembic upgrade head` — create/upgrade the schema.
3. Seed the ticket sequence, default rooms and administrator (idempotent).
4. Start Uvicorn on `0.0.0.0:8000`.

Check readiness:

```bash
curl http://localhost:8000/health/live
curl http://localhost:8000/health/ready
```

`/health/ready` returns `503` until MySQL is reachable.

### 4. Optional demo staff

```bash
SEED_DEMO_DATA=true docker compose up -d backend_api
```

or seed manually:

```bash
docker compose exec backend_api python -m app.db.seed --demo
```

Demo accounts use `SEED_DEMO_PASSWORD`:

| Username | Role | Station |
| --- | --- | --- |
| `reception` | reception | Reception |
| `doctor.layla` | doctor | CMO |
| `doctor.omar` | doctor | CMO |
| `pharmacy.staff` | branch_staff | Pharmacy |
| `cashier.staff` | branch_staff | Cashier |

### 5. Stop / reset

```bash
docker compose down            # stop containers, keep data
docker compose down -v         # stop and delete the MySQL volume (destructive)
```

---

## First login and API examples

```bash
# Login
TOKEN=$(curl -s http://localhost:8000/api/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"username":"admin","password":"YOUR_SEED_ADMIN_PASSWORD"}' \
  | python -c "import sys,json; print(json.load(sys.stdin)['access_token'])")

# Who am I?
curl -s http://localhost:8000/api/auth/me -H "Authorization: Bearer $TOKEN"

# Issue a ticket at the kiosk (Reception)
curl -s http://localhost:8000/api/tickets/issue \
  -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' \
  -d '{"initial_destination":"Reception"}'

# Transfer ticket 1 to Cashier (Cashier is transfer-only)
curl -s http://localhost:8000/api/tickets/transfer \
  -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' \
  -d '{"ticket_code":1,"to_location":"Cashier","note":"Payment after consultation"}'

# Call the next ticket at a station
curl -s http://localhost:8000/api/tickets/next \
  -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' \
  -d '{"station":"Reception"}'

# Close a ticket
curl -s http://localhost:8000/api/tickets/done \
  -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' \
  -d '{"ticket_id":1}'

# Read a queue and a door display
curl -s http://localhost:8000/api/queues/Reception -H "Authorization: Bearer $TOKEN"
curl -s http://localhost:8000/api/queues/Reception/display -H "Authorization: Bearer $TOKEN"

# Attendance PDF (admin)
curl -s -o attendance.pdf \
  "http://localhost:8000/api/admin/reports/attendance.pdf?start_date=2026-11-01&end_date=2026-11-30" \
  -H "Authorization: Bearer $TOKEN"
```

All errors share one envelope:

```json
{
  "error": {
    "code": "CASHIER_NOT_INITIAL_DESTINATION",
    "message": "Cashier tickets cannot be created at the kiosk. Transfer a ticket to Cashier instead.",
    "details": null
  }
}
```

Validation failures use `code: "VALIDATION_ERROR"` and include a `details`
array. Requests may carry `X-Request-ID`; the same value is returned and logged.

---

## Data model

### `users`

| Column | Notes |
| --- | --- |
| `id` | Primary key |
| `username` | Unique, case-insensitive collation, validated pattern |
| `password_hash` | Argon2id |
| `full_name` | Display name |
| `role` | `admin`, `reception`, `doctor`, `branch_staff` |
| `assigned_station` | Required for non-admin roles; `NULL` for admins (CHECK constraint) |
| `default_shift_start` | Default `08:00`, used when a session starts without an explicit scheduled time |
| `is_active` | Disabled accounts cannot log in or use existing tokens |

### `employee_sessions`

| Column | Notes |
| --- | --- |
| `user_id` | FK → `users`, `ON DELETE RESTRICT` |
| `station` | Station worked during the session |
| `shift_start_scheduled` | Planned start in naive UTC |
| `start_session_at` / `end_session_at` | Actual shift boundaries |
| `is_late_start`, `late_minutes` | Computed beyond the grace period |
| `active_user_id` | Stored generated column: `user_id` when open, `NULL` when closed |

A unique index on `active_user_id` enforces **at most one open session per
employee** atomically, without relying on application locking.

### `tickets`

| Column | Notes |
| --- | --- |
| `ticket_code` | Circular `1..999`, CHECK constrained |
| `initial_destination` | CHECK rejects `Cashier` |
| `current_location` | Current department |
| `status` | `WAITING`, `SERVING`, `LATE`, `DONE` |
| `is_overbooked` | CMO daily-slot overbooking flag |
| `assigned_user_id` | Staff member serving/closing the ticket |
| `late_at` | When the ticket was marked late |
| `completed_at` | When it was closed |
| `active_ticket_code` | Stored generated column: code when not `DONE`, `NULL` when done |

Indexes include the required composite `(current_location, status)` and a
unique index on `active_ticket_code`. Completed codes can be reused later, but
two **active** tickets can never share a code.

### `ticket_transfers`

Immutable audit trail: `ISSUED`, `SERVING`, `TRANSFER`, `LATE`, `RECALL`,
`DONE`, with `from_location`, `to_location`, actor and optional note.

### `ticket_sequence`

Singleton row (`id = 1`) holding `next_ticket_code`. Issuance locks it with
`SELECT ... FOR UPDATE` for the duration of the allocation transaction.

### `rooms`

Seeded physical destinations used for realtime scoping. Each row has a unique
`code` (for example `ROOM-101`), display name, floor number and station.

---

## Business rules

### Circular ticket codes (1–999)

1. Lock the `ticket_sequence` row with `SELECT ... FOR UPDATE`.
2. Take `next_ticket_code` as the candidate.
3. Advance the sequence (`999 → 1`).
4. If an **active** ticket already uses the candidate, try the next value,
   up to 999 attempts.
5. Insert the ticket and commit. The row lock and the unique generated-column
   index together prevent duplicate active codes.

If all 999 codes are active, the API returns `503
TICKET_CODE_POOL_EXHAUSTED`.

### Cashier is transfer-only

- `POST /api/tickets/issue` rejects `Cashier` with
  `CASHIER_NOT_INITIAL_DESTINATION`.
- The database CHECK `ck_tickets_cashier_not_initial` is a second line of
  defence for direct SQL inserts.
- Cashier is reachable through `POST /api/tickets/transfer`.

### Queue order

`SERVING` first, then `WAITING` in creation order, then `LATE` ordered by the
time they were marked late (`late_at`). `DONE` tickets never appear in active
queues.

`POST /api/tickets/next` uses `FOR UPDATE SKIP LOCKED`, so two staff members
cannot pull the same next patient.

### Late handling

- `POST /api/tickets/late` sets `status = LATE` and `late_at = now`.
- Late tickets queue behind on-time waiting patients.
- `POST /api/tickets/recall` returns a late ticket to `WAITING`.
- The original creation time is preserved for audit/history.

### Attendance grace

A session is late only for the minutes **beyond** `ATTENDANCE_GRACE_MINUTES`
(default `15`). Starting 10 minutes after the scheduled shift records
`late_minutes = 0`; starting 37 minutes late records `22`.

The scheduled start comes from the employee's `users.default_shift_start`
unless an administrator explicitly supplies `shift_start_scheduled` when
starting a session. Employees cannot backdate their shift.

### CMO overbooking

For `CMO` tickets, the service counts today's CMO issuance in the facility
timezone and sets `is_overbooked` when the count reaches
`DOCTOR_DAILY_SLOT_LIMIT`. A receptionist may override with
`"is_overbooked": true|false`.

### Time and timezone

All `DATETIME` values are stored as **naive UTC**. Shift boundaries, report date
ranges and "today" are calculated in `FACILITY_TIMEZONE` (default
`Africa/Cairo`). Responses serialise timestamps as UTC ISO-8601 with a `Z`
suffix.

---

## HTTP API

Base path: `/api`. Every route except `/api/auth/login` requires
`Authorization: Bearer <token>`.

### Roles

| Role | Scope |
| --- | --- |
| `admin` | Everything, including users, history and reports |
| `reception` | Issue tickets, transfer, late/recall/done/next, all queues |
| `doctor` | Act on tickets at their assigned station; call next there |
| `branch_staff` | Act on tickets at their assigned station; call next there |

`admin` and `reception` may act on any station. `doctor` and `branch_staff`
are restricted to `assigned_station`. Admins must explicitly pass `station`
when starting a session or calling the next ticket.

### Endpoints

| Method | Path | Description |
| --- | --- | --- |
| `POST` | `/auth/login` | Authenticate and obtain a JWT |
| `GET` | `/auth/me` | Current account |
| `POST` | `/sessions/start` | Start a shift session and record lateness |
| `POST` | `/sessions/end` | End the open session |
| `GET` | `/sessions/me` | Paginated personal session history |
| `POST` | `/tickets/issue` | Issue the next circular code |
| `POST` | `/tickets/transfer` | Transfer a ticket to another destination |
| `POST` | `/tickets/late` | Mark a ticket late |
| `POST` | `/tickets/recall` | Return a late ticket to the waiting queue |
| `POST` | `/tickets/next` | Call the next on-time/late ticket |
| `POST` | `/tickets/done` | Close a ticket |
| `GET` | `/tickets/by-code/{code}` | Look up by circular code |
| `GET` | `/tickets/{id}` | Look up by database id |
| `GET` | `/queues` | Summary counts for every station |
| `GET` | `/queues/{station}` | Full active queue for a station |
| `GET` | `/queues/{station}/display` | Patient-facing door board |
| `GET` | `/meta/departments` | Destinations and kiosk eligibility |
| `GET` | `/meta/rooms` | Active floor/room/door definitions |
| `GET` | `/admin/users` | List accounts (admin) |
| `POST` | `/admin/users` | Create an account (admin) |
| `PATCH` | `/admin/users/{id}` | Update role, station, password, active flag (admin) |
| `GET` | `/admin/sessions` | Attendance history with filters (admin) |
| `GET` | `/admin/tickets` | Ticket history with filters (admin) |
| `GET` | `/admin/ticket-sequence` | Inspect the next circular code (admin) |
| `GET` | `/admin/reports/attendance.pdf` | Attendance/activity PDF (admin) |
| `GET` | `/health/live` | Liveness (outside `/api`) |
| `GET` | `/health/ready` | Readiness including MySQL (outside `/api`) |
| `WS` | `/ws/queues` | Realtime queue stream |

### Request contracts

```jsonc
// POST /api/tickets/issue
{ "initial_destination": "Reception", "is_overbooked": false }

// Ticket actions accept either locator; ticket_id wins if both are given.
{ "ticket_id": 12, "ticket_code": 87, "note": "optional" }

// POST /api/tickets/transfer adds:
{ "to_location": "Cashier" }

// POST /api/tickets/next
{ "station": "CMO" }          // required for admins, optional for staff

// POST /api/sessions/start
{ "shift_start_scheduled": "2026-11-11T06:00:00Z", "station": "CMO" }
```

Only administrators may send `shift_start_scheduled`. Other roles always use
their account's `default_shift_start`, which prevents employees from
backdating a shift to erase lateness.

`GET /api/admin/sessions` filters: `start_from`, `start_to`, `user_id`,
`station`, `active_only`, `limit`, `offset`.

`GET /api/admin/tickets` filters: `station`, `status`, `ticket_code`,
`created_from`, `created_to`, `limit`, `offset`.

Pagination responses use `{ "items": [...], "total": n, "limit": n, "offset": n }`.

---

## Realtime WebSocket API

Connect one socket per display/console:

```text
ws://<host>:8000/ws/queues?token=<JWT>&station=CMO&floor=1&room=ROOM-101
```

- `token` is required. It may also be sent as `Authorization: Bearer ...`, but
  the query parameter is the browser-friendly option.
- `station`, `floor` and `room` are optional initial subscriptions.
- The JWT is never written to access logs: query strings are excluded from the
  HTTP access log and Uvicorn's access log is disabled.
- Browser `Origin` must be in `WS_ORIGINS` (falls back to `CORS_ORIGINS`).

### Subscription rooms

| Target | Meaning |
| --- | --- |
| `station:<Location>` | Events for one department, e.g. `station:CMO` |
| `floor:<n>` | Events for any active room on that floor |
| `room:<CODE>` | Events for one physical room/door, e.g. `room:ROOM-101` |

Authorization:

- `admin` and `reception` may subscribe to anything.
- `doctor` / `branch_staff` may subscribe to their own station, floors that
  contain a room of their station, and rooms belonging to their station.
- Invalid targets return an `error` message; the socket stays open.

### Client → server messages

```jsonc
{ "action": "subscribe", "station": "CMO", "floor": 1, "room": "ROOM-101" }
{ "action": "unsubscribe", "station": "CMO" }
{ "action": "ping" }
```

Any text message must arrive within `WS_RECEIVE_TIMEOUT_SECONDS` (default 90)
or the server closes with code `4408`. Send a `ping` every 30 seconds.

### Server → client messages

| `type` | Purpose |
| --- | --- |
| `connected` | Identity, server time and empty subscription list |
| `subscriptions.updated` | Current targets |
| `queue.snapshot` | Door-board snapshot after a station subscription |
| `ticket.created` | New ticket issued |
| `ticket.transferred` | Ticket moved; includes `previous_location` |
| `ticket.serving` | Ticket called |
| `ticket.late` | Ticket marked late |
| `ticket.recalled` | Late ticket returned to waiting |
| `ticket.completed` | Ticket closed |
| `session.started` / `session.ended` | Station-level attendance change |
| `pong` | Heartbeat reply |
| `error` | `{ code, message }` |

Example ticket event:

```json
{
  "type": "ticket.transferred",
  "ticket": {
    "id": 12,
    "ticket_code": 87,
    "initial_destination": "Reception",
    "current_location": "Cashier",
    "status": "WAITING",
    "is_overbooked": false,
    "assigned_user_id": null,
    "late_at": null,
    "created_at": "2026-11-11T08:12:00Z",
    "completed_at": null
  },
  "station": "Cashier",
  "previous_location": "Reception",
  "emitted_at": "2026-11-11T08:44:10Z"
}
```

Close codes: `4401` missing/invalid token, `4403` origin rejected, `4408`
heartbeat timeout.

---

## Attendance and PDF reports

`GET /api/admin/reports/attendance.pdf` accepts:

| Query | Default | Notes |
| --- | --- | --- |
| `start_date` | first day of the current month | Facility-local inclusive date |
| `end_date` | today | Facility-local inclusive date |
| `station` | all departments | Filter by assigned station |
| `user_id` | all users | One employee |

The report excludes `admin` accounts, aggregates sessions, lateness and
completed tickets per employee, and renders an A4 landscape PDF with a summary
block and per-employee rows. Date ranges are limited to 366 days.

Headers on the response:

- `Content-Disposition: attachment; filename="pfc-attendance-YYYY-MM-DD-to-YYYY-MM-DD.pdf"`
- `X-Report-Rows: <employee count>`
- `Cache-Control: no-store`

---

## Local development

### Requirements

- Python **3.12** (the container image and the async MySQL driver target 3.12)
- MySQL 8.0, or SQLite for the test suite

### Setup

```bash
cd backend
python -m venv .venv
# Windows
.venv\Scripts\activate
# Linux/macOS
source .venv/bin/activate

pip install -r requirements-dev.txt
```

Create `backend/.env` (or keep the repository-root `.env`) with at least:

```dotenv
APP_ENV=development
JWT_SECRET_KEY=local-development-secret-key-at-least-32-characters
DATABASE_URL=mysql+asyncmy://pfc_user:pfc_password@127.0.0.1:3306/pfc
FACILITY_TIMEZONE=Africa/Cairo
DOCS_ENABLED=true
```

Run:

```bash
alembic upgrade head
python -m app.db.seed --demo
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

With `DOCS_ENABLED=true`, interactive documentation is available at
`http://localhost:8000/docs`.

### Migrations

```bash
alembic upgrade head
alembic downgrade base
alembic revision --autogenerate -m "describe change"
```

Offline SQL generation (no database connection or async driver required):

```bash
alembic upgrade head --sql
```

---

## Tests

The suite is split so fast unit tests run without any database dependency:

```bash
cd backend
pytest -m "not integration"   # time/grace, security, schemas, metadata, PDF
pytest -m integration         # service + HTTP tests on SQLite
pytest                        # everything
```

Requires Python 3.12 for the integration tests (`greenlet` is needed by
SQLAlchemy's asyncio bridge). They are skipped automatically when it is not
available.

To run against a dedicated MySQL database instead:

```bash
PFC_TEST_DATABASE_URL=mysql+asyncmy://pfc_user:pfc_password@127.0.0.1:3306/pfc_test \
  pytest -m integration
```

Using Docker (SQLite test database):

```bash
docker compose --profile test run --rm tests
```

The integration suite covers:

- circular rollover `999 → 1`, skipping active codes, code reuse after `DONE`
- Cashier blocked at issuance and reachable by transfer
- transfer audit trail and closed-ticket protection
- late-ticket ordering behind on-time patients and recall
- single open session, grace period, lateness minutes
- attendance aggregation and PDF generation
- JWT login, auth failures, error envelope, issue → transfer → queue flow

### Linting

```bash
ruff check app tests
ruff format --check app tests
```

---

## Operations

### Logs and health

```bash
docker compose logs -f backend_api
docker compose exec backend_api python -m app.db.wait_for_db
curl -fsS http://localhost:8000/health/ready
```

### Apply migrations after an image update

```bash
docker compose pull            # if using a registry
docker compose up -d --build
# The entrypoint runs `alembic upgrade head` on every start.
```

### Database backup and restore

```bash
# Backup
docker compose exec -T mysql_db sh -c \
  'exec mysqldump --single-transaction --routines -u"$MYSQL_USER" -p"$MYSQL_PASSWORD" "$MYSQL_DATABASE"' \
  > "pfc-$(date +%F).sql"

# Restore
docker compose exec -T mysql_db sh -c \
  'exec mysql -u"$MYSQL_USER" -p"$MYSQL_PASSWORD" "$MYSQL_DATABASE"' < pfc-YYYY-MM-DD.sql
```

Schedule backups off-host; the named volume protects against container
recreation, not disk loss.

### Change an administrator password

Use the API (preferred):

```bash
curl -X PATCH http://localhost:8000/api/admin/users/1 \
  -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' \
  -d '{"password":"NewStrongPassword123!"}'
```

`SEED_ADMIN_PASSWORD` is only used when the seed creates the account. Changing
it later does **not** reset an existing password.

### Rotate the JWT secret

1. Update `JWT_SECRET_KEY` in `.env`.
2. `docker compose up -d backend_api`.
3. All existing sessions are invalidated; users log in again.

### Timezone / clock

Keep the Docker host clock synchronised (NTP). Set `FACILITY_TIMEZONE` to the
IANA zone used by staff. MySQL runs with `--default-time-zone=+00:00` and the
application stores UTC, so changing the host timezone does not shift data.

---

## Configuration reference

All settings are read from environment variables (and `.env`). Names are
case-insensitive.

| Variable | Default | Purpose |
| --- | --- | --- |
| `APP_ENV` | `production` | `production`, `staging`, `development`, `test` |
| `APP_NAME`, `APP_VERSION` | `PFC Backend`, `1.0.0` | Service metadata |
| `DEBUG` | `false` | Debug flag |
| `DOCS_ENABLED` | `false` | Serve `/docs`, `/redoc`, `/openapi.json` |
| `API_PREFIX` | `/api` | HTTP API prefix |
| `LOG_LEVEL` | `INFO` | Root log level |
| `JWT_SECRET_KEY` | placeholder | **Required**, 32+ chars, no placeholder markers in production |
| `JWT_ALGORITHM` | `HS256` | `HS256`, `HS384`, `HS512` |
| `JWT_ISSUER`, `JWT_AUDIENCE` | `pfc-backend`, `pfc-clients` | Token validation |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `480` | 8-hour shift token |
| `DATABASE_URL` | MySQL DSN | `mysql+asyncmy://...`; `mysql://` and `mysql+pymysql://` are normalised |
| `DATABASE_ECHO` | `false` | Log SQL |
| `DB_POOL_SIZE` | `10` | MySQL connection pool |
| `DB_MAX_OVERFLOW` | `20` | Pool overflow |
| `DB_POOL_RECYCLE_SECONDS` | `3600` | Recycle idle connections |
| `CORS_ORIGINS` | localhost origins | Comma-separated browser origins |
| `WS_ORIGINS` | empty | Comma-separated WebSocket origins; falls back to CORS |
| `WS_RECEIVE_TIMEOUT_SECONDS` | `90` | Heartbeat timeout |
| `MAX_WS_SUBSCRIPTIONS` | `20` | Per-socket subscription cap |
| `FACILITY_TIMEZONE` | `Africa/Cairo` | Business-day timezone |
| `ATTENDANCE_GRACE_MINUTES` | `15` | Grace before lateness counts |
| `DOCTOR_DAILY_SLOT_LIMIT` | `20` | CMO overbooking threshold |
| `SEED_ON_START` | `true` | Run the idempotent seed in the container entrypoint |
| `SEED_DEMO_DATA` | `false` | Include demo staff when seeding |
| `SEED_ADMIN_USERNAME` | `admin` | Seed administrator username |
| `SEED_ADMIN_PASSWORD` | placeholder | Seed administrator password |
| `SEED_ADMIN_FULL_NAME` | `System Administrator` | Seed administrator display name |
| `SEED_DEMO_PASSWORD` | placeholder | Password for demo accounts |
| `BACKEND_PORT` | `8000` | Host port published by Compose |

Production/staging startup **fails fast** if `JWT_SECRET_KEY` is short or still
contains a placeholder marker (`change-me`, `example`, etc.).

---

## Security notes

- Argon2id password hashing; invalid usernames still perform a dummy verify to
  reduce timing differences.
- JWTs are signed, audience/issuer scoped and require `sub`, `exp`, `iat`,
  `iss`, `aud`. Expired and tampered tokens return a stable error code.
- Disabled accounts are rejected on every request, even with a valid token.
- Role checks are centralised in `app/api/deps.py`; station checks live in the
  ticket service so direct service calls cannot bypass them.
- The API does not log query strings (WebSocket tokens) or request bodies.
- Security headers: `X-Content-Type-Options`, `X-Frame-Options`,
  `Referrer-Policy`, `Permissions-Policy`, and `Cache-Control: no-store` for API
  responses.
- CORS is opt-in; add the exact LAN origins used by displays and kiosks.
- The container runs as UID/GID `10001`, not root; MySQL is not published.
- Cashier issuance is blocked in the API **and** by a database CHECK
  constraint.
- Active-code and active-session uniqueness are enforced by the database, not
  just by application code.

For a hardened deployment, also terminate TLS at a reverse proxy (Caddy, Nginx
or the facility gateway), restrict the API port to the LAN, and keep `.env`
readable only by the deployment account.

---

## Frontend integration

The current `app.js` persists everything in `localStorage`. To use this
backend, replace those flows with the following calls (all need the bearer
token):

| Front-end action | Backend call |
| --- | --- |
| Login | `POST /api/auth/login` → store `access_token` |
| Load departments/kiosk buttons | `GET /api/meta/departments` |
| Issue a ticket | `POST /api/tickets/issue` |
| Display a queue | `GET /api/queues/{station}` |
| Door display | `GET /api/queues/{station}/display` |
| Transfer | `POST /api/tickets/transfer` |
| Mark late / recall | `POST /api/tickets/late`, `POST /api/tickets/recall` |
| Call next patient | `POST /api/tickets/next` |
| Complete visit | `POST /api/tickets/done` |
| Attendance clock-in/out | `POST /api/sessions/start`, `POST /api/sessions/end` |
| Live updates | `WS /ws/queues?token=...&station=...` |
| Attendance report | `GET /api/admin/reports/attendance.pdf` |

Notes for the integration:

- The front-end treats late as a UI flag on `WAITING`; the backend exposes it
  as the explicit `LATE` status. Render `LATE` with the same visual treatment
  and use `late_at` for ordering context.
- The front-end destination list includes `CMO`; the backend keeps it as a
  first-class station and block only `Cashier` at issuance.
- The front-end grace period is 15 minutes, matching the backend default.
- Each kiosk/display should use its own service account and a short-lived token
  or a long-lived reception token stored according to facility policy.

---

## Troubleshooting

| Symptom | Cause / fix |
| --- | --- |
| `JWT_SECRET_KEY must be at least 32 characters` | Generate a longer secret in `.env` |
| `JWT_SECRET_KEY is using an insecure placeholder` | Replace the example secret before production |
| Backend restarts with `MySQL did not become ready` | Check `docker compose logs mysql_db`; verify `MYSQL_*` and volume permissions |
| `Access denied for user` | `DATABASE_URL` password does not match `MYSQL_PASSWORD`, or contains unencoded reserved characters |
| `TICKET_CODE_POOL_EXHAUSTED` | 999 tickets are still active; close stale tickets or inspect `/api/admin/tickets?status=WAITING` |
| `ACTIVE_SESSION_EXISTS` | The employee already has an open session; call `/api/sessions/end` first |
| `CASHIER_NOT_INITIAL_DESTINATION` | Expected: issue to another department, then transfer to Cashier |
| WebSocket closes with `4401` | Missing/expired token; log in again and reconnect |
| WebSocket closes with `4408` | No message within the heartbeat window; send `{"action":"ping"}` every 30s |
| WebSocket closes with `4403` | Add the display origin to `WS_ORIGINS`/`CORS_ORIGINS` |
| Reports show a different day | Check `FACILITY_TIMEZONE`; storage is UTC, reports use facility-local dates |
| `greenlet` missing during local tests | Use Python 3.12 and `pip install -r requirements-dev.txt` |
| Docker health check fails after startup | Migrations/seed can take time on first boot; inspect `docker compose logs backend_api` |

---

## License

Proprietary — Egypt Healthcare Authority / Patient Flow Controller deployment.
