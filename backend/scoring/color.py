from nlp.taxonomy import COLOR_FAMILIES, NEUTRAL_FAMILY


def _family(color_name):
    if not color_name:
        return None
    c = color_name.strip().lower()
    for fam, members in COLOR_FAMILIES.items():
        if c in members:
            return fam
    return None


def score_color(user_color, product_color):
    if not user_color:
        return 5.0
    u = user_color.strip().lower()
    p = (product_color or "").strip().lower()
    if not p:
        return 5.0
    if u == p:
        return 10.0

    p_fam = _family(p)
    u_fam = _family(u) or u

    if p_fam == NEUTRAL_FAMILY:
        return 10.0 if u_fam == NEUTRAL_FAMILY else 5.0
    if p_fam == u_fam:
        return 5.0
    return 0.0