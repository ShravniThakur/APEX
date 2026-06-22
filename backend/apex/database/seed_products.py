"""Load product_catalogue.json into the PRODUCTS table (idempotent upsert)."""
import json

from sqlalchemy.dialects.postgresql import insert

from ..config import CATALOGUE_PATH
from .db import SessionLocal
from .models import Product

# Columns we copy straight from the catalogue JSON.
_FIELDS = (
    "product_id", "name", "category", "depth", "verified", "verification_source",
    "description", "eligibility_rules", "key_facts", "landing_url", "primary_use", "tax_saving",
)


def seed_products() -> int:
    with open(CATALOGUE_PATH, encoding="utf-8") as fh:
        catalogue = json.load(fh)

    rows = [{k: p.get(k) for k in _FIELDS} for p in catalogue["products"]]

    with SessionLocal() as session:
        stmt = insert(Product).values(rows)
        # On re-run, refresh everything except the PK.
        update_cols = {c: stmt.excluded[c] for c in _FIELDS if c != "product_id"}
        stmt = stmt.on_conflict_do_update(index_elements=["product_id"], set_=update_cols)
        session.execute(stmt)
        session.commit()

    return len(rows)


if __name__ == "__main__":
    n = seed_products()
    print(f"Seeded/updated {n} products from {CATALOGUE_PATH}")
