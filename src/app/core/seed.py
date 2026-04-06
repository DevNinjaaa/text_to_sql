import json
from pathlib import Path
from sentence_transformers import SentenceTransformer
from src.app.core.dp import collection
import os

q_path = os.path.join("data","queries.json")


def seed_database(model: SentenceTransformer, queries_path: str = q_path):
    """
    Seed ChromaDB collection from a JSON file.
    
    Logic:
    1. Only add queries that are not already in the collection (by ID).
    2. Each query stores 'user_text' embedding for semantic search.
    3. 'required' fields are stored as a comma-separated string in metadata.
    """

    queries_file = Path(queries_path)
    if not queries_file.exists():
        print(f"Error: {queries_file} not found at {queries_file.absolute()}")
        return

    # Load queries from JSON
    with open(queries_file, "r", encoding="utf-8") as f:
        queries = json.load(f)

    # Fetch existing IDs in the collection to avoid duplicates
    try:
        existing_entries = collection.get()
        existing_ids = set(existing_entries.get("ids", []))
    except Exception as e:
        print(f"Note: Could not fetch existing IDs ({e}), proceeding with empty set.")
        existing_ids = set()

    ids_to_add, embeds, metadatas, docs = [], [], [], []

    for entry in queries:
        uid = str(entry.get("id"))
        sql_template = entry.get("query")
        description = entry.get("user_text")
        required_list = entry.get("required", [])

        # Skip invalid entries
        if not uid or not sql_template or not description:
            continue

        # Skip queries already in DB
        if uid in existing_ids:
            continue


        entry_metadata = {
            "sql": sql_template
        }

        if required_list:
            entry_metadata["required"] = ", ".join(required_list)

        embedding = model.encode(description).tolist()

        ids_to_add.append(uid)
        embeds.append(embedding)
        metadatas.append(entry_metadata)
        docs.append(description)

    if ids_to_add:
        collection.add(
            ids=ids_to_add,
            embeddings=embeds,
            metadatas=metadatas,
            documents=docs
        )
        print(f"Seeding complete: {len(ids_to_add)} new queries added.")
    else:
        print("No new queries to add; database is up to date.")