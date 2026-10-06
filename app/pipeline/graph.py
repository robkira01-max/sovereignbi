"""Pipeline à 3 nœuds : générer le SQL -> valider/exécuter (retry) -> rédiger la réponse."""
import re
from pathlib import Path
from typing import TypedDict

import yaml
from langgraph.graph import END, StateGraph

from app.data.duckdb_store import DataStore
from app.llm.ollama_client import LLM
from app.security.sql_guard import SQLGuardError, validate_sql

MAX_ATTEMPTS = 3

SQL_SYSTEM = (
    "Tu es un expert SQL DuckDB. Réponds uniquement par UNE requête SELECT, "
    "sans explication. Utilise exclusivement les tables et colonnes fournies."
)
ANSWER_SYSTEM = "Tu es un analyste de données. Réponds en français, de façon concise et factuelle, uniquement à partir des résultats fournis."


class State(TypedDict, total=False):
    question: str
    dry_run: bool
    sql: str
    error: str | None
    columns: list[str]
    rows: list[tuple]
    attempts: int
    answer: str


def load_semantic(path: str = "semantic/model.yaml") -> str:
    p = Path(path)
    if not p.exists():
        return ""
    m = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
    gl = "\n".join(f"- {g['terme']} : {g['definition']}" for g in m.get("glossary", []))
    rules = "\n".join(f"- {r}" for r in m.get("rules", []))
    return f"Glossaire métier :\n{gl}\nRègles :\n{rules}"


def extract_sql(text: str) -> str:
    m = re.search(r"```(?:sql)?\s*(.*?)```", text, re.S | re.I)
    return (m.group(1) if m else text).strip().rstrip(";")


def build_graph(llm: LLM, store: DataStore, semantic: str = "", linker=None):
    def generate_sql(state: State) -> State:
        if linker is not None:
            context = linker.get_relevant_context(state["question"])
        else:
            context = semantic
        prompt = f"Schéma pertinent :\n{store.schema_description()}\n\n{context}\n\nQuestion : {state['question']}"
        if state.get("error"):
            prompt += f"\n\nTa requête précédente a échoué :\n{state['sql']}\nErreur : {state['error']}\nCorrige-la."
        return {"sql": extract_sql(llm.complete(SQL_SYSTEM, prompt)), "error": None}

    def validate_execute(state: State) -> State:
        attempts = state.get("attempts", 0) + 1
        try:
            safe = validate_sql(state["sql"], store.tables)
            if state.get("dry_run"):
                return {"sql": safe, "attempts": attempts, "error": None, "columns": [], "rows": []}
            cols, rows = store.execute(safe)
            return {"sql": safe, "attempts": attempts, "error": None, "columns": cols, "rows": rows}
        except SQLGuardError as e:
            return {"attempts": attempts, "error": f"Refusé : {e}"}
        except Exception as e:  # erreur d'exécution DuckDB
            return {"attempts": attempts, "error": str(e)}

    def answer(state: State) -> State:
        if state.get("error"):
            return {"answer": f"Je n'ai pas réussi à répondre ({state['error']})."}
        if state.get("dry_run"):
            return {"answer": "Mode dry-run : requête générée, non exécutée."}
        preview = {"colonnes": state["columns"], "lignes": state["rows"][:50]}
        text = llm.complete(ANSWER_SYSTEM, f"Question : {state['question']}\nRésultats : {preview}")
        return {"answer": text.strip()}

    def route(state: State) -> str:
        if state.get("error") and state.get("attempts", 0) < MAX_ATTEMPTS:
            return "generate_sql"
        return "answer"

    g = StateGraph(State)
    g.add_node("generate_sql", generate_sql)
    g.add_node("validate_execute", validate_execute)
    g.add_node("answer", answer)
    g.set_entry_point("generate_sql")
    g.add_edge("generate_sql", "validate_execute")
    g.add_conditional_edges("validate_execute", route, {"generate_sql": "generate_sql", "answer": "answer"})
    g.add_edge("answer", END)
    return g.compile()
