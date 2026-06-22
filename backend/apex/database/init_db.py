"""Create all tables and seed the product catalogue.

Usage:  python -m apex.database.init_db
Requires backend/.env with a valid DATABASE_URL.
"""
from sqlalchemy import text

from . import models  # noqa: F401  (registers all tables on Base.metadata)
from .db import Base, engine
from .seed_products import seed_products

# Idempotent, data-preserving column additions for tables that already exist (create_all only
# creates missing *tables*, never alters existing ones). Postgres ADD COLUMN IF NOT EXISTS makes
# re-running init_db on a populated DB safe — no drop/regenerate needed.
_MIGRATIONS = (
    "ALTER TABLE decisions ADD COLUMN IF NOT EXISTS rm_status VARCHAR DEFAULT 'open'",
)


def main() -> None:
    print("Creating tables...")
    Base.metadata.create_all(engine)
    print(f"  {len(Base.metadata.tables)} tables ready: {', '.join(sorted(Base.metadata.tables))}")

    print("Applying column migrations...")
    with engine.begin() as conn:
        for stmt in _MIGRATIONS:
            conn.execute(text(stmt))
    print(f"  {len(_MIGRATIONS)} migration(s) applied")

    print("Seeding products...")
    n = seed_products()
    print(f"  seeded {n} products")
    print("Done.")


if __name__ == "__main__":
    main()
