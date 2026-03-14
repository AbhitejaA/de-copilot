import os
from schema import SCHEMA, format_schema_for_prompt
from dag_generator import generate_pipeline
from rag import add_to_knowledge_base, search_knowledge_base


def get_table_schema(table_name: str) -> str:
    """
    Looks up a specific table's schema.
    Returns schema as readable text or error if table not found.
    """
    if table_name in SCHEMA:
        table = SCHEMA[table_name]
        result = f"Table: {table_name}\n"
        result += f"Description: {table['description']}\n"
        result += "Columns:\n"
        for col_name, col_info in table["columns"].items():
            result += f"  - {col_name} ({col_info['type']}): {col_info['description']}\n"
        return result
    else:
        available = ", ".join(SCHEMA.keys())
        return f"Table '{table_name}' not found. Available tables: {available}"


def save_file(filename: str, content: str) -> str:
    """
    Saves generated SQL or any content to the output folder.
    Creates output folder if it doesn't exist.
    """
    output_dir = "output"

    # Create output folder if it doesn't exist
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    filepath = os.path.join(output_dir, filename)

    with open(filepath, "w") as f:
        f.write(content)
    # Auto index in knowledge base
    add_to_knowledge_base(filename, content)
    return f"File saved: {filepath} and indexed in knowledge base"


def validate_sql(sql: str) -> str:
    """
    Basic SQL validation without running it.
    Checks for common issues and table/column references.
    """
    issues = []

    # Check if SQL is empty
    if not sql.strip():
        return "Validation failed: SQL is empty"

    sql_upper = sql.upper()

    # Check for basic SQL structure
    if "SELECT" not in sql_upper and "INSERT" not in sql_upper \
            and "UPDATE" not in sql_upper and "ALTER" not in sql_upper:
        issues.append("No SELECT/INSERT/UPDATE/ALTER found — may not be valid SQL")

    # Check if referenced tables exist in schema
    for table_name in SCHEMA.keys():
        if table_name.upper() in sql_upper:
            issues.append(f"✅ References known table: {table_name}")

    # Check for common Snowflake anti-patterns
    if "SELECT *" in sql_upper:
        issues.append("⚠️  Uses SELECT * — consider selecting specific columns")

    if "LIMIT" not in sql_upper and "SELECT" in sql_upper:
        issues.append("⚠️  No LIMIT clause — could return large result set")

    if not issues:
        return "✅ SQL looks valid — no issues found"

    return "\n".join(issues)


def list_output_files() -> str:
    """
    Lists all files saved in the output folder.
    """
    output_dir = "output"

    if not os.path.exists(output_dir):
        return "No output folder yet — no files saved"

    files = os.listdir(output_dir)

    if not files:
        return "Output folder is empty"

    result = "Files in output folder:\n"
    for f in files:
        result += f"  - {f}\n"

    return result


def create_pipeline(
    pipeline_name: str,
    schedule_interval: str,
    sql: str,
    input_tables: list,
    output_table: str,
    description: str
) -> str:
    """
    Generates complete pipeline — DAG, YAML config, Databricks notebook.
    Calls dag_generator.py and saves all 3 files to output folder.
    """
    return generate_pipeline(
        pipeline_name=pipeline_name,
        schedule_interval=schedule_interval,
        sql=sql,
        input_tables=input_tables,
        output_table=output_table,
        description=description
    )

def search_files(query: str) -> str:
    """
    Search knowledge base for relevant files.
    """
    return search_knowledge_base(query)