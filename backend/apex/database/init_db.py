"""Create all tables and seed the product catalogue.

Usage:  python -m apex.database.init_db
Requires backend/.env with a valid DATABASE_URL.
"""
from . import models  # noqa: F401  (registers all tables on Base.metadata)
from .db import Base, engine
from .seed_products import seed_products


def main() -> None:
    print("Creating tables...")
    Base.metadata.create_all(engine)
    print(f"  {len(Base.metadata.tables)} tables ready: {', '.join(sorted(Base.metadata.tables))}")

    print("Seeding products...")
    n = seed_products()
    print(f"  seeded {n} products")
    print("Done.")


if __name__ == "__main__":
    main()
