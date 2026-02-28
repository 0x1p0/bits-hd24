import json
from pathlib import Path
from typing import Tuple
import pandas as pd
import plotly.express as px
import streamlit as st

st.set_page_config(
    page_title="BITS HD Admissions Analytics (2024)",
    layout="wide",
    initial_sidebar_state="expanded",
)

@st.cache_data
def load_data(path: str | Path) -> pd.DataFrame:
    """Load and clean the raw JSON data into a DataFrame."""
    with open(path, "r", encoding="utf-8") as f:
        raw = json.load(f)
    df_ = pd.DataFrame(raw)
    df_.columns = df_.columns.str.strip()

    #time to clean up some things blehhhhhhh :P
    df_ = df_.rename(
        columns={
            "GATE or GPAT score (if not through GATE/GPAT then put 0)": "GATE Score",
            "BITS HD Marks Scored in (Paper 1+ Paper 2) for Core Engineering disciple (CS/MECH/CIVIL/IT/BIOTECH/ECE/ETC/EE)  (Enter 0 if not applicable)": "HD Core",
            "BITS HD test marks (Paper 1 + Software systems) for  Software System only (SS) (Enter 0 if not applicable)": "HD SS",
            "For which ME / M.Pharm branch you got provisionally shortlisted at BITS ?": "ME Branch",
            "Which campus did you get admission (choose - not applicable if you did not get admission)": "Campus",
        }
    )

    def clean_numeric(s: pd.Series) -> pd.Series:
        return (
            pd.to_numeric(
                s.astype(str).str.extract(r"(\d+\.?\d*)")[0],
                errors="coerce",
            )
            .fillna(0.0)
            .astype(float)
        )

    df_["GATE Score"] = clean_numeric(df_["GATE Score"])
    df_["HD Core"] = clean_numeric(df_["HD Core"])
    df_["HD SS"] = clean_numeric(df_["HD SS"])

    df_["HD Score"] = df_[["HD Core", "HD SS"]].max(axis=1)

    for col in ["ME Branch", "Campus"]:
        if col in df_.columns:
            df_[col] = df_[col].astype(str).str.strip()

    return df_


def split_modes(df_: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Split into GATE-based and HD-test-based admissions, drop duplicates."""
    gate_df_ = df_[df_["GATE Score"] > 0].copy().drop_duplicates()
    hd_df_ = df_[(df_["GATE Score"] == 0) & (df_["HD Score"] > 0)].copy().drop_duplicates()
    return gate_df_, hd_df_

DATA_PATH = "bits_hd_2024_clean.json"

if not Path(DATA_PATH).exists():
    st.error(f"Data file not found: {DATA_PATH}")
    st.stop()

df = load_data(DATA_PATH)
gate_df, hd_df = split_modes(df)

st.sidebar.title("Filters")

all_branches = sorted(df["ME Branch"].dropna().unique())
all_campuses = sorted(df["Campus"].dropna().unique())

selected_mode = st.sidebar.radio(
    "Admission mode",
    ("All", "GATE only", "BITS-HD Test only"),
    index=0,
)

branch_filter = st.sidebar.multiselect(
    "ME / M.Pharm Branch",
    options=all_branches,
    default=all_branches,
)

campus_filter = st.sidebar.multiselect(
    "Campus",
    options=all_campuses,
    default=all_campuses,
)

st.sidebar.markdown("---")

branch_drill = st.sidebar.selectbox(
    "Branch drilldown",
    options=["All branches"] + all_branches,
    index=0,
    help="Select a branch to see focused stats and raw data.",
)

st.sidebar.caption(
    "Use filters and branch drilldown together to zoom into specific patterns."
)


def apply_filters(df_: pd.DataFrame) -> pd.DataFrame:
    mask = df_["ME Branch"].isin(branch_filter) & df_["Campus"].isin(campus_filter)
    if branch_drill != "All branches":
        mask &= df_["ME Branch"] == branch_drill
    return df_[mask]

st.title("BITS HD Admissions Analytics (2024)")

st.caption(
    "BITS HD 2024 admissions analytics based on GATE and BITS-HD test–"
    "based entries, showing score distributions, branch cutoffs, and "
    "campus trends."
)

st.caption(
    "Source: Community-contributed Google Sheet "
    "[BITS HD 2024 Data]"
    "(https://docs.google.com/spreadsheets/d/16fZ25NnCwiVtJN5jI9ZPNHm32WJOJ5tRtljcvYTXF6c/)"
)

summary_col1, summary_col2, summary_col3, summary_col4 = st.columns(4)

summary_col1.metric("Total Records", len(df))
summary_col2.metric("Unique Branches", df["ME Branch"].nunique())
summary_col3.metric("Unique Campuses", df["Campus"].nunique())
summary_col4.metric(
    "GATE vs HD Share",
    f"{len(gate_df)} GATE / {len(hd_df)} HD",
)

if branch_drill != "All branches":
    st.info(f"Branch drilldown active: {branch_drill}")

def format_mean(x: float) -> float:
    return round(float(x), 2)


def apply_hover_rounding(fig, axis: str = "x"):
    fig.update_traces(
        hovertemplate=f"<b>Score</b>: %{{{axis}:.2f}}<br><b>Count</b>: %{{y}}<extra></extra>"
    )
    return fig

tab_gate, tab_hd = st.tabs(["GATE Admissions", "BITS-HD Admissions"])

with tab_gate:
    st.header("GATE Admissions Analysis")

    gated = apply_filters(gate_df)

    if gated.empty:
        st.info("No GATE admissions match the current filters.")
    else:
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Total GATE Entries", len(gated))
        m2.metric("Average GATE Score", f"{format_mean(gated['GATE Score'].mean()):.2f}")
        m3.metric("Highest GATE Score", int(gated["GATE Score"].max()))
        m4.metric("Lowest GATE Score", int(gated["GATE Score"].min()))

        st.markdown("### GATE Score Distribution")

        c1, c2 = st.columns((2, 1))

        with c1:
            bins = st.slider(
                "Histogram bins (GATE)",
                10,
                50,
                25,
                key="gate_bins",
            )
            fig_gate_hist = px.histogram(
                gated,
                x="GATE Score",
                nbins=bins,
                marginal="box",
                color_discrete_sequence=["#60a5fa"],
                title="GATE Score Distribution",
            )
            fig_gate_hist.update_layout(
                xaxis_title="GATE Score",
                yaxis_title="Count",
                hovermode="closest",
            )
            fig_gate_hist = apply_hover_rounding(fig_gate_hist, "x")
            st.plotly_chart(fig_gate_hist, width="stretch")

        with c2:
            fig_gate_box = px.box(
                gated,
                x="GATE Score",
                points="all",
                color_discrete_sequence=["#f97316"],
                title="Score Spread",
            )
            fig_gate_box.update_layout(hovermode="x")
            st.plotly_chart(fig_gate_box, width="stretch")

        st.markdown("### Branch & Campus-level Cutoffs")

        gate_cutoff = (
            gated.groupby(["ME Branch", "Campus"])["GATE Score"]
            .agg(["min", "max", "mean", "count"])
            .reset_index()
            .sort_values(["ME Branch", "Campus"])
        )
        gate_cutoff["mean"] = gate_cutoff["mean"].apply(format_mean)

        st.dataframe(
            gate_cutoff,
            width="stretch",
            hide_index=True,
        )

        st.markdown("### Average GATE Score by Branch")

        branch_mean_gate = (
            gated.groupby("ME Branch")["GATE Score"]
            .mean()
            .reset_index()
        )
        branch_mean_gate["GATE Score"] = branch_mean_gate["GATE Score"].apply(format_mean)
        branch_mean_gate = branch_mean_gate.sort_values("GATE Score", ascending=True)

        fig_gate_branch = px.bar(
            branch_mean_gate,
            x="GATE Score",
            y="ME Branch",
            orientation="h",
            color="GATE Score",
            color_continuous_scale="Blues",
            title="Average GATE Score by Branch",
        )
        fig_gate_branch.update_layout(
            coloraxis_showscale=False,
            hovermode="y unified",
        )
        fig_gate_branch.update_traces(
            hovertemplate="Branch: %{y}<br>Avg GATE: %{x:.2f}<extra></extra>"
        )
        st.plotly_chart(fig_gate_branch, width="stretch")

        st.markdown("### Campus Distribution (GATE)")

        col1, col2 = st.columns(2)

        campus_branch_gate = (
            gated.groupby(["Campus", "ME Branch"])
            .size()
            .reset_index(name="Count")
        )

        with col1:
            fig_gate_campus_bar = px.bar(
                campus_branch_gate,
                x="Count",
                y="Campus",
                color="ME Branch",
                title="GATE Entries per Campus by Branch",
                orientation="h",
            )
            fig_gate_campus_bar.update_layout(
                yaxis_title="Campus",
                xaxis_title="Number of entries",
                legend_title="ME Branch",
                barmode="stack",
            )
            st.plotly_chart(fig_gate_campus_bar, width="stretch")

        with col2:
            branch_counts_gate = (
                gated.groupby("ME Branch")
                .size()
                .reset_index(name="Count")
            )

            fig_gate_branch_pie = px.pie(
                branch_counts_gate,
                names="ME Branch",
                values="Count",
                title="GATE Share by Branch (all campuses)",
                hole=0.35,
            )
            fig_gate_branch_pie.update_traces(
                textposition="inside",
                texttemplate="%{label}<br>%{percent:.1%}",
            )
            st.plotly_chart(fig_gate_branch_pie, width="stretch")

#bits tab huihuihui
with tab_hd:
    st.header("BITS-HD Test Admissions Analysis")

    hdd = apply_filters(hd_df)

    if hdd.empty:
        st.info("No BITS-HD test admissions match the current filters.")
    else:
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Total HD Entries", len(hdd))
        m2.metric("Average HD Score", f"{format_mean(hdd['HD Score'].mean()):.2f}")
        m3.metric("Highest HD Score", int(hdd["HD Score"].max()))
        m4.metric("Lowest HD Score", int(hdd["HD Score"].min()))

        st.markdown("### BITS-HD Score Distribution")

        c1, c2 = st.columns((2, 1))

        with c1:
            bins_hd = st.slider(
                "Histogram bins (HD)",
                10,
                50,
                20,
                key="hd_bins",
            )
            fig_hd_hist = px.histogram(
                hdd,
                x="HD Score",
                nbins=bins_hd,
                marginal="box",
                color_discrete_sequence=["#f97373"],
                title="BITS-HD Score Distribution",
            )
            fig_hd_hist.update_layout(
                xaxis_title="HD Score",
                yaxis_title="Count",
                hovermode="closest",
            )
            fig_hd_hist = apply_hover_rounding(fig_hd_hist, "x")
            st.plotly_chart(fig_hd_hist, width="stretch")

        with c2:
            fig_hd_box = px.box(
                hdd,
                x="HD Score",
                points="all",
                color_discrete_sequence=["#22c55e"],
                title="Score Spread",
            )
            fig_hd_box.update_layout(hovermode="x")
            st.plotly_chart(fig_hd_box, width="stretch")

        st.markdown("### Branch & Campus-level Cutoffs")

        hd_cutoff = (
            hdd.groupby(["ME Branch", "Campus"])["HD Score"]
            .agg(["min", "max", "mean", "count"])
            .reset_index()
            .sort_values(["ME Branch", "Campus"])
        )
        hd_cutoff["mean"] = hd_cutoff["mean"].apply(format_mean)

        st.dataframe(
            hd_cutoff,
            width="stretch",
            hide_index=True,
        )

        st.markdown("### Average HD Score by Branch")

        branch_mean_hd = (
            hdd.groupby("ME Branch")["HD Score"]
            .mean()
            .reset_index()
        )
        branch_mean_hd["HD Score"] = branch_mean_hd["HD Score"].apply(format_mean)
        branch_mean_hd = branch_mean_hd.sort_values("HD Score", ascending=True)

        fig_hd_branch = px.bar(
            branch_mean_hd,
            x="HD Score",
            y="ME Branch",
            orientation="h",
            color="HD Score",
            color_continuous_scale="Reds",
            title="Average HD Score by Branch",
        )
        fig_hd_branch.update_layout(
            coloraxis_showscale=False,
            hovermode="y unified",
        )
        fig_hd_branch.update_traces(
            hovertemplate="Branch: %{y}<br>Avg HD: %{x:.2f}<extra></extra>"
        )
        st.plotly_chart(fig_hd_branch, width="stretch")

        st.markdown("### Campus Distribution (BITS-HD)")

        col1, col2 = st.columns(2)

        campus_branch_hd = (
            hdd.groupby(["Campus", "ME Branch"])
            .size()
            .reset_index(name="Count")
        )

        with col1:
            fig_hd_campus_bar = px.bar(
                campus_branch_hd,
                x="Count",
                y="Campus",
                color="ME Branch",
                title="HD Entries per Campus by Branch",
                orientation="h",
            )
            fig_hd_campus_bar.update_layout(
                yaxis_title="Campus",
                xaxis_title="Number of entries",
                legend_title="ME Branch",
                barmode="stack",
            )
            st.plotly_chart(fig_hd_campus_bar, width="stretch")

        with col2:
            branch_counts_hd = (
                hdd.groupby("ME Branch")
                .size()
                .reset_index(name="Count")
            )

            fig_hd_branch_pie = px.pie(
                branch_counts_hd,
                names="ME Branch",
                values="Count",
                title="HD Share by Branch (all campuses)",
                hole=0.35,
            )
            fig_hd_branch_pie.update_traces(
                textposition="inside",
                texttemplate="%{label}<br>%{percent:.1%}",
            )
            st.plotly_chart(fig_hd_branch_pie, width="stretch")

st.markdown("---")
st.subheader("Raw Data (after filters)")

if selected_mode == "GATE only":
    combined = apply_filters(gate_df)
elif selected_mode == "BITS-HD Test only":
    combined = apply_filters(hd_df)
else:
    combined = apply_filters(df)

st.dataframe(combined, width="stretch", height=400)

st.caption(
    "Note: This dashboard summarizes BITS HD 2024 data only. "
    "Original responses: "
    "[Google Sheet link]"
    "(https://docs.google.com/spreadsheets/d/16fZ25NnCwiVtJN5jI9ZPNHm32WJOJ5tRtljcvYTXF6c/)."
)
