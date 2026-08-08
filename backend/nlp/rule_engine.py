

from filters.hard_filters import passes_hard_filters
from scoring.occasion import score_occasion
from scoring.style import score_style
from scoring.color import score_color
from scoring.fabric import score_fabric_comfort, apply_fabric_boost
from scoring.body_type import score_body_type
from scoring.skin_tone import score_skin_tone
from scoring.age import score_age
from scoring.budget import score_budget
from scoring.formula import combine_scores


def score_product(user_prefs: dict, product: dict) -> dict:
    if not passes_hard_filters(user_prefs, product):
        return {"sku_id": product.get("sku_id"), "final_score": -1, "eliminated": True}

    is_wedding_formal = user_prefs.get("occasion") in ("wedding_bride", "wedding_guest")

    occasion_s = score_occasion(user_prefs.get("occasion"), product.get("occasion_primary"), product.get("occasion_tags"))
    budget_s = score_budget(user_prefs.get("budget"), product.get("price", 0))
    style_s = score_style(user_prefs.get("style"), product.get("style"))
    color_s = score_color(user_prefs.get("color"), product.get("specific_color"))
    comfort_s = score_fabric_comfort(user_prefs.get("fabric_comfort"), product.get("fabric_category"), is_wedding_formal)
    comfort_s = apply_fabric_boost(user_prefs.get("occasion"), product.get("fabric_category"), comfort_s)
    body_s = score_body_type(user_prefs.get("body_type"), product.get("silhouettes"), product.get("body_type_fit"))
    skin_s = score_skin_tone(user_prefs.get("skin_tone"), product.get("color_family"), product.get("high_contrast_festive", False))
    age_s = score_age(user_prefs.get("age_group"), product.get("age_tags"))

    user_input, characteristics, business, final = combine_scores(
        occasion_s, budget_s, style_s, color_s, comfort_s,
        body_s, skin_s, age_s,
        seasonal=product.get("seasonal_score", 0.5) * 10,
        popular=product.get("bestseller_score", 0.5) * 10,
        trend_color=product.get("trend_color_score", product.get("trend_score", 0.5)) * 10,
        trend_silhouette=product.get("trend_silhouette_score", product.get("trend_score", 0.5)) * 10,
        best_fabric=product.get("best_fabric_score", 0.5) * 10,
    )

    return {
        "sku_id": product.get("sku_id"), "eliminated": False,
        "occasion_score": occasion_s, "budget_score": budget_s, "style_score": style_s,
        "color_score": color_s, "comfort_score": comfort_s, "body_score": body_s,
        "skin_score": skin_s, "age_score": age_s,
        "user_input_bucket": round(user_input, 3),
        "characteristics_bucket": round(characteristics, 3),
        "business_bucket": round(business, 3),
        "final_score": round(final, 3),
    }


def rank_products(user_prefs: dict, products: list, top_k: int = 5) -> list:
    scored = [s for s in (score_product(user_prefs, p) for p in products) if not s["eliminated"]]
    scored.sort(key=lambda x: x["final_score"], reverse=True)
    labels = ["#1 Best Match"] + ["#2-#3 Great Alternative"] * 2 + ["#4-#5 You Might Also Like"] * 2
    for i, item in enumerate(scored[:top_k]):
        item["rank_label"] = labels[i] if i < len(labels) else f"#{i+1}"
    return scored[:top_k]