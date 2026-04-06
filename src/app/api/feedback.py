import yaml
import chromadb
from fastapi import APIRouter, HTTPException
from sentence_transformers import SentenceTransformer

# Local Imports
from src.app.models.feedback_request import FeedbackRequest
from src.app.scripts.gemini_service import gemini_reasoner 

# --- Configuration & Initialization ---
with open("config.yaml", "r") as f:
    config = yaml.safe_load(f)

MODEL_PATH = config["MODEL_PATH"]
CHROMA_PATH = config["CHROMA_PATH"]
CONFIDENCE_THRESHOLD = config["CONFIDENCE_THRESHOLD"]

router = APIRouter(
    prefix="",       
    tags=["Items"]         
)

# Load Model and Database
model = SentenceTransformer(MODEL_PATH)
client = chromadb.PersistentClient(path=CHROMA_PATH) # type: ignore
collection = client.get_or_create_collection(name="sql_templates")

# --- Routes ---
@router.post("/feedback")
async def process_feedback(feedback: FeedbackRequest):
    
    # CASE 1: User says "No, this is wrong"
    if not feedback.is_correct:
        # Trigger Gemini to analyze and FIX the query
        analysis = gemini_reasoner.analyze_sql_failure(
            user_text=feedback.user_phrase,
            matched_template=feedback.matched_sql or "Unknown",
            extracted_params=feedback.extracted_params or {}
        )
        
        return {
            "status": "ai_correction",
            "analysis": analysis.get("explanation"),
            "suggestion": analysis.get("fix_suggestion"),
            "corrected_sql": analysis.get("corrected_sql"), # <-- Added AI Correction
            "error_type": analysis.get("error_type")
        }

    # CASE 2: User says "Yes, this is correct" -> System Learns
    else:
        # Safety Check 1: Ensure template_id was provided
        if not feedback.template_id:
            raise HTTPException(
                status_code=400, 
                detail="Cannot process positive feedback without a valid template_id."
            )

        # Retrieve original SQL metadata for the template
        original = collection.get(ids=[feedback.template_id])
        
        # Safety Check 2: Ensure the ID actually exists in Chroma
        if not original.get("metadatas") or not original["metadatas"][0]:
            raise HTTPException(
                status_code=404, 
                detail=f"Original Template ID '{feedback.template_id}' not found in Chroma."
            )
        
        target_sql = original["metadatas"][0].get("sql")
        
        # Safety Check 3: Ensure the target SQL isn't empty
        if not target_sql:
            raise HTTPException(
                status_code=500,
                detail="Found template, but it is missing the 'sql' metadata field."
            )
        
        # Generate a unique ID for the new database entry
        new_id = f"fb_{feedback.template_id}_{abs(hash(feedback.user_phrase))}"
        
        # Add the new phrasing to the vector database
        collection.add(
            ids=[new_id],
            embeddings=[model.encode(feedback.user_phrase).tolist()],
            metadatas=[{"sql": target_sql, "is_feedback": "true"}],
            documents=[feedback.user_phrase]
        )
        
        return {"status": "updated", "message": "System learned from your phrasing!"}