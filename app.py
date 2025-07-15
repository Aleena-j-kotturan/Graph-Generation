import streamlit as st
import pandas as pd
import plotly.express as px
import json
import requests
import traceback
import plotly.graph_objects as go

OLLAMA_URL = "http://localhost:11500"

st.set_page_config(page_title="Chart Dashboard", layout="wide")
st.title("AI Chart Dashboard")

# === Upload CSV ===
uploaded_file = st.file_uploader("Upload your CSV data", type=["csv"])
if uploaded_file:
    df = pd.read_csv(uploaded_file)
    df.columns = df.columns.str.strip()
    st.success("Data loaded successfully!")
    #st.dataframe(df.head(5))

    # === Persist chart specs in session state
    if "chart_specs" not in st.session_state:
        st.session_state.chart_specs = []

    # === Chart spec input ===
    chart_spec_option = st.radio("Choose chart spec method", ["Upload JSON file", "Generate using Ollama"])

    if chart_spec_option == "Upload JSON file":
        uploaded_json = st.file_uploader("📄 Upload your chart spec JSON", type=["json"])
        if uploaded_json and st.button("Generate Charts"):
            try:
                parsed_specs = json.load(uploaded_json)
                if isinstance(parsed_specs, dict):
                    parsed_specs = [parsed_specs]
                st.session_state.chart_specs = parsed_specs
                st.success("✅ JSON parsed and stored!")
            except Exception as e:
                st.error(f"❌ Invalid JSON: {e}")
                st.stop()
    else:
        df_preview = df.head(5).to_dict(orient="records")
        prompt = f"""
You are a chart specification assistant.

Given a data preview, return a list of valid chart specification(s) in JSON format. Each spec should include:

chart: one of "bar", "pie", "treemap", "line", "bubble", "waterfall", "big_number"
x, y fields depending on chart
optional "group" for color/lines
optional "filters": dict with column name and allowed values list

Data Preview:
{json.dumps(df_preview, indent=2)}
        """
        if st.button("🧠 Ask Ollama to Generate Chart Spec"):
            try:
                with st.spinner("Calling Ollama..."):
                    response = requests.post(
                        f"{OLLAMA_URL}/api/generate",
                        json={"model": "codellama", "prompt": prompt, "stream": False}
                    )
                    response.raise_for_status()
                    result = response.json()["response"]

                    cleaned = result.replace("[PYTHON]", "").replace("[/PYTHON]", "").strip()
                    cleaned = cleaned.strip("").replace("json", "").strip()
                    parsed_specs = json.loads(cleaned)

                    st.session_state.chart_specs = parsed_specs
                    st.code(json.dumps(parsed_specs, indent=2), language="json")
                    st.success("✅ Chart spec generated and stored!")
            except Exception as e:
                st.error("❌ Error calling Ollama:\n" + traceback.format_exc())
                st.stop()

    # === Chart rendering function
    def render_chart(spec, df):
        spec.setdefault("group", None)
        spec.setdefault("filters", {})

        group_col = spec.get("group")
        if not group_col or group_col.strip() == "" or group_col not in df.columns:
            group_col = None

        fig = None
        chart_type = spec.get("chart", "").lower()

        if chart_type == "bar":
            fig = px.bar(df, x=spec["x"], y=spec["y"], color=group_col)

        elif chart_type == "line":
            fig = px.line(df, x=spec["x"], y=spec["y"], color=group_col)

        elif chart_type == "pie":
            fig = px.pie(df, names=spec["labels"], values=spec["values"])

        elif chart_type == "treemap":
            path = [group_col, spec["x"]] if group_col else [spec["x"]]
            fig = px.treemap(df, path=path, values=spec["y"])

        elif chart_type == "bubble":
            fig = px.scatter(df, x=spec["x"], y=spec["y"], size=spec["size"], color=group_col)

        elif chart_type == "waterfall":
            fig = go.Figure(go.Waterfall(
                name="",
                orientation="v",
                x=spec["x"],
                y=spec["y"],
                measure=spec.get("measure", ["relative"] * len(spec["x"]))
            ))

        elif chart_type == "big_number":
            y_field = spec.get("y")
            agg = spec.get("aggregation", "sum").lower()
            title = spec.get("title", "Metric")
            delta = spec.get("delta")

            value = None
            if y_field and y_field in df.columns:
                try:
                    if agg == "sum":
                        value = df[y_field].sum()
                    elif agg in ["avg", "mean"]:
                        value = df[y_field].mean()
                    elif agg == "count":
                        value = df[y_field].count()
                    elif agg == "max":
                        value = df[y_field].max()
                    elif agg == "min":
                        value = df[y_field].min()
                except Exception as e:
                    st.warning(f"⚠️ Could not compute value for '{y_field}' with aggregation '{agg}': {e}")
                    value = None
            else:
                st.warning(f"⚠️ '{y_field}' not found in uploaded data columns.")

            if value is None or pd.isna(value):
                value = 0

            indicator_args = {
                "mode": "number+delta" if delta else "number",
                "value": value,
                "title": {"text": title},
                "number": {"font": {"size": 48}}
            }

            if delta:
                indicator_args["delta"] = {
                    "reference": delta,
                    "relative": True,
                    "valueformat": ".1%",
                    "increasing": {"color": "green"},
                    "decreasing": {"color": "red"}
                }

            fig = go.Figure(go.Indicator(**indicator_args))

        return fig

    # === Apply per-chart filters using unique keys
    def apply_per_chart_filter(df, idx):
        chart_cats = df.select_dtypes(include=['object', 'category']).columns.tolist()
        filtered_df = df.copy()

        with st.expander(f" Filters for Chart {idx + 1}"):
            for cat in chart_cats:
                unique_vals = df[cat].dropna().unique().tolist()
                options = ["ALL"] + unique_vals
                pretty_name = cat.replace("_", " ").strip().title()

                selected = st.selectbox(pretty_name, options, key=f"{cat}_{idx}")

                if selected and selected != "ALL":
                    filtered_df = filtered_df[filtered_df[cat] == selected]

        return filtered_df

    # === Display charts: KPIs on left, others on right
    chart_specs = st.session_state.get("chart_specs", [])
    if chart_specs:
        big_number_specs = [s for s in chart_specs if s.get("chart") == "big_number"]
        other_specs = [s for s in chart_specs if s.get("chart") != "big_number"]

        left_col, right_col = st.columns([1, 2])

        with left_col:
            for idx, spec in enumerate(big_number_specs):
                fig = render_chart(spec, df)
                if fig:
                    st.plotly_chart(fig, use_container_width=True)

        with right_col:
            st.markdown("### 📊 Charts")
            for idx, spec in enumerate(other_specs):
                st.markdown(f"##### 📊 {spec['chart'].capitalize()} Chart")
                filtered_df = apply_per_chart_filter(df, idx)
                fig = render_chart(spec, filtered_df)
                if fig:
                    st.plotly_chart(fig, use_container_width=True)
