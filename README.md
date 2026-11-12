# VLSMatic

VLSMatic is an explainable and visual IPv4 subnet-planning system developed for CSIT327 – Information Management 2. The project uses full-stack Django: Django provides the backend, authentication, authorization, and server-rendered frontend through Django templates.

## Current project scope

The current milestone implements the Account Feature required for Project Development 1:

- Account registration with required-field, email, uniqueness, and password-confirmation validation
- Secure password hashing through Django authentication
- Login, POST-only logout, session handling, and clear user feedback
- Protected pages that redirect anonymous users to the login page
- Separate Regular User and Administrator dashboards
- Server-side role authorization that prevents cross-role dashboard access
- Profile viewing and editing, including persistent profile photos, for the currently authenticated user
- PostgreSQL persistence through Supabase
- Automated tests for registration, authentication, authorization, and profile ownership

Subnet calculation, network-project management, reporting, and export features are planned for later milestones and are not part of the current implementation.

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
DJANGO_SECRET_KEY=replace-with-a-generated-secret
DEBUG=True
DATABASE_URL=postgresql://database-user:url-encoded-password@database-host:5432/postgres
DATABASE_SSL_REQUIRE=True
ALLOWED_HOSTS=localhost,127.0.0.1
CSRF_TRUSTED_ORIGINS=http://localhost:8000
SECURE_SSL_REDIRECT=False
SECURE_HSTS_SECONDS=0
SUPABASE_URL=https://your-project-reference.supabase.co
SUPABASE_SECRET_KEY=sb_secret_replace-with-your-secret-key
SUPABASE_PROFILE_BUCKET=profile-photos
```

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

In the Supabase dashboard, open **Storage**, create a public bucket named `profile-photos`, and keep its file-size limit at or above 5 MB. The application validates uploads as JPEG, PNG, or WebP before sending them to this bucket.

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
| `/dashboard/user/` | Regular User dashboard |
| `/dashboard/administrator/` | Administrator dashboard |
| `/profile/` | View and update the authenticated user's profile |
| `/admin/` | Django administration for authorized staff |

## Testing

Run the complete test suite:

```powershell
python manage.py test
```

Run Django configuration and migration checks:

```powershell
python manage.py check
python manage.py makemigrations --check --dry-run
```

Tests must use an isolated test database and must not modify production data.

## Vercel deployment

Automatic Git-based deployments are enabled through the connected Vercel project. Pushes and merged pull requests can therefore produce new Vercel deployments. Vercel Authentication is configured in the Vercel dashboard to protect deployments from public access while the project remains under development.

Production requires these Vercel environment variables:

```text
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
```

Production `DATABASE_URL` should use the Supabase Transaction Pooler on port `6543`.

## Development workflow

Do not develop new features or meaningful changes directly on `main`.

1. Update the local `main` branch.
2. Create a focused branch such as `feature/subnet-calculator`, `fix/login-validation`, or `docs/setup-guide`.
3. Implement and test the change. If it changes a model or migration, update [DATABASE.md](DATABASE.md) in the same branch.
4. Commit with a clear message.
5. Push the branch to GitHub.
6. Open a pull request targeting `main`.
7. Review and verify the pull request before merging.

Keep `main` deployable and never commit secrets or generated environment files.

## Project credit

- **Developer:** Ralph Lawrence Santillan
- **Section:** G01
- **Course:** CSIT327 – Information Management 2

## Repository

[VLSMatic-Santillan-RalphLawrence-G01](https://github.com/RafreenCode/VLSMatic-Santillan-RalphLawrence-G01)
