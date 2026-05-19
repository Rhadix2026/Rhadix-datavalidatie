# Changelog

All notable changes to the Rhadix platform are documented here.
Follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/) conventions.

---

## [1.4.0] — 2026-05-19  Phase 2: Licenses, Applications & Access Control

### Added

**Backend**
- `Application` model — built-in product modules with stable slugs (`kikv-validator`, `zib-validator`, `algemeen-validator`, `reconciliation`).
- `License` model — tenant-scoped licences with optional expiry date and max-user cap, created by RHADIX_ADMIN.
- `TenantApplication` model — links an Application to a Tenant under an optional License; created by RHADIX_ADMIN.
- `UserApplication` model — links an Application to a specific User within a Tenant; created by ORG_ADMIN.
- Alembic migration `0002_phase2_licenses` — creates four new tables, seeds the four built-in applications, and extends `validation_runs` with `application_id` and `license_id` columns.
- `/api/admin/applications/` — CRUD endpoints for applications (RHADIX_ADMIN only).
- `/api/admin/licenses/` — CRUD endpoints for licenses (RHADIX_ADMIN only).
- `/api/admin/tenants/{id}/applications` — assign / revoke applications to a tenant (RHADIX_ADMIN only).
- `/api/org/` — new org-admin router: list tenant apps, list users, assign / revoke user-app assignments (ORG_ADMIN + RHADIX_ADMIN).
- `require_app_access(slug)` FastAPI dependency — enforces per-application access for authenticated users; anonymous (demo) calls are passed through unchanged.
- `ValidationRun` now stores `application_id` and `license_id` on every authenticated scan; demo runs keep `NULL`.
- `/api/auth/me` now returns `assigned_app_slugs` — the list of application slugs the authenticated user may access.

**Frontend**
- `AdminDashboard` rebuilt with three tabs: **Organisaties** (orgs + app assignments + license overview), **Licenties** (license CRUD), **Applicaties** (app metadata editing).
- New `OrgAdminDashboard` page for ORG_ADMIN: lists all users in the org with expandable rows to assign / revoke applications per user.
- **Beheer** button in Nav for ORG_ADMIN users (mirrors the existing Admin button for RHADIX_ADMIN).
- `SelectSystems` — locked standard tiles (🔒 badge + "Geen toegang" label) for standards the logged-in user is not licensed for; clicking them shows an access-denied alert without navigating.
- `api.js` — new API helpers: `getAdminApplications`, `updateAdminApplication`, `getAdminLicenses`, `createAdminLicense`, `updateAdminLicense`, `getAdminTenantApps`, `assignAppToTenant`, `revokeAppFromTenant`, `getAdminTenantLicenses`, `getMyTenantApps`, `getOrgUsers`, `getUserApps`, `assignAppToUser`, `revokeAppFromUser`.

**Tests** (`tests/test_licenses.py`, 35 new tests)
- License creation + validation (RHADIX_ADMIN only, unknown tenant rejected).
- Application listing and update.
- Org-app assignment, duplicate prevention, revocation, and license linkage.
- User-app assignment, duplicate prevention, "app not licensed for tenant" guard.
- Unauthorized access (ORG_USER, ORG_ADMIN, unauthenticated → correct status codes).
- Cross-tenant isolation (ORG_ADMIN of tenant A cannot touch tenant B's users or see their apps).
- `ValidationRun.application_id` and `license_id` stored correctly; demo runs left as NULL.
- `/api/auth/me` returns correct `assigned_app_slugs` per role.

### Changed
- `auth_models.py` extended with `Application`, `License`, `TenantApplication`, `UserApplication` (same file, backwards-compatible).
- `models.py` `ValidationRun` — two new nullable FK columns (`application_id`, `license_id`).
- `validate.py` — inline app-access check for authenticated uploads; `_resolve_app_and_license()` helper links `application_id` + `license_id` to every new `ValidationRun`.
- `auth/router.py` `/me` endpoint — now queries `UserApplication` and returns `assigned_app_slugs`.
- `auth/schemas.py` — `UserResponse` gains `assigned_app_slugs`; `PasswordChangeRequest` migrated to Pydantic v2 `@field_validator`.
- `conftest.py` — updated to register new models, seed applications once per session, and clean up new tables between tests.

### Business rules enforced
- **RHADIX_ADMIN** — unrestricted access to all applications and all admin endpoints.
- **ORG_ADMIN** — may assign/revoke only applications that are already assigned to their own tenant; cannot touch other tenants.
- **ORG_USER** — may only access applications explicitly assigned to them; 403 otherwise.
- **Anonymous / demo users** — bypass app-access checks entirely (public demo flow unchanged).
- No user may access data from another organisation (tenant isolation enforced at every layer).

---

## [1.3.1] — 2026-05-19  Phase 1: Authentication & Multi-tenancy

### Added
- Alembic migration `0001_phase1_auth` — `tenants`, `users` (with `userrole` enum), extended `validation_runs`.
- JWT authentication: `POST /api/auth/login`, `GET /api/auth/me`, `PATCH /api/auth/me/password`.
- Role model: `RHADIX_ADMIN`, `ORG_ADMIN`, `ORG_USER`.
- Tenant isolation on all history / export / report routes.
- Admin dashboard: `GET /api/admin/stats`, tenant CRUD, user listing.
- Seed script (`scripts/seed.py`) — bootstraps the platform tenant + first RHADIX_ADMIN.
- Frontend login screen, auth guard, and Nav with user avatar + logout.
- Test suite: 29 tests covering login, `/me`, role checks, tenant isolation, protected routes, password change, and admin tenant creation.

---

## [1.3.0] — earlier  DTAP Pipeline & Reconciliation Engine

- Staging / production Docker Compose configurations.
- GitHub Actions CI + staging deploy + production deploy (with manual approval gate).
- Reconciliation Engine redesign with domain picker.
