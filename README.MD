# ⚡ DE Copilot

AI-powered Data Engineering Assistant built with Claude API.

## What it does
- Generates Snowflake SQL from plain English
- Creates full Airflow pipelines (DAG + YAML + Databricks notebook)
- Validates SQL automatically
- Schema-aware — uses your actual table definitions

## Built with
- Claude API (Anthropic)
- Python, Streamlit
- Airflow, Databricks, Snowflake patterns

## Run locally
pip install -r requirements.txt
streamlit run app.py