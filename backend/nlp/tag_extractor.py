import json
import os
from dotenv import load_dotenv
load_dotenv()
from google import genai
from nlp.taxonomy import (
    OCCASION_TAGS, STYLE_TAGS, FABRIC_TAGS, BODY_TYPE_TAGS,
    SKIN_TONE_TAGS, AGE_TAGS, COMFORT_LEVELS,
)

client = genai.Client(
    api_key=os.environ.get("GEMINI_API_KEY")
)

CATEGORY_SYNONYMS = {
    "saree": "saree", "sari": "saree", "sarees": "saree",
    "kurta": "kurta",
    "lehenga": "lehenga", "lehnga": "lehenga",
    "dupatta": "dupatta", "chunni": "dupatta", "stole": "dupatta",
    "trouser": "trouser", "trousers": "trouser", "pant": "trouser", "pants": "trouser",
    "shirt": "shirt",
    "salwar set": "salwar set", "salwar suit": "salwar set", "salwar kameez": "salwar set",
    "dress": "dress", "gown": "dress",
    "kurta set": "kurta set",
    "indo-western": "indo-western", "indo western": "indo-western",
}

def normalize_category(value):
    if not value:
        return None
    key = str(value).strip().lower()
    return CATEGORY_SYNONYMS.get(key)

EXTRACTION_SCHEMA_HINT = {
    "occasion": "one of OCCASION_TAGS or null",
    "style": "one of STYLE_TAGS or null",
    "color": "free text specific color mentioned by user, or null",
    "fabric_comfort": "one of COMFORT_LEVELS or null",
    "body_type": "one of BODY_TYPE_TAGS or null",
    "skin_tone": "one of SKIN_TONE_TAGS or null",
    "age_group": "one of AGE_TAGS or null",
    "budget_min": "integer INR lower bound or null",
    "budget_max": "integer INR upper bound or null",
    "category": "product category e.g. saree, kurta, dress, or null",
    "height_cm_or_label": "user height/petite-tall label if mentioned, or null",
    "event_context": "free text event or relationship context like sister's marriage, family function, office party, or null",
    "formality": "free text such as festive, formal, casual, office, or null",
    "mood": "free text such as elegant, minimal, vibrant, comfortable, or null",
}

PROMPT_TEMPLATE = """You are a fashion tag extraction engine for an e-commerce search system.
You must ONLY use tags from the allowed lists below for the taxonomy fields. Never invent new tags.
For free-text fields, preserve important intent details from the user query.
If the user query does not mention a dimension, return null for it.

For budget, ALWAYS return two separate fields, never a single number:
- "budget_min": lowest acceptable price in INR, or null if no lower bound was stated
- "budget_max": highest acceptable price in INR, or null if no upper bound was stated
Examples:
  "under 5000" / "maximum 5000" / "max budget is 5000" -> budget_min: null, budget_max: 5000
  "at least 2000" / "minimum 2000" / "above 2000"       -> budget_min: 2000, budget_max: null
  "2000 to 5000" / "between 2000 and 5000"              -> budget_min: 2000, budget_max: 5000
  "around 3000" / "budget 3000" (no min/max wording)    -> budget_min: 3000, budget_max: 3000
  no budget mentioned                                    -> budget_min: null, budget_max: null

ALLOWED occasion tags: {occasions}
ALLOWED style tags: {styles}
ALLOWED fabric comfort levels: {comforts}
ALLOWED body type tags: {body_types}
ALLOWED skin tone tags: {skin_tones}
ALLOWED age group tags: {ages}

User Query:
\"\"\"{query}\"\"\"

Return JSON ONLY, no markdown fences, no explanation, matching exactly this shape:
{{
  "occasion": "",
  "style": "",
  "color": "",
  "fabric_comfort": "",
  "body_type": "",
  "skin_tone": "",
  "age_group": "",
  "budget_min": null,
  "budget_max": null,
  "category": "",
  "height_cm_or_label": "",
  "event_context": "",
  "formality": "",
  "mood": ""
}}
"""


def extract_tags(query: str) -> dict:
    prompt = PROMPT_TEMPLATE.format(
        occasions=", ".join(OCCASION_TAGS),
        styles=", ".join(STYLE_TAGS),
        comforts=", ".join(COMFORT_LEVELS),
        body_types=", ".join(BODY_TYPE_TAGS),
        skin_tones=", ".join(SKIN_TONE_TAGS),
        ages=", ".join(AGE_TAGS),
        query=query,
    )

    response = client.models.generate_content(
        model="gemini-3.1-flash-lite",
        contents=prompt
    )

    raw = response.text.strip()

    if raw.startswith("```"):
        raw = raw.strip("`")
        if raw.lower().startswith("json"):
            raw = raw[4:]
        raw = raw.strip()

    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        parsed = {k: None for k in EXTRACTION_SCHEMA_HINT}

    def clean(value, allowed=None):
        if value in (None, "", "null"):
            return None
        if allowed and value not in allowed:
            return None
        return value

    budget_min = parsed.get("budget_min")
    budget_max = parsed.get("budget_max")

    budget = None
    if budget_min is not None or budget_max is not None:
        budget = {"min": budget_min, "max": budget_max}

    return {
        "occasion": clean(parsed.get("occasion"), OCCASION_TAGS),
        "style": clean(parsed.get("style"), STYLE_TAGS),
        "color": clean(parsed.get("color")),
        "fabric_comfort": clean(parsed.get("fabric_comfort"), COMFORT_LEVELS),
        "body_type": clean(parsed.get("body_type"), BODY_TYPE_TAGS),
        "skin_tone": clean(parsed.get("skin_tone"), SKIN_TONE_TAGS),
        "age_group": clean(parsed.get("age_group"), AGE_TAGS),
        "budget": budget,   # {"min":.., "max":..} or None — matches normalize_budget's expected shape
        "category": normalize_category(clean(parsed.get("category"))),
        "height_cm_or_label": clean(parsed.get("height_cm_or_label")),
        "event_context": clean(parsed.get("event_context")),
        "formality": clean(parsed.get("formality")),
        "mood": clean(parsed.get("mood")),
    }


if __name__ == "__main__":
    test_queries = [
        "Need a saree for Onam. Budget 5000. Medium skin tone. Height 5'4.",
        "I want something simple and elegant for the office",
        "Wedding guest dress, comfortable, not too tight",
        "elegant saree for Onam under 5000, medium skin tone",
        "party wear kurta minimum 2000",
        "festive lehenga between 3000 and 8000",
    ]
    for q in test_queries:
        print(q, "->", extract_tags(q))