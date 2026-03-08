SCHEMA = {
    "subscribers": {
        "description": "Contains all Peacock subscriber account information",
        "columns": {
            "subscriber_id":    {"type": "STRING",    "description": "Unique identifier for each subscriber"},
            "email":            {"type": "STRING",    "description": "Subscriber email address"},
            "subscription_tier":{"type": "STRING",    "description": "Plan type: FREE, PREMIUM, or BUNDLE"},
            "is_active":        {"type": "BOOLEAN",   "description": "Whether subscription is currently active"},
            "created_at":       {"type": "TIMESTAMP", "description": "When the subscriber joined Peacock"}
        }
    },
    "watch_history": {
        "description": "Records every content viewing event by subscribers",
        "columns": {
            "watch_event_id":   {"type": "STRING",    "description": "Unique identifier for each watch event"},
            "subscriber_id":    {"type": "STRING",    "description": "Foreign key to subscribers table"},
            "content_id":       {"type": "STRING",    "description": "Foreign key to content catalog"},
            "watch_time_minutes":{"type": "INTEGER",  "description": "Duration watched in minutes"},
            "watched_at":       {"type": "TIMESTAMP", "description": "When the viewing event occurred"},
            "device_type":      {"type": "STRING",    "description": "Device used: MOBILE, TV, WEB, TABLET"}
        }
    },
    "content": {
        "description": "Peacock content catalog with show and movie metadata",
        "columns": {
            "content_id":       {"type": "STRING",    "description": "Unique identifier for each piece of content"},
            "title":            {"type": "STRING",    "description": "Title of the show or movie"},
            "content_type":     {"type": "STRING",    "description": "Type: MOVIE, SERIES, LIVE, NEWS"},
            "genre":            {"type": "STRING",    "description": "Genre: DRAMA, COMEDY, SPORTS, NEWS etc"},
            "release_date":     {"type": "DATE",      "description": "When content was released on Peacock"},
            "is_premium":       {"type": "BOOLEAN",   "description": "Whether content requires premium subscription"}
        }
    }
}


def format_schema_for_prompt(schema: dict) -> str:
    """
    Converts schema dictionary into readable text for Claude's system prompt.
    In real world, this would query Unity Catalog instead of reading a dict.
    """
    formatted = "DATABASE SCHEMA:\n\n"

    for table_name, table_info in schema.items():
        formatted += f"Table: {table_name}\n"
        formatted += f"Description: {table_info['description']}\n"
        formatted += "Columns:\n"

        for col_name, col_info in table_info["columns"].items():
            formatted += f"  - {col_name} ({col_info['type']}): {col_info['description']}\n"

        formatted += "\n"

    return formatted
