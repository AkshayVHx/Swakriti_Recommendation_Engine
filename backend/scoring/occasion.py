from nlp.taxonomy import OCCASION_ADJACENCY


def score_occasion(user_occasion, product_primary, product_secondary=None):
    product_secondary = product_secondary or []
    if not user_occasion:
        return 5.0
    if product_primary == user_occasion:
        return 10.0
    adj = OCCASION_ADJACENCY.get(user_occasion, set())
    if product_primary in adj or any(s in adj for s in product_secondary):
        return 5.0
    if user_occasion in product_secondary:
        return 5.0
    return 0.0