import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import json
import requests
import traceback
import os
import time
from streamlit_autorefresh import st_autorefresh

os.chdir(os.path.dirname(os.path.abspath(__file__)))

OLLAMA_URL = "http://localhost:11500"

st.set_page_config(page_title="📊 Chart Dashboard", layout="wide")
st.title("Chart Dashboard with KPIs + Global Filters")

params = st.query_params
csv_path = params.get("csv", "data/default.csv")
json_path = params.get("json", "data/default.json")
delimiter = params.get("delim", None)

def get_mod_time(path):
    try:
        return os.path.getmtime(path)
    except FileNotFoundError:
        return 0

csv_mod_time = get_mod_time(csv_path)
json_mod_time = get_mod_time(json_path)
refresh_trigger = int(csv_mod_time + json_mod_time)

# Auto-refresh if either CSV or JSON file changes
st_autorefresh(interval=1000, limit=None, key=f"autorefresh_{refresh_trigger}")

if csv_mod_time == 0:
    st.error(f"❌ CSV file not found: {csv_path}")
    st.stop()

try:
    if delimiter:
        df = pd.read_csv(csv_path, sep=delimiter)
    else:
        df = pd.read_csv(csv_path, sep=None, engine="python")
    df.columns = df.columns.str.strip().str.replace('\ufeff', '')
    st.success(f"✅ CSV data loaded from {csv_path}")
    st.dataframe(df.head(5))
except Exception as e:
    st.error(f"❌ Error loading CSV from {csv_path}: {e}")
    st.stop()

if "chart_specs" not in st.session_state:
    st.session_state.chart_specs = []
if "global_filter_cols" not in st.session_state:
    st.session_state.global_filter_cols = []

# Load or generate chart spec
try:
    with open(json_path) as f:
        raw = json.load(f)
    st.session_state.global_font = raw.get("global_font", {"family": "Arial", "size": 14, "color": "black"})
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
  "global_filters": {{"Segment": [], "Region": []}},
  "charts": [
    {{"chart": "kpi", "label": "Total Sales", "metric": "Sales", "agg": "sum"}},
    {{"chart": "bar", "x": "Part", "y": "Sales"}}
  ]
}}
Data Preview:
{json.dumps(df_preview, indent=2)}
        """
        with st.spinner("Calling Ollama..."):
            response = requests.post(f"{OLLAMA_URL}/api/generate", json={"model": "codellama", "prompt": prompt, "stream": False})
            response.raise_for_status()
            result = response.json()["response"]
            cleaned = result.replace("[PYTHON]", "").replace("[/PYTHON]", "").strip("`").replace("json", "").strip()
            parsed = json.loads(cleaned)
            st.session_state.global_filter_cols = list(parsed.get("global_filters", {}).keys())
            st.session_state.chart_specs = parsed.get("charts", parsed if isinstance(parsed, list) else [])
            st.code(json.dumps(parsed, indent=2), language="json")
            st.success("✅ Fallback spec generated and loaded from Ollama")
    except Exception:
        st.error("❌ Ollama failed to generate a fallback spec:\n" + traceback.format_exc())
        st.stop()

def apply_global_filters(df, filter_columns):
    filtered_df = df.copy()
    if filter_columns:
        with st.expander("🌍 Global Filters", expanded=True):
            for col in filter_columns:
                if col in df.columns:
                    values = sorted(df[col].dropna().unique().tolist())
                    selected = st.selectbox(f"Select value for {col}:", ["All"] + values, index=0, key=f"global_filter_{col}")
                    if selected != "All":
                        filtered_df = filtered_df[filtered_df[col] == selected]
    return filtered_df

def apply_individual_filters(df, chart_id, filter_columns):
    filtered_df = df.copy()
    if filter_columns:
        #with st.expander(f"🎯 Filters for Chart {chart_id}", expanded=False):
            for col in filter_columns:
                if col in df.columns:
                    values = sorted(df[col].dropna().unique().tolist())
                    selected = st.selectbox(f"{col}", ["All"] + values, index=0, key=f"individual_filter_{chart_id}_{col}")
                    if selected != "All":
                        filtered_df = filtered_df[filtered_df[col] == selected]
    return filtered_df

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

def resolve_color_sequence(color_names):
    named_colors = {
        "red": "#FF0000", "green": "#008000", "blue": "#0000FF", "orange": "#FFA500",
        "yellow": "#FFFF00", "purple": "#800080", "pink": "#FFC0CB", "brown": "#A52A2A",
        "black": "#000000", "white": "#FFFFFF", "gray": "#808080", "grey": "#808080",
        "cyan": "#00FFFF", "magenta": "#FF00FF", "lime": "#00FF00", "teal": "#008080",
        "navy": "#000080", "maroon": "#800000", "olive": "#808000", "gold": "#FFD700",
        "indigo": "#4B0082", "crimson": "#DC143C"
    }
    hex_colors = []
    for color in color_names:
        if color.startswith("#"):
            hex_colors.append(color)
        else:
            hex_colors.append(named_colors.get(color.lower(), "#000000"))
    return hex_colors

def render_chart(spec, data):
    chart = spec.get("chart")
    x = spec.get("x")
    y = spec.get("y")
    group = spec.get("group") if spec.get("group") in data.columns else None
    default_font = st.session_state.get("global_font", {"family": "Arial", "size": 14, "color": "black"})
    font = spec.get("font", default_font)
    color_sequence = resolve_color_sequence(spec.get("colorSequence", [])) if spec.get("colorSequence") else None
    show_legend = spec.get("showLegend", True)  # 🔸 Read legend flag (default True)

    if chart == "bar":
        fig = px.bar(data, x=x, y=y, color=group, color_discrete_sequence=color_sequence)
    elif chart == "line":
        fig = px.line(data, x=x, y=y, color=group, color_discrete_sequence=color_sequence)
    elif chart == "pie":
        fig = px.pie(data, names=spec.get("labels"), values=spec.get("values"))
    elif chart == "treemap":
        path = [group, x] if group else [x]
        fig = px.treemap(data, path=path, values=y)
    elif chart == "bubble":
        fig = px.scatter(data, x=x, y=y, size=spec.get("size"), color=group, color_discrete_sequence=color_sequence)
    elif chart == "waterfall":
        fig = go.Figure(go.Waterfall(
            x=spec["x"],
            y=spec["y"],
            measure=spec.get("measure", ["relative"] * len(spec["x"]))
        ))
        fig.update_layout(title=spec.get("title", ""), font=font, showlegend=show_legend)  # 🔹 Add legend here too
        return fig
    elif chart == "area":
        area_mode = spec.get("mode", "stack")
        opacity = spec.get("opacity", 0.7)
        line_shape = "spline" if spec.get("lineSmoothing", False) else "linear"
        sort_x = spec.get("sortX", False)

        if sort_x and x in data.columns:
            data = data.sort_values(by=x)
            fig = px.area(
                data,
                x=x,
                y=y,
                color=group,
                line_shape=line_shape,
                color_discrete_sequence=color_sequence,
                groupnorm="percent" if area_mode == "percent" else None
            )
            fig.update_traces(opacity=opacity, stackgroup="one" if area_mode == "stack" else None)

    else:
        return None

    # 🔸 Apply title, font, and legend for all charts
    fig.update_layout(title=spec.get("title", ""), font=font, showlegend=show_legend)
    return fig

layout_options = ["Auto Grid (2 per row)", "All Full Width", "1 Top + 2 Below"]
if "layout_choice" not in st.session_state:
    st.session_state.layout_choice = layout_options[0]

new_layout = st.selectbox("📐 Select Layout", layout_options, index=layout_options.index(st.session_state.layout_choice))
if new_layout != st.session_state.layout_choice:
    st.session_state.layout_choice = new_layout
    st.rerun()

chart_specs = st.session_state.get("chart_specs", [])
global_cols = st.session_state.get("global_filter_cols", [])

if chart_specs:
    filtered_df = apply_global_filters(df, global_cols)
    render_kpi_cards(chart_specs, filtered_df)
    st.markdown("---")
    st.subheader("📊 Dashboard")
    chart_specs = [s for s in chart_specs if s.get("chart") != "kpi"]
    num_charts = len(chart_specs)

    def get_chart_title(spec):
        return spec.get("title") or f"{spec.get('chart', '').capitalize()} Chart"

    layout_choice = st.session_state.layout_choice
    if layout_choice == "Auto Grid (2 per row)":
        cols = st.columns(2)
        for i, spec in enumerate(chart_specs):
            with cols[i % 2]:
                chart_id = f"{spec.get('chart')}_{i}"
                individual_filter_cols = spec.get("filters", [])
                filtered_df_chart = apply_individual_filters(filtered_df, chart_id, individual_filter_cols)
                fig = render_chart(spec, filtered_df_chart)
                if fig:
                    st.plotly_chart(fig, use_container_width=True)
    elif layout_choice == "All Full Width":
        for i, spec in enumerate(chart_specs):
            chart_id = f"{spec.get('chart')}_{i}"
            individual_filter_cols = spec.get("filters", [])
            filtered_df_chart = apply_individual_filters(filtered_df, chart_id, individual_filter_cols)
            fig = render_chart(spec, filtered_df_chart)
            if fig:
                st.plotly_chart(fig, use_container_width=True)
    elif layout_choice == "1 Top + 2 Below":
        if num_charts > 0:
            chart_id = f"{chart_specs[0].get('chart')}_0"
            individual_filter_cols = chart_specs[0].get("filters", [])
            filtered_df_chart = apply_individual_filters(filtered_df, chart_id, individual_filter_cols)
            st.plotly_chart(render_chart(chart_specs[0], filtered_df_chart), use_container_width=True)
        if num_charts > 1:
            cols = st.columns(2)
            for i in range(1, min(num_charts, 3)):
                with cols[i - 1]:
                    chart_id = f"{chart_specs[i].get('chart')}_{i}"
                    individual_filter_cols = chart_specs[i].get("filters", [])
                    filtered_df_chart = apply_individual_filters(filtered_df, chart_id, individual_filter_cols)
                    st.plotly_chart(render_chart(chart_specs[i], filtered_df_chart), use_container_width=True)
        for i in range(3, num_charts, 2):
            cols = st.columns(2)
            for j in range(2):
                if i + j < num_charts:
                    with cols[j]:
                        chart_id = f"{chart_specs[i + j].get('chart')}_{i + j}"
                        individual_filter_cols = chart_specs[i + j].get("filters", [])
                        filtered_df_chart = apply_individual_filters(filtered_df, chart_id, individual_filter_cols)
                        st.plotly_chart(render_chart(chart_specs[i + j], filtered_df_chart), use_container_width=True)
