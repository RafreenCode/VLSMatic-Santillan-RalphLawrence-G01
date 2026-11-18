# Project Development 2 Implementation Plan

## Project Information

- **System:** VLSMatic: An Explainable and Visual IPv4 Subnet Planning System
- **Developer:** Ralph Lawrence Santillan
- **Section:** G01
- **Course:** CSIT327 - Information Management 2
- **Increment:** Project Development 2 - Core Feature (Vertical Slice)
- **Repository:** `VLSMatic-Santillan-RalphLawrence-G01`

## 1. Core Feature

The PD2 core feature is **VLSM Project Planning and Subnet Allocation**.

A logged-in user will be able to create a network project, enter subnet requirements, generate a largest-first VLSM allocation, and view or manage the saved results. The implementation will work through every application layer:

- **Database:** Django models and migrations persisted in PostgreSQL/Supabase
- **Backend:** Django forms, views, services, authorization, messages, and URL routes
- **Frontend:** Django templates that support the complete user workflow

The completed workflow will be:

1. The user logs in.
2. The user opens **My Network Projects**.
3. The user creates a project with a name, base IPv4 network, prefix, and optional description.
4. The user adds one or more named subnet requirements with required host counts.
5. The user generates the VLSM allocation.
6. The system validates capacity and allocates subnets from largest to smallest.
7. The system saves and displays the calculated subnet details.
8. The user can reopen, edit, recalculate, or delete the project and its requirements.

### Included in PD2

- Network project CRUD
- Subnet requirement CRUD
- IPv4 and CIDR validation
- Largest-first VLSM allocation
- Persistent allocation results
- Per-user record ownership
- Role-aware dashboard integration
- Clear validation, success, and error messages
- Automated tests

### Deferred to Future Increments

- Explain Mode
- Visual address canvas
- Scenario comparison
- Search and advanced filtering
- CSV and PDF exports
- Project sharing and collaboration

## 2. Acceptance Criteria

The feature is complete when all of the following are true:

- A logged-in regular user can complete the entire project-to-allocation workflow through the UI.
- Projects, requirements, and calculated results persist in PostgreSQL/Supabase.
- Create, read, update, and delete operations work where applicable.
- Invalid IPv4 networks, prefixes, and host counts produce clear validation errors.
- Requirements that cannot fit in the selected base network are rejected without partial data changes.
- Every project is linked to the user who created it.
- Regular users can view and modify only their own projects.
- Administrators receive the approved administrative overview of project records.
- Project links and summaries appear on the correct role dashboards.
- The existing account, login/logout, dashboard, and profile features continue to work.
- Automated tests cover calculations, validation, persistence, ownership, and role access.

## 3. Proposed Application Structure

Create a focused Django application named `network_projects`:

```text
network_projects/
|-- __init__.py
|-- admin.py
|-- apps.py
|-- forms.py
|-- models.py
|-- services.py
|-- urls.py
|-- views.py
|-- migrations/
`-- tests/
    |-- __init__.py
    |-- test_models.py
    |-- test_forms.py
    |-- test_allocation.py
    `-- test_views.py

templates/network_projects/
|-- project_list.html
|-- project_form.html
|-- project_detail.html
|-- project_confirm_delete.html
|-- requirement_form.html
`-- requirement_confirm_delete.html
```

The calculation logic will be placed in `services.py` so that it can be tested independently from HTTP views and templates.

## 4. Database Design

### 4.1 NetworkProject

The `NetworkProject` model represents one saved VLSM planning project.

| Field | Proposed type | Purpose |
| --- | --- | --- |
| `id` | BigAutoField | Primary key |
| `owner` | ForeignKey to User | User who owns the project |
| `name` | CharField | Required project name |
| `description` | TextField | Optional project notes |
| `base_network` | GenericIPAddressField | Normalized IPv4 network address |
| `prefix_length` | PositiveSmallIntegerField | Base CIDR prefix |
| `created_at` | DateTimeField | Creation timestamp |
| `updated_at` | DateTimeField | Last-update timestamp |

Planned rules:

- `owner` uses `settings.AUTH_USER_MODEL`.
- Deleting a user deletes or handles owned projects according to the approved ERD.
- The base network must be IPv4.
- The prefix must be within the supported range, initially `/8` through `/30`.
- Project names are required and trimmed.
- An index will support listing projects by owner and update time.

### 4.2 SubnetRequirement

The `SubnetRequirement` model stores both a requested subnet and its latest calculated allocation.

| Field | Proposed type | Purpose |
| --- | --- | --- |
| `id` | BigAutoField | Primary key |
| `project` | ForeignKey to NetworkProject | Parent project |
| `name` | CharField | Required subnet name |
| `required_hosts` | PositiveIntegerField | Requested usable host count |
| `sort_order` | PositiveIntegerField | Stable display order |
| `network_address` | GenericIPAddressField | Calculated subnet address |
| `prefix_length` | PositiveSmallIntegerField | Calculated CIDR prefix |
| `subnet_mask` | GenericIPAddressField | Calculated mask |
| `first_usable_address` | GenericIPAddressField | First usable host |
| `last_usable_address` | GenericIPAddressField | Last usable host |
| `broadcast_address` | GenericIPAddressField | Broadcast address |
| `allocated_capacity` | PositiveIntegerField | Number of usable allocated hosts |

Calculated fields will allow blank or null values before the first successful calculation.

Planned rules:

- Deleting a project cascade-deletes its requirements.
- `required_hosts` must be at least 1.
- A project cannot have duplicate subnet names.
- A database constraint will enforce positive host counts.
- An index will support requirements ordered within a project.

### 4.3 Relationships

```text
accounts.User
    1
    |
    | owns
    many
network_projects.NetworkProject
    1
    |
    | contains
    many
network_projects.SubnetRequirement
```

All schema additions, constraints, indexes, and ownership behavior must also be documented in `DATABASE.md`.

## 5. VLSM Allocation Logic

The allocation service will use Python's standard `ipaddress` module.

### Calculation Process

1. Parse and validate the project's base IPv4 network.
2. Reject projects with no subnet requirements.
3. Sort requirements by required hosts from largest to smallest.
4. Add the network and broadcast addresses to each host requirement.
5. Round the required address count up to the next power of two.
6. Derive the appropriate CIDR prefix.
7. Allocate the next correctly aligned subnet within the base network.
8. Calculate the subnet mask, first usable address, last usable address, broadcast address, and usable capacity.
9. Confirm that every allocation is inside the base network and does not overlap.
10. Save all calculated fields inside `transaction.atomic()`.

If the requirements do not fit, the service will raise a controlled validation error. No partial allocation will be saved.

### Recalculation Behavior

Changing the base network, prefix, required host count, or requirement list can make saved results stale. Such changes will clear the affected calculated fields or explicitly mark the project as needing recalculation. The UI must never present stale results as current.

## 6. Forms and Validation

### NetworkProjectForm

Validate:

- Required and trimmed project name
- Valid IPv4 address or network
- IPv6 rejection
- Supported prefix range
- Correct network boundary behavior
- Optional description length

The form may accept CIDR input such as `192.168.10.0/24` or separate address and prefix fields. The stored values must always be normalized consistently.

### SubnetRequirementForm

Validate:

- Required and trimmed subnet name
- Host count is an integer
- Host count is greater than zero
- Host count can fit within the project's base network
- Subnet name is unique within the current project

### Business Validation

The allocation service must also validate the complete set of requirements because individually valid requirements may not fit when combined.

Expected messages include:

- `Project created successfully.`
- `Subnet requirement added.`
- `Allocation generated successfully.`
- `The subnet requirements exceed the selected network's capacity.`
- `Project updated. Generate the allocation again to refresh the results.`
- `Project deleted.`

## 7. Views and URL Routes

| Route | View purpose | Methods |
| --- | --- | --- |
| `/projects/` | List the current user's projects | GET |
| `/projects/new/` | Create a project | GET, POST |
| `/projects/<id>/` | View project, requirements, and results | GET |
| `/projects/<id>/edit/` | Update a project | GET, POST |
| `/projects/<id>/delete/` | Confirm and delete a project | GET, POST |
| `/projects/<id>/requirements/new/` | Add a subnet requirement | GET, POST |
| `/requirements/<id>/edit/` | Update a requirement | GET, POST |
| `/requirements/<id>/delete/` | Confirm and delete a requirement | GET, POST |
| `/projects/<id>/calculate/` | Generate or regenerate allocations | POST |

All routes require authentication. Delete and calculate actions must change state only through POST requests with CSRF protection.

## 8. Authorization and Record Ownership

Regular users must never be able to retrieve another user's project by changing a URL. Owned objects will be loaded with ownership included in the query, for example:

```python
project = get_object_or_404(
    NetworkProject,
    pk=project_id,
    owner=request.user,
)
```

The same ownership chain applies to subnet requirements through `requirement.project.owner`.

### Regular User

- Sees **My Network Projects** on the regular-user dashboard.
- Can create, view, update, calculate, and delete only their own projects.
- Cannot view or mutate another user's project or requirements.

### Administrator

- Sees total project and requirement counts on the administrator dashboard.
- Receives a read-only project overview unless the approved SDD explicitly grants broader management authority.
- Does not silently bypass project ownership for edit or delete operations.

## 9. Frontend Implementation

### Project List

- Page title and short feature description
- New-project action
- Project name, base network, requirement count, and update time
- Empty state for first-time users
- View and edit actions

### Project Form

- Persistent labels and help text
- Field-level validation errors
- Clear IPv4/CIDR examples
- Save and cancel actions

### Project Detail

This is the primary vertical-slice page. It will contain:

- Project name, description, and base network
- Edit and delete controls
- Subnet requirements table
- Add, edit, and delete requirement controls
- Generate or regenerate allocation button
- Capacity or validation message
- Saved allocation-results table

The allocation table will display:

- Subnet name
- Required hosts
- Allocated capacity
- Network/CIDR
- Subnet mask
- First usable address
- Last usable address
- Broadcast address

### Dashboard Integration

The regular-user dashboard will show:

- Project count
- Recent projects
- **New Project** action
- **View All Projects** action

The administrator dashboard will show approved system-level project statistics and a read-only overview.

All pages must remain responsive and keyboard accessible, with visible focus styles and status messages that do not rely on color alone.

## 10. Test Plan

The existing PD1 tests must remain green. The current baseline is 32 passing tests in local mode.

### Model Tests

- Project creation and user relationship
- Requirement creation and project relationship
- Cascade deletion behavior
- Positive-host database constraint
- Unique subnet name within a project
- Model string representations

### Form Tests

- Required project fields
- Invalid IPv4 input
- IPv6 rejection
- Invalid prefix range
- Valid CIDR normalization
- Missing subnet name
- Zero and negative host counts
- Duplicate subnet name
- Oversized individual requirement

### Allocation Tests

- Correct largest-first ordering
- Correct prefix selection for common host counts
- Correct network address and subnet mask
- Correct first and last usable addresses
- Correct broadcast address
- Exact-fit allocation
- Insufficient-address-space failure
- No overlapping allocations
- Results remain inside the base network
- Failed calculation does not partially update saved results

### View and Authorization Tests

- Anonymous users redirect to login
- User can complete project CRUD
- User can complete requirement CRUD
- Successful calculation persists results
- Project list includes only the current user's projects
- User A cannot view User B's project
- User A cannot update, calculate, or delete User B's project
- Delete and calculate endpoints reject GET mutations
- Administrator receives the intended overview
- Success and error messages are rendered

### Verification Commands

For offline local verification:

```powershell
$env:APP_ENV='local'
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py migrate
python manage.py test
```

Before submission, apply the committed migrations to the authorized Supabase PostgreSQL database and test the deployed workflow.

## 11. Git Branch and Pull Request Plan

The repository currently has a stable `main` branch but no `develop` branch. PD2 development must not occur directly on `main`.

### Create the Integration Branch

```powershell
git switch main
git pull --ff-only origin main
git switch -c develop
git push -u origin develop
```

### Feature Branch 1: Project CRUD

Branch:

```text
feature/network-project-crud
```

Create it from `develop`. Implement:

- `network_projects` app
- Models and migrations
- Project CRUD
- Requirement CRUD
- Ownership authorization
- Base templates
- Model, form, and CRUD tests
- Database documentation

Suggested commits:

```text
Add network project and subnet requirement models
Add owned network project CRUD views
Add subnet requirement validation and tests
Document network project database schema
```

Open and merge:

```text
feature/network-project-crud -> develop
```

Do not delete the merged feature branch.

### Feature Branch 2: VLSM Allocation

Branch:

```text
feature/vlsm-allocation
```

Create it from the updated `develop`. Implement:

- Largest-first allocation service
- Transactional persistence of results
- Generate/regenerate action
- Allocation-results interface
- Dashboard and navigation integration
- Allocation and authorization tests
- README updates

Suggested commits:

```text
Add largest-first VLSM allocation service
Persist calculated subnet allocation results
Add allocation results interface and messages
Integrate network projects with role dashboards
Add VLSM allocation and ownership tests
Update README for the PD2 core feature
```

Open and merge:

```text
feature/vlsm-allocation -> develop
```

Do not delete the merged feature branch.

### Final Increment Pull Request

After all checks and manual tests pass, open and merge:

```text
develop -> main
```

This workflow satisfies the required minimum of:

- Two feature branches
- Two merged pull requests into `develop`
- One merged pull request from `develop` into `main`
- No direct PD2 implementation commits on `main`

## 12. Recommended Implementation Order

### Phase 1: Foundation

- Create and push `develop`.
- Create `feature/network-project-crud`.
- Generate the Django app.
- Add the app to `INSTALLED_APPS` and root URLs.
- Implement models and migration.
- Update `DATABASE.md`.

### Phase 2: CRUD Vertical Path

- Implement forms and validation.
- Implement ownership-filtered views.
- Create project and requirement templates.
- Add navigation and dashboard links.
- Add tests for models, forms, CRUD, and ownership.
- Run all tests and merge the first PR into `develop`.

### Phase 3: Allocation Vertical Path

- Create `feature/vlsm-allocation` from updated `develop`.
- Implement and unit-test the calculation service.
- Implement transactional result persistence.
- Add the calculate route and POST action.
- Display the allocation table and capacity feedback.
- Add dashboard statistics and role behavior.
- Update `README.md`.
- Run all tests and merge the second PR into `develop`.

### Phase 4: Integration and Submission

- Test the full workflow in local mode.
- Apply migrations to Supabase.
- Test persistence against PostgreSQL.
- Test the deployed application.
- Complete and commit the PD2 report.
- Open and merge `develop` into `main`.
- Verify the public repository in an incognito window.
- Submit the repository URL through the required Google Form.

## 13. Documentation Tasks

### README.md

Update the README with:

- PD2 core-feature description
- End-to-end user workflow
- New project structure and routes
- Database relationships
- Setup and migration instructions
- PostgreSQL/Supabase notes
- Test commands
- Role behavior

### DATABASE.md

Document:

- `NetworkProject` table
- `SubnetRequirement` table
- All fields and data types
- Foreign keys and cascade behavior
- Constraints and indexes
- Ownership and authorization behavior
- Persistent calculation fields

### Completion Report

Obtain and complete `PD-Completion-Report-Template.docx` without removing any section. Include:

- Features implemented
- Branch names
- Pull request links
- Remaining tasks
- Outstanding issues
- Test accounts and roles
- Test and deployment results

Save the PDF as:

```text
VLSMatic-Santillan-RalphLawrence-G01-PD2.pdf
```

Commit it at:

```text
docs/VLSMatic-Santillan-RalphLawrence-G01-PD2.pdf
```

The completion-report template is not currently present in the repository and must be obtained before the report can be prepared.

## 14. Definition of Done

### Feature

- [ ] A user can create a network project through the UI.
- [ ] A user can add, edit, and delete subnet requirements.
- [ ] A user can generate a valid largest-first VLSM allocation.
- [ ] Calculated results are saved and can be reopened later.
- [ ] A user can edit and delete their project.
- [ ] Invalid input and insufficient capacity display clear errors.

### Security and Roles

- [ ] Every feature route requires authentication.
- [ ] Every project has a user foreign key.
- [ ] Regular users can access only their own records.
- [ ] Cross-user URL manipulation is rejected.
- [ ] Mutating actions use POST and CSRF protection.
- [ ] Role dashboards show the correct feature links and data.

### Database and Quality

- [ ] Models and migrations are committed.
- [ ] Migrations are applied to Supabase PostgreSQL.
- [ ] `DATABASE.md` matches the implemented schema.
- [ ] All existing PD1 tests still pass.
- [ ] New calculation, validation, CRUD, and ownership tests pass.
- [ ] `manage.py check` reports no issues.
- [ ] No uncommitted migration changes remain.

### GitHub and Documentation

- [ ] `develop` exists and is pushed.
- [ ] Two feature branches are retained.
- [ ] Two feature pull requests are merged into `develop`.
- [ ] One pull request is merged from `develop` into `main`.
- [ ] Commit messages clearly describe each change.
- [ ] `.env` remains ignored and contains no committed secrets.
- [ ] `requirements.txt` is current.
- [ ] `README.md` describes the core feature and setup.
- [ ] The completed PD2 PDF exists in `docs/`.
- [ ] The public repository and PDF are visible in an incognito window.
- [ ] All required work is pushed before the deadline.

## 15. Submission Checklist

- [ ] Confirm the latest stable increment is on `main`.
- [ ] Confirm the production deployment uses PostgreSQL/Supabase.
- [ ] Register or verify regular-user and administrator test accounts.
- [ ] Complete the full user workflow on the deployed application.
- [ ] Confirm account registration, login, logout, dashboards, and profile still work.
- [ ] Confirm no user can access another user's projects.
- [ ] Confirm the repository is public.
- [ ] Confirm the PD2 PDF is downloadable from `docs/`.
- [ ] Submit the GitHub repository link through the required Google Form.

