import hashlib
import pandas as pd
import os
import threading
from sentence_transformers import SentenceTransformer
from fastembed import SparseTextEmbedding
from qdrant_client import QdrantClient
from qdrant_client.models import (
    VectorParams, SparseVectorParams, Distance, PointStruct,
    Filter, FieldCondition, MatchValue, MatchAny, Range,
    SparseVector, Prefetch, FusionQuery, Fusion,
)

from erp.erp_fetch import fetch_products_from_erp, fetch_single_product

from nlp.tag_extractor import extract_tags
from nlp.rule_engine import rank_products
from scoring.budget import normalize_budget
from nlp.taxonomy import COLOR_FAMILIES

COLLECTION = "skus"

dense_model = SentenceTransformer("BAAI/bge-large-en-v1.5")
sparse_model = SparseTextEmbedding("Qdrant/bm25")

client = QdrantClient(
    url=os.environ.get("QDRANT_URL"),
    api_key=os.environ.get("QDRANT_API_KEY"),
    timeout=60,
)

_model_lock = threading.Lock()


def get_vector_db_status():
    collection_exists = client.collection_exists(COLLECTION)
    count = 0
    if collection_exists:
        try:
            count = client.count(collection_name=COLLECTION).count
        except Exception:
            count = 0
    return {
        "collection": COLLECTION,
        "exists": collection_exists,
        "count": count,
    }


def sku_to_point_id(sku):
    if isinstance(sku, int):
        return sku
    return int(hashlib.md5(str(sku).encode("utf-8")).hexdigest()[:12], 16)


def _build_embedding_text(product: dict) -> str:
    occasion_tags = product.get("occasion_tags") or []
    style_tags = product.get("style") or []
    body_type_fit = product.get("body_type_fit") or []
    skin_tone_match = product.get("skin_tone_match") or []
    age_group_fit = product.get("age_tags") or []
    color_family = product.get("color_family") or []

    return " ".join(filter(None, [
        product.get("name"),
        product.get("item_group"),
        product.get("brand"),
        product.get("gender"),
        ", ".join(occasion_tags),
        ", ".join(style_tags),
        product.get("fabric_category"),
        product.get("specific_color"),
        product.get("color_tone"),
        ", ".join(body_type_fit),
        ", ".join(skin_tone_match),
        ", ".join(age_group_fit),
        ", ".join(color_family),
    ]))


def update_single_product(item_code: str):
    """
    Incremental update: fetch ONE product from ERPNext, re-embed it,
    and upsert just that point into Qdrant. Used by the webhook handler
    so we never rebuild the whole index for one change.
    """
    product = fetch_single_product(item_code)
    if not product:
        print(f"[update_single_product] Item {item_code} not found in ERPNext.")
        return False

    sizes_str = ", ".join(product.get("available_sizes", []))
    occasion_tags = product.get("occasion_tags", []) or []
    style_tags = product.get("style", []) or []
    body_type_fit = product.get("body_type_fit", []) or []
    skin_tone_match = product.get("skin_tone_match", []) or []
    age_group_fit = product.get("age_tags", []) or []
    color_family = product.get("color_family") or []

    embedding_text = _build_embedding_text(product)

    with _model_lock:
        dense_vec = dense_model.encode(embedding_text, normalize_embeddings=True).tolist()
        sparse_vec = list(sparse_model.embed([embedding_text]))[0]

    point = PointStruct(
        id=sku_to_point_id(product["sku_id"]),
        vector={
            "dense": dense_vec,
            "sparse": SparseVector(
                indices=sparse_vec.indices.tolist(),
                values=sparse_vec.values.tolist(),
            ),
        },
        payload={
            "sku_id": product.get("sku_id"),
            "product_name": product.get("name"),
            "category": str(product.get("item_group", "")).strip().lower(),
            "gender": str(product.get("gender", "")).strip().lower(),
            "brand": product.get("brand"),
            "price": float(product.get("price", 0)),
            "sizes": [s.strip().upper() for s in sizes_str.split(",") if s.strip()],
            "in_stock": product.get("stock_count", 0) > 0,
            "is_active": not product.get("disabled", 0),
            "is_new_arrival": product.get("is_new_arrival", False),
            "stock_count": product.get("stock_count", 0),

            "specific_color": product.get("specific_color"),
            "secondary_colors": ", ".join(color_family[1:]) if isinstance(color_family, list) else "",
            "color_family": str(product.get("color_tone", "")).strip().lower() or None,
            "high_contrast_festive": str(product.get("color_tone", "")).strip().lower() == "high_contrast_festive",
            "fabric_category": product.get("fabric_category"),
            "occasion_primary": occasion_tags[0] if occasion_tags else None,
            "occasion_tags": occasion_tags[1:],
            "style": style_tags[0] if style_tags else None,
            "silhouettes": [],

            "body_type_fit": body_type_fit,
            "skin_tone_match": skin_tone_match,
            "age_tags": age_group_fit,

            "trend_score": product.get("trend_score"),
            "bestseller_score": product.get("bestseller_score"),
            "margin_score": product.get("margin_score"),
            "inventory_urgency": product.get("inventory_urgency"),
        },
    )

    client.upsert(collection_name=COLLECTION, points=[point])
    print(f"[update_single_product] Upserted {product['sku_id']} into Qdrant.")
    return True


def delete_product(item_code: str):
    """Remove a product from the index (e.g. when disabled/deleted in ERPNext)."""
    point_id = sku_to_point_id(item_code)
    client.delete(collection_name=COLLECTION, points_selector=[point_id])
    print(f"[delete_product] Removed {item_code} from Qdrant.")
    return True


def load_merged_dataset():
    """Pull live product data from ERPNext instead of the static Excel file."""
    products = fetch_products_from_erp()
 
    rows = []
    for p in products:
        sizes_str = ", ".join(p.get("available_sizes", []))
        occasion_str = ", ".join(p.get("occasion_tags", []))
        style_str = ", ".join(p.get("style", []))
        body_fit_str = ", ".join(p.get("body_type_fit", []))
        skin_str = ", ".join(p.get("skin_tone_match", []))
        age_str = ", ".join(p.get("age_tags", []))
 
        # build the text blob used for embeddings (dense + sparse search)
        embedding_text = " ".join(filter(None, [
            p.get("name"),
            p.get("item_group"),
            p.get("brand"),
            p.get("gender"),
            occasion_str,
            style_str,
            p.get("fabric_category"),
            p.get("specific_color"),
            p.get("color_tone"),
            body_fit_str,
            skin_str,
            age_str,
        ]))
 
        rows.append({
            "SKU ID": p.get("sku_id"),
            "Product Name": p.get("name"),
            "Category": p.get("item_group"),
            "Gender": p.get("gender"),
            "Brand": p.get("brand"),
            "Discounted Price (INR)": p.get("price", 0),
            "Available Sizes": sizes_str,
            "In Stock": "YES" if p.get("stock_count", 0) > 0 else "NO",
            "Is Active": "YES",  # ERPNext already filters disabled=0 in erp_fetch
            "Is New Arrival": "YES" if p.get("is_new_arrival") else "NO",
            "Stock Count": p.get("stock_count", 0),
 
            "Primary Color": p.get("specific_color"),
            "Secondary Colors": ", ".join(p.get("color_family", [])[1:]),  # skip primary
            "Color Tone": p.get("color_tone"),
            "Fabric": p.get("fabric_category"),
            "Occasion Tags": occasion_str,
            "Style Tags": style_str,
 
            "Body Type Fit": body_fit_str,
            "Skin Tone Match": skin_str,
            "Age Group Fit": age_str,
 
            "Trend Score (0-1)": p.get("trend_score", 0.5),
            "Bestseller Score (0-1)": p.get("bestseller_score", 0.5),
            "Margin Score (0-1)": p.get("margin_score", 0.5),
            "Inventory Urgency (0-1)": p.get("inventory_urgency", 0.0),
 
            "SKU Text for Embedding (feed this to BGE-large-en-v1.5)": embedding_text,
        })
 
    return pd.DataFrame(rows)
 


def build_index(force: bool = False):
    status = get_vector_db_status()
    if not force and status["exists"]:
        count = status["count"]
        if count > 0:
            print(f"[build_index] vector DB already exists with {count} SKUs — skipping rebuild.")
            return
        print(f"[build_index] vector DB collection exists but is empty (count={count}). Rebuilding index.")
    else:
        print("[build_index] vector DB collection missing. Rebuilding index.")

    df = load_merged_dataset()
    texts = df["SKU Text for Embedding (feed this to BGE-large-en-v1.5)"].fillna("").tolist()

    dense_vectors = dense_model.encode(texts, normalize_embeddings=True)
    sparse_vectors = list(sparse_model.embed(texts))

    if client.collection_exists(COLLECTION):
        client.delete_collection(COLLECTION)

    client.create_collection(
        collection_name=COLLECTION,
        vectors_config={"dense": VectorParams(size=dense_vectors.shape[1], distance=Distance.COSINE)},
        sparse_vectors_config={"sparse": SparseVectorParams()},
    )

    points = []
    for i, row in df.iterrows():
        sizes = [s.strip().upper() for s in str(row["Available Sizes"]).split(",")]
        occasion_tags = [t.strip() for t in str(row.get("Occasion Tags", "")).split(",") if t.strip()]
        style_tags = [t.strip() for t in str(row.get("Style Tags", "")).split(",") if t.strip()]
        body_type_fit = [t.strip() for t in str(row.get("Body Type Fit", "")).split(",") if t.strip()]
        skin_tone_match = [t.strip() for t in str(row.get("Skin Tone Match", "")).split(",") if t.strip()]
        age_group_fit = [t.strip() for t in str(row.get("Age Group Fit", "")).split(",") if t.strip()]

        points.append(
            PointStruct(
                id=sku_to_point_id(row["SKU ID"]),
                vector={
                    "dense": dense_vectors[i].tolist(),
                    "sparse": SparseVector(
                        indices=sparse_vectors[i].indices.tolist(),
                        values=sparse_vectors[i].values.tolist(),
                    ),
                },
                payload={
                    # ---- sheet1: core / filter fields ----
                    "sku_id": row["SKU ID"],
                    "product_name": row["Product Name"],
                    "category": str(row["Category"]).strip().lower(),
                    "gender": str(row["Gender"]).strip().lower(),
                    "brand": row["Brand"],
                    "price": float(row["Discounted Price (INR)"]),
                    "sizes": sizes,
                    "in_stock": row["In Stock"] == "YES",
                    "is_active": row["Is Active"] == "YES",
                    "is_new_arrival": row["Is New Arrival"] == "YES",
                    "stock_count": row["Stock Count"],

                    # ---- sheet2: content tags -> renamed/added for rule_engine ----
                    "specific_color": row.get("Primary Color"),
                    "secondary_colors": row.get("Secondary Colors"),
                    "color_family": str(row.get("Color Tone", "")).strip().lower() or None,
                    "high_contrast_festive": str(row.get("Color Tone", "")).strip().lower() == "high_contrast_festive",
                    "fabric_category": row.get("Fabric"),
                    "occasion_primary": occasion_tags[0] if occasion_tags else None,
                    "occasion_tags": occasion_tags[1:],   # secondary tags only
                    "style": style_tags[0] if style_tags else None,
                    "silhouettes": [],   # fill in if you add a silhouette column later

                    # ---- sheet3: physical fit ----
                    "body_type_fit": body_type_fit,
                    "skin_tone_match": skin_tone_match,
                    "age_tags": age_group_fit,

                    # ---- sheet4: business signals ----
                    "trend_score": row.get("Trend Score (0-1)"),
                    "bestseller_score": row.get("Bestseller Score (0-1)"),
                    "margin_score": row.get("Margin Score (0-1)"),
                    "inventory_urgency": row.get("Inventory Urgency (0-1)"),
                },
            )
        )

    BATCH_SIZE = 50
    for i in range(0, len(points), BATCH_SIZE):
        batch = points[i:i + BATCH_SIZE]
        client.upsert(collection_name=COLLECTION, points=batch)
        print(f"[build_index] uploaded batch {i//BATCH_SIZE + 1} ({len(batch)} points)")
    print(f"[build_index] Index built: {len(points)} SKUs ready (dense + sparse).")
    print(f"[build_index] Final vector DB count: {client.count(collection_name=COLLECTION).count}")


def build_search_query(raw_query: str, tags: dict) -> str:
    """Build QUERY_2: Clean keyword search query for BM25 (removes duplication + noise)."""
    parts = []
    seen = set()
    
    def add_tag(tag_name, value):
        """Helper to add tags without duplication."""
        if not value:
            return
        if isinstance(value, (list, tuple, set)):
            values = [str(v).strip().lower() for v in value if str(v).strip()]
        else:
            values = [str(value).strip().lower()]
        
        for item in values:
            if item and item not in seen:
                seen.add(item)
                parts.append(item)
    
    # Priority order for tags (most specific first)
    add_tag("occasion", tags.get("occasion"))
    add_tag("event_context", tags.get("event_context"))
    add_tag("category", tags.get("category"))
    add_tag("style", tags.get("style"))
    
    
    color_value = tags.get("color")
    if not color_value and tags.get("formality") in COLOR_FAMILIES:
        color_value = tags.get("formality")
    if color_value:
    
        color_list = color_value if isinstance(color_value, list) else [color_value]
        for c in color_list:
            c_lower = str(c).strip().lower()
            if c_lower in COLOR_FAMILIES:            # it's a family name like "warm"
                add_tag("color_family", sorted(COLOR_FAMILIES[c_lower]))  # expand to all specific colors
            else:
                add_tag("color", c)                  # it's already a specific color
    
    add_tag("fabric_comfort", tags.get("fabric_comfort"))
    add_tag("body_type", tags.get("body_type"))
    add_tag("skin_tone", tags.get("skin_tone"))
    add_tag("mood", tags.get("mood"))
    add_tag("formality", tags.get("formality"))
    add_tag("height_cm_or_label", tags.get("height_cm_or_label"))
    add_tag("age_group", tags.get("age_group"))
    
    # Budget as keywords (no duplication)
    budget = tags.get("budget")
    if budget and isinstance(budget, dict):
        max_b = budget.get("max")
        min_b = budget.get("min")
        if max_b is not None:
            add_tag("budget_max", f"under {max_b}")
        elif min_b is not None:
            add_tag("budget_min", f"from {min_b}")
    
    # Join and return
    return " ".join(parts).strip()


def search(query_text: str, gender: str = None, size: str = None,
           budget: int = None, top_k: int = 50, semantic_query: str = None, category: str = None):
    if gender:
        gender = gender.strip().lower()
    if size:
        size = size.strip().upper()

    semantic_query = semantic_query or query_text

    with _model_lock:   # ← NEW: serialize access to the shared tokenizer/model
        query_dense = dense_model.encode(semantic_query, normalize_embeddings=True).tolist()
        query_sparse = list(sparse_model.embed([query_text]))[0]

    must = [
        FieldCondition(key="in_stock", match=MatchValue(value=True)),
        FieldCondition(key="is_active", match=MatchValue(value=True)),
    ]
    if gender:
        must.append(FieldCondition(key="gender", match=MatchValue(value=gender)))

    if category:                                                   
        must.append(FieldCondition(key="category", match=MatchValue(value=category.strip().lower())))

    if size:
        must.append(FieldCondition(key="sizes", match=MatchAny(any=[size])))
    budget_range = normalize_budget(budget)
    if budget_range:
        min_value = budget_range.get("min")
        max_value = budget_range.get("max")
        if min_value is not None and max_value is not None:
            must.append(FieldCondition(key="price", range=Range(gte=min_value, lte=max_value)))
        elif max_value is not None:
            must.append(FieldCondition(key="price", range=Range(lte=max_value)))
        elif min_value is not None:
            must.append(FieldCondition(key="price", range=Range(gte=min_value)))

    print("\nFILTERS APPLIED:")
    print(must)

    response = client.query_points(
        collection_name=COLLECTION,
        prefetch=[
            Prefetch(query=query_dense, using="dense", limit=top_k, filter=Filter(must=must)),
            Prefetch(
                query=SparseVector(indices=query_sparse.indices.tolist(), values=query_sparse.values.tolist()),
                using="sparse", limit=top_k, filter=Filter(must=must),
            ),
        ],
        query=FusionQuery(fusion=Fusion.RRF),
        limit=top_k,
    )

    candidates = response.points
    print(f"\n--- HYBRID (dense+sparse+filter, ONE call) -> {len(candidates)} candidates ---")
    for r in candidates[:10]:
        print(f"sku_id={r.payload['sku_id']}  rrf_score={r.score:.4f}")

    return candidates


def recommend(raw_query: str, gender: str = None, size: str = None, top_k: int = 5, budget: dict = None):
    """Full pipeline: Gemini extraction -> hybrid search -> rule engine -> top 5."""

    tags = extract_tags(raw_query)
    print("\nEXTRACTED TAGS:", tags)

    if budget is not None:
        tags["budget"] = budget   # structured value wins over Gemini's re-guess

    search_text = build_search_query(raw_query, tags)
    print(f"\n{'='*80}")
    print(f"[QUERY_2] KEYWORD SEARCH QUERY (BM25 sparse search):")
    print(f"  {search_text!r}")
    print(f"{'='*80}")
    print(f"[QUERY_3] VECTOR SEARCH QUERY (BGE dense semantic embedding):")
    print(f"  {raw_query!r}")
    print(f"{'='*80}")
    
    candidates = search(
        query_text=search_text,
        gender=gender,
        size=size,
        budget=tags.get("budget"),
        top_k=50,
        semantic_query=raw_query,
        category=tags.get("category"),
    )

    products = [c.payload for c in candidates]

    user_prefs = {
        "occasion": tags.get("occasion"),
        "style": tags.get("style"),
        "color": tags.get("color"),
        "fabric_comfort": tags.get("fabric_comfort"),
        "body_type": tags.get("body_type"),
        "skin_tone": tags.get("skin_tone"),
        "age_group": tags.get("age_group"),
        "budget": tags.get("budget"),
    }
    ranked = rank_products(user_prefs, products, top_k=top_k)

    products_by_sku = {p.get("sku_id"): p for p in products}
    for item in ranked:
        product = products_by_sku.get(item["sku_id"], {})
        item["name"] = product.get("product_name") or product.get("sku_id")
        item["category"] = product.get("category")
        item["brand"] = product.get("brand")
        item["price"] = product.get("price")
        item["specific_color"] = product.get("specific_color")
        item["fabric_category"] = product.get("fabric_category")
        item["occasion_primary"] = product.get("occasion_primary")
        item["occasion_tags"] = product.get("occasion_tags")
        item["style"] = product.get("style")
        item["is_new_arrival"] = product.get("is_new_arrival")

    return ranked, tags



if __name__ == "__main__":
    build_index()

    results, extracted = recommend(
        "Need an elegant saree for Onam under 5000, medium skin tone",
        gender="female",
    )

    print("\n--- FINAL TOP 5 (Gemini tags + full rule engine) ---")
    for r in results:
        print(f"{r['rank_label']}: {r['sku_id']}  final_score={r['final_score']}")