# PesaSave API (Retain backend)

Django REST API for PesaSave, a budget and expense tracker for Kenyan students.

**Live API:** https://pesasave-api.onrender.com/api
**Live app:** https://retain-frontend-three.vercel.app
**Frontend repo:** https://github.com/VeronicahWanjuu/retain-frontend

**Admin login (for grading):** username `admin`, password `veronicah`
## Tech
Django, Django REST Framework, SimpleJWT, PostgreSQL (SQLite locally), WhiteNoise, Gunicorn.

## Run locally
    python -m venv venv
    venv\Scripts\activate
    pip install -r requirements.txt
    python manage.py migrate
    python manage.py seed
    python manage.py runserver
    python manage.py test

## API
| Method | URL | Who | What |
|---|---|---|---|
| POST | /api/auth/register/ | anyone | sign up |
| POST | /api/auth/login/ | anyone | get access + refresh tokens |
| POST | /api/auth/refresh/ | anyone | new access token |
| GET | /api/auth/me/ | user | who am I (includes role) |
| GET, POST | /api/expenses/ | user | list (paginated) / create |
| GET, PUT, DELETE | /api/expenses/:id/ | owner | one expense |
| GET, POST, PUT | /api/budget/?month=&year= | user | get / set monthly budget |
| GET | /api/dashboard/?month=&year= | user | totals, status, by category, recent |
| GET | /api/categories/ | user | all categories |
| POST | /api/categories/ | admin | add category |
| PUT, DELETE | /api/categories/:id/ | admin | rename / delete (expenses move to Uncategorized) |
| GET | /api/admin-dashboard/ | admin | platform insights |

Expense list filters: `search, category, payment_method, start_date, end_date, min_amount, max_amount, sort (date, -date, amount, -amount), page, page_size`.

## Decisions

**Why Django.** I study backend development in Python, and Django already gives you the hard parts: user accounts, password checks, an ORM and an admin site. Django REST Framework then made it quick to build the API and the JWT login. I didn't want to spend my time rebuilding login from scratch and then get it wrong.

**How users can't see each other's data.** Every expense and budget query is filtered by the logged-in user, for example `Expense.objects.filter(user=request.user)`. For a single expense I look it up by id and owner together, so if someone guesses another person's id they get a 404, not the data. The `user` field is read-only, so the server always sets it and a client can't send someone else's id. Admin routes use `IsAdminUser`, and I wrote tests that check a normal user gets 403 on them.

**Deleting a category.** If an admin deletes a category, the expenses in it move to a default "Uncategorized" category first, so nobody loses their data. "Uncategorized" itself can't be deleted.

**What I found hard.**
- Making the budget status feel right: I used "approaching" from 80% spent and "over" from 100%.
- Keeping the login alive: the access token expires after an hour, so the frontend quietly swaps it using the refresh token and retries the request.
- Search, filters and pagination together: changing any filter has to send you back to page 1, otherwise you can land on an empty page.

**What I'd add next.** Charts for spending by category, recurring expenses (like rent or airtime), and an export to CSV.