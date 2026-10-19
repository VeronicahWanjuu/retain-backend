# PesaSave API (Retain backend)

Django REST API for PesaSave, a budget and expense tracker for Kenyan university students. Amounts are in KES, and M-Pesa is a payment method.

**Live API:** https://pesasave-api.onrender.com/api
**Live app:** https://retain-frontend-three.vercel.app
**Frontend repo:** https://github.com/VeronicahWanjuu/retain-frontend
**Backend repo:** https://github.com/VeronicahWanjuu/retain-backend

## Grader login

| Role  | Username | Password |
|-------|----------|----------|
| Admin | `admin`  | `veronicah` |
| User  | Register on the live app | |

Note: the free Render server sleeps when idle. The first request can take up to a minute. Please wait and refresh once.

## Tech

Django, Django REST Framework, SimpleJWT (1 hour access token, 7 day refresh token), django-cors-headers, WhiteNoise, Gunicorn, dj-database-url. PostgreSQL (Neon) in production, SQLite locally.

## Run locally

You need Python 3.12.

```
git clone https://github.com/VeronicahWanjuu/retain-backend.git
cd retain-backend
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python manage.py migrate
set ADMIN_PASSWORD=ChooseAPassword123!
python manage.py seed
python manage.py runserver
```

On PowerShell, use `$env:ADMIN_PASSWORD="ChooseAPassword123!"` instead of `set`. On Mac or Linux use `source venv/bin/activate` and `export ADMIN_PASSWORD=...`.

The API runs at http://127.0.0.1:8000/api. Opening `/api/categories/` in the browser shows a 401 message until you log in. That is correct.

`seed` creates the starter categories (including "Uncategorized") and the `admin` user. It refuses to run without `ADMIN_PASSWORD`, so there is no default password in the code.

## Tests

```
python manage.py test
```

Expected: `Ran 18 tests ... OK`. They cover sign up and login, password and email rules, a user only seeing their own expenses, filters and sorting, pagination, budget status (within, approaching, over), and admin-only routes. Note: on Windows the run takes about 2 minutes because password hashing is slow.

## API

| Method | URL | Who | What |
|--------|-----|-----|------|
| POST | /api/auth/register/ | anyone | sign up |
| POST | /api/auth/login/ | anyone | get access and refresh tokens |
| POST | /api/auth/refresh/ | anyone | new access token |
| GET | /api/auth/me/ | user | who am I (includes role) |
| GET, POST | /api/expenses/ | user | list (paginated) or create |
| GET, PUT, DELETE | /api/expenses/:id/ | owner | one expense |
| GET, POST, PUT | /api/budget/?month=&year= | user | get or set the monthly budget |
| GET | /api/dashboard/?month=&year= | user | totals, budget status, by category, recent |
| GET | /api/categories/ | user | all categories |
| POST | /api/categories/ | admin | add a category |
| PUT, DELETE | /api/categories/:id/ | admin | rename or delete (expenses move to Uncategorized) |
| GET | /api/admin-dashboard/ | admin | platform insights |

Send the token as `Authorization: Bearer <access token>`.

**Expense list query options:**
`search`, `category`, `payment_method`, `start_date`, `end_date`, `min_amount`, `max_amount`, `sort` (`date`, `-date`, `amount`, `-amount`), `page`, `page_size` (default 10, max 50).
A bad value (for example `sort=banana` or a wrong date) returns 400 with a message instead of being ignored.

**Budget status:** `within` under 80% of the budget, `approaching` from 80% up to 100%, `over` at 100% or more.

## Environment variables

| Name | What it is |
|------|------------|
| `SECRET_KEY` | long random string |
| `DEBUG` | `False` in production |
| `ALLOWED_HOSTS` | the API host, no `https://` |
| `DATABASE_URL` | Postgres connection string (falls back to SQLite if missing) |
| `ADMIN_PASSWORD` | password for the seeded `admin` user |
| `CORS_ORIGINS` | the frontend URL, no trailing slash |
| `CSRF_ORIGINS` | the API URL with `https://` |

No secrets are stored in this repo.

## Deploy (Render)

- Build command: `pip install -r requirements.txt && python manage.py collectstatic --noinput && python manage.py migrate && python manage.py seed`
- Start command: `gunicorn retain.wsgi`
- Add the environment variables above, plus `PYTHON_VERSION=3.12.3`.

## Decisions

**Why Django.** I'm studying Python,  and Django gave me users, passwords, the admin and a database layer out of the box, so I could spend my time on the budget logic instead of rebuilding login. Django REST Framework made the API routes and pagination quick to set up.

**How users can't see each other's data.** Every expense query starts with `request.user`, so a user can only ever fetch their own rows. If someone asks for another person's expense by id, they get a 404 and not a "forbidden", so the id isn't even confirmed to exist. The `user` field is read only, so it can't be set from the request body. Admin routes use `IsAdminUser`.

**Deleting categories.** When an admin deletes a category, its expenses move to "Uncategorized" instead of being deleted. "Uncategorized" itself can't be deleted, so there's always somewhere for them to go.

**What I found hard.** Getting the budget thresholds right (80% and 100% of the budget) and keeping the numbers consistent between the dashboard and the budget page. I also lost time on token expiry, which is why the frontend refreshes the token quietly. And filters had to go back to page 1 whenever they changed.

**What's next.** Spending charts, recurring expenses (rent, data bundles) and CSV export.