"""Give every Spice Hub dish its own description and drop mismatched stock-photo URLs.

Revision ID: 0014
Revises: 0013
Create Date: 2026-10-20 10:00:00.000000

Migration 0011 inserted every dish with the placeholder text "Freshly prepared <name>." and the
development seed attached guessed stock-photo URLs (several dishes shared one photo, e.g. Coca-Cola
showed a Sprite picture). This migration:

1. Replaces ONLY placeholder / empty descriptions with a dish-specific one. A description an admin
   has edited by hand is never touched.
2. Clears image URLs that point at the old seeded stock photos (`https://images.unsplash.com/...`)
   or at the retired `/menu/...` illustrations. Photos uploaded through the admin panel
   (`/static/...` or the CDN) are kept. The customer app shows a dedicated illustration for every
   item code (customer-web/public/dishes/<ITEM_CODE>.svg) whenever no real photo is set.
"""

# ruff: noqa: E501

from __future__ import annotations

import sqlalchemy as sa
from alembic import context, op

revision = "0014"
down_revision = "0013"
branch_labels = None
depends_on = None

# item_code -> description (every item code of MENU_CATALOG in migration 0011 appears exactly once)
ITEM_DESCRIPTIONS: dict[str, str] = {
    # Breakfast
    "BF-IDL": "Soft, fluffy steamed rice-and-lentil cakes served with sambar and chutney.",
    "BF-PD": "Thin, crisp golden dosa served with sambar and chutney.",
    "BF-MD": "Crispy dosa filled with spiced potato masala, served with sambar and chutney.",
    "BF-SD": "Three soft, spongy set dosas served with sambar and chutney.",
    "BF-PB": "Three puffed golden pooris served with a mildly spiced potato bhaji.",
    # Lunch - Meals
    "LM-VM": "Simple vegetarian meal with rice, sambar, rasam, vegetable curry, curd and papad.",
    "LM-SVM": "Our bigger vegetarian thali with rice, extra curries, a sweet, curd and papad.",
    "LM-SIM": "Traditional South Indian meal with rice, sambar, rasam, poriyal, curd and pickle.",
    "LM-CM": "Rice meal served with spicy chicken curry, sambar, rasam, curd and papad.",
    "LM-FM": "Rice meal with fried fish and fish curry. Seasonal catch, ask your waiter for today's price.",
    # Lunch - Rice & Pulao
    "LR-SR": "Plain steamed white rice, the perfect partner for any curry or gravy.",
    "LR-JR": "Fragrant rice tempered with cumin seeds and a touch of ghee.",
    "LR-GR": "Aromatic rice cooked in ghee and whole spices, topped with fried cashews.",
    "LR-VP": "Mildly spiced rice cooked with carrots, peas and beans.",
    "LR-EFR": "Fragrant rice stir-fried with scrambled egg, spring onion and vegetables.",
    # Biryani
    "BY-VB": "Fragrant biryani rice layered with mixed vegetables and whole spices, served with raita.",
    "BY-EB": "Spiced biryani rice with boiled eggs, fried onions and fresh herbs, served with raita.",
    "CB": "Classic hot chicken biryani with tender chicken, saffron rice and fried onions, served with raita.",
    "BY-CDB": "Chicken and rice slow-cooked together in a sealed pot so every grain soaks up the masala.",
    "BY-MB": "Tender mutton and fragrant rice cooked in a rich biryani masala, served with raita.",
    # Dinner - Indian Breads
    "BR-KP": "Flaky, layered Kerala parotta, crisp outside and soft inside. 2 pieces.",
    "BR-CH": "Soft whole-wheat chapatis cooked fresh on the tawa. 2 pieces.",
    "BR-TR": "Whole-wheat roti baked in the tandoor with a light char.",
    "BR-PN": "Soft leavened naan baked fresh in the tandoor.",
    "BR-BN": "Soft tandoor naan brushed with melted butter.",
    # Dinner - Veg Curries
    "VC-PBM": "Soft paneer cubes in a rich, creamy tomato-butter gravy. Mild.",
    "VC-KP": "Paneer tossed with capsicum, onion and freshly ground spices in a thick tomato gravy.",
    "VC-DF": "Yellow lentils tempered with garlic, cumin and red chilli.",
    "VC-VK": "Mixed vegetables simmered in a mild, aromatic coconut kurma.",
    "VC-CM": "Chickpeas slow-cooked in a tangy, spiced onion-tomato masala.",
    # Dinner - Non-Veg Curries
    "NC-CC": "Home-style chicken curry in a spicy onion-tomato gravy.",
    "NC-BC": "Tender chicken in a mild, creamy tomato-butter gravy.",
    "NC-CCN": "Fiery Chettinad-style chicken with freshly ground pepper and spices.",
    "NC-MC": "Tender mutton slow-cooked in a robust, spicy masala.",
    "NC-EC": "Boiled eggs simmered in a spiced onion-tomato gravy.",
    # Mandi & Grilled Chicken
    "MD-AFM": "Fragrant mandi rice served with smoky Alfaham-style grilled chicken.",
    "MD-BQM": "Fragrant mandi rice served with barbecue-glazed grilled chicken.",
    "MD-TDM": "Fragrant mandi rice served with spicy tandoori-marinated chicken.",
    "MD-AFC": "Chicken marinated in Arabian-style spices and char-grilled until juicy.",
    "MD-GC": "Chicken grilled until golden and juicy, with a smoky char.",
    # Snacks - Veg
    "SV-GM": "Crispy cauliflower florets tossed in a tangy, spicy Manchurian sauce.",
    "SV-P65": "Spicy, crisp-fried paneer cubes tempered with curry leaves and green chilli.",
    "SV-CP": "Paneer cubes wok-tossed with capsicum, onion and chilli sauce.",
    "SV-FF": "Golden, crispy french fries, lightly salted.",
    "SV-VM": "Six steamed dumplings stuffed with spiced vegetables, served with red chilli chutney.",
    # Snacks - Chicken
    "SC-C65": "Spicy, crisp-fried chicken bites tempered with curry leaves and green chilli.",
    "SC-CC": "Fried chicken tossed with capsicum, onion and a spicy Indo-Chinese sauce.",
    "SC-CLL": "Chicken wings shaped like lollipops, fried and tossed in a spicy red sauce.",
    "SC-CKB": "Juicy spiced chicken kebabs grilled on skewers.",
    "SC-CTK": "Chicken cubes marinated in yogurt and spices, grilled with onion and capsicum.",
    # Snacks - Fish & Seafood (seasonal pricing)
    "SF-FF": "Fresh fish marinated in spices and shallow-fried until crisp. Seasonal price.",
    "SF-ATF": "Anjal (seer fish) steak rubbed in masala and pan-fried on the tawa. Seasonal price.",
    "SF-PRF": "Prawns fried with spicy masala and curry leaves. Seasonal price.",
    "SF-FFG": "Crumb-coated fish strips fried golden, served with a dip. Seasonal price.",
    "SF-GFP": "Crisp, golden breadcrumb-coated fried prawns. Seasonal price.",
    # Snacks - Rolls & Quick Bites
    "RK-VRL": "Soft wrap filled with spiced vegetables, onion and sauce.",
    "RK-ERL": "Soft wrap rolled around a fluffy egg omelette with onion and sauce.",
    "RK-CRL": "Soft wrap stuffed with spiced chicken, onion and sauce.",
    "RK-CSH": "Grilled chicken shawarma wrapped in soft bread with garlic sauce and salad.",
    "RK-CBG": "Crispy chicken patty in a toasted bun with lettuce, cheese and mayo.",
    # Soups
    "SP-TOM": "Smooth, tangy tomato soup served piping hot.",
    "SP-CRN": "Thick, creamy sweet corn soup with vegetables.",
    "SP-VCL": "Light, clear vegetable broth with fresh vegetables.",
    "SP-CCL": "Light, clear broth with shredded chicken and vegetables.",
    "SP-MCW": "Hot and spicy vegetable soup topped with crispy fried noodles.",
    # Beverages - Fresh Juice
    "BJ-LIM": "Freshly squeezed lime juice served chilled, sweet or salted.",
    "BJ-ORG": "Freshly squeezed orange juice served chilled.",
    "BJ-WML": "Chilled fresh watermelon juice.",
    "BJ-MSB": "Freshly squeezed mosambi (sweet lime) juice served chilled.",
    "BJ-MXF": "A refreshing blend of seasonal fruit juices.",
    # Beverages - Milkshakes & Lassi
    "BM-CHK": "Thick, chilled chocolate milkshake with a chocolate drizzle.",
    "BM-ORO": "Creamy milkshake blended with Oreo cookies.",
    "BM-MNG": "Thick milkshake made with sweet, ripe mango.",
    "BM-COF": "Chilled coffee blended with milk and ice, topped with cream.",
    "BM-LSS": "Thick, creamy sweet yogurt lassi served chilled.",
    # Beverages - Cold & Hot Drinks
    "BD-SPR": "Sprite, the clear lemon-lime soft drink. Served chilled.",
    "BD-COL": "Coca-Cola soft drink. Served chilled.",
    "BD-THM": "Thums Up soft drink with a strong cola kick. Served chilled.",
    "BD-TEA": "Hot Indian tea (chai) brewed with milk.",
    "BD-COF": "Hot milk coffee, freshly brewed.",
    # Ice Creams & Desserts
    "DS-VAN": "Two scoops of creamy vanilla ice cream.",
    "DS-CHO": "Two scoops of rich chocolate ice cream.",
    "DS-BRW": "Fudgy chocolate brownie served with two scoops of ice cream.",
    "DS-GJM": "Two soft, syrup-soaked gulab jamuns, served warm.",
    "DS-FAL": "Rose falooda with vermicelli, basil seeds, milk and ice cream.",
    # Chinese & Indo-Chinese
    "CH-VFR": "Wok-tossed rice with fresh vegetables and spring onion.",
    "CH-EFR": "Indo-Chinese style egg fried rice, tossed on high heat with spring onion.",
    "CH-CFR": "Wok-tossed rice with chicken pieces and vegetables.",
    "CH-CHN": "Stir-fried hakka noodles with chicken and crunchy vegetables.",
    "CH-CMD": "Crispy chicken balls tossed in a spicy, tangy Manchurian sauce (dry).",
}

PLACEHOLDER_PREFIX = "Freshly prepared %"
OLD_IMAGE_PATTERNS = ("https://images.unsplash.com/%", "/menu/%")


def upgrade() -> None:
    if context.is_offline_mode():
        return
    conn = op.get_bind()

    for code, description in ITEM_DESCRIPTIONS.items():
        conn.execute(
            sa.text(
                "UPDATE menu_items SET description = :description, updated_at = now() "
                "WHERE upper(item_code) = upper(:code) "
                "AND (description IS NULL OR description = '' OR description LIKE :placeholder)"
            ),
            {"description": description, "code": code, "placeholder": PLACEHOLDER_PREFIX},
        )

    for pattern in OLD_IMAGE_PATTERNS:
        conn.execute(
            sa.text(
                "UPDATE menu_items SET image_url = NULL, updated_at = now() "
                "WHERE image_url LIKE :pattern"
            ),
            {"pattern": pattern},
        )


def downgrade() -> None:
    # Data-only migration; descriptions and image URLs are not restored.
    pass
