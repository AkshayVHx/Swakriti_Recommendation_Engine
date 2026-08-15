import os
from typing import Iterable

import pandas as pd

EXCEL_PATH = os.environ.get(
    "PRODUCT_MASTER_PATH",
    os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "..", "Swakriti_Womens_Dresses_Product_Master_Top35_v5_cleaned.xlsx")
    ),
)
SHEET_NAME = "Product Master"


def _split_csv(value):
    if value is None or pd.isna(value):
        return []
    if isinstance(value, (int, float)):
        return []
    return [v.strip() for v in str(value).split(",") if v.strip()]


def _as_bool(value):
    if value is None or pd.isna(value):
        return False
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "y", "on", "t"}


def _slug(text):
    return str(text).strip().upper().replace(" ", "")[:4]


def _map_gender(category: str) -> str:
    return {"Women's Wear": "female"}.get(str(category).strip(), "female")


def _build_group_product(group: pd.DataFrame):
    row = group.iloc[0].copy()
    style_code = str(row["Style Code"]).strip()
    colour = str(row["Primary Colour"]).strip()
    sizes = sorted({str(v).strip().upper() for v in group["Size"].dropna().astype(str) if str(v).strip()})
    stock_count = int(group["Inventory Quantity"].fillna(0).astype(float).sum())
    occasion_tags = _split_csv(row.get("Occasion"))

    pattern = row.get("Pattern")
    if pattern == "Plain colour":
        pattern = None

    product = {
        "sku_id": f"{style_code}-{_slug(colour)}",
        "sku_codes": group["SKU"].astype(str).tolist(),
        "name": row.get("Product Name"),
        "item_group": "dress",
        "sub_category": row.get("Sub Category"),
        "brand": row.get("Brand"),
        "collection_name": row.get("Collection Name"),
        "gender": _map_gender(row.get("Category")),

        "price": float(row.get("Price", 0) or 0),
        "budget_tier": row.get("Budget Tier"),
        "available_sizes": sizes,
        "stock_count": stock_count,
        "is_new_arrival": _as_bool(row.get("New Arrival")),

        "specific_color": row.get("Primary Colour"),
        "color_family": row.get("Colour Family"),
        "pattern": pattern,

        "style_category": row.get("Style Category"),
        "silhouette": row.get("Silhouette"),
        "fit_type": row.get("Fit Type"),
        "length": row.get("Length"),
        "sleeve_type": row.get("Sleeve Type"),
        "neckline": row.get("Neckline"),

        "fabric_category": row.get("Fabric"),
        "fabric_weight": row.get("Fabric Weight"),
        "breathability": row.get("Breathability"),
        "stretch": row.get("Stretch"),
        "texture": row.get("Texture"),
        "care_difficulty": row.get("Care Difficulty"),
        "comfort_level": row.get("Comfort Level"),

        "weather_suitability": row.get("Weather Suitability"),
        "season": row.get("Season"),
        "occasion_primary": occasion_tags[0] if occasion_tags else None,
        "occasion_tags": occasion_tags,
        "occasion_intensity": row.get("Occasion Intensity"),
        "dress_code": row.get("Dress Code"),
        "indoor_outdoor": row.get("Indoor/Outdoor"),

        "trend_level": row.get("Trend Level"),
        "statement_level": row.get("Statement Level"),
        "minimal_maximal": row.get("Minimal/Maximal"),

        "body_type_fit": _split_csv(row.get("Body Shape Suitability")),
        "skin_tone_match": _split_csv(row.get("Skin Tone Suitability")),
        "age_tags": _split_csv(row.get("Age Group Suitability")),
        "height_band_fit": _split_csv(row.get("Height Band Suitability")),
        "petite_friendly": _as_bool(row.get("Petite Friendly")),
        "plus_size_friendly": _as_bool(row.get("Plus Size Friendly")),
        "alteration_available": _as_bool(row.get("Alteration Available")),

        "wedding_suitability": _as_bool(row.get("Wedding Suitability")),
        "wedding_function": row.get("Wedding Function"),
        "travel_friendly": _as_bool(row.get("Travel Friendly")),
        "layer_friendly": _as_bool(row.get("Layer Friendly")),
        "premium_flag": _as_bool(row.get("Premium Flag")),
        "bestseller_flag": _as_bool(row.get("Bestseller")),
        "trending_flag": _as_bool(row.get("Trending")),
        "limited_edition": _as_bool(row.get("Limited Edition")),
        "sale_item": _as_bool(row.get("Sale Item")),
        "rating": float(row.get("Rating", 0) or 0),

        "image_url": row.get("Image URL"),
        "back_image_url": row.get("Back Image URL"),

        "trend_score": 1.0 if _as_bool(row.get("Trending")) else (0.6 if str(row.get("Trend Level", "")).strip() == "Latest trends" else 0.4),
        "bestseller_score": 1.0 if _as_bool(row.get("Bestseller")) else 0.4,
        "margin_score": 0.5,
        "inventory_urgency": 1.0 if stock_count <= 3 else 0.0,
        "embedding_text_dense": str(row.get("Product Description") or ""),
        "embedding_text_sparse": str(row.get("Fashion Keywords") or ""),
    }
    return product


def fetch_products_from_excel(path: str = EXCEL_PATH) -> list[dict]:
    df = pd.read_excel(path, sheet_name=SHEET_NAME)
    products = []
    for (style_code, colour), group in df.groupby(["Style Code", "Primary Colour"], sort=False):
        _ = style_code, colour
        products.append(_build_group_product(group))
    return products


def fetch_single_product_excel(sku_id: str, path: str = EXCEL_PATH):
    df = pd.read_excel(path, sheet_name=SHEET_NAME)
    matches = df[df.apply(lambda row: f"{str(row['Style Code']).strip()}-{_slug(row['Primary Colour'])}" == str(sku_id).strip(), axis=1)]
    if matches.empty:
        return None
    return _build_group_product(matches)


if __name__ == "__main__":
    items = fetch_products_from_excel()
    print(f"Fetched {len(items)} products from Excel.")
    if items:
        print(items[0]["sku_id"], items[0]["available_sizes"]) 
