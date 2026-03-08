import anthropic
import os
import sys
from dotenv import load_dotenv
from schema import SCHEMA, format_schema_for_prompt
from tools import get_table_schema, save_file, validate_sql, list_output_files, create_pipeline

load_dotenv()

client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

# ─────────────────────────────────────────
# SYSTEM PROMPT
# ─────────────────────────────────────────
SYSTEM_PROMPT = f"""You are a Lead Data Engineer at a Big Tech firm,
expert in SQL, Snowflake, Databricks, and Airflow.

{format_schema_for_prompt(SCHEMA)}

Guidelines:
- Always call get_table_schema() BEFORE generating SQL
- Always call validate_sql() AFTER generating SQL
- Always call save_file() when user wants to save SQL output
- When user asks to create a pipeline, DAG, or schedule a query:
  → First generate and validate the SQL if not already done
  → Then call create_pipeline() with all required parameters
  → Convert natural language schedule to cron e.g. "every day at 7am" = "0 7 * * *"
  → Extract input tables from the SQL automatically
- For tables in the schema above, always call get_table_schema() for exact columns
- For tables NOT in the schema above:
  → generate SQL using common sense column names (id, name, amount, created_at etc)
  → clearly state your assumptions e.g. "I assumed orders has: id, customer_id, amount, created_at"
  → invite user to correct if column names are wrong
  → ask clarifying questions ONLY if the request is truly ambiguous
  → never refuse to generate SQL just because table is unknown
- Always use Snowflake compatible syntax
- Explain key decisions after generating SQL or pipelines"""


# ─────────────────────────────────────────
# TOOL DEFINITIONS — tells Claude what tools exist
# ─────────────────────────────────────────
TOOL_DEFINITIONS = [
    {
        "name": "get_table_schema",
        "description": "Look up schema for a specific table including column names, data types and descriptions. Always call this BEFORE generating SQL to ensure correct column names.",
        "input_schema": {
            "type": "object",
            "properties": {
                "table_name": {
                    "type": "string",
                    "description": "Exact name of the table to look up e.g. subscribers, watch_history, content"
                }
            },
            "required": ["table_name"]
        }
    },
    {
        "name": "save_file",
        "description": "Save generated SQL or any code to the output folder. Call this after generating and validating SQL when user wants to save the result.",
        "input_schema": {
            "type": "object",
            "properties": {
                "filename": {
                    "type": "string",
                    "description": "Name of file with extension e.g. top_subscribers.sql"
                },
                "content": {
                    "type": "string",
                    "description": "Complete file content to save"
                }
            },
            "required": ["filename", "content"]
        }
    },
    {
        "name": "validate_sql",
        "description": "Check generated SQL for issues before saving. Always call this AFTER generating SQL and BEFORE saving.",
        "input_schema": {
            "type": "object",
            "properties": {
                "sql": {
                    "type": "string",
                    "description": "Complete SQL query to validate"
                }
            },
            "required": ["sql"]
        }
    },
    {
        "name": "list_output_files",
        "description": "List all files saved in the output folder. Use when user asks what files have been generated or saved.",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },
    {
        "name": "create_pipeline",
        "description": "Generate a complete Airflow pipeline including DAG file, YAML config (dev/stage/prod), and Databricks notebook. Call this when user asks to create a pipeline, DAG, or automate a SQL query on a schedule.",
        "input_schema": {
            "type": "object",
            "properties": {
                "pipeline_name": {
                    "type": "string",
                    "description": "Short descriptive name for the pipeline e.g. top_subscribers, premium_watch_time"
                },
                "schedule_interval": {
                    "type": "string",
                    "description": "Cron schedule expression e.g. 0 7 * * * for 7am daily"
                },
                "sql": {
                    "type": "string",
                    "description": "Complete SQL query this pipeline will run"
                },
                "input_tables": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of input table names used in the SQL e.g. ['subscribers', 'watch_history']"
                },
                "output_table": {
                    "type": "string",
                    "description": "Name of the output/destination table e.g. top_subscribers_daily"
                },
                "description": {
                    "type": "string",
                    "description": "Plain English description of what this pipeline does"
                }
            },
            "required": ["pipeline_name", "schedule_interval", "sql", "input_tables", "output_table", "description"]
        }
    }
]


# ─────────────────────────────────────────
# TOOL EXECUTOR — runs the actual function
# ─────────────────────────────────────────
def execute_tool(tool_name: str, tool_input: dict) -> str:
    """
    Receives tool name and inputs from Claude
    Calls the actual Python function
    Returns result as string back to Claude
    """
    print(f"\n[Tool Call] {tool_name}({tool_input})\n")

    if tool_name == "get_table_schema":
        return get_table_schema(tool_input["table_name"])

    elif tool_name == "save_file":
        return save_file(tool_input["filename"], tool_input["content"])

    elif tool_name == "validate_sql":
        return validate_sql(tool_input["sql"])

    elif tool_name == "list_output_files":
        return list_output_files()

    elif tool_name == "create_pipeline":
        return create_pipeline(
            pipeline_name=tool_input["pipeline_name"],
            schedule_interval=tool_input["schedule_interval"],
            sql=tool_input["sql"],
            input_tables=tool_input["input_tables"],
            output_table=tool_input["output_table"],
            description=tool_input["description"]
        )

    else:
        return f"Unknown tool: {tool_name}"


# ─────────────────────────────────────────
# MAIN AGENT LOOP
# ─────────────────────────────────────────
conversation_history = []

print("=" * 60)
print("DE Copilot — AI Data Engineering Assistant (Stage 4)")
print("=" * 60)
print("Commands:")
print("  Ask anything       → plain English question")
print("  review <file>      → review a SQL file")
print("  list files         → show saved output files")
print("  quit               → exit")
print("=" * 60 + "\n")

user_input = input("You: ").strip()

# ── OUTER LOOP — conversation continues ──
while user_input.lower() != "quit":

    if user_input == "":
        user_input = input("You: ").strip()
        continue

    # Handle file review command
    if user_input.lower().startswith("review "):
        file_path = user_input[7:].strip()
        try:
            with open(file_path, "r") as f:
                file_content = f.read()
            user_input = f"Review this SQL file ({file_path}):\n\n{file_content}"
        except FileNotFoundError:
            print(f"File not found: {file_path}\n")
            user_input = input("You: ").strip()
            continue

    # Add user message to history
    conversation_history.append({
        "role": "user",
        "content": user_input
    })

    # ── INNER LOOP — handle tool calls until Claude finishes ──
    while True:
        try:
            response = client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=4096,
                system=SYSTEM_PROMPT,
                tools=TOOL_DEFINITIONS,
                messages=conversation_history
            )

            # ── Claude wants to call a tool ──
            if response.stop_reason == "tool_use":

                # Add Claude's response to history
                conversation_history.append({
                    "role": "assistant",
                    "content": response.content
                })

                # Process ALL tool calls in this response
                tool_results = []
                for block in response.content:
                    if block.type == "tool_use":
                        # Execute the tool
                        result = execute_tool(block.name, block.input)

                        # Collect result
                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": result
                        })

                # Send all tool results back to Claude
                conversation_history.append({
                    "role": "user",
                    "content": tool_results
                })

                # Continue inner loop — Claude thinks again

            # ── Claude finished, return text response ──
            elif response.stop_reason == "end_turn":

                # Extract text from response
                reply = ""
                for block in response.content:
                    if hasattr(block, "text"):
                        reply += block.text

                # Add to history
                conversation_history.append({
                    "role": "assistant",
                    "content": reply
                })

                print(f"\nDE Copilot: {reply}\n")
                break  # exits inner loop only, outer loop continues

        except Exception as e:
            print(f"\nError: {e}\n")
            break

    # Ask for next input — outer loop continues
    user_input = input("You: ").strip()

print("\nGoodbye!")
