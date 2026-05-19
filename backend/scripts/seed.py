#!/usr/bin/env python3
"""
seed.py — Bootstrap the Rhadix platform with a RHADIX_ADMIN user and
          optionally a first customer tenant.

Usage (from the backend/ directory):
    python -m scripts.seed

Environment variables (or defaults):
    DATABASE_URL             — PostgreSQL connection string
    SEED_ADMIN_EMAIL         — email for the RHADIX_ADMIN account (required)
    SEED_ADMIN_PASSWORD      — password (min 12 chars, required)
    SEED_ADMIN_NAME          — display name (optional)
    SEED_TENANT_NAME         — create a demo tenant with this name (optional)
    SEED_TENANT_SLUG         — slug for the demo tenant (optional, derived from name)
    SEED_TENANT_ADMIN_EMAIL  — email for the tenant ORG_ADMIN (optional)
    SEED_TENANT_ADMIN_PASS   — password for the tenant ORG_ADMIN (optional)
"""
import os
import sys
import uuid

# Ensure the backend package is on the path when run as `python -m scripts.seed`
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.database import SessionLocal
from app.models.auth_models import Tenant, User, UserRole
from app.auth.security import hash_password


def _slugify(name: str) -> str:
    import re
    return re.sub(r"[^a-z0-9-]", "-", name.lower().strip()).strip("-")


def seed():
    db = SessionLocal()
    try:
        admin_email    = os.getenv("SEED_ADMIN_EMAIL", "").strip()
        admin_password = os.getenv("SEED_ADMIN_PASSWORD", "").strip()
        admin_name     = os.getenv("SEED_ADMIN_NAME", "Rhadix Admin").strip()

        if not admin_email or not admin_password:
            print("ERROR: SEED_ADMIN_EMAIL and SEED_ADMIN_PASSWORD are required.")
            sys.exit(1)
        if len(admin_password) < 12:
            print("ERROR: SEED_ADMIN_PASSWORD must be at least 12 characters.")
            sys.exit(1)

        # ── 1. Rhadix system tenant (houses the RHADIX_ADMIN account) ──────────
        rhadix_tenant = db.query(Tenant).filter(Tenant.slug == "rhadix-platform").first()
        if not rhadix_tenant:
            rhadix_tenant = Tenant(
                id        = uuid.uuid4(),
                slug      = "rhadix-platform",
                name      = "Rhadix Platform",
                is_active = True,
            )
            db.add(rhadix_tenant)
            db.flush()
            print(f"  + Created system tenant:  {rhadix_tenant.name} ({rhadix_tenant.id})")
        else:
            print(f"  ~ System tenant exists:   {rhadix_tenant.name}")

        # ── 2. RHADIX_ADMIN user ───────────────────────────────────────────────
        existing_admin = db.query(User).filter(User.email == admin_email.lower()).first()
        if not existing_admin:
            admin_user = User(
                id            = uuid.uuid4(),
                tenant_id     = rhadix_tenant.id,
                email         = admin_email.lower(),
                password_hash = hash_password(admin_password),
                full_name     = admin_name,
                role          = UserRole.RHADIX_ADMIN,
                is_active     = True,
            )
            db.add(admin_user)
            print(f"  + Created RHADIX_ADMIN:   {admin_email}")
        else:
            print(f"  ~ RHADIX_ADMIN exists:    {admin_email}")

        # ── 3. Optional demo / first customer tenant ───────────────────────────
        tenant_name       = os.getenv("SEED_TENANT_NAME", "").strip()
        tenant_slug       = os.getenv("SEED_TENANT_SLUG", "").strip() or _slugify(tenant_name)
        tenant_admin_email = os.getenv("SEED_TENANT_ADMIN_EMAIL", "").strip()
        tenant_admin_pass  = os.getenv("SEED_TENANT_ADMIN_PASS", "").strip()

        if tenant_name:
            demo_tenant = db.query(Tenant).filter(Tenant.slug == tenant_slug).first()
            if not demo_tenant:
                demo_tenant = Tenant(
                    id        = uuid.uuid4(),
                    slug      = tenant_slug,
                    name      = tenant_name,
                    is_active = True,
                )
                db.add(demo_tenant)
                db.flush()
                print(f"  + Created tenant:         {tenant_name} ({demo_tenant.id})")
            else:
                print(f"  ~ Tenant exists:          {tenant_name}")

            if tenant_admin_email and tenant_admin_pass:
                if len(tenant_admin_pass) < 12:
                    print("  ! SEED_TENANT_ADMIN_PASS too short — skipping tenant admin user.")
                elif db.query(User).filter(User.email == tenant_admin_email.lower()).first():
                    print(f"  ~ Tenant admin exists:    {tenant_admin_email}")
                else:
                    t_admin = User(
                        id            = uuid.uuid4(),
                        tenant_id     = demo_tenant.id,
                        email         = tenant_admin_email.lower(),
                        password_hash = hash_password(tenant_admin_pass),
                        role          = UserRole.ORG_ADMIN,
                        is_active     = True,
                    )
                    db.add(t_admin)
                    print(f"  + Created ORG_ADMIN:      {tenant_admin_email}")

        db.commit()
        print("\nSeed completed successfully.")

    except Exception as exc:
        db.rollback()
        print(f"Seed failed: {exc}")
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    seed()
