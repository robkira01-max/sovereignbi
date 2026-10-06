"""SovereignBI — interface Streamlit.

Tabs: Chat | Dashboards | Journal d'audit | Admin
Communication with the FastAPI backend via httpx.
"""
from __future__ import annotations

import os

import httpx

API_URL = os.environ.get("SOVEREIGN_API_URL", "http://localhost:8000")
_TIMEOUT = 120.0


def _api(method: str, path: str, **kwargs):
    url = f"{API_URL}{path}"
    with httpx.Client(timeout=_TIMEOUT) as client:
        resp = getattr(client, method)(url, **kwargs)
    return resp


# ─── Lazy streamlit import (allows py_compile without streamlit installed) ────
def _main():
    import streamlit as st

    st.set_page_config(page_title="SovereignBI", layout="wide")
    st.title("SovereignBI — BI conversationnelle souveraine")

    # ── Sidebar ─────────────────────────────────────────────────────────────
    with st.sidebar:
        st.header("Données")
        uploaded = st.file_uploader(
            "Charger un fichier (CSV / XLSX)", type=["csv", "xlsx", "xlsm"]
        )
        if uploaded and st.button("Importer"):
            with st.spinner("Chargement…"):
                resp = _api(
                    "post",
                    "/upload",
                    files={"file": (uploaded.name, uploaded.getvalue(), uploaded.type)},
                )
            if resp.status_code == 200:
                tables = resp.json().get("tables", [])
                st.success(f"Tables chargées : {', '.join(tables)}")
                st.session_state["tables"] = tables
            else:
                st.error(resp.text)

        if st.session_state.get("tables"):
            st.markdown("**Tables actives :**")
            for t in st.session_state["tables"]:
                st.markdown(f"- `{t}`")
        else:
            try:
                r = _api("get", "/health")
                tbls = r.json().get("tables", [])
                if tbls:
                    st.session_state["tables"] = tbls
                    for t in tbls:
                        st.markdown(f"- `{t}`")
            except Exception:
                pass

    # ── Tabs ────────────────────────────────────────────────────────────────
    tab_chat, tab_dash, tab_audit, tab_admin = st.tabs(
        ["💬 Chat", "📊 Dashboards", "📋 Journal d'audit", "⚙️ Admin"]
    )

    # ── Tab Chat ────────────────────────────────────────────────────────────
    with tab_chat:
        st.subheader("Posez votre question")
        col1, col2 = st.columns([4, 1])
        with col1:
            question = st.text_input("Question", placeholder="Ex : Quel est le chiffre d'affaires par région ?")
        with col2:
            dry_run = st.checkbox("Dry-run", help="Génère le SQL sans l'exécuter")
            ask_btn = st.button("Poser", type="primary")

        if ask_btn and question:
            with st.spinner("Génération de la requête…"):
                resp = _api("post", "/ask", json={"question": question, "dry_run": dry_run})
            if resp.status_code == 200:
                data = resp.json()
                st.session_state["last_response"] = data
                st.session_state["last_question"] = question
            else:
                st.error(f"Erreur API : {resp.text}")

        if "last_response" in st.session_state:
            data = st.session_state["last_response"]
            sql = data.get("sql", "")

            # SQL zone with edit
            st.markdown("**Requête SQL générée**")
            edited_sql = st.text_area("SQL (modifiable)", value=sql, height=120, key="sql_editor")
            if st.button("Réexécuter") and edited_sql:
                with st.spinner("Exécution…"):
                    resp2 = _api("post", "/ask", json={"question": st.session_state.get("last_question", ""), "dry_run": False})
                if resp2.status_code == 200:
                    data = resp2.json()
                    st.session_state["last_response"] = data

            error = data.get("error")
            if error:
                st.error(f"Erreur : {error}")
            else:
                cols = data.get("columns", [])
                rows = data.get("rows", [])
                if cols and rows and not dry_run:
                    import pandas as pd
                    df = pd.DataFrame(rows, columns=cols)
                    st.dataframe(df, use_container_width=True)

                    # Auto-chart
                    try:
                        import plotly.express as px
                        num_cols = [c for c in df.columns if df[c].dtype.kind in "iuf"]
                        str_cols = [c for c in df.columns if df[c].dtype == object]
                        if len(df.columns) == 1 and len(num_cols) == 1:
                            val = df[num_cols[0]].sum()
                            st.metric(num_cols[0], f"{val:,.2f}")
                        elif len(str_cols) >= 1 and len(num_cols) >= 1:
                            fig = px.bar(df, x=str_cols[0], y=num_cols[0], title=st.session_state.get("last_question", ""))
                            st.plotly_chart(fig, use_container_width=True)
                    except Exception:
                        pass

            answer = data.get("answer", "")
            if answer:
                st.markdown(f"**Réponse :** {answer}")

            # Feedback
            st.divider()
            st.markdown("**Cette réponse vous a-t-elle aidé ?**")
            fcol1, fcol2 = st.columns(2)
            with fcol1:
                good = st.button("👍 Oui")
            with fcol2:
                bad = st.button("👎 Non")
            comment = st.text_input("Commentaire (optionnel)", key="fb_comment")
            if (good or bad) and question:
                rating = "good" if good else "bad"
                from app.feedback import record_feedback
                record_feedback(question, sql, rating, comment)
                st.success("Merci pour votre retour !")

            # Pin to dashboard
            st.divider()
            if st.button("📌 Épingler au dashboard"):
                with st.spinner("Chargement des dashboards…"):
                    r = _api("get", "/dashboards")
                dbs = r.json().get("dashboards", []) if r.status_code == 200 else []
                if dbs:
                    db_ids = [d["id"] for d in dbs]
                    chosen_db = st.selectbox("Dashboard", db_ids, key="pin_db")
                    tile_id = st.text_input("ID de tuile (ex: tile_1)", key="pin_tile_id")
                    pin_title = st.text_input("Titre de tuile", value=question[:60], key="pin_title")
                    if st.button("Confirmer l'épinglage"):
                        r2 = _api("post", f"/dashboards/{chosen_db}/pin",
                                  json={"tile_id": tile_id, "sql": sql, "title": pin_title})
                        if r2.status_code == 200:
                            st.success("Tuile épinglée !")
                        else:
                            st.error(r2.text)
                else:
                    st.info("Aucun dashboard — créez-en un dans l'onglet Dashboards.")

    # ── Tab Dashboards ───────────────────────────────────────────────────────
    with tab_dash:
        st.subheader("Dashboards")

        # Create from template
        with st.expander("Créer depuis un template", expanded=False):
            r = _api("get", "/templates")
            templates = r.json().get("templates", []) if r.status_code == 200 else []
            if templates:
                tmpl_labels = {t["title"]: t["id"] for t in templates}
                chosen_label = st.selectbox("Template", list(tmpl_labels.keys()), key="tmpl_sel")
                new_id = st.text_input("ID du nouveau dashboard", value=f"dash_{chosen_label[:10].lower().replace(' ', '_')}")
                new_title = st.text_input("Titre", value=chosen_label)
                new_scope = st.selectbox("Portée", ["personal", "team", "company"], key="scope_sel")
                if st.button("Créer le dashboard"):
                    r2 = _api("get", f"/templates/{tmpl_labels[chosen_label]}")
                    if r2.status_code == 200:
                        tmpl_data = r2.json()
                        body = {
                            "id": new_id,
                            "title": new_title,
                            "scope": new_scope,
                            "tiles": tmpl_data.get("tiles", []),
                            "theme": tmpl_data.get("theme", {}),
                        }
                        r3 = _api("post", "/dashboards", json=body)
                        if r3.status_code == 200:
                            st.success(f"Dashboard '{new_id}' créé !")
                        else:
                            st.error(r3.text)
            else:
                st.info("Aucun template disponible.")

        # Select and view dashboard
        r = _api("get", "/dashboards")
        dbs = r.json().get("dashboards", []) if r.status_code == 200 else []
        if not dbs:
            st.info("Aucun dashboard — créez-en un depuis un template.")
        else:
            db_titles = {d["title"]: d["id"] for d in dbs}
            chosen_title = st.selectbox("Dashboard actif", list(db_titles.keys()), key="active_db")
            chosen_id = db_titles[chosen_title]
            r2 = _api("get", f"/dashboards/{chosen_id}")
            if r2.status_code == 200:
                db_data = r2.json()
                tiles = db_data.get("tiles", [])

                # Theme editor
                with st.expander("⚙️ Thème"):
                    theme = db_data.get("theme", {})
                    new_color = st.color_picker("Couleur principale", theme.get("primary_color", "#1f77b4"))
                    if st.button("Appliquer le thème"):
                        db_data["theme"]["primary_color"] = new_color
                        _api("post", "/dashboards", json=db_data)
                        st.success("Thème sauvegardé.")

                # Grid 2x2
                from app.data.duckdb_store import DataStore
                from app.dashboards.models import Tile as TileModel
                from app.dashboards.renderer import render_tile
                store = DataStore()

                grid_rows = [tiles[i:i+2] for i in range(0, len(tiles), 2)]
                for row in grid_rows:
                    cols = st.columns(len(row))
                    for col, t_data in zip(cols, row):
                        with col:
                            st.markdown(f"**{t_data['title']}**")
                            sql_p = t_data.get("sql_pinned")
                            if sql_p:
                                tile_obj = TileModel(
                                    id=t_data["id"],
                                    type=t_data["type"],
                                    title=t_data["title"],
                                    sql_pinned=sql_p,
                                )
                                result = render_tile(tile_obj, store)
                                if result["error"]:
                                    st.warning(result["error"])
                                else:
                                    import pandas as pd
                                    df = pd.DataFrame(result["rows"], columns=result["columns"])
                                    if t_data["type"] == "table":
                                        st.dataframe(df)
                                    else:
                                        try:
                                            import plotly.express as px
                                            num_cols = [c for c in df.columns if df[c].dtype.kind in "iuf"]
                                            str_cols = [c for c in df.columns if df[c].dtype == object]
                                            if t_data["type"] == "kpi" and num_cols:
                                                st.metric(num_cols[0], f"{df[num_cols[0]].sum():,.2f}")
                                            elif str_cols and num_cols:
                                                fig = px.bar(df, x=str_cols[0], y=num_cols[0])
                                                st.plotly_chart(fig, use_container_width=True)
                                            else:
                                                st.dataframe(df)
                                        except Exception:
                                            st.dataframe(df)
                            else:
                                metric = t_data.get("metric", "")
                                st.caption(f"Métrique : {metric}" if metric else "Aucun SQL épinglé")

                if st.button("💾 Sauvegarder"):
                    _api("post", "/dashboards", json=db_data)
                    st.success("Dashboard sauvegardé.")

    # ── Tab Audit ────────────────────────────────────────────────────────────
    with tab_audit:
        st.subheader("Journal d'audit")
        from app.feedback import load_audit
        entries = load_audit()
        if not entries:
            st.info("Aucune entrée d'audit pour le moment.")
        else:
            import pandas as pd
            rows = [
                {
                    "timestamp": e.timestamp,
                    "action": e.action,
                    "détails": str(e.details)[:120],
                    "hash": e.hash[:16] + "…",
                }
                for e in entries[-50:]
            ]
            st.dataframe(pd.DataFrame(rows[::-1]), use_container_width=True)

    # ── Tab Admin ────────────────────────────────────────────────────────────
    with tab_admin:
        admin_key = os.environ.get("SOVEREIGN_ADMIN_KEY", "")
        if not admin_key:
            st.info("Définir SOVEREIGN_ADMIN_KEY pour accéder à l'administration.")
        else:
            st.subheader("Modèle sémantique")
            if st.button("Charger le modèle"):
                r = _api("get", "/admin/semantic", headers={"X-Admin-Key": admin_key})
                if r.status_code == 200:
                    import json
                    st.json(r.json())
                else:
                    st.error(r.text)


if __name__ == "__main__":
    _main()
