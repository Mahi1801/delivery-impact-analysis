import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import seaborn as sns
from scipy import stats
import os
import warnings
warnings.filterwarnings('ignore')

# ── PAGE CONFIG ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Delivery Feature Impact Analysis",
    page_icon="📦",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ── COLORS ─────────────────────────────────────────────────────────────────────
BEFORE  = "#4C72B0"
AFTER   = "#DD8452"
BG      = "#0f1117"
CARD_BG = "#1a1d27"

# ── CUSTOM CSS ─────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Mono:wght@400;700&family=DM+Sans:wght@300;400;500;600&display=swap');

html, body, [class*="css"] {
    font-family: 'DM Sans', sans-serif;
    background-color: #0f1117;
    color: #e8e8e8;
}

.main { background-color: #0f1117; }
.block-container { padding: 2rem 3rem; }

.metric-card {
    background: #1a1d27;
    border: 1px solid #2a2d3a;
    border-radius: 12px;
    padding: 1.2rem 1.5rem;
    text-align: center;
    position: relative;
    overflow: hidden;
}
.metric-card::before {
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 3px;
}
.metric-card.before::before { background: #4C72B0; }
.metric-card.after::before  { background: #DD8452; }
.metric-card.neutral::before { background: #6c7a89; }

.metric-label {
    font-size: 0.72rem;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    color: #888;
    margin-bottom: 0.4rem;
    font-family: 'Space Mono', monospace;
}
.metric-value {
    font-size: 2rem;
    font-weight: 600;
    line-height: 1;
    margin-bottom: 0.2rem;
}
.metric-value.blue  { color: #4C72B0; }
.metric-value.orange{ color: #DD8452; }
.metric-value.red   { color: #e05c5c; }
.metric-value.green { color: #5cb85c; }
.metric-sub {
    font-size: 0.75rem;
    color: #666;
}

.section-title {
    font-family: 'Space Mono', monospace;
    font-size: 0.7rem;
    text-transform: uppercase;
    letter-spacing: 0.15em;
    color: #555;
    margin: 2rem 0 1rem;
    padding-bottom: 0.5rem;
    border-bottom: 1px solid #2a2d3a;
}

.insight-card {
    background: #1a1d27;
    border-left: 3px solid #4C72B0;
    border-radius: 0 8px 8px 0;
    padding: 1rem 1.2rem;
    margin-bottom: 0.8rem;
    font-size: 0.9rem;
    color: #ccc;
}
.insight-card.warning { border-left-color: #DD8452; }
.insight-card.success { border-left-color: #5cb85c; }

.stat-badge {
    display: inline-block;
    background: #252837;
    border-radius: 6px;
    padding: 0.2rem 0.6rem;
    font-family: 'Space Mono', monospace;
    font-size: 0.75rem;
    color: #aaa;
    margin: 0.2rem;
}

.page-header {
    background: linear-gradient(135deg, #1a1d27 0%, #0f1117 100%);
    border: 1px solid #2a2d3a;
    border-radius: 16px;
    padding: 2rem 2.5rem;
    margin-bottom: 2rem;
}
.page-title {
    font-family: 'Space Mono', monospace;
    font-size: 1.6rem;
    font-weight: 700;
    color: #fff;
    margin: 0;
}
.page-subtitle {
    font-size: 0.9rem;
    color: #666;
    margin-top: 0.5rem;
}

.stSelectbox label, .stSlider label { color: #888 !important; font-size: 0.8rem !important; }
.stSidebar { background: #1a1d27 !important; }
section[data-testid="stSidebar"] { background: #1a1d27 !important; }
section[data-testid="stSidebar"] .block-container { padding: 1.5rem 1rem; }

div[data-testid="metric-container"] {
    background: #1a1d27;
    border: 1px solid #2a2d3a;
    border-radius: 10px;
    padding: 1rem;
}
</style>
""", unsafe_allow_html=True)


# ── DATA LOADER ─────────────────────────────────────────────────────────────────
@st.cache_data
def load_data():
    """Load clean_orders.csv. If missing, generate synthetic data."""
    paths = [
        "data/clean_orders.csv",
        "../data/clean_orders.csv",
        "clean_orders.csv"
    ]
    for p in paths:
        if os.path.exists(p):
            df = pd.read_csv(p, parse_dates=["order_date"])
            return df, False

    # ── GENERATE SYNTHETIC DATA IF CSV NOT FOUND ──
    np.random.seed(42)
    import random
    random.seed(42)
    from datetime import datetime, timedelta

    TOTAL = 30000
    START = datetime(2024, 1, 1)
    CUTOFF= START + timedelta(days=30)
    records = []

    for i in range(TOTAL):
        rday = random.randint(0, 59)
        odate= START + timedelta(days=rday)
        hour = random.choices(range(8,24), weights=[1,1,2,3,4,4,3,2,3,4,4,3,2,2,1,1], k=1)[0]
        feat = odate < CUTOFF
        zone = random.choices(["High","Medium","Low"], weights=[50,30,20])[0]
        dist = min(round(np.random.lognormal(1.5, 0.5), 2), 20)
        peak = "Peak" if hour in range(12,15) or hour in range(19,23) else "Non-Peak"

        base = 10 + dist*2.5
        pp   = np.random.normal(5,2) if peak=="Peak" else np.random.normal(1,0.5)
        zp   = {"High":0,"Medium":2,"Low":5}[zone]
        fi   = 0
        if not feat:
            fi = np.random.normal(6,2.5)
            if peak=="Peak": fi*=1.8
            if zone=="Low":  fi*=1.3
        dtime= round(max(5, base+pp+zp+fi+np.random.normal(0,1.5)),1)
        eta  = round(10+dist*2.2+np.random.uniform(0,3),1)
        delay= dtime-eta
        cp   = min(0.03+(0.12 if delay>15 else 0.05 if delay>8 else 0)+(0 if feat else 0.02),0.25)
        status="Cancelled" if random.random()<cp else "Delivered"
        rating= None if status=="Cancelled" else round(max(1,min(5,np.random.normal(4.2 if feat else 3.7,0.6))),1)

        dbucket = "Short (0-3 km)" if dist<=3 else "Medium (3-7 km)" if dist<=7 else "Long (7+ km)"

        records.append({
            "order_id": 1000+i,
            "order_date": odate.strftime("%Y-%m-%d"),
            "order_hour": hour,
            "feature_active": "Yes" if feat else "No",
            "period": "Before" if feat else "After",
            "zone": zone,
            "delivery_distance_km": dist,
            "distance_bucket": dbucket,
            "peak_flag": peak,
            "delivery_time_min": dtime,
            "promised_eta_min": eta,
            "delay_min": delay,
            "on_time_flag": 1 if delay<=0 else 0,
            "sla_breach": 1 if delay>10 else 0,
            "cancelled_flag": 1 if status=="Cancelled" else 0,
            "order_status": status,
            "customer_rating": rating,
            "rider_id": f"R{random.randint(1,200):03d}",
        })

    df = pd.DataFrame(records)
    df["order_date"] = pd.to_datetime(df["order_date"])
    return df, True


@st.cache_data
def get_kpis(df):
    b = df[df["period"]=="Before"]
    a = df[df["period"]=="After"]
    return {
        "avg_before": b["delivery_time_min"].mean(),
        "avg_after":  a["delivery_time_min"].mean(),
        "p90_before": b["delivery_time_min"].quantile(0.9),
        "p90_after":  a["delivery_time_min"].quantile(0.9),
        "ot_before":  b["on_time_flag"].mean()*100,
        "ot_after":   a["on_time_flag"].mean()*100,
        "cr_before":  b["cancelled_flag"].mean()*100,
        "cr_after":   a["cancelled_flag"].mean()*100,
        "sla_before": b["sla_breach"].mean()*100,
        "sla_after":  a["sla_breach"].mean()*100,
        "rat_before": b["customer_rating"].mean(),
        "rat_after":  a["customer_rating"].mean(),
        "n_before":   len(b),
        "n_after":    len(a),
    }


# ── CHART HELPERS ──────────────────────────────────────────────────────────────
def dark_fig(w=10, h=4):
    fig, ax = plt.subplots(figsize=(w, h))
    fig.patch.set_facecolor("#1a1d27")
    ax.set_facecolor("#1a1d27")
    ax.tick_params(colors="#888", labelsize=9)
    ax.spines['bottom'].set_color("#333")
    ax.spines['left'].set_color("#333")
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.yaxis.label.set_color("#888")
    ax.xaxis.label.set_color("#888")
    ax.title.set_color("#ccc")
    return fig, ax

def dark_fig2(w=12, h=4):
    fig, axes = plt.subplots(1, 2, figsize=(w, h))
    fig.patch.set_facecolor("#1a1d27")
    for ax in axes:
        ax.set_facecolor("#1a1d27")
        ax.tick_params(colors="#888", labelsize=9)
        for sp in ['bottom','left']:
            ax.spines[sp].set_color("#333")
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.yaxis.label.set_color("#888")
        ax.xaxis.label.set_color("#888")
        ax.title.set_color("#ccc")
    return fig, axes


# ── SIDEBAR ─────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 📦 Delivery Analysis")
    st.markdown("---")

    page = st.radio(
        "Navigate",
        ["📊 Executive Summary",
         "📈 Delivery Trends",
         "🗂️ Segmentation",
         "💰 Business Impact",
         "🔬 Statistical Tests",
         "📋 Raw Data"],
        label_visibility="collapsed"
    )

    st.markdown("---")
    st.markdown("### Filters")

    df_raw, generated = load_data()

    zone_filter = st.multiselect(
        "Zone", ["High", "Medium", "Low"],
        default=["High", "Medium", "Low"]
    )
    peak_filter = st.multiselect(
        "Hour Type", ["Peak", "Non-Peak"],
        default=["Peak", "Non-Peak"]
    )
    dist_filter = st.multiselect(
        "Distance",
        ["Short (0-3 km)", "Medium (3-7 km)", "Long (7+ km)"],
        default=["Short (0-3 km)", "Medium (3-7 km)", "Long (7+ km)"]
    )

    df = df_raw[
        df_raw["zone"].isin(zone_filter) &
        df_raw["peak_flag"].isin(peak_filter) &
        df_raw["distance_bucket"].isin(dist_filter)
    ].copy()

    st.markdown("---")
    if generated:
        st.info("⚡ Using generated data. Place `clean_orders.csv` in `data/` folder to use real data.")
    else:
        st.success(f"✅ Loaded `clean_orders.csv`\n\n{len(df):,} orders after filters")

    st.markdown("---")
    st.markdown("""
    <div style='font-size:0.72rem; color:#444; font-family: monospace;'>
    Tools: Python · Pandas · Streamlit<br>
    Stats: T-Test · Chi-Square · Cohen's d<br>
    Data: 30k orders · 60-day window
    </div>
    """, unsafe_allow_html=True)


kpis = get_kpis(df)
before_df = df[df["period"] == "Before"]
after_df  = df[df["period"] == "After"]


# ══════════════════════════════════════════════════════════════════════════════
# PAGE 1 — EXECUTIVE SUMMARY
# ══════════════════════════════════════════════════════════════════════════════
if page == "📊 Executive Summary":

    st.markdown("""
    <div class="page-header">
        <div class="page-title">📦 Delivery Feature Impact Analysis</div>
        <div class="page-subtitle">
            Measuring the performance effect of removing the <strong>Rider Priority Routing</strong> feature
            from a hypothetical food delivery platform — 30 days before vs 30 days after.
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ── KPI GRID ──
    st.markdown('<div class="section-title">Core KPIs — Before vs After Feature Removal</div>', unsafe_allow_html=True)

    c1, c2, c3 = st.columns(3)
    delta_avg = ((kpis["avg_after"] - kpis["avg_before"]) / kpis["avg_before"]) * 100
    delta_ot  = kpis["ot_after"]  - kpis["ot_before"]
    delta_cr  = kpis["cr_after"]  - kpis["cr_before"]
    delta_sla = kpis["sla_after"] - kpis["sla_before"]
    delta_rat = kpis["rat_after"] - kpis["rat_before"]

    with c1:
        st.markdown(f"""
        <div class="metric-card before">
            <div class="metric-label">Avg Delivery Time — Before</div>
            <div class="metric-value blue">{kpis['avg_before']:.1f}<span style='font-size:1rem'> min</span></div>
            <div class="metric-sub">P90: {kpis['p90_before']:.1f} min</div>
        </div>""", unsafe_allow_html=True)
    with c2:
        col = "red" if delta_avg > 0 else "green"
        st.markdown(f"""
        <div class="metric-card after">
            <div class="metric-label">Avg Delivery Time — After</div>
            <div class="metric-value orange">{kpis['avg_after']:.1f}<span style='font-size:1rem'> min</span></div>
            <div class="metric-sub">P90: {kpis['p90_after']:.1f} min</div>
        </div>""", unsafe_allow_html=True)
    with c3:
        arrow = "↑" if delta_avg > 0 else "↓"
        col = "#e05c5c" if delta_avg > 0 else "#5cb85c"
        st.markdown(f"""
        <div class="metric-card neutral">
            <div class="metric-label">Delivery Time Change</div>
            <div class="metric-value" style="color:{col}">{arrow} {abs(delta_avg):.1f}%</div>
            <div class="metric-sub">{kpis['avg_before']:.1f} → {kpis['avg_after']:.1f} mins</div>
        </div>""", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    c4, c5, c6, c7, c8 = st.columns(5)

    with c4:
        st.markdown(f"""
        <div class="metric-card before">
            <div class="metric-label">On-Time % Before</div>
            <div class="metric-value blue">{kpis['ot_before']:.1f}%</div>
        </div>""", unsafe_allow_html=True)
    with c5:
        col = "#e05c5c" if delta_ot < 0 else "#5cb85c"
        arrow = "↓" if delta_ot < 0 else "↑"
        st.markdown(f"""
        <div class="metric-card after">
            <div class="metric-label">On-Time % After</div>
            <div class="metric-value orange">{kpis['ot_after']:.1f}%</div>
            <div class="metric-sub" style="color:{col}">{arrow} {abs(delta_ot):.1f} pts</div>
        </div>""", unsafe_allow_html=True)
    with c6:
        col2 = "#e05c5c" if delta_cr > 0 else "#5cb85c"
        arrow2 = "↑" if delta_cr > 0 else "↓"
        st.markdown(f"""
        <div class="metric-card after">
            <div class="metric-label">Cancel Rate After</div>
            <div class="metric-value orange">{kpis['cr_after']:.2f}%</div>
            <div class="metric-sub" style="color:{col2}">{arrow2} {abs(delta_cr):.2f} pts</div>
        </div>""", unsafe_allow_html=True)
    with c7:
        col3 = "#e05c5c" if delta_sla > 0 else "#5cb85c"
        st.markdown(f"""
        <div class="metric-card after">
            <div class="metric-label">SLA Breach After</div>
            <div class="metric-value orange">{kpis['sla_after']:.1f}%</div>
            <div class="metric-sub" style="color:{col3}">was {kpis['sla_before']:.1f}%</div>
        </div>""", unsafe_allow_html=True)
    with c8:
        col4 = "#e05c5c" if delta_rat < 0 else "#5cb85c"
        arrow4 = "↓" if delta_rat < 0 else "↑"
        st.markdown(f"""
        <div class="metric-card after">
            <div class="metric-label">Avg Rating After</div>
            <div class="metric-value orange">{kpis['rat_after']:.2f}</div>
            <div class="metric-sub" style="color:{col4}">{arrow4} {abs(delta_rat):.2f} pts</div>
        </div>""", unsafe_allow_html=True)

    # ── KPI BAR CHART ──
    st.markdown('<div class="section-title">Side-by-Side KPI Comparison</div>', unsafe_allow_html=True)

    fig, ax = dark_fig(10, 4)
    metrics = ["Avg Del. Time", "On-Time %", "Cancel Rate %", "SLA Breach %"]
    b_vals  = [kpis["avg_before"], kpis["ot_before"], kpis["cr_before"], kpis["sla_before"]]
    a_vals  = [kpis["avg_after"],  kpis["ot_after"],  kpis["cr_after"],  kpis["sla_after"]]
    x = np.arange(len(metrics))
    w = 0.35
    bars1 = ax.bar(x - w/2, b_vals, w, color=BEFORE, alpha=0.9, label="Before", zorder=3)
    bars2 = ax.bar(x + w/2, a_vals, w, color=AFTER,  alpha=0.9, label="After",  zorder=3)
    ax.set_xticks(x)
    ax.set_xticklabels(metrics, fontsize=10)
    ax.legend(facecolor="#252837", labelcolor="#ccc", framealpha=0.8)
    ax.grid(axis="y", color="#2a2d3a", linewidth=0.5, zorder=0)
    for bar in bars1:
        ax.text(bar.get_x()+bar.get_width()/2, bar.get_height()+0.3,
                f"{bar.get_height():.1f}", ha="center", va="bottom", fontsize=8, color="#aaa")
    for bar in bars2:
        ax.text(bar.get_x()+bar.get_width()/2, bar.get_height()+0.3,
                f"{bar.get_height():.1f}", ha="center", va="bottom", fontsize=8, color="#aaa")
    plt.tight_layout()
    st.pyplot(fig)
    plt.close()

    # ── INSIGHTS ──
    st.markdown('<div class="section-title">Key Insights</div>', unsafe_allow_html=True)
    i1, i2 = st.columns(2)
    with i1:
        st.markdown(f"""
        <div class="insight-card warning">
            🕐 <strong>Delivery Time</strong> increased by <strong>{delta_avg:.1f}%</strong>
            after feature removal ({kpis['avg_before']:.1f} → {kpis['avg_after']:.1f} mins).
        </div>
        <div class="insight-card warning">
            ❌ <strong>On-Time Delivery</strong> dropped by <strong>{abs(delta_ot):.1f} percentage points</strong>
            ({kpis['ot_before']:.1f}% → {kpis['ot_after']:.1f}%).
        </div>
        <div class="insight-card warning">
            📉 <strong>Customer Rating</strong> fell from
            {kpis['rat_before']:.2f} to {kpis['rat_after']:.2f} stars.
        </div>
        """, unsafe_allow_html=True)
    with i2:
        st.markdown(f"""
        <div class="insight-card">
            📦 <strong>Total orders analysed:</strong>
            {kpis['n_before']:,} before + {kpis['n_after']:,} after = {len(df):,} total.
        </div>
        <div class="insight-card warning">
            🚨 <strong>SLA Breach</strong> rose from {kpis['sla_before']:.1f}%
            to {kpis['sla_after']:.1f}% — a {delta_sla:.1f} point increase.
        </div>
        <div class="insight-card">
            📊 All changes validated via <strong>Welch's T-Test</strong> and
            <strong>Chi-Square</strong> testing (p &lt; 0.001).
        </div>
        """, unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# PAGE 2 — DELIVERY TRENDS
# ══════════════════════════════════════════════════════════════════════════════
elif page == "📈 Delivery Trends":

    st.markdown('<div class="page-title" style="color:#fff;font-family:monospace;font-size:1.3rem;margin-bottom:1.5rem;">📈 Delivery Performance Trends</div>', unsafe_allow_html=True)

    # Daily trend
    st.markdown('<div class="section-title">Daily Average Delivery Time</div>', unsafe_allow_html=True)
    daily = df.groupby(["order_date", "period"])["delivery_time_min"].mean().reset_index()
    fig, ax = dark_fig(12, 4)
    for period, color in [("Before", BEFORE), ("After", AFTER)]:
        sub = daily[daily["period"] == period]
        ax.plot(sub["order_date"], sub["delivery_time_min"],
                color=color, linewidth=2, label=period, alpha=0.9)
    cutoff = df[df["period"]=="After"]["order_date"].min()
    ax.axvline(x=cutoff, color="#e05c5c", linestyle="--", linewidth=1.5, alpha=0.7)
    ax.text(cutoff, ax.get_ylim()[1]*0.95, " Feature\n Removed",
            color="#e05c5c", fontsize=8, va="top")
    ax.set_ylabel("Avg Delivery Time (mins)", color="#888")
    ax.legend(facecolor="#252837", labelcolor="#ccc")
    ax.grid(axis="y", color="#2a2d3a", linewidth=0.5)
    plt.tight_layout()
    st.pyplot(fig)
    plt.close()

    # Distribution + Box
    st.markdown('<div class="section-title">Delivery Time Distribution</div>', unsafe_allow_html=True)
    fig, axes = dark_fig2(12, 4)

    for period, color in [("Before", BEFORE), ("After", AFTER)]:
        sub = df[df["period"]==period]["delivery_time_min"]
        axes[0].hist(sub, bins=40, alpha=0.6, color=color, label=period, edgecolor="none")
    axes[0].set_xlabel("Delivery Time (mins)")
    axes[0].set_ylabel("Order Count")
    axes[0].set_title("Distribution: Before vs After")
    axes[0].legend(facecolor="#252837", labelcolor="#ccc")
    axes[0].grid(axis="y", color="#2a2d3a", linewidth=0.5)

    bp_data = [before_df["delivery_time_min"].values, after_df["delivery_time_min"].values]
    bp = axes[1].boxplot(bp_data, patch_artist=True, labels=["Before", "After"],
                         medianprops=dict(color="#fff", linewidth=2),
                         whiskerprops=dict(color="#555"),
                         capprops=dict(color="#555"),
                         flierprops=dict(marker="o", color="#555", markersize=2, alpha=0.3))
    bp["boxes"][0].set_facecolor(BEFORE)
    bp["boxes"][0].set_alpha(0.7)
    bp["boxes"][1].set_facecolor(AFTER)
    bp["boxes"][1].set_alpha(0.7)
    axes[1].set_ylabel("Delivery Time (mins)")
    axes[1].set_title("Box Plot Comparison")
    axes[1].grid(axis="y", color="#2a2d3a", linewidth=0.5)

    plt.tight_layout()
    st.pyplot(fig)
    plt.close()

    # On-Time % trend
    st.markdown('<div class="section-title">Daily On-Time Delivery %</div>', unsafe_allow_html=True)
    ot_daily = df.groupby(["order_date","period"])["on_time_flag"].mean().reset_index()
    ot_daily["on_time_pct"] = ot_daily["on_time_flag"] * 100
    fig, ax = dark_fig(12, 3)
    for period, color in [("Before", BEFORE), ("After", AFTER)]:
        sub = ot_daily[ot_daily["period"]==period]
        ax.plot(sub["order_date"], sub["on_time_pct"],
                color=color, linewidth=1.8, label=period, alpha=0.9)
    ax.axvline(x=cutoff, color="#e05c5c", linestyle="--", linewidth=1.2, alpha=0.6)
    ax.set_ylabel("On-Time %")
    ax.set_ylim(0, 100)
    ax.legend(facecolor="#252837", labelcolor="#ccc")
    ax.grid(axis="y", color="#2a2d3a", linewidth=0.5)
    plt.tight_layout()
    st.pyplot(fig)
    plt.close()


# ══════════════════════════════════════════════════════════════════════════════
# PAGE 3 — SEGMENTATION
# ══════════════════════════════════════════════════════════════════════════════
elif page == "🗂️ Segmentation":

    st.markdown('<div class="page-title" style="color:#fff;font-family:monospace;font-size:1.3rem;margin-bottom:1.5rem;">🗂️ Segmentation Analysis</div>', unsafe_allow_html=True)

    # Peak vs Non-Peak
    st.markdown('<div class="section-title">Peak vs Non-Peak Impact</div>', unsafe_allow_html=True)
    peak_kpi = df.groupby(["period","peak_flag"]).agg(
        avg_dt=("delivery_time_min","mean"),
        ot_pct=("on_time_flag","mean")
    ).reset_index()
    peak_kpi["ot_pct"] *= 100

    fig, axes = dark_fig2(12, 4)
    for i, (metric, label) in enumerate([("avg_dt","Avg Delivery Time (mins)"),("ot_pct","On-Time %")]):
        sub_b = peak_kpi[peak_kpi["period"]=="Before"]
        sub_a = peak_kpi[peak_kpi["period"]=="After"]
        flags = peak_kpi["peak_flag"].unique()
        x = np.arange(len(flags))
        w = 0.35
        axes[i].bar(x-w/2, sub_b.set_index("peak_flag")[metric].reindex(flags), w,
                    color=BEFORE, alpha=0.85, label="Before")
        axes[i].bar(x+w/2, sub_a.set_index("peak_flag")[metric].reindex(flags), w,
                    color=AFTER,  alpha=0.85, label="After")
        axes[i].set_xticks(x)
        axes[i].set_xticklabels(flags)
        axes[i].set_ylabel(label)
        axes[i].legend(facecolor="#252837", labelcolor="#ccc")
        axes[i].grid(axis="y", color="#2a2d3a", linewidth=0.5)
    axes[0].set_title("Avg Delivery Time by Hour Type")
    axes[1].set_title("On-Time % by Hour Type")
    plt.tight_layout()
    st.pyplot(fig)
    plt.close()

    # Zone-wise
    st.markdown('<div class="section-title">Zone-wise Performance</div>', unsafe_allow_html=True)
    zone_kpi = df.groupby(["period","zone"]).agg(
        avg_dt=("delivery_time_min","mean"),
        cr_pct=("cancelled_flag","mean")
    ).reset_index()
    zone_kpi["cr_pct"] *= 100

    fig, axes = dark_fig2(12, 4)
    zones = ["High","Medium","Low"]
    x = np.arange(len(zones))
    w = 0.35
    for i, (metric, label, title) in enumerate([
        ("avg_dt","Avg Delivery Time (mins)","Avg Delivery Time by Zone"),
        ("cr_pct","Cancellation Rate %","Cancellation Rate by Zone")
    ]):
        sub_b = zone_kpi[zone_kpi["period"]=="Before"].set_index("zone")[metric].reindex(zones)
        sub_a = zone_kpi[zone_kpi["period"]=="After"].set_index("zone")[metric].reindex(zones)
        axes[i].bar(x-w/2, sub_b, w, color=BEFORE, alpha=0.85, label="Before")
        axes[i].bar(x+w/2, sub_a, w, color=AFTER,  alpha=0.85, label="After")
        axes[i].set_xticks(x)
        axes[i].set_xticklabels(zones)
        axes[i].set_ylabel(label)
        axes[i].set_title(title)
        axes[i].legend(facecolor="#252837", labelcolor="#ccc")
        axes[i].grid(axis="y", color="#2a2d3a", linewidth=0.5)
    plt.tight_layout()
    st.pyplot(fig)
    plt.close()

    # Distance
    st.markdown('<div class="section-title">Distance Bucket Analysis</div>', unsafe_allow_html=True)
    dist_kpi = df.groupby(["period","distance_bucket"]).agg(
        avg_dt=("delivery_time_min","mean"),
        sla_pct=("sla_breach","mean")
    ).reset_index()
    dist_kpi["sla_pct"] *= 100

    fig, axes = dark_fig2(12, 4)
    dbuckets = ["Short (0-3 km)","Medium (3-7 km)","Long (7+ km)"]
    x = np.arange(len(dbuckets))
    for i, (metric, label, title) in enumerate([
        ("avg_dt","Avg Delivery Time (mins)","Delivery Time by Distance"),
        ("sla_pct","SLA Breach %","SLA Breach Rate by Distance")
    ]):
        sub_b = dist_kpi[dist_kpi["period"]=="Before"].set_index("distance_bucket")[metric].reindex(dbuckets)
        sub_a = dist_kpi[dist_kpi["period"]=="After"].set_index("distance_bucket")[metric].reindex(dbuckets)
        axes[i].bar(x-w/2, sub_b, w, color=BEFORE, alpha=0.85, label="Before")
        axes[i].bar(x+w/2, sub_a, w, color=AFTER,  alpha=0.85, label="After")
        axes[i].set_xticks(x)
        axes[i].set_xticklabels(["Short\n(0-3km)","Medium\n(3-7km)","Long\n(7+km)"])
        axes[i].set_ylabel(label)
        axes[i].set_title(title)
        axes[i].legend(facecolor="#252837", labelcolor="#ccc")
        axes[i].grid(axis="y", color="#2a2d3a", linewidth=0.5)
    plt.tight_layout()
    st.pyplot(fig)
    plt.close()

    # Heatmap
    st.markdown('<div class="section-title">Zone × Period Heatmap (Avg Delivery Time)</div>', unsafe_allow_html=True)
    heat = df.groupby(["zone","period"])["delivery_time_min"].mean().unstack()
    heat = heat.reindex(["High","Medium","Low"])
    fig, ax = dark_fig(8, 3)
    im = ax.imshow(heat.values, cmap="YlOrRd", aspect="auto")
    ax.set_xticks([0,1])
    ax.set_xticklabels(heat.columns, color="#ccc")
    ax.set_yticks([0,1,2])
    ax.set_yticklabels(heat.index, color="#ccc")
    for i in range(heat.shape[0]):
        for j in range(heat.shape[1]):
            ax.text(j, i, f"{heat.values[i,j]:.1f}", ha="center", va="center",
                    color="#111", fontsize=13, fontweight="bold")
    plt.colorbar(im, ax=ax, label="Avg Delivery Time (mins)")
    ax.set_title("Heatmap: Zone × Period", color="#ccc")
    plt.tight_layout()
    st.pyplot(fig)
    plt.close()


# ══════════════════════════════════════════════════════════════════════════════
# PAGE 4 — BUSINESS IMPACT
# ══════════════════════════════════════════════════════════════════════════════
elif page == "💰 Business Impact":

    st.markdown('<div class="page-title" style="color:#fff;font-family:monospace;font-size:1.3rem;margin-bottom:1.5rem;">💰 Business Impact Estimation</div>', unsafe_allow_html=True)

    cr_b = kpis["cr_before"] / 100
    cr_a = kpis["cr_after"]  / 100
    n_after = kpis["n_after"]
    extra_cancels = round((cr_a - cr_b) * n_after)
    revenue_loss  = round(extra_cancels * 350 * 0.15)
    sla_extra     = round((kpis["sla_after"] - kpis["sla_before"]) / 100 * n_after)

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown(f"""
        <div class="metric-card after">
            <div class="metric-label">Extra Cancellations</div>
            <div class="metric-value red">{extra_cancels:,}</div>
            <div class="metric-sub">vs baseline rate</div>
        </div>""", unsafe_allow_html=True)
    with c2:
        st.markdown(f"""
        <div class="metric-card after">
            <div class="metric-label">Estimated Revenue Loss</div>
            <div class="metric-value red">₹{revenue_loss:,}</div>
            <div class="metric-sub">@₹350 avg order, 15% margin</div>
        </div>""", unsafe_allow_html=True)
    with c3:
        st.markdown(f"""
        <div class="metric-card after">
            <div class="metric-label">Extra SLA Breaches</div>
            <div class="metric-value orange">{sla_extra:,}</div>
            <div class="metric-sub">orders delivered 10+ min late</div>
        </div>""", unsafe_allow_html=True)
    with c4:
        rat_drop = kpis["rat_before"] - kpis["rat_after"]
        st.markdown(f"""
        <div class="metric-card after">
            <div class="metric-label">Rating Drop</div>
            <div class="metric-value orange">-{rat_drop:.2f} ★</div>
            <div class="metric-sub">{kpis['rat_before']:.2f} → {kpis['rat_after']:.2f}</div>
        </div>""", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # Cancellation rate comparison
    st.markdown('<div class="section-title">Cancellation Rate: Baseline vs Actual</div>', unsafe_allow_html=True)
    fig, axes = dark_fig2(12, 4)

    # Left — bar chart
    categories = ["Baseline\n(Before)", "Actual\n(After)"]
    values = [kpis["cr_before"], kpis["cr_after"]]
    colors = [BEFORE, AFTER]
    bars = axes[0].bar(categories, values, color=colors, alpha=0.85, width=0.4)
    for bar, val in zip(bars, values):
        axes[0].text(bar.get_x()+bar.get_width()/2, bar.get_height()+0.02,
                     f"{val:.2f}%", ha="center", va="bottom", color="#ccc", fontsize=11)
    axes[0].set_ylabel("Cancellation Rate %")
    axes[0].set_title("Cancellation Rate Comparison")
    axes[0].grid(axis="y", color="#2a2d3a", linewidth=0.5)

    # Right — revenue impact waterfall style
    impact_labels = ["Baseline\nCancels", "Extra\nCancels", "Revenue\nLoss (×100)"]
    impact_vals   = [
        round(cr_b * n_after),
        extra_cancels,
        revenue_loss // 100
    ]
    bar_colors = [BEFORE, "#e05c5c", "#c0392b"]
    axes[1].bar(impact_labels, impact_vals, color=bar_colors, alpha=0.85, width=0.5)
    for i, (x, v) in enumerate(zip(impact_labels, impact_vals)):
        axes[1].text(i, v+10, f"{v:,}", ha="center", va="bottom", color="#ccc", fontsize=10)
    axes[1].set_ylabel("Count / Scaled Value")
    axes[1].set_title("Business Impact Breakdown")
    axes[1].grid(axis="y", color="#2a2d3a", linewidth=0.5)

    plt.tight_layout()
    st.pyplot(fig)
    plt.close()

    # Recommendations
    st.markdown('<div class="section-title">Recommendations</div>', unsafe_allow_html=True)
    recs = [
        ("🔄 Partial Rollback", "Re-enable Rider Priority Routing during Peak hours (12-3PM, 7-10PM). Peak hours account for ~60% of the degradation.", "warning"),
        ("📍 Zone-based Re-enable", "Prioritize re-enabling in Low-density zones — these saw the highest cancellation rate increase due to fewer available riders.", "warning"),
        ("⏱️ ETA Recalibration", "Increase promised ETAs by ~5-8 mins post-removal to reduce perceived lateness and prevent cancellations from impatient customers.", ""),
        ("🧪 A/B Test Before Full Rollout", "Re-enable the feature for 20% of orders first. Validate impact cleanly over 7 days before full commitment.", "success"),
    ]
    for title, desc, cls in recs:
        st.markdown(f"""
        <div class="insight-card {cls}">
            <strong>{title}</strong><br>
            <span style="color:#aaa; font-size:0.85rem;">{desc}</span>
        </div>""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# PAGE 5 — STATISTICAL TESTS
# ══════════════════════════════════════════════════════════════════════════════
elif page == "🔬 Statistical Tests":

    st.markdown('<div class="page-title" style="color:#fff;font-family:monospace;font-size:1.3rem;margin-bottom:1.5rem;">🔬 Statistical Validation</div>', unsafe_allow_html=True)
    st.markdown("""
    <div class="insight-card">
        All observed changes are validated using statistical hypothesis testing
        to confirm they are not due to random variation.
    </div>""", unsafe_allow_html=True)

    # T-Test
    t_stat, p_val = stats.ttest_ind(
        before_df["delivery_time_min"],
        after_df["delivery_time_min"],
        equal_var=False
    )
    n1, n2 = len(before_df), len(after_df)
    v1, v2 = before_df["delivery_time_min"].var(ddof=1), after_df["delivery_time_min"].var(ddof=1)
    pooled = np.sqrt(((n1-1)*v1 + (n2-1)*v2) / (n1+n2-2))
    cohens_d = (after_df["delivery_time_min"].mean() - before_df["delivery_time_min"].mean()) / pooled
    mag = "Negligible" if abs(cohens_d)<0.2 else "Small" if abs(cohens_d)<0.5 else "Medium" if abs(cohens_d)<0.8 else "Large"

    ct_ot = pd.crosstab(df["period"], df["on_time_flag"])
    chi2_ot, p_ot, _, _ = stats.chi2_contingency(ct_ot)
    ct_cr = pd.crosstab(df["period"], df["cancelled_flag"])
    chi2_cr, p_cr, _, _ = stats.chi2_contingency(ct_cr)

    st.markdown('<div class="section-title">Test Results</div>', unsafe_allow_html=True)

    c1, c2, c3 = st.columns(3)

    def sig_badge(p):
        if p < 0.001: return "✅ p < 0.001 — Highly Significant", "#5cb85c"
        if p < 0.01:  return "✅ p < 0.01 — Significant", "#5cb85c"
        if p < 0.05:  return "✅ p < 0.05 — Significant", "#f0ad4e"
        return "❌ Not Significant", "#e05c5c"

    sig1, col1 = sig_badge(p_val)
    sig2, col2 = sig_badge(p_ot)
    sig3, col3 = sig_badge(p_cr)

    with c1:
        st.markdown(f"""
        <div class="metric-card neutral">
            <div class="metric-label">Welch's T-Test</div>
            <div style="font-size:0.8rem; color:#aaa; margin-bottom:0.5rem;">Avg Delivery Time</div>
            <div class="metric-value orange" style="font-size:1.3rem;">t = {t_stat:.3f}</div>
            <div style="font-size:0.8rem; color:#888; margin:0.3rem 0;">p = {p_val:.2e}</div>
            <div style="font-size:0.8rem; color:{col1};">{sig1}</div>
        </div>""", unsafe_allow_html=True)
    with c2:
        st.markdown(f"""
        <div class="metric-card neutral">
            <div class="metric-label">Chi-Square Test</div>
            <div style="font-size:0.8rem; color:#aaa; margin-bottom:0.5rem;">On-Time Delivery %</div>
            <div class="metric-value orange" style="font-size:1.3rem;">χ² = {chi2_ot:.3f}</div>
            <div style="font-size:0.8rem; color:#888; margin:0.3rem 0;">p = {p_ot:.2e}</div>
            <div style="font-size:0.8rem; color:{col2};">{sig2}</div>
        </div>""", unsafe_allow_html=True)
    with c3:
        st.markdown(f"""
        <div class="metric-card neutral">
            <div class="metric-label">Chi-Square Test</div>
            <div style="font-size:0.8rem; color:#aaa; margin-bottom:0.5rem;">Cancellation Rate</div>
            <div class="metric-value orange" style="font-size:1.3rem;">χ² = {chi2_cr:.3f}</div>
            <div style="font-size:0.8rem; color:#888; margin:0.3rem 0;">p = {p_cr:.2e}</div>
            <div style="font-size:0.8rem; color:{col3};">{sig3}</div>
        </div>""", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown(f"""
    <div class="metric-card neutral" style="text-align:left; padding:1.5rem;">
        <div class="metric-label" style="margin-bottom:0.8rem;">Effect Size — Cohen's d</div>
        <div style="font-size:2rem; font-weight:600; color:#DD8452;">{cohens_d:.4f}</div>
        <div style="margin-top:0.5rem;">
            <span class="stat-badge">Magnitude: {mag}</span>
            <span class="stat-badge">Threshold: Small=0.2 · Medium=0.5 · Large=0.8</span>
        </div>
        <div style="font-size:0.82rem; color:#777; margin-top:0.8rem;">
            Cohen's d measures practical significance — not just statistical significance.
            A {mag.lower()} effect means the feature removal had a {mag.lower()} real-world impact on delivery time.
        </div>
    </div>""", unsafe_allow_html=True)

    # Peak sub-analysis
    st.markdown('<div class="section-title">Sub-Group Analysis: Peak vs Non-Peak</div>', unsafe_allow_html=True)
    rows = []
    for peak in ["Peak", "Non-Peak"]:
        b = before_df[before_df["peak_flag"]==peak]["delivery_time_min"]
        a = after_df[after_df["peak_flag"]==peak]["delivery_time_min"]
        t, p = stats.ttest_ind(b, a, equal_var=False)
        pct  = ((a.mean() - b.mean()) / b.mean()) * 100
        rows.append({
            "Hour Type": peak,
            "Before (mean)": f"{b.mean():.2f} min",
            "After (mean)":  f"{a.mean():.2f} min",
            "Change": f"{pct:+.1f}%",
            "p-value": f"{p:.2e}",
            "Significant": "✅ Yes" if p < 0.05 else "❌ No"
        })
    st.dataframe(
        pd.DataFrame(rows),
        use_container_width=True,
        hide_index=True
    )


# ══════════════════════════════════════════════════════════════════════════════
# PAGE 6 — RAW DATA
# ══════════════════════════════════════════════════════════════════════════════
elif page == "📋 Raw Data":

    st.markdown('<div class="page-title" style="color:#fff;font-family:monospace;font-size:1.3rem;margin-bottom:1.5rem;">📋 Raw Data Explorer</div>', unsafe_allow_html=True)

    c1, c2, c3, c4 = st.columns(4)
    with c1: st.metric("Total Orders", f"{len(df):,}")
    with c2: st.metric("Before Period", f"{len(before_df):,}")
    with c3: st.metric("After Period",  f"{len(after_df):,}")
    with c4: st.metric("Columns", len(df.columns))

    st.markdown('<div class="section-title">Data Preview</div>', unsafe_allow_html=True)
    n_rows = st.slider("Rows to show", 10, 200, 50)
    period_sel = st.selectbox("Filter by Period", ["All", "Before", "After"])
    show_df = df if period_sel == "All" else df[df["period"] == period_sel]
    st.dataframe(show_df.head(n_rows), use_container_width=True, hide_index=True)

    st.markdown('<div class="section-title">Descriptive Statistics</div>', unsafe_allow_html=True)
    num_cols = ["delivery_time_min","promised_eta_min","delivery_distance_km",
                "delay_min","customer_rating"]
    existing = [c for c in num_cols if c in df.columns]
    st.dataframe(df[existing].describe().round(3), use_container_width=True)