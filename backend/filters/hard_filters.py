from nlp.taxonomy import OCCASION_HARD_BLOCK

def passes_hard_filters(user_prefs, product):
    user_occasion = user_prefs.get("occasion")
    product_occasion = product.get("occasion_primary")

    if user_occasion and product_occasion in OCCASION_HARD_BLOCK.get(user_occasion, set()):
        return False
    if user_occasion == "kidswear" and "kidswear" not in (product.get("occasion_tags") or []):
        return False
    return True