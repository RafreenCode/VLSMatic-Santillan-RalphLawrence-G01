# VLSMatic Database Reference

This document explains the PostgreSQL schema used by VLSMatic. Supabase hosts the database, while Django models and migrations remain the schema's source of truth.

## Maintenance requirement

This document must be updated whenever a pull request does any of the following:

- Creates, renames, or removes a model or database table
- Adds, renames, changes, or removes a model field
- Changes a primary key, foreign key, unique constraint, check constraint, or index
- Changes how sessions, permissions, roles, or stored records are used
- Adds Supabase-specific database behavior such as Row Level Security, functions, triggers, or storage metadata

The documentation update must be included in the same branch and pull request as the related model and migration changes. A database change is not considered complete until its migration, tests, and this reference agree.

## Schema ownership

VLSMatic uses Django's migration system to manage the `public` PostgreSQL schema. Schema changes should be expressed through Django models and migration files, then applied with:

```powershell
python manage.py makemigrations
python manage.py migrate
```

Do not make undocumented table or column changes manually in the Supabase Table Editor. Manual changes can cause the live schema and Django migration history to disagree.

## Current relationships

```text
accounts_user
├── accounts_user_groups ─────────── auth_group
├── accounts_user_user_permissions ─ auth_permission
├── django_admin_log
└── django_session (logical session ownership through encoded session data)

auth_group ── auth_group_permissions ── auth_permission
auth_permission ── django_content_type
django_admin_log ── django_content_type
```

`django_migrations` independently records the migration history used to construct the schema.

## Application table

### `accounts_user`

The central VLSMatic account table. It is generated from the custom `accounts.User` model, which extends Django's `AbstractUser`.

| Column | Purpose |
| --- | --- |
| `id` | Primary key for the account |
| `password` | Django password hash; never contains a plain-text password |
| `last_login` | Timestamp of the most recent successful login, when available |
| `is_superuser` | Grants all Django permissions without individual permission assignments |
| `username` | Unique login name |
| `first_name` | Optional given name shown in the profile and dashboard |
| `last_name` | Optional family name shown in the profile |
| `is_staff` | Allows access to Django Admin when combined with appropriate permissions |
| `is_active` | Controls whether the account is considered active without deleting it |
| `date_joined` | Timestamp recording when the account was created |
| `email` | Required unique email address used by registration and profile management |
| `role` | VLSMatic role: `user` or `admin`; controls dashboard routing and authorization |
| `contact_number` | Optional profile contact number |

Important constraints and indexes:

- Primary key on `id`
- Unique constraints and indexes on `username` and `email`
- Pattern indexes on `username` and `email` for efficient text lookups

Application behavior:

- Public registration always creates the `user` role.
- The `promote_admin` management command assigns the `admin` role and enables `is_staff`.
- Profile editing exposes only first name, last name, email, and contact number.
- Role, username, staff status, and superuser status cannot be changed through the public profile form.

## Authorization tables

These tables are created by Django's authentication framework. They are valid even when some currently contain no rows.

### `auth_group`

Stores named permission groups. Groups allow several permissions to be assigned as a reusable set. VLSMatic currently uses its custom `role` field for dashboard access, but Django Admin and future granular authorization can use groups.

Key rules:

- Primary key on `id`
- Unique group `name`

### `auth_permission`

Stores Django model permissions such as add, change, delete, and view. Django creates these records for installed models and uses them for staff and admin authorization.

Key columns:

- `name`: human-readable permission name
- `content_type_id`: model to which the permission applies
- `codename`: programmatic permission identifier

Key rules:

- Foreign key to `django_content_type`
- Unique combination of `content_type_id` and `codename`

### `accounts_user_groups`

Junction table connecting VLSMatic accounts to Django groups. It implements the many-to-many relationship between `accounts_user` and `auth_group`.

Key rules:

- Foreign key from `user_id` to `accounts_user`
- Foreign key from `group_id` to `auth_group`
- Unique combination of `user_id` and `group_id`, preventing duplicate membership

### `accounts_user_user_permissions`

Junction table connecting an individual account directly to Django permissions without requiring a group.

Key rules:

- Foreign key from `user_id` to `accounts_user`
- Foreign key from `permission_id` to `auth_permission`
- Unique combination of `user_id` and `permission_id`, preventing duplicate assignments

### `auth_group_permissions`

Junction table connecting Django groups to the permissions granted to those groups.

Key rules:

- Foreign key from `group_id` to `auth_group`
- Foreign key from `permission_id` to `auth_permission`
- Unique combination of `group_id` and `permission_id`, preventing duplicate assignments

## Django framework tables

### `django_session`

Stores database-backed login sessions. Django sends the browser only a session identifier; session data remains in PostgreSQL.

Key columns:

- `session_key`: primary key used by the session cookie
- `session_data`: signed and encoded session contents
- `expire_date`: expiration timestamp used to reject and clean up old sessions

An index on `expire_date` supports efficient session cleanup.

### `django_admin_log`

Records changes performed through Django Admin, providing an administrative audit history.

Key columns:

- `action_time`: when the action occurred
- `user_id`: administrator who performed the action
- `content_type_id`: affected model, when available
- `object_id` and `object_repr`: affected record identification
- `action_flag`: addition, change, or deletion category
- `change_message`: description of the change

The table has foreign keys to `accounts_user` and `django_content_type`.

### `django_content_type`

Catalogs installed Django models by application label and model name. Permissions and generic administrative references use this catalog to identify model types.

Key rules:

- Primary key on `id`
- Unique combination of `app_label` and `model`

### `django_migrations`

Records every Django migration applied to the database. Django consults this table to determine which schema operations remain pending.

Key columns:

- `app`: Django application that owns the migration
- `name`: migration identifier
- `applied`: timestamp when the migration completed

Do not edit or delete migration-history rows manually.

## Tables intentionally not present

The `dashboard` application has no models because it reads and presents account information without owning persistent data. No subnet, network-project, allocation, report, or export tables exist yet because those features are outside the current Account Feature milestone.

When those features are implemented, their models, relationships, constraints, indexes, ownership rules, and retention behavior must be added to this document in the same pull request.

## Supabase and security notes

- Supabase provides managed PostgreSQL; Django remains the only application data-access layer.
- Database credentials and connection URLs belong in `.env` locally and Vercel environment variables in production.
- The local application uses the Supabase Session Pooler on port `5432`.
- Serverless production uses the Transaction Pooler on port `6543` with prepared statements disabled.
- Row Level Security is not currently required because browsers do not query Supabase directly. RLS policies must be designed and documented before any direct Supabase client access is introduced.
- Production data must never be used as a test database.

## Verification checklist

After any database-related change:

```powershell
python manage.py makemigrations --check --dry-run
python manage.py migrate --check
python manage.py test
```

Also confirm that:

- The migration file is committed.
- The live migration is applied through an authorized process.
- Constraints and indexes match the model's integrity requirements.
- Forms and authorization rules expose only intended fields.
- `DATABASE.md` describes the resulting schema accurately.
