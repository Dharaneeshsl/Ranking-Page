# 🏆 Ranking Platform — Gamified Leaderboard

A production-ready, full-stack platform for tracking member contributions,
awarding points and badges, and ranking members on a live gamified leaderboard.

**Stack:** FastAPI (Python 3.11) · MongoDB · React 19 + Vite 7 · Bootstrap 5 · Docker · nginx

---

## ✨ Features

| Area | What you get |
| --- | --- |
| **Leaderboard** | Live ranked leaderboard (public), medals, XP progress to next level |
| **Gamification** | 5 action types, 4 levels (Bronze → Platinum), 7 badges (Event Organizer, Sponsorship Champion, Top Contributor…) |
| **Contributions** | Server-side points (clients can't tamper), full ledger, per-member history & breakdowns |
| **Admin** | Cookie-session login, CSRF protection, role checks, edit/delete members, remove contributions |
| **Filters** | All time / week / month / year / custom date range + CSV export |
| **Dashboard** | Total members, total points, 7-day-active count, top contributor, stats by level |
| **Security** | bcrypt passwords, HttpOnly secure cookies, SameSite, CSRF tokens, rate limiting, security headers, CORS allow-list, non-root containers |
| **Observability** | `/api/health` liveness, `/api/ready` readiness, request IDs, structured logs |

---

## 🚀 Quick start (Docker — production-like)

```bash
cp .env.example .env        # fill in SECRET_KEY, admin + mongo passwords
docker compose up -d --build
```

Open **http://localhost:8080** and sign in with `ADMIN_EMAIL` / `ADMIN_PASSWORD`.

- Optional Mongo UI: `docker compose --profile tools up -d` → http://localhost:8081

---

## 🧑‍💻 Local development (no Docker)

**1. Backend** (needs MongoDB, or use the in-memory demo mode):

```bash
cd BackEnd
python -m venv venv && source venv/bin/activate
pip install -r requirements-dev.txt

cp ../.env.example .env            # optional; defaults work in dev
export MOCK_DB=1                   # zero-dependency in-memory Mongo (demo only!)
uvicorn main:app --reload          # http://localhost:8000/api/docs
```

**2. Frontend** (Vite proxies `/api` → `http://127.0.0.1:8000`):

```bash
cd FrontEnd/RankingPage
npm install
npm run dev                        # http://localhost:5173
```

Browser code never calls localhost directly — it uses relative `/api` URLs.

---

## 🔐 Admin credentials

The admin account is seeded on first startup from `ADMIN_EMAIL` / `ADMIN_PASSWORD`
in your `.env` file (see `.env.example`) — **never commit real credentials**.

For local development only, a dev account is created when no `.env` is present:
use the email `admin@example.com` and any password you set via `ADMIN_PASSWORD`
(copy `.env.example` → `.env` first).

---

## 🌐 API overview

Base path: `/api` — interactive docs at `/api/docs` (development only).

| Method | Endpoint | Auth | Description |
| --- | --- | --- | --- |
| `GET` | `/health`, `/ready` | public | liveness / readiness |
| `GET` | `/leaderboard` | public | ranked list (`time_frame=all\|week\|month\|year\|custom`, `start_date`, `end_date`, `limit`) |
| `GET` | `/leaderboard/export` | public | CSV download |
| `GET` | `/stats` | public | dashboard aggregates |
| `GET` | `/members` | public | all members |
| `POST` | `/members` | admin | create member |
| `GET` | `/members/{id}` | public | profile + rank + progress + history |
| `PUT` | `/members/{id}` | admin | override total points (logged as manual adjustment) |
| `DELETE` | `/members/{id}` | admin | delete member |
| `GET` | `/members/{id}/contributions` | public | contribution ledger |
| `POST` | `/members/{id}/contributions` | admin | add contribution (points computed server-side) |
| `DELETE` | `/members/{id}/contributions/{cid}` | admin | remove contribution + recalc |
| `POST` | `/points` | admin | award points by name (auto-creates member) |
| `POST` | `/auth/login` / `/auth/logout` | — / session | session auth |
| `GET` | `/auth/me`, `/auth/check` | session | current user + CSRF token |

> Mutating admin endpoints require the `X-CSRF-Token` header (returned by
> login/me) in addition to the `session_id` cookie.

---

## ✅ Points, levels & badges

| Action | Points |
| --- | --- |
| Attend Event | +10 |
| Upload Docs | +15 |
| Volunteer Task | +20 |
| Lead Event | +50 |
| Bring Sponsorship | +100 |

| Level | Points | Badges |
| --- | --- | --- |
| Bronze | 0+ | Bronze Member |
| Silver | 51+ | Silver Member |
| Gold | 151+ | Gold Member |
| Platinum | 301+ | Platinum Member, Top Contributor (500+), Event Organizer (lead 5 events), Sponsorship Champion (3 sponsorships) |

---

## 🧪 Tests & CI

```bash
cd BackEnd
pip install -r requirements-dev.txt
ruff check .        # lint
pytest              # 15 tests (auth, CSRF, points, leaderboard, stats, CSV)
```

GitHub Actions (`.github/workflows/ci.yml`) runs backend lint+tests,
frontend lint+build, and a Docker build on every push/PR.

---

## 🚢 Production checklist

1. Copy `.env.example` → `.env` and set strong `SECRET_KEY`, `ADMIN_PASSWORD`, Mongo credentials.
2. Put **nginx / a load balancer with TLS** in front; set `COOKIE_SECURE=1` and `FRONTEND_URLS=https://your-domain`.
3. Point `MONGODB_URI` at managed MongoDB (Atlas) or keep the bundled `mongo` service.
4. `docker compose up -d --build` → https://your-domain
5. Backups: snapshot the `mongodb_data` volume (or enable Atlas backups).
6. For multi-instance scaling, front the backend with a load balancer; the in-memory rate limiter is per-process (swap for a Redis-backed one if you need strict global limits).

---

## 📁 Repository layout

```text
BackEnd/                    FastAPI app (config, models, routes, middleware, tests)
FrontEnd/RankingPage/       React + Vite SPA (components, context, styles)
FrontEnd/RankingPage/deploy/nginx.conf
Dockerfile                  multi-stage: frontend build → backend → nginx web
docker-compose.yml          mongo + backend + frontend (+ optional mongo-express)
.env.example                all environment variables documented
.github/workflows/ci.yml    CI pipeline
```

## 📝 License

MIT — see [LICENSE](LICENSE).
