import os
import yaml
import json
import chromadb
from fastapi import APIRouter, HTTPException
from sentence_transformers import SentenceTransformer

# Local Imports
from src.app.models.feedback_request import FeedbackRequest
from src.app.scripts.gemini_service import gemini_reasoner
from src.app.scripts.schema import SchemaProvider
from src.app.utils import update_query_json 

# --- Configuration ---
with open("config.yaml", "r") as f:
    config = yaml.safe_load(f)

MODEL_PATH = config["MODEL_PATH"]
CHROMA_PATH = config["CHROMA_PATH"]
QUERIES_JSON_PATH = config.get("QUERIES_JSON_PATH", r"data/queries.json")

router = APIRouter(prefix="/sql", tags=["Feedback & Correction"])

# Load Vector DB
model = SentenceTransformer(MODEL_PATH)
client = chromadb.PersistentClient(path=CHROMA_PATH)
collection = client.get_or_create_collection(name="sql_templates")

@router.post("/feedback")
async def process_feedback(feedback: FeedbackRequest):
    if not feedback.is_correct:
        # --- Negative Feedback: AI Fix ---
        # 1. Get relevant table names from JSON for this template
        with open(QUERIES_JSON_PATH, "r") as f:
            data = json.load(f)
        target = next((item for item in data if str(item["id"]) == str(feedback.template_id)), None)
        
        # 2. Inject ONLY the necessary table schemas into Gemini
        relevant_tables = target.get("tables", []) if target else []
        schema_context = SchemaProvider.get_context(relevant_tables)

        analysis = gemini_reasoner.analyze_user_discrepancy(
            executed_sql=feedback.matched_sql,
            table_schema=schema_context,
            user_intent=feedback.user_phrase,
            user_feedback=feedback.user_comment
        )
        return {"status": "ai_correction", **analysis}

    else:
        # --- Positive Feedback: Learning ---
        # 1. Immediate retrieval fix in ChromaDB
        res = collection.get(ids=[feedback.template_id])
        if res.get("metadatas"):
            if res["metadatas"]:
                target_sql = res["metadatas"][0].get("sql")
                collection.add(
                    ids=[f"fb_{feedback.template_id}_{abs(hash(feedback.user_phrase))}"],
                    embeddings=[model.encode(feedback.user_phrase).tolist()],
                    metadatas=[{"sql": target_sql, "is_feedback": "true"}],
                    documents=[feedback.user_phrase]
                )

        # 2. Long-term persistence fix in JSON
        synced = update_query_json(feedback.template_id, feedback.user_phrase)
        
        return {"status": "success", "learned": True, "persisted": synced}