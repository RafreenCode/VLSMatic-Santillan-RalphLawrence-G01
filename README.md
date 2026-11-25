# VLSMatic

VLSMatic is an explainable and visual IPv4 subnet-planning system developed for CSIT327 – Information Management 2. The project uses full-stack Django: Django provides the backend, authentication, authorization, and server-rendered frontend through Django templates.

## Current project scope

The current milestone retains the Account Feature from Project Development 1 and adds the Project Development 2 core vertical slice: saved VLSM project planning and subnet allocation.

### Core feature: VLSM project planning

- Create, view, update, and delete user-owned network projects
- Add, edit, and delete named subnet requirements with validated host counts
- Validate IPv4 network boundaries and supported CIDR prefixes
- Generate largest-first VLSM allocations without overlaps
- Persist network addresses, masks, usable ranges, broadcasts, and capacities
- Reject plans that exceed the selected base network without partial updates
- Restrict regular users to their own records
- Provide administrators with read-only project oversight and live statistics
- Access the complete workflow through Django templates rather than Django Admin

### Standard account features

- Account registration with required-field, email, uniqueness, and password-confirmation validation
- Secure password hashing through Django authentication
- Login, POST-only logout, session handling, and clear user feedback
- Protected pages that redirect anonymous users to the login page
- Separate Regular User and Administrator dashboards
- Server-side role authorization that prevents cross-role dashboard access
- Profile viewing and editing, including persistent profile photos, for the currently authenticated user
- PostgreSQL persistence through Supabase
- Automated tests for registration, authentication, authorization, and profile ownership

Explain Mode, the visual Address Canvas, scenario comparison, reporting, and exports remain planned for later milestones.

## Technology stack

| Area | Technology |
| --- | --- |
| Application | Python 3.14 and Django 6.1 |
| Frontend | Django templates, HTML, and CSS |
| Database | PostgreSQL through Supabase |
| Image storage | Supabase Storage |
| Authentication | Django authentication and database-backed sessions |
| Static files | Django staticfiles and WhiteNoise |
| Hosting | Vercel |
| Testing | Django test framework |

React, Next.js, Vue, and SQLite are not used in the final application setup.

## Project structure

```text
accounts/             Account model, forms, authentication, profile, and admin tools
dashboard/            Role-based dashboard views, routes, authorization, and tests
network_projects/     Project CRUD, subnet requirements, allocation service, and tests
static/css/           Application styles
templates/accounts/   Registration, login, profile, and shared account templates
templates/dashboard/  Regular User and Administrator dashboard templates
vlsmatic/             Django project settings and root URL configuration
manage.py             Django management entry point
requirements.txt      Python dependencies
.env.example          Safe environment-variable template
```

Detailed explanations of every current database table, relationship, constraint, and maintenance requirement are available in [DATABASE.md](DATABASE.md).

## Prerequisites

Install the following before running the project locally:

- Git
- Python 3.14
- PostgreSQL client libraries or PostgreSQL 18 command-line tools on Windows
- Access to a PostgreSQL database or Supabase project

## Local setup

### 1. Clone the repository

```powershell
git clone https://github.com/RafreenCode/VLSMatic-Santillan-RalphLawrence-G01.git
cd "VLSMatic-Santillan-RalphLawrence-G01"
```

### 2. Create and activate a virtual environment

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### 3. Install dependencies

```powershell
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### 4. Create the local environment file

Copy `.env.example` to `.env`:

```powershell
Copy-Item .env.example .env
```

Update `.env` with local values:

```env
APP_ENV=local
DJANGO_SECRET_KEY=replace-with-a-generated-secret
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1
CSRF_TRUSTED_ORIGINS=http://localhost:8000
SECURE_SSL_REDIRECT=False
SECURE_HSTS_SECONDS=0
PROFILE_PHOTO_STORAGE=local
```

This default local mode is fully offline: it stores application data in
`local.sqlite3` and profile photos in `media/`. Both are ignored by Git. To
develop against PostgreSQL and Supabase instead, set `APP_ENV=remote`, set
`PROFILE_PHOTO_STORAGE=supabase`, and provide the database and Supabase values
shown in `.env.example`.

Generate a Django secret key locally with:

```powershell
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

Do not add quotation marks, angle brackets, or the variable name when copying values into an environment-variable field. URL-encode reserved password characters inside `DATABASE_URL`; for example, `#` becomes `%23`.

Never commit `.env`, database credentials, Django secret keys, or account passwords.

### 5. Apply database migrations

```powershell
python manage.py migrate
```

### 6. Run the application

```powershell
python manage.py runserver
```

Open `http://127.0.0.1:8000/` in a browser.

## Supabase configuration

Use the Supabase Session Pooler connection on port `5432` for local development. Use the Transaction Pooler connection on port `6543` for serverless Vercel environments. The application automatically disables prepared statements when it detects port `6543`.

A Supabase transaction-pooler URL generally follows this structure:

```text
postgresql://postgres.PROJECT_REFERENCE:URL_ENCODED_PASSWORD@POOLER_HOST:6543/postgres
```

Copy the connection details from the Supabase project dashboard. Do not copy real values into documentation or source files.

### Profile-photo storage

In the Supabase dashboard, open **Storage**, create a public bucket named `profile-photos`, and keep its file-size limit at or above 5 MB. The profile editor provides an interactive crop-and-zoom dialog; the server then validates the result, corrects its orientation, and stores it as an optimized 512-by-512 WebP image.

Copy the project URL and secret key from the Supabase project API settings into `.env` locally and into Vercel environment variables for production. The secret key is server-only: never place it in templates, JavaScript, screenshots, documentation values, or Git. Existing projects may temporarily use the legacy `SUPABASE_SERVICE_ROLE_KEY`; the application accepts it as a fallback while Supabase completes its key migration.

## Windows PostgreSQL client setup

If Windows Application Control blocks Psycopg's bundled binary, install the official PostgreSQL command-line tools and use the trusted system `libpq` implementation for the current PowerShell session:

```powershell
$env:Path = "C:\Program Files\PostgreSQL\18\bin;$env:Path"
$env:PSYCOPG_IMPL = "python"
python manage.py check
python manage.py migrate
python manage.py runserver
```

## Accounts and roles

VLSMatic currently defines two application roles:

- **Regular User:** assigned automatically during public registration; can access the Regular User dashboard and manage only their own profile.
- **Administrator:** assigned through a trusted management command; can access the Administrator dashboard and staff functionality.

Create a Django superuser:

```powershell
python manage.py createsuperuser
```

Assign an existing account the VLSMatic Administrator role:

```powershell
python manage.py promote_admin USERNAME
```

A Django superuser is a permission level, while Administrator is the custom VLSMatic application role. Assign both when an account needs access to Django administration and the VLSMatic Administrator dashboard.

## Application routes

| Route | Purpose |
| --- | --- |
| `/register/` | Create a Regular User account |
| `/login/` | Authenticate an existing account |
| `/logout/` | End the active session through a POST request |
| `/dashboard/` | Redirect to the dashboard for the authenticated role |
| `/dashboard/user/` | Regular User dashboard and group join-code panel |
| `/groups/join/` | Join an open workspace group via POST with a join code |
| `/console/` | Unified Administrator Console (Overview, Groups, Users) |
| `/console/groups/<slug>/` | Manage a workspace group, join code, members, and member projects |
| `/console/users/<username>/` | Regulate a user account and inspect their projects (read-only) |
| `/profile/` | View and update the authenticated user's profile |
| `/projects/` | List the signed-in user's own network projects |
| `/projects/new/` | Create a network project with live CIDR boundary validation |
| `/projects/<slug>/` | Manage requirements and inspect saved VLSM allocation results |
| `/admin/` | Redirects to the unified Administrator Console (`/console/`) |

## Testing

Run the complete Django test suite offline against an isolated local SQLite test database:

```powershell
$env:APP_ENV="local"
$env:DEBUG="True"
$env:SECURE_SSL_REDIRECT="False"
$env:PROFILE_PHOTO_STORAGE="local"
.\.venv\Scripts\python.exe manage.py test --noinput
```

To run the full suite including PostgreSQL row-locking concurrency tests against an isolated local PostgreSQL instance:

```powershell
$env:APP_ENV="remote"
$env:DATABASE_URL="postgresql://USER:PASSWORD@127.0.0.1:5432/postgres"
$env:DATABASE_SSL_REQUIRE="False"
$env:PROFILE_PHOTO_STORAGE="local"
$env:DEBUG="True"
$env:SECURE_SSL_REDIRECT="False"
$env:PSYCOPG_IMPL="python"
.\.venv\Scripts\python.exe manage.py test --noinput
```

Run Django configuration and migration drift checks:

```powershell
.\.venv\Scripts\python.exe manage.py check
.\.venv\Scripts\python.exe manage.py makemigrations --check --dry-run
```

Tests must always use an isolated test database and must never target production data.

## Vercel deployment

Automatic Git-based deployments are enabled through the connected Vercel project. Pushes and merged pull requests can therefore produce new Vercel deployments. Vercel Authentication is configured in the Vercel dashboard to protect deployments from public access while the project remains under development.

Production requires these Vercel environment variables:

```text
APP_ENV=remote
DJANGO_SECRET_KEY
DATABASE_URL
DATABASE_SSL_REQUIRE=True
DEBUG=False
ALLOWED_HOSTS
CSRF_TRUSTED_ORIGINS
SECURE_SSL_REDIRECT=True
SUPABASE_URL
SUPABASE_SECRET_KEY
SUPABASE_PROFILE_BUCKET=profile-photos
PROFILE_PHOTO_STORAGE=supabase
```

Production `DATABASE_URL` should use the Supabase Transaction Pooler on port `6543`.

## Development workflow

Do not develop features, hardening fixes, or documentation changes directly on `main` or `develop`.

1. Update your local `develop` branch (`git checkout develop; git pull origin develop`).
2. Create a focused work branch from `develop` (for example `hardening/data-integrity`, `test/pd3-regression-coverage`, `fix/login-validation`, or `docs/pd3-report-and-readme`).
3. Implement and test the change. If it modifies a model or migration, update [DATABASE.md](DATABASE.md) in the same branch.
4. Commit with a clear message and push the work branch to GitHub.
5. Open a pull request targeting `develop` and wait for GitHub Actions PostgreSQL checks to pass before merging.
6. Preserve merged work branches for audit history.
7. Once an entire increment is complete and verified on `develop`, open a release pull request from `develop` into `main`.

Keep `main` deployable at all times and never commit secrets, `.env` files, or local database artifacts.

## Project credit

- **Developer:** Ralph Lawrence Santillan
- **Section:** G01
- **Course:** CSIT327 – Information Management 2

## Repository

[VLSMatic-Santillan-RalphLawrence-G01](https://github.com/RafreenCode/VLSMatic-Santillan-RalphLawrence-G01)
