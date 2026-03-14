"""
app.py — Stage 6 (Enhanced)
DE Copilot — AI Data Engineering Assistant
Dark terminal aesthetic, SQL highlighting, downloads, pipeline visualization
Run with: streamlit run app.py
"""

import streamlit as st
import anthropic
import os
from dotenv import load_dotenv
from schema import SCHEMA, format_schema_for_prompt
from tools import get_table_schema, save_file, validate_sql, list_output_files, create_pipeline, search_files

load_dotenv()

# ─────────────────────────────────────────
# PAGE CONFIG
# ─────────────────────────────────────────
st.set_page_config(
    page_title="DE Copilot",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ─────────────────────────────────────────
# CUSTOM CSS — dark terminal aesthetic
# ─────────────────────────────────────────
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;600&family=Inter:wght@400;500;600&display=swap');

    .stApp { background-color: #0d1117; color: #e6edf3; font-family: 'Inter', sans-serif; }
    [data-testid="stSidebar"] { background-color: #161b22; border-right: 1px solid #30363d; }

    .de-header {
        background: linear-gradient(135deg, #0d1117 0%, #161b22 100%);
        border: 1px solid #30363d;
        padding: 1.25rem 1.5rem;
        margin-bottom: 1.5rem;
        border-radius: 8px;
        display: flex;
        align-items: center;
    }
    .de-title {
        font-family: 'JetBrains Mono', monospace;
        font-size: 1.6rem;
        font-weight: 600;
        color: #58a6ff;
        margin: 0;
    }
    .de-subtitle {
        font-size: 0.8rem;
        color: #8b949e;
        margin: 0;
        font-family: 'JetBrains Mono', monospace;
    }
    .de-badge {
        background: #1f6feb22;
        border: 1px solid #1f6feb;
        color: #58a6ff;
        padding: 3px 12px;
        border-radius: 20px;
        font-size: 0.7rem;
        font-family: 'JetBrains Mono', monospace;
        letter-spacing: 1px;
        margin-left: auto;
    }
    .sidebar-label {
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.7rem;
        color: #8b949e;
        letter-spacing: 1px;
        text-transform: uppercase;
        margin-bottom: 0.5rem;
        display: block;
    }
    .tool-call {
        background: #1c2128;
        border-left: 3px solid #3fb950;
        border-radius: 0 4px 4px 0;
        padding: 0.35rem 0.6rem;
        margin: 0.2rem 0;
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.75rem;
        color: #3fb950;
    }
    .pipeline-card {
        background: #161b22;
        border: 1px solid #30363d;
        border-radius: 8px;
        padding: 1rem;
    }
    .pipeline-node {
        background: #21262d;
        border: 1px solid #388bfd44;
        border-radius: 4px;
        padding: 4px 12px;
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.75rem;
        color: #58a6ff;
        display: inline-block;
        margin: 2px;
    }
    .welcome-box {
        background: #161b22;
        border: 1px solid #30363d;
        border-radius: 8px;
        padding: 1.25rem;
        margin-bottom: 1rem;
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.82rem;
        color: #8b949e;
        line-height: 2;
    }
    .stDownloadButton button {
        background-color: #1f6feb11 !important;
        color: #58a6ff !important;
        border: 1px solid #1f6feb55 !important;
        border-radius: 5px !important;
        font-family: 'JetBrains Mono', monospace !important;
        font-size: 0.75rem !important;
        width: 100% !important;
        text-align: left !important;
        padding: 0.3rem 0.6rem !important;
    }
    .stDownloadButton button:hover {
        background-color: #1f6feb33 !important;
        border-color: #58a6ff !important;
    }
    .stButton button {
        background-color: #21262d !important;
        color: #8b949e !important;
        border: 1px solid #30363d !important;
        border-radius: 5px !important;
        font-size: 0.8rem !important;
    }
    .stButton button:hover { color: #e6edf3 !important; border-color: #58a6ff !important; }
    [data-testid="stMetricValue"] { color: #58a6ff !important; font-family: 'JetBrains Mono', monospace !important; }
    [data-testid="stMetricLabel"] { color: #8b949e !important; font-size: 0.75rem !important; }
    #MainMenu {visibility: hidden;} footer {visibility: hidden;} header {visibility: hidden;}
</style>
""", unsafe_allow_html=True)


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
- Keep explanations concise and technical
 When user asks specific questions about file contents
  (cron schedules, table names, SQL details, config values)
  → always call search_files() not list_output_files()
  → list_output_files only returns names, not contents
"""


# ─────────────────────────────────────────
# TOOL DEFINITIONS
# ─────────────────────────────────────────
TOOL_DEFINITIONS = [
    {
        "name": "get_table_schema",
        "description": "Look up schema for a specific table. Always call BEFORE generating SQL.",
        "input_schema": {
            "type": "object",
            "properties": {"table_name": {"type": "string"}},
            "required": ["table_name"]
        }
    },
    {
        "name": "save_file",
        "description": "Save generated SQL or code to output folder. Call after validating SQL.",
        "input_schema": {
            "type": "object",
            "properties": {
                "filename": {"type": "string"},
                "content": {"type": "string"}
            },
            "required": ["filename", "content"]
        }
    },
    {
        "name": "validate_sql",
        "description": "Validate SQL for issues. Always call AFTER generating, BEFORE saving.",
        "input_schema": {
            "type": "object",
            "properties": {"sql": {"type": "string"}},
            "required": ["sql"]
        }
    },
    {
        "name": "list_output_files",
        "description": "List all saved files in output folder.",
        "input_schema": {"type": "object", "properties": {}, "required": []}
    },
    {
        "name": "create_pipeline",
        "description": "Generate complete Airflow pipeline: DAG, YAML config, Databricks notebook.",
        "input_schema": {
            "type": "object",
            "properties": {
                "pipeline_name": {"type": "string"},
                "schedule_interval": {"type": "string"},
                "sql": {"type": "string"},
                "input_tables": {"type": "array", "items": {"type": "string"}},
                "output_table": {"type": "string"},
                "description": {"type": "string"}
            },
            "required": ["pipeline_name", "schedule_interval", "sql", "input_tables", "output_table", "description"]
        }
    },
    {
        "name": "search_files",
        "description": "Search knowledge base to find CONTENTS of past generated files. Call this when user asks specific questions about what is INSIDE files — cron schedules, table names, SQL queries, pipeline configurations. list_output_files only returns filenames, search_files returns actual file contents.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search query e.g. 'daily subscriber pipeline' or 'what tables does my pipeline use'"
                }
            },
            "required": ["query"]
        }
    }
]


# ─────────────────────────────────────────
# TOOL EXECUTOR
# ─────────────────────────────────────────
def execute_tool(tool_name: str, tool_input: dict) -> str:
    if tool_name == "get_table_schema":
        return get_table_schema(tool_input["table_name"])
    elif tool_name == "save_file":
        result = save_file(tool_input["filename"], tool_input["content"])
        st.session_state.files_generated += 1
        return result
    elif tool_name == "validate_sql":
        return validate_sql(tool_input["sql"])
    elif tool_name == "list_output_files":
        return list_output_files()
    elif tool_name == "create_pipeline":
        result = create_pipeline(
            pipeline_name=tool_input["pipeline_name"],
            schedule_interval=tool_input["schedule_interval"],
            sql=tool_input["sql"],
            input_tables=tool_input["input_tables"],
            output_table=tool_input["output_table"],
            description=tool_input["description"]
        )
        st.session_state.pipelines_generated += 1
        st.session_state.files_generated += 3
        st.session_state.last_pipeline = {
            "name": tool_input["pipeline_name"],
            "schedule": tool_input["schedule_interval"],
            "input_tables": tool_input["input_tables"],
            "output_table": tool_input["output_table"],
        }
        return result
    elif tool_name == "search_files":
        return search_files(tool_input["query"])
    return f"Unknown tool: {tool_name}"


# ─────────────────────────────────────────
# AGENT
# ─────────────────────────────────────────
def run_agent(user_input: str):
    client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
    st.session_state.conversation_history.append({"role": "user", "content": user_input})
    tool_calls_made = []

    while True:
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=4096,
            system=SYSTEM_PROMPT,
            tools=TOOL_DEFINITIONS,
            messages=st.session_state.conversation_history
        )

        if response.stop_reason == "tool_use":
            st.session_state.conversation_history.append({
                "role": "assistant", "content": response.content
            })
            tool_results = []
            for block in response.content:
                if block.type == "tool_use":
                    tool_calls_made.append(block.name)
                    result = execute_tool(block.name, block.input)
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": result
                    })
            st.session_state.conversation_history.append({
                "role": "user", "content": tool_results
            })

        elif response.stop_reason == "end_turn":
            reply = "".join(
                block.text for block in response.content if hasattr(block, "text")
            )
            st.session_state.conversation_history.append({
                "role": "assistant", "content": reply
            })
            st.session_state.queries_answered += 1
            return reply, tool_calls_made


# ─────────────────────────────────────────
# SESSION STATE
# ─────────────────────────────────────────
defaults = {
    "conversation_history": [],
    "messages_display": [],
    "files_generated": 0,
    "pipelines_generated": 0,
    "queries_answered": 0,
    "last_pipeline": None,
    "tool_log": []
}
for key, val in defaults.items():
    if key not in st.session_state:
        st.session_state[key] = val


# ─────────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────────
with st.sidebar:
    st.markdown('<span class="sidebar-label">Session Stats</span>', unsafe_allow_html=True)
    c1, c2, c3 = st.columns(3)
    c1.metric("Files", st.session_state.files_generated)
    c2.metric("DAGs", st.session_state.pipelines_generated)
    c3.metric("Queries", st.session_state.queries_answered)

    st.divider()

    # Output files + downloads
    st.markdown('<span class="sidebar-label">📁 Output Files</span>', unsafe_allow_html=True)
    output_dir = "output"
    if os.path.exists(output_dir):
        files = sorted(os.listdir(output_dir))
        if files:
            for f in files:
                icon = "🐍" if f.endswith(".py") else "⚙️" if f.endswith(".yml") else "🗄️"
                try:
                    with open(os.path.join(output_dir, f), "r") as fh:
                        content = fh.read()
                    st.download_button(
                        label=f"{icon} {f}",
                        data=content,
                        file_name=f,
                        mime="text/plain",
                        key=f"dl_{f}"
                    )
                except Exception:
                    st.caption(f)
        else:
            st.caption("No files yet")
    else:
        st.caption("No files yet")

    st.divider()

    # Schema explorer
    st.markdown('<span class="sidebar-label">🗄️ Schema Explorer</span>', unsafe_allow_html=True)
    for table_name, table_info in SCHEMA.items():
        with st.expander(f"`{table_name}`"):
            st.caption(table_info["description"])
            for col_name, col_info in table_info["columns"].items():
                st.markdown(
                    f'<span style="color:#79c0ff;font-family:JetBrains Mono,monospace;font-size:0.78rem">'
                    f'{col_name}</span> '
                    f'<span style="color:#8b949e;font-size:0.72rem">· {col_info["type"]}</span>',
                    unsafe_allow_html=True
                )

    st.divider()

    # Pipeline visualization
    if st.session_state.last_pipeline:
        p = st.session_state.last_pipeline
        st.markdown('<span class="sidebar-label">🔀 Last Pipeline</span>', unsafe_allow_html=True)
        nodes_html = "".join([f'<span class="pipeline-node">{t}</span>' for t in p["input_tables"]])
        st.markdown(f"""
        <div class="pipeline-card">
            <div style="text-align:center">
                <div style="color:#58a6ff;font-family:JetBrains Mono,monospace;font-size:0.8rem;margin-bottom:4px">
                    {p['name']}
                </div>
                <div style="color:#8b949e;font-size:0.7rem;margin-bottom:8px">{p['schedule']}</div>
                {nodes_html}
                <div style="color:#3fb950;margin:6px 0">↓</div>
                <span style="color:#8b949e;font-family:JetBrains Mono,monospace;font-size:0.72rem">
                    Databricks Notebook
                </span>
                <div style="color:#3fb950;margin:6px 0">↓</div>
                <span class="pipeline-node" style="border-color:#3fb95055;color:#3fb950">
                    {p['output_table']}
                </span>
            </div>
        </div>
        """, unsafe_allow_html=True)

    st.divider()

    # Tool log
    if st.session_state.tool_log:
        st.markdown('<span class="sidebar-label">🔧 Tool Log</span>', unsafe_allow_html=True)
        for log in st.session_state.tool_log[-6:]:
            st.markdown(f'<div class="tool-call">→ {log}</div>', unsafe_allow_html=True)

    st.divider()
    if st.button("🗑️ Clear Session", use_container_width=True):
        for key, val in defaults.items():
            st.session_state[key] = val
        st.rerun()


# ─────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────
st.markdown("""
<div class="de-header">
    <div>
        <p class="de-title">⚡ DE Copilot</p>
        <p class="de-subtitle">// AI Data Engineering Assistant</p>
    </div>
    <span class="de-badge">CLAUDE · SONNET</span>
</div>
""", unsafe_allow_html=True)

chat_tab, ref_tab = st.tabs(["💬  Chat", "📖  Quick Reference"])

with chat_tab:

    # Welcome
    if not st.session_state.messages_display:
        st.markdown("""
        <div class="welcome-box">
            <span style="color:#3fb950">● online</span> &nbsp;
            <span style="color:#58a6ff">DE Copilot ready</span><br><br>
            <span style="color:#58a6ff">→</span> Generate Snowflake SQL from plain English<br>
            <span style="color:#58a6ff">→</span> Create full Airflow pipelines (DAG + YAML + Notebook)<br>
            <span style="color:#58a6ff">→</span> Validate and review SQL files<br>
            <span style="color:#58a6ff">→</span> Download all generated files from sidebar<br><br>
            <span style="color:#636e7b">Try: "Generate SQL for top 10 subscribers by watch time and save it"</span>
        </div>
        """, unsafe_allow_html=True)

    # Chat history
    for msg in st.session_state.messages_display:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # Input
    if user_input := st.chat_input("Ask anything — SQL, pipelines, schema questions..."):
        with st.chat_message("user"):
            st.markdown(user_input)
        st.session_state.messages_display.append({"role": "user", "content": user_input})

        with st.chat_message("assistant"):
            with st.spinner("⚡ Running agent..."):
                reply, tool_calls = run_agent(user_input)
            for tc in tool_calls:
                st.session_state.tool_log.append(tc)
            st.markdown(reply)

        st.session_state.messages_display.append({"role": "assistant", "content": reply})
        st.rerun()

with ref_tab:
    st.markdown("#### Example Prompts")
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("**SQL Generation**")
        st.code(
            "Generate SQL for top 10 subscribers\nby watch time and save it\n\n"
            "Show most watched content this month\n\n"
            "Find subscribers inactive for 30 days",
            language="text"
        )
        st.markdown("**Pipeline Creation**")
        st.code(
            "Create a daily pipeline for top\nsubscribers, run every day at 7am\n\n"
            "Build a weekly content report\npipeline, run every Monday at 6am",
            language="text"
        )

    with col2:
        st.markdown("**Schema Queries**")
        st.code(
            "What tables do we have?\n\n"
            "Show me the watch_history schema\n\n"
            "What columns are in subscribers?",
            language="text"
        )
        st.markdown("**File Operations**")
        st.code(
            "What files have been generated?\n\n"
            "review sample_query.sql\n\n"
            "List all output files",
            language="text"
        )

    st.divider()
    st.markdown("**Available Tables**")
    for tn, ti in SCHEMA.items():
        st.markdown(f"`{tn}` — {ti['description']}")
