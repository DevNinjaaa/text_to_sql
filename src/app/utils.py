import json
import yaml


def update_query_json(template_id, new_user_text):
    """Clones the template logic and saves the new user phrasing to JSON."""
    try:

        with open("config.yaml", "r") as f:
            config = yaml.safe_load(f)
        QUERIES_JSON_PATH = config["QUERIES_JSON_PATH"]
        with open(QUERIES_JSON_PATH, "r") as f:
            data = json.load(f)

        # Match ID (handling string/int mismatch)
        target = next((item for item in data if str(item["id"]) == str(template_id)), None)

        if target:
            new_entry = {
                "id": f"{target['id']}_fb_{abs(hash(new_user_text)) % 10000}",
                "query": target["query"],
                "required": target.get("required", []),
                "tables": target.get("tables", []), # Preserves your table mapping
                "user_text": new_user_text,
                "is_reinforced": True
            }
            data.append(new_entry)

            with open(QUERIES_JSON_PATH, "w") as f:
                json.dump(data, f, indent=4)
            return True
    except Exception as e:
        print(f"JSON Sync Error: {e}")
        return False