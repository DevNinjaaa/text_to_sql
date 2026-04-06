import json
import os
import yaml
import chromadb
from fastapi import APIRouter
from sentence_transformers import SentenceTransformer

from src.app.models.SQLresponse import SQLResponse
from src.app.models.query_response import QueryRequest
from src.app.scripts.forbid_actions import process_query
from src.app.scripts.extract_variables import extract_variables

# Load Config
with open("config.yaml", "r") as f:
    config = yaml.safe_load(f)

# Load Queries JSON once at startup to save I/O time per request
QUERIES_PATH = "data/queries.json"
with open(QUERIES_PATH, "r") as f:
    TEMPLATES_DATA = json.load(f)

router = APIRouter(prefix="", tags=["Items"])

model_name = 'sentence-transformers/all-MiniLM-L6-v2'
custom_path = "LLMmodels"

model_path = config["MODEL_PATH"]

if os.path.exists(model_path):
    # Load directly from your specific local folder
    model = SentenceTransformer(model_path)
    print(f"Loaded model locally from {model_path}")
else:
    # If the path doesn't exist yet, download it to that path
    print("Local model path not found. Downloading...")
    model = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')
    # Save it specifically to your path for next time
    model.save(model_path)

client = chromadb.PersistentClient(path=config["CHROMA_PATH"]) # type: ignore
collection = client.get_or_create_collection(name="sql_templates")
CONFIDENCE_THRESHOLD = config["CONFIDENCE_THRESHOLD"]

@router.post("/ask", response_model=SQLResponse)
async def ask_sql(request: QueryRequest):
    user_input = request.user_text.strip()
    
    # 1. Security Check
    result = process_query(user_input)
    if result.get("status") == "BLOCKED":
        return SQLResponse(
            status="blocked",
            message=result.get("reason") or "Action forbidden."
        )

    # 2. Vector Search
    query_emb = model.encode(user_input).tolist()
    results = collection.query(query_embeddings=[query_emb], n_results=1)

    if not results["ids"] or not results["ids"][0]:
        return SQLResponse(status="no_match", message="No templates found.")

    final_id = int(results["ids"][0][0])
    final_dist = float(results["distances"][0][0]) if results["distances"] else 1.0

    # Confidence Check
    if final_dist > CONFIDENCE_THRESHOLD:
        return SQLResponse(
            status="low_confidence", 
            message="Match found but confidence is too low.", 
            distance=final_dist
        )

    # 3. Match with JSON Template
    matched_template = next((item for item in TEMPLATES_DATA if item["id"] == final_id), None)
    
    if not matched_template:
        return SQLResponse(status="error", message=f"Template ID {final_id} not found.")

    # 4. Extract and Format
    required_fields = matched_template.get("required", [])
    raw_query = matched_template.get("query", "")
    
    variables = {}
    if required_fields:
        variables = extract_variables(user_input, required_fields)
        print(variables)
        
        # Validate all required fields were found
        missing = [f for f in required_fields if f not in variables]
        if missing:
            return SQLResponse(
                status="missing_params", 
                message=f"Please provide: {', '.join(missing)}",
                extracted_params=variables
            )
    
    try:
        # String interpolation
        final_sql = raw_query.format(**variables)
    except Exception as e:
        return SQLResponse(status="error", message=f"SQL Generation failed: {str(e)}")

    return SQLResponse(
        status="success",
        message="Match found.",
        matched_sql=final_sql,
        template_id=str(final_id),
        distance=final_dist,
        extracted_params=variables
    )