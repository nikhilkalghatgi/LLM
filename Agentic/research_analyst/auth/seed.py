"""Seed the default tenants and users defined in ``config['auth']``.

Idempotent: running it repeatedly never duplicates rows. Called once from the
API lifespan so a fresh clone has working logins immediately.
"""

from typing import Dict

from auth.security import hash_password
from db.database import session_scope
from db.models import Tenant, User


def seed_auth(config: Dict) -> None:
    """Create configured tenants and users if they do not already exist."""
    auth_cfg = config.get("auth", {})
    seed_tenants = auth_cfg.get("seed_tenants", [])
    seed_users = auth_cfg.get("seed_users", [])

    with session_scope() as session:
        for t in seed_tenants:
            exists = session.get(Tenant, t["id"])
            if not exists:
                session.add(Tenant(id=t["id"], name=t.get("name", t["id"])))

        # Flush tenants so user FK constraints resolve within the same txn.
        session.flush()

        for u in seed_users:
            existing = (
                session.query(User).filter(User.username == u["username"]).first()
            )
            if existing:
                continue
            session.add(
                User(
                    username=u["username"],
                    password_hash=hash_password(u["password"]),
                    tenant_id=u["tenant_id"],
                    role=u.get("role", "analyst"),
                )
            )
