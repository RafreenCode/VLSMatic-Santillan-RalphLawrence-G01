# VLSMatic Database Reference

VLSMatic uses Django migrations as the source of truth for its PostgreSQL/Supabase schema. The application implements the six logical entities specified by the SDD: roles, users, projects, subnet requirements, calculation runs, and subnet allocations.

## Schema rules

- Apply changes with `python manage.py makemigrations` and `python manage.py migrate`; do not edit production tables manually.
- Update this document whenever a model, field, constraint, relationship, role, or storage behavior changes.
- Django framework authentication, permission, session, content-type, admin-log, and migration tables remain present in addition to the six application entities.

## Application relationships

```text
accounts_role 1 ----- M accounts_user
accounts_user 1 ----- M network_projects_networkproject
network_projects_networkproject 1 ----- M network_projects_subnetrequirement
network_projects_networkproject 1 ----- 0..1 network_projects_calculationrun
network_projects_calculationrun 1 ----- M network_projects_subnetallocation
network_projects_subnetrequirement 1 ----- 0..1 network_projects_subnetallocation
```

All parent relationships use database foreign keys. Deleting a user cascades through owned projects and planning data. Roles are protected from deletion while assigned to a user.

## `accounts_role`

| Column | Rules | Purpose |
| --- | --- | --- |
| `code` | Primary key, varchar(10) | Stable `user` or `admin` code |
| `name` | Required, varchar(50) | Display name |

The migration seeds Regular User and Administrator records. A database check constraint rejects any other role code. Public registration always assigns the Regular User role.

## `accounts_user`

This custom Django user table stores the normal `AbstractUser` authentication fields plus unique `email`, required `role_code`, optional `contact_number`, and optional `profile_photo_path`. `role_code` is a protected foreign key to `accounts_role`. Passwords contain Django hashes, never plaintext.

Profile images are stored locally or in the configured Supabase Storage bucket; PostgreSQL stores only their object path. Django's group and permission junction tables continue to support staff authorization.

## `network_projects_networkproject`

| Column | Rules | Purpose |
| --- | --- | --- |
| `id` | Primary key | Project identifier |
| `owner_id` | Required FK, cascade | Owning account |
| `name` | Required, varchar(120) | Owner-visible project name |
| `description` | Optional, max 1,000 | Planning notes |
| `base_network` | Required IPv4 | Aligned network address |
| `prefix_length` | Check 0 through 30 | Base CIDR prefix |
| `created_at`, `updated_at` | Required timestamps | Audit dates |

Project names are case-insensitively unique per owner. Application validation requires the address to be the boundary for its prefix. The owner/update index supports the project ledger.

## `network_projects_subnetrequirement`

| Column | Rules | Purpose |
| --- | --- | --- |
| `id` | Primary key | Requirement identifier |
| `project_id` | Required FK, cascade | Parent project |
| `name` | Required, varchar(100) | Subnet label |
| `required_hosts` | BIGINT, check at least 1 | Required usable hosts, including full `/0` capacity |
| `sort_order` | Non-negative | Stable input order |

Names are case-insensitively unique within a project. Allocation results are deliberately stored separately rather than mixed into requirement inputs.

## `network_projects_calculationrun`

| Column | Rules | Purpose |
| --- | --- | --- |
| `id` | Primary key | Run identifier |
| `project_id` | Required one-to-one FK, cascade | The project whose current plan this represents |
| `generated_at` | Required timestamp | Replacement time |

A project has no run before it has requirements and exactly one current run after successful allocation. Recalculation atomically replaces the old run; historical runs are outside the current scope.

## `network_projects_subnetallocation`

| Column | Rules | Purpose |
| --- | --- | --- |
| `id` | Primary key | Allocation identifier |
| `run_id` | Required FK, cascade | Current calculation run |
| `requirement_id` | Required one-to-one FK, cascade | Represented requirement |
| `network_address` | Required IPv4 | Calculated subnet boundary |
| `prefix_length` | Check 0 through 30 | Calculated prefix |
| `subnet_mask` | Required IPv4 | Dotted-decimal mask |
| `first_usable_address`, `last_usable_address` | Required IPv4 | Host range |
| `broadcast_address` | Required IPv4 | Broadcast address |
| `allocated_addresses` | Check at least 4 | Full block size including network and broadcast |

The allocation service verifies that the run and requirement share a project, processes requirements largest-first, selects the smallest fitting block, prevents overlap and overflow, and replaces all current allocations in one transaction.

Planning boundaries and generated records are read-only in Django Admin so manual administrative edits cannot bypass automatic recalculation. Project names and descriptions remain editable there.

## Verification

After database changes run:

```powershell
python manage.py makemigrations --check --dry-run
python manage.py migrate --check
python manage.py test
```

Tests must use an isolated database and must never target production data.
