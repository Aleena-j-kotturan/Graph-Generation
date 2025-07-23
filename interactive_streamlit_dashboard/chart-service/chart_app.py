import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import json
import requests
import traceback
import os
import argparse

os.chdir(os.path.dirname(os.path.abspath(__file__)))

OLLAMA_URL = "http://localhost:11500"

st.set_page_config(page_title="📊 Chart Dashboard", layout="wide")
st.title("📊 AI Chart Dashboard with KPIs + Global Filters")

# New: Accept query params from URL
params = st.query_params
csv_path = params.get("csv", "data/default.csv")
json_path = params.get("json", "data/default.json")

# 2️⃣ Load CSV
try:
    df = pd.read_csv(csv_path)
    df.columns = df.columns.str.strip()
    st.success(f"✅ CSV data loaded from {csv_path}")
    st.dataframe(df.head(5))
except Exception as e:
    st.error(f"❌ Error loading CSV from {csv_path}: {e}")
    st.stop()

# 3️⃣ Initialize session state
if "chart_specs" not in st.session_state:
    st.session_state.chart_specs = []
if "global_filter_cols" not in st.session_state:
    st.session_state.global_filter_cols = []

# 4️⃣ Load JSON chart spec or fallback to Ollama
try:
    with open(json_path) as f:
        raw = json.load(f)

    st.session_state.global_filter_cols = list(raw.get("global_filters", {}).keys())
    parsed_specs = raw.get("charts", raw if isinstance(raw, list) else [])
    st.session_state.chart_specs = parsed_specs
    st.success(f"✅ Chart spec loaded from {json_path}")

except Exception as e:
    st.warning(f"⚠️ Spec JSON not found or invalid: {e}")
    st.info("🤖 Auto-generating chart spec using Ollama...")

    try:
        df_preview = df.head(5).to_dict(orient="records")
        prompt = f"""
You are a chart specification assistant.

Return a JSON like:
{{
  "global_filters": {{
    "Segment": [],
    "Region": []
  }},
  "charts": [
    {{
      "chart": "kpi",
      "label": "Total Sales",
      "metric": "Sales",
      "agg": "sum"
    }},
    {{
      "chart": "bar",
      "x": "Part",
      "y": "Sales"
    }}
  ]
}}

Data Preview:
{json.dumps(df_preview, indent=2)}
        """
        with st.spinner("Calling Ollama..."):
            response = requests.post(
                f"{OLLAMA_URL}/api/generate",
                json={"model": "codellama", "prompt": prompt, "stream": False}
            )
            response.raise_for_status()
            result = response.json()["response"]
            cleaned = result.replace("[PYTHON]", "").replace("[/PYTHON]", "").strip("`").replace("json", "").strip()
            parsed = json.loads(cleaned)
            st.session_state.global_filter_cols = list(parsed.get("global_filters", {}).keys())
            st.session_state.chart_specs = parsed.get("charts", parsed if isinstance(parsed, list) else [])
            st.code(json.dumps(parsed, indent=2), language="json")
            st.success("✅ Fallback spec generated and loaded from Ollama")
    except Exception as ollama_error:
        st.error("❌ Ollama failed to generate a fallback spec:\n" + traceback.format_exc())
        st.stop()

# Global Filter Function
def apply_global_filters(df, filter_columns):
    filtered_df = df.copy()
    if filter_columns:
        with st.expander("🌍 Global Filters", expanded=True):
            for col in filter_columns:
                if col in df.columns:
                    values = sorted(df[col].dropna().unique().tolist())
                    selected = st.selectbox(
                        f"Select value for {col}:",
                        options=["All"] + values,
                        index=0,
                        key=f"global_filter_{col}"
                    )
                    if selected != "All":
                        filtered_df = filtered_df[filtered_df[col] == selected]
    return filtered_df

# KPI Renderer
def render_kpi_cards(specs, df):
        kpi_specs = [s for s in specs if s.get("chart") == "kpi"]
        if not kpi_specs:
            return
        st.subheader("📌 Key Metrics")
        cols = st.columns(len(kpi_specs))
        for idx, spec in enumerate(kpi_specs):
            metric = spec.get("metric")
            label = spec.get("label", metric)
            agg = spec.get("agg", "sum").lower()
            value = None
            if metric in df.columns:
                if agg == "sum":
                    value = df[metric].sum()
                elif agg == "avg":
                    value = df[metric].mean()
                elif agg == "count":
                    value = df[metric].count()
                elif agg == "max":
                    value = df[metric].max()
                elif agg == "min":
                    value = df[metric].min()
            with cols[idx]:
                st.metric(label=label, value=f"{value:,.2f}" if isinstance(value, (int, float)) else value)

    # Chart Renderer
def render_chart(spec, data):
        chart = spec.get("chart")
        x = spec.get("x")
        y = spec.get("y")
        group = spec.get("group", None)
        if group and group not in data.columns:
            group = None

        if chart == "bar":
            return px.bar(data, x=x, y=y, color=group)
        elif chart == "line":
            return px.line(data, x=x, y=y, color=group)
        elif chart == "pie":
            return px.pie(data, names=spec.get("labels"), values=spec.get("values"))
        elif chart == "treemap":
            path = [group, x] if group else [x]
            return px.treemap(data, path=path, values=y)
        elif chart == "bubble":
            return px.scatter(data, x=x, y=y, size=spec.get("size"), color=group)
        elif chart == "waterfall":
            return go.Figure(go.Waterfall(
                name="",
                orientation="v",
                x=spec["x"],
                y=spec["y"],
                measure=spec.get("measure", ["relative"] * len(spec["x"]))
            ))
        return None


# Render Charts
layout_choice = st.selectbox("📐 Select Layout", ["Auto Grid (2 per row)", "All Full Width", "1 Top + 2 Below", "2x2 Grid"])
chart_specs = st.session_state.get("chart_specs", [])
global_cols = st.session_state.get("global_filter_cols", [])

if chart_specs:
    filtered_df = apply_global_filters(df, global_cols)
    render_kpi_cards(chart_specs, filtered_df)
    chart_specs = [s for s in chart_specs if s.get("chart") != "kpi"]

    st.markdown("---")
    st.subheader("📊 Dashboard")
    num_charts = len(chart_specs)

    if layout_choice == "Auto Grid (2 per row)":
        cols = st.columns(2)
        for idx, spec in enumerate(chart_specs):
            with cols[idx % 2]:
                st.markdown(f"**{spec.get('chart', '').capitalize()} Chart**")
                fig = render_chart(spec, filtered_df)
                if fig:
                    st.plotly_chart(fig, use_container_width=True)

    elif layout_choice == "All Full Width":
        for idx, spec in enumerate(chart_specs):
            st.markdown(f"**{spec.get('chart', '').capitalize()} Chart**")
            fig = render_chart(spec, filtered_df)
            if fig:
                st.plotly_chart(fig, use_container_width=True)

    elif layout_choice == "1 Top + 2 Below":
        if num_charts >= 1:
            st.plotly_chart(render_chart(chart_specs[0], filtered_df), use_container_width=True)
        if num_charts > 1:
            cols = st.columns(2)
            for i in range(1, min(num_charts, 3)):
                with cols[i - 1]:
                    st.plotly_chart(render_chart(chart_specs[i], filtered_df), use_container_width=True)

    elif layout_choice == "2x2 Grid":
        rows = (num_charts + 1) // 2
        for i in range(rows):
            cols = st.columns(2)
            for j in range(2):
                idx = i * 2 + j
                if idx < num_charts:
                    with cols[j]:
                        st.markdown(f"**{chart_specs[idx]['chart'].capitalize()} Chart**")
                        fig = render_chart(chart_specs[idx], filtered_df)
                        if fig:
                            st.plotly_chart(fig, use_container_width=True)
