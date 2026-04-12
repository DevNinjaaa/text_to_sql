import os
import uvicorn
from fastapi import FastAPI
from sentence_transformers import SentenceTransformer
from src.app.core.config import MODEL_PATH
from src.app.core.seed import seed_database
from src.app.api.ask import router as askRouter
from src.app.api.feedback import router as feedbackRouter

app = FastAPI(title="Safe NL2SQL Interface")

# Include routers
app.include_router(askRouter)
app.include_router(feedbackRouter)

# Load embedding model
model = SentenceTransformer(MODEL_PATH)
path  = os.path.join("data","queries.json")
@app.on_event("startup")
async def startup_event():
    seed_database(model,path)

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)