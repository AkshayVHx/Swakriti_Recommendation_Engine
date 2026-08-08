import os
import json
from typing import Any, Optional

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from dotenv import load_dotenv
from google import genai

from search.recommend_engine import (
    build_index,
    recommend,
    update_single_product,
    delete_product,
    get_vector_db_status,
)
from erp.erp_webhook import handle_erp_webhook
from nlp.answer_extractor import extract_answers
from search.query_builder import (
    state_to_gender,
    state_to_size,
    state_to_query,
    build_clean_query_with_gemini,
)
from voice.live_token import create_live_token


load_dotenv()

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  
    allow_methods=["*"],
    allow_headers=["*"],
)

client = genai.Client(api_key=os.environ.get("GOOGLE_API_KEY"))

index_ready = False


@app.on_event("startup")
def startup_event():
    global index_ready
    status = get_vector_db_status()
    print("[startup] checking vector DB status...")
    print(
        f"[startup] collection='{status['collection']}' exists={status['exists']} count={status['count']}"
    )

    if status["exists"] and status["count"] > 0:
        print(f"[startup] vector DB already populated with {status['count']} points. Skipping rebuild.")
        index_ready = True
        return

    print("[startup] vector DB is missing or empty. Initializing index on startup.")
    ensure_index()


def ensure_index():
    global index_ready
    if not index_ready:
        print("[ensure_index] loading vector index...")
        build_index()
        status = get_vector_db_status()
        print(
            f"[ensure_index] vector DB ready: collection='{status['collection']}' exists={status['exists']} count={status['count']}"
        )
        index_ready = True




class ParseAnswerRequest(BaseModel):
    transcript: str = ""
    remaining_questions: list[dict] = []
    current_question_id: Optional[str] = None
    known_state: dict[str, Any] = {}


class RecommendRequest(BaseModel):
    budget: Optional[Any] = None   

    class Config:
        extra = "allow"

class TTSRequest(BaseModel):
    text: str


@app.post("/live-token")
def live_token_endpoint():
    return {"token": create_live_token()}


@app.post("/erp-webhook")
async def erp_webhook(request: Request):
    """
    ERPNext calls this URL automatically whenever an Item is created,
    updated, or deleted — configured in ERPNext under:
    Setup > Integrations > Webhook.

    We only touch the ONE changed product in Qdrant — no full rebuild.
    """
    raw_body = await request.body()
    try:
        payload = json.loads(raw_body) if raw_body else {}
    except json.JSONDecodeError:
        payload = {}

    try:
        item_code, action = handle_erp_webhook(payload, ensure_index, update_single_product, delete_product)
        return {"status": "ok", "item_code": item_code, "action": action}
    except ValueError as exc:
        return JSONResponse(status_code=400, content={"status": "error", "message": str(exc)})
    except Exception as exc:
        print(f"[erp_webhook] error: {exc}")
        return JSONResponse(status_code=500, content={"status": "error", "message": str(exc)})


@app.post("/parse-answer")
def parse_answer(body: ParseAnswerRequest):
    extracted, raw_extracted, rejected, low_confidence, product_category = extract_answers(
        client, body.transcript, body.remaining_questions, body.current_question_id, body.known_state
    )

    return {
        "extracted": extracted,
        "raw_extracted": raw_extracted,
        "rejected": rejected,
        "low_confidence": low_confidence,
        "product_category": product_category,
    }

BUDGET_LABEL_MAP = {
    "Under 1000":   {"min": 0,     "max": 1000},
    "1000-2500":    {"min": 1000,  "max": 2500},
    "2500-5000":    {"min": 2500,  "max": 5000},
    "5000-10000":   {"min": 5000,  "max": 10000},
    "10000+":       {"min": 10000, "max": None},
}

def normalize_budget(budget):
    if isinstance(budget, dict):
        return budget
    if isinstance(budget, str):
        return BUDGET_LABEL_MAP.get(budget)
    return None

@app.post("/recommend")
def recommend_endpoint(body: RecommendRequest):
    state = body.dict()
    state["budget"] = normalize_budget(state.get("budget")) 

    
    query_text = build_clean_query_with_gemini(client, state)
    if not query_text:
        query_text = state_to_query(state)

    gender = state_to_gender(state)
    size = state_to_size(state)
    budget = state.get("budget")   # already {"min":..,"max":..} from parse-answer

    print(f"[recommend] built query from state: {query_text!r}")

    if not query_text:
        return {"recommendations": [], "extracted_tags": {}, "query_used": ""}

    try:
        ensure_index()
        results, extracted_tags = recommend(
            query_text,
            gender=gender,
            size=size,
            top_k=5,
            budget=budget,   # new: structured override
        )
    except Exception as exc:
        print(f"[recommend] error: {exc}")
        return JSONResponse(status_code=500, content={"recommendations": [], "error": str(exc)})

    print(f"[recommend] query_used={query_text!r} gender={gender} size={size}")

    return {
        "recommendations": results,
        "extracted_tags": extracted_tags,
        "query_used": query_text
    }


import time

@app.post("/tts")
def tts_endpoint(body: TTSRequest):
    t0 = time.time()
    if not body.text.strip():
        return JSONResponse(status_code=400, content={"error": "text is required"})
    try:
        interaction = client.interactions.create(
            model="gemini-3.1-flash-tts-preview",
            input=body.text,
            response_format={"type": "audio"},
            generation_config={"speech_config": [{"voice": "Kore"}]},
        )
        print(f"[tts] Google call took {time.time()-t0:.2f}s")
        return {"audio": interaction.output_audio.data}
    except Exception as exc:
        print(f"[tts] error: {exc}")
        return JSONResponse(status_code=500, content={"error": str(exc)})