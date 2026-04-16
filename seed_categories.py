import logging
import re
from sqlalchemy.orm import Session
from database.config import SessionLocal
from database.affiliate_models import SystemCategory, CategoryType

logger = logging.getLogger(__name__)

BRAND_CATEGORIES = [
    "Fashion & Apparel",
    "Health & Beauty",
    "Electronics & Tech",
    "Home & Living",
    "Food & Beverage",
    "Fitness & Sports",
    "Education & courses",
    "Digital Products & Software",
    "Travel & Lifestyle",
    "Automotive",
    "Finance & Business",
    "Entertainment & Gaming"
]

PRODUCT_CATEGORIES = [
    "E-Books & Guides",
    "Online Courses",
    "Software & Tools",
    "Templates & Assets",
    "Memberships",
    "Consulting & Services",
    "Clothing & Accessories",
    "Skincare & Cosmetics",
    "Supplements & Vitamins",
    "Smartphones & Gadgets",
    "Computers & Laptops",
    "Home Decor",
    "Kitchenware",
    "Fitness Equipment",
    "Groceries & Snacks",
    "Toys & Games",
    "Jewelry & Watches",
    "Pet Supplies",
    "Handmade & Crafts"
]

def create_slug(name: str) -> str:
    slug = re.sub(r'[^a-zA-Z0-9]', '-', name.lower())
    slug = re.sub(r'-+', '-', slug).strip('-')
    return slug

def seed_categories():
    db: Session = SessionLocal()
    try:
        added = 0
        
        # Seed Brand Categories
        for cat_name in BRAND_CATEGORIES:
            slug = create_slug(cat_name)
            existing = db.query(SystemCategory).filter(
                SystemCategory.slug == slug,
                SystemCategory.type == CategoryType.BRAND
            ).first()
            if not existing:
                cat = SystemCategory(name=cat_name, slug=slug, type=CategoryType.BRAND)
                db.add(cat)
                added += 1
                
        # Seed Product Categories
        for cat_name in PRODUCT_CATEGORIES:
            slug = create_slug(cat_name)
            existing = db.query(SystemCategory).filter(
                SystemCategory.slug == slug,
                SystemCategory.type == CategoryType.PRODUCT
            ).first()
            if not existing:
                cat = SystemCategory(name=cat_name, slug=slug, type=CategoryType.PRODUCT)
                db.add(cat)
                added += 1
                
        if added > 0:
            db.commit()
            logger.info(f"Seeded {added} new system categories.")
        else:
            logger.info("System categories already seeded.")
            
    except Exception as e:
        db.rollback()
        logger.error(f"Error seeding categories: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    seed_categories()
