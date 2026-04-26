"""
app.py — DFDD Streamlit UI  (wizard / linear-flow rewrite)
All computation is delegated to core.py
Design system: DFDD hi-fi prototype (Hengphasatporn et al., JCIM 2026)
"""

import streamlit as st
import os, sys, json

# ── Always-available packages ─────────────────────────────────────────────────
try:
    import pandas as pd
    _pandas_ok = True
except ImportError:
    _pandas_ok = False; pd = None

try:
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots
    _plotly_ok = True
except ImportError:
    _plotly_ok = False; go = None; make_subplots = None

try:
    import numpy as np
    _numpy_ok = True
except ImportError:
    _numpy_ok = False; np = None

_openmm_ok = False
try:
    import openmm; _openmm_ok = True
except ImportError:
    pass

_rdkit_ok = False
try:
    from rdkit import Chem; _rdkit_ok = True
except ImportError:
    pass

import core

# ─── Page config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="DFDD — Molecular Dynamics Wizard",
    page_icon="🧬",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── Design system CSS injection ───────────────────────────────────────────────
def _inject_css():
    st.markdown("""<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans:ital,wght@0,300;0,400;0,500;0,600;0,700;1,400&family=Noto+Sans+Thai:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500;600&display=swap');

    /* ── Streamlit chrome reset ─────────────────────────────────────────────── */
    #MainMenu, footer, header { visibility: hidden; }
    .block-container { padding: 0 !important; max-width: 100% !important; }
    [data-testid="stAppViewContainer"] { padding: 0; }

    /* ── Theme tokens ───────────────────────────────────────────────────────── */
    :root {
        --accent:        #6366f1;
        --accent2:       #06b6d4;
        --accent-soft:   rgba(99,102,241,0.08);
        --card-bg:       rgba(255,255,255,0.72);
        --card-border:   rgba(255,255,255,0.88);
        --border:        rgba(99,102,241,0.14);
        --surface:       rgba(255,255,255,0.78);
        --input-bg:      rgba(255,255,255,0.95);
        --terminal-bg:   oklch(11% 0.04 270);
        --text-primary:  oklch(14% 0.025 270);
        --text-secondary:oklch(40% 0.015 270);
        --text-tertiary: oklch(60% 0.008 270);
        --sidebar-bg:    oklch(14% 0.065 274);
        --sidebar-border:oklch(22% 0.06 274);
    }

    /* ── Background mesh ────────────────────────────────────────────────────── */
    [data-testid="stAppViewContainer"] {
        background:
            radial-gradient(ellipse 65% 50% at 8% 5%, oklch(87% 0.05 285 / 0.55) 0%, transparent 58%),
            radial-gradient(ellipse 55% 65% at 92% 88%, oklch(91% 0.04 195 / 0.45) 0%, transparent 55%),
            radial-gradient(ellipse 35% 40% at 55% 40%, oklch(93% 0.03 260 / 0.30) 0%, transparent 50%),
            oklch(97% 0.012 270);
        font-family: 'Noto Sans', 'Noto Sans Thai', system-ui, sans-serif;
    }

    /* ── Sidebar ────────────────────────────────────────────────────────────── */
    [data-testid="stSidebar"] {
        background: oklch(14% 0.065 274) !important;
        border-right: 1px solid oklch(22% 0.06 274);
        min-width: 252px !important;
        max-width: 252px !important;
    }
    [data-testid="stSidebar"] * { color: oklch(62% 0.02 274); }
    [data-testid="stSidebar"] .sb-logo-title { color: #fff !important; }
    [data-testid="stSidebar"] h1,
    [data-testid="stSidebar"] h2,
    [data-testid="stSidebar"] h3 { color: #e0e7ff !important; }

    /* Sidebar nav buttons */
    [data-testid="stSidebar"] .stButton > button {
        width: 100%;
        text-align: left;
        padding: 7px 10px !important;
        border-radius: 8px !important;
        border: none !important;
        background: transparent !important;
        color: oklch(62% 0.02 274) !important;
        font-size: 12px !important;
        font-weight: 500;
        display: flex;
        align-items: center;
        gap: 9px;
        transition: background 0.15s;
        margin-bottom: 1px;
    }
    [data-testid="stSidebar"] .stButton > button:hover {
        background: oklch(21% 0.06 274) !important;
        color: #e0e7ff !important;
    }
    [data-testid="stSidebar"] .stButton > button[kind="primary"] {
        background: oklch(27% 0.10 275) !important;
        color: #e0e7ff !important;
    }
    [data-testid="stSidebar"] .stButton > button[kind="primary"]:hover {
        transform: none !important;
        box-shadow: none !important;
    }

    /* ── Main content area ──────────────────────────────────────────────────── */
    [data-testid="stMainBlockContainer"],
    section[data-testid="stMain"] > div {
        padding: 0 !important;
    }

    /* ── Phase stepper ──────────────────────────────────────────────────────── */
    .phase-strip {
        display: flex;
        align-items: center;
        padding: 10px 28px;
        border-bottom: 1px solid var(--border);
        background: var(--surface);
        backdrop-filter: blur(20px);
        -webkit-backdrop-filter: blur(20px);
        overflow-x: auto;
        scrollbar-width: none;
        gap: 0;
    }
    .phase-strip::-webkit-scrollbar { display: none; }
    .phase-chip {
        display: flex; align-items: center; gap: 7px;
        padding: 5px 12px; border-radius: 20px;
        cursor: pointer; font-size: 11px; font-weight: 600;
        color: var(--text-tertiary);
        transition: all 0.2s; white-space: nowrap; flex-shrink: 0;
    }
    .phase-chip.active { color: var(--accent); background: var(--accent-soft); }
    .phase-chip.done { color: #10b981; }
    .phase-circle {
        width: 19px; height: 19px; border-radius: 50%;
        background: var(--border); color: var(--text-tertiary);
        font-size: 9px; font-weight: 700;
        display: flex; align-items: center; justify-content: center;
        font-family: 'JetBrains Mono', monospace; transition: all 0.2s;
    }
    .phase-circle.active { background: var(--accent); color: #fff; }
    .phase-circle.done { background: #10b981; color: #fff; }
    .phase-connector {
        flex: 1; min-width: 18px; max-width: 50px; height: 1px;
        background: var(--border); margin: 0 3px;
    }
    .phase-connector.done { background: #10b981; }

    /* ── TopBar ─────────────────────────────────────────────────────────────── */
    .topbar {
        height: 50px; display: flex; align-items: center;
        justify-content: space-between;
        padding: 0 28px;
        border-bottom: 1px solid var(--border);
        background: var(--surface);
        backdrop-filter: blur(20px);
        -webkit-backdrop-filter: blur(20px);
    }
    .topbar-breadcrumb { font-size: 13px; color: var(--text-primary); display: flex; align-items: center; gap: 5px; }
    .bc-sep { color: var(--text-tertiary); font-size: 14px; }

    /* ── Step header ────────────────────────────────────────────────────────── */
    .step-header { margin-bottom: 26px; display: flex; align-items: flex-start; gap: 13px; padding: 30px 36px 0; }
    .step-badge {
        width: 34px; height: 34px; border-radius: 9px;
        background: var(--accent); color: #fff;
        font-size: 13px; font-weight: 700;
        display: flex; align-items: center; justify-content: center;
        flex-shrink: 0; font-family: 'JetBrains Mono', monospace;
        box-shadow: 0 4px 14px rgba(99,102,241,0.35);
    }
    .step-title { font-size: 21px; font-weight: 700; color: var(--text-primary); letter-spacing: -0.3px; line-height: 1.2; }
    .step-subtitle { font-size: 13px; color: var(--text-secondary); margin-top: 4px; line-height: 1.55; }

    /* ── Content area ───────────────────────────────────────────────────────── */
    .content-pad { padding: 0 36px 48px; }

    /* ── Glass card ─────────────────────────────────────────────────────────── */
    .glass-card {
        background: var(--card-bg);
        backdrop-filter: blur(20px);
        -webkit-backdrop-filter: blur(20px);
        border: 1px solid var(--card-border);
        border-radius: 12px;
        box-shadow: 0 2px 18px rgba(99,102,241,.06), 0 1px 3px rgba(0,0,0,.04);
        transition: border-color .2s, box-shadow .2s;
        margin-bottom: 16px;
        padding: 18px 22px;
    }

    /* ── Buttons ────────────────────────────────────────────────────────────── */
    /* Primary override */
    .stButton > button[kind="primary"],
    .stButton > button[data-testid="baseButton-primary"] {
        background: linear-gradient(135deg, #6366f1 0%, color-mix(in srgb, #6366f1 62%, #06b6d4) 100%) !important;
        color: #fff !important;
        border: none !important;
        border-radius: 9px !important;
        font-weight: 600 !important;
        font-size: 13px !important;
        padding: 8px 19px !important;
        transition: transform 0.15s, box-shadow 0.15s !important;
        letter-spacing: 0.01em !important;
    }
    .stButton > button[kind="primary"]:hover {
        transform: translateY(-1px) !important;
        box-shadow: 0 5px 18px rgba(99,102,241,0.38) !important;
        filter: brightness(1.06) !important;
    }
    /* Secondary */
    .stButton > button[kind="secondary"],
    .stButton > button[data-testid="baseButton-secondary"] {
        border: 1px solid var(--border) !important;
        background: var(--surface) !important;
        color: var(--text-primary) !important;
        border-radius: 9px !important;
        font-size: 13px !important;
        transition: border-color 0.15s, color 0.15s !important;
    }
    .stButton > button[kind="secondary"]:hover {
        border-color: var(--accent) !important;
        color: var(--accent) !important;
    }

    /* ── Progress bar ───────────────────────────────────────────────────────── */
    .stProgress > div > div > div {
        background: linear-gradient(90deg, var(--accent), var(--accent2)) !important;
        border-radius: 3px !important;
    }
    .stProgress > div > div {
        background: var(--border) !important;
        border-radius: 3px !important;
        height: 6px !important;
    }

    /* ── Inputs ─────────────────────────────────────────────────────────────── */
    .stTextInput > div > div > input,
    .stTextArea > div > div > textarea,
    .stNumberInput > div > div > input,
    .stSelectbox > div > div {
        background: var(--input-bg) !important;
        border: 1px solid var(--border) !important;
        border-radius: 8px !important;
        color: var(--text-primary) !important;
        font-size: 13px !important;
        font-family: 'Noto Sans', sans-serif !important;
    }
    .stTextInput > div > div > input:focus,
    .stTextArea > div > div > textarea:focus,
    .stNumberInput > div > div > input:focus {
        border-color: var(--accent) !important;
        box-shadow: 0 0 0 3px rgba(99,102,241,0.15) !important;
    }
    .stSlider > div > div > div > div {
        background: var(--accent) !important;
    }
    .stSlider > div > div > div {
        background: var(--border) !important;
    }

    /* ── Labels ─────────────────────────────────────────────────────────────── */
    .stTextInput label, .stTextArea label, .stNumberInput label,
    .stSelectbox label, .stSlider label, .stRadio label {
        font-size: 11px !important;
        font-weight: 700 !important;
        text-transform: uppercase !important;
        letter-spacing: 0.06em !important;
        color: var(--text-tertiary) !important;
    }

    /* ── Step host card ─────────────────────────────────────────────────────── */
    .host-card {
        display: flex; align-items: center; gap: 12px;
        padding: 13px 16px; border-radius: 10px;
        border: 1px solid var(--card-border);
        background: var(--card-bg);
        cursor: pointer; transition: all 0.18s;
        margin-bottom: 8px;
        backdrop-filter: blur(12px);
    }
    .host-card:hover { border-color: rgba(99,102,241,0.35); transform: translateX(2px); }
    .host-card.selected { border-width: 2px; transform: translateX(4px); }
    .host-color-dot { width: 10px; height: 10px; border-radius: 50%; flex-shrink: 0; }
    .host-name { font-size: 13px; font-weight: 600; color: var(--text-primary); }
    .host-tag {
        font-size: 10px; font-weight: 700; padding: 2px 8px;
        border-radius: 20px; margin-left: auto;
        font-family: 'JetBrains Mono', monospace;
        background: var(--accent-soft); color: var(--accent);
    }

    /* ── Tab bar ────────────────────────────────────────────────────────────── */
    .tab-bar {
        display: flex; gap: 4px; margin-bottom: 16px;
        background: var(--surface); border-radius: 10px; padding: 4px;
        border: 1px solid var(--border);
    }
    .tab-btn {
        flex: 1; padding: 6px 12px; border-radius: 7px; border: none;
        background: transparent; color: var(--text-secondary);
        font-size: 12px; font-weight: 500; cursor: pointer;
        transition: all 0.15s; font-family: inherit;
    }
    .tab-btn.active {
        background: var(--accent); color: #fff; font-weight: 600;
    }

    /* ── Metric card ────────────────────────────────────────────────────────── */
    .metric-card {
        background: var(--card-bg); border: 1px solid var(--card-border);
        border-radius: 12px; padding: 18px 22px; text-align: center;
        backdrop-filter: blur(20px);
    }
    .metric-value {
        font-size: 30px; font-weight: 700; color: var(--accent);
        font-family: 'JetBrains Mono', monospace; line-height: 1;
    }
    .metric-unit { font-size: 14px; font-weight: 400; margin-left: 3px; }
    .metric-label { font-size: 11px; color: var(--text-tertiary); margin-top: 8px; line-height: 1.4; }
    .metric-delta-pos { font-size: 11px; color: #10b981; margin-top: 4px; font-family: 'JetBrains Mono', monospace; }
    .metric-delta-neg { font-size: 11px; color: #ef4444; margin-top: 4px; font-family: 'JetBrains Mono', monospace; }

    /* ── Done bar ───────────────────────────────────────────────────────────── */
    .done-bar {
        display: flex; align-items: center; gap: 14px;
        padding: 14px 18px; border-radius: 10px;
        background: rgba(16,185,129,0.08); border: 1px solid rgba(16,185,129,0.22);
        margin-top: 16px;
    }
    .done-icon { font-size: 20px; line-height: 1; }
    .done-text { font-size: 14px; font-weight: 600; color: #10b981; }
    .done-file { font-size: 11px; color: var(--text-tertiary); font-family: 'JetBrains Mono', monospace; margin-top: 2px; }

    /* ── Terminal / log block ───────────────────────────────────────────────── */
    .stCodeBlock pre, pre {
        background: oklch(11% 0.04 270) !important;
        border-radius: 10px !important;
        font-family: 'JetBrains Mono', monospace !important;
        font-size: 12px !important;
        border: 1px solid oklch(20% 0.04 270) !important;
    }

    /* ── Param grid label ───────────────────────────────────────────────────── */
    .param-label {
        font-size: 11px; font-weight: 700; text-transform: uppercase;
        letter-spacing: 0.06em; color: var(--text-tertiary);
        margin-bottom: 7px; display: block;
    }
    .param-hint { font-weight: 400; text-transform: none; letter-spacing: 0; margin-left: 5px; }

    /* ── File row (download) ────────────────────────────────────────────────── */
    .file-row {
        display: flex; align-items: center; gap: 12px;
        padding: 9px 0; border-bottom: 1px solid var(--border);
    }
    .file-name { font-family: 'JetBrains Mono', monospace; font-size: 12px; color: var(--accent); flex: 1; }
    .file-desc { font-size: 12px; color: var(--text-secondary); flex: 2; }
    .file-size { font-size: 11px; color: var(--text-tertiary); font-family: 'JetBrains Mono', monospace; }

    /* ── Section group label ────────────────────────────────────────────────── */
    .group-label {
        font-size: 10px; font-weight: 700; text-transform: uppercase;
        letter-spacing: 0.1em; color: var(--text-tertiary); margin-bottom: 8px; margin-top: 20px;
    }

    /* ── Wait/install card ──────────────────────────────────────────────────── */
    .wait-card {
        text-align: center; padding: 52px 36px;
        background: var(--card-bg); border: 1px solid var(--card-border);
        border-radius: 12px; backdrop-filter: blur(20px); margin: 0 auto; max-width: 480px;
    }
    .wait-icon { font-size: 52px; margin-bottom: 18px; display: block; }
    .wait-title { font-size: 20px; font-weight: 700; color: var(--text-primary); margin-bottom: 8px; }
    .wait-sub { font-size: 13px; color: var(--text-secondary); line-height: 1.55; }

    /* ── Summary card ───────────────────────────────────────────────────────── */
    .summary-card {
        padding: 14px 18px; border-radius: 10px;
        background: var(--accent-soft); border: 1px solid var(--border);
        font-size: 13px; color: var(--text-primary); margin-bottom: 16px;
        font-family: 'JetBrains Mono', monospace;
    }

    /* ── Chip / pill ────────────────────────────────────────────────────────── */
    .chip {
        display: inline-flex; align-items: center; padding: 4px 12px;
        border-radius: 20px; font-size: 12px; font-weight: 500;
        background: var(--accent-soft); border: 1px solid var(--border);
        color: var(--accent); cursor: pointer; transition: all 0.15s;
        margin: 3px; user-select: none;
    }
    .chip:hover { background: var(--accent); color: #fff; border-color: var(--accent); }

    /* ── Expander override ──────────────────────────────────────────────────── */
    [data-testid="stExpander"] {
        border: 1px solid var(--border) !important;
        border-radius: 10px !important;
        background: var(--card-bg) !important;
        backdrop-filter: blur(12px) !important;
        margin-bottom: 12px !important;
    }
    [data-testid="stExpander"] summary {
        font-size: 13px !important;
        font-weight: 600 !important;
        color: var(--text-primary) !important;
    }

    /* ── Divider ────────────────────────────────────────────────────────────── */
    hr { border-color: var(--border) !important; margin: 20px 0 !important; }

    /* ── Animation ──────────────────────────────────────────────────────────── */
    @keyframes fadeIn { from { opacity: 0; transform: translateY(8px); } to { opacity: 1; transform: translateY(0); } }
    .step-body { animation: fadeIn 0.22s ease; }
    @keyframes spin { to { transform: rotate(360deg); } }
    .spin { display: inline-block; animation: spin 1.2s linear infinite; }

    /* General font override */
    body, .stApp, * { font-family: 'Noto Sans', 'Noto Sans Thai', system-ui, sans-serif; }
    code, pre, .mono { font-family: 'JetBrains Mono', monospace; }
    </style>""", unsafe_allow_html=True)
_inject_css()

# ─── Session state defaults ────────────────────────────────────────────────────
DEFAULTS = {
    "step":              0,        # current wizard step (0 = installing)
    "install_done":      False,
    "workdir":           os.path.expanduser("~/dfdd_workspace"),
    # host
    "host_option":       None,
    "host_path":         None,
    "host_prep":         None,
    "host_frcmod":       None,
    "host_forcefield":   None,
    "host_type":         None,
    # guest
    "guest_input_type":  "SMILES",
    "guest_smiles":      "",
    "guest_path":        None,
    "guest_prep":        None,
    "guest_frcmod":      None,
    "detected_charge":   0,
    "guest_pH":          7.4,
    "guest_pH_range":    0.5,
    "guest_apply_ph":    True,
    "guest_smiles_protonated": "",
    # PubChem name search
    "guest_pubchem_query":        "",
    "guest_pubchem_results":      [],
    "guest_pubchem_selected_cid": None,
    "guest_pubchem_error":        None,
    # sim params (set in step 6 UI)
    "pacsmd_cycles":     40,
    "pacsmd_candi":      3,
    "pacsmd_sim_time":   10,
    "pacsmd_timestep":   1,
    "pacsmd_temp":       300.0,
    "pacsmd_pressure":   1.0,
    # flags
    "build_done":        False,
    "topo_done":         False,
    "build_dist_confirmed": False,
    "min_done":          False,
    "pacsmd_done":       False,
    "pacsmd_extended":   False,
    "cmd_done":          False,
    "mmpbsa_done":       False,
    "dbfe_asked":        False,
    "dbfe_want":         False,
    "dbfe_done":         False,
    # logs
    "log_install": "", "log_host": "", "log_guest": "",
    "log_complex": "", "log_tleap": "", "log_min":   "",
    "log_pacsmd":  "", "log_cmd":   "", "log_cv":    "",
    "log_mmpbsa":  "",
    # results
    "gb_result":  None,
    "pb_result":  None,
}
for k, v in DEFAULTS.items():
    if k not in st.session_state:
        st.session_state[k] = v

os.makedirs(st.session_state["workdir"], exist_ok=True)

# ─── Helpers ──────────────────────────────────────────────────────────────────
def WD():
    return st.session_state["workdir"]

def wpath(*parts):
    return os.path.join(WD(), *parts)

def go_step(n):
    st.session_state["step"] = n
    st.rerun()

def log_expander(key, label="📋 Log"):
    txt = st.session_state.get(key, "")
    if txt.strip():
        with st.expander(label, expanded=False):
            st.code(txt[-4000:])

def next_button(next_step: int, label: str = "Next →", key_suffix: str = ""):
    """Render a centred green Next button that advances the wizard."""
    st.markdown("<div style='height:1.25rem'></div>", unsafe_allow_html=True)
    col = st.columns([1, 2, 1])[1]
    with col:
        if st.button(label, key=f"next_to_{next_step}{key_suffix}", type="primary",
                     use_container_width=True):
            go_step(next_step)


def section_header(title: str, subtitle: str = "", step_num: int = None):
    """Render a step header with badge + title + subtitle (DFDD design system)."""
    badge_html = ""
    if step_num is not None:
        badge_html = f'<div class="step-badge">{step_num}</div>'
    st.markdown(
        f'<div class="step-header">'
        f'{badge_html}'
        f'<div><div class="step-title">{title}</div>'
        + (f'<div class="step-subtitle">{subtitle}</div>' if subtitle else "")
        + "</div></div>",
        unsafe_allow_html=True,
    )


def waiting_card(title: str, subtitle: str = "", icon: str = "⚙️"):
    """Render a centred install/wait card (DFDD design system)."""
    st.markdown(
        f'''<div class="wait-card">
            <span class="wait-icon">{icon}</span>
            <div class="wait-title">{title}</div>
            <div class="wait-sub">{subtitle}</div>
        </div>''',
        unsafe_allow_html=True,
    )


def py3dmol_html_fmt(mol_str, fmt="sdf", width=680, height=420, side_view=False):
    """Render any molecule format with 3Dmol.js + click-to-inspect atoms."""
    rotate = "v.rotate(90, {x:1, y:0, z:0});" if side_view else ""
    return f"""
    <script src="https://3Dmol.org/build/3Dmol-min.js"></script>
    <div style="position:relative;width:{width}px;height:{height}px;">
      <div id="vfmt" style="
          width:100%;height:100%;border-radius:12px;overflow:hidden;
          border:1px solid #E5E7EB;background:#FAFBFC;"></div>
      <div id="vfmt-info" style="
          display:none;position:absolute;top:10px;left:12px;
          background:rgba(91,63,209,0.92);color:#fff;
          font-size:12px;font-family:monospace;padding:6px 12px;
          border-radius:8px;pointer-events:none;line-height:1.6;
          box-shadow:0 2px 8px rgba(0,0,0,0.2);max-width:220px;"></div>
      <div style="position:absolute;bottom:10px;left:12px;font-size:11px;color:#888;
           background:rgba(255,255,255,0.82);padding:2px 8px;border-radius:5px;
           pointer-events:none;">
        Left-drag: rotate &nbsp;·&nbsp; Scroll: zoom &nbsp;·&nbsp; Click atom: info
      </div>
    </div>
    <script>
      var v = $3Dmol.createViewer(document.getElementById('vfmt'),
                                  {{backgroundColor:'#FAFBFC'}});
      v.addModel(`{mol_str}`,'{fmt}');
      v.setStyle({{}}, {{stick:{{colorscheme:'Jmol', radius:0.15}}}});
      v.addStyle({{elem:'H'}}, {{stick:{{colorscheme:'Jmol', radius:0.06}}}});
      v.addSurface($3Dmol.SurfaceType.VDW,
                   {{opacity:0.07, colorscheme:'Jmol'}},
                   {{not:{{elem:'H'}}}});
      var infoBox = document.getElementById('vfmt-info');
      v.setClickable({{}}, true, function(atom) {{
        var lines = [
          'Element: ' + (atom.elem || '?'),
          'Atom:    ' + (atom.atom || '?'),
          'Residue: ' + (atom.resn || '?') + ' ' + (atom.resi || ''),
          'Coords:  (' +
            (atom.x ? atom.x.toFixed(2) : '?') + ', ' +
            (atom.y ? atom.y.toFixed(2) : '?') + ', ' +
            (atom.z ? atom.z.toFixed(2) : '?') + ')'
        ];
        infoBox.innerHTML = lines.join('<br>');
        infoBox.style.display = 'block';
        setTimeout(function(){{ infoBox.style.display='none'; }}, 4000);
        v.render();
      }});
      v.zoomTo();
      {rotate}
      v.render();
    </script>"""


def py3dmol_html(pdb_str, width=680, height=420, side_view=False):
    """Render a PDB with 3Dmol.js. Jmol colors; guest GST cyan. Click atom for info."""
    rotate = "v.rotate(90, {x:1, y:0, z:0});" if side_view else ""
    return f"""
    <script src="https://3Dmol.org/build/3Dmol-min.js"></script>
    <div style="position:relative;width:{width}px;height:{height}px;">
      <div id="v3d" style="
          width:100%;height:100%;border-radius:12px;overflow:hidden;
          border:1px solid #E5E7EB;background:#FAFBFC;
          box-shadow:0 1px 3px rgba(0,0,0,0.04);"></div>
      <div id="v3d-info" style="
          display:none;position:absolute;top:10px;left:12px;
          background:rgba(91,63,209,0.92);color:#fff;
          font-size:12px;font-family:monospace;padding:6px 12px;
          border-radius:8px;pointer-events:none;line-height:1.6;
          box-shadow:0 2px 8px rgba(0,0,0,0.2);max-width:220px;"></div>
      <div style="position:absolute;bottom:10px;left:12px;font-size:11px;color:#888;
           background:rgba(255,255,255,0.82);padding:2px 8px;border-radius:5px;
           pointer-events:none;">
        Left-drag: rotate &nbsp;·&nbsp; Scroll: zoom &nbsp;·&nbsp; Click atom: info
      </div>
    </div>
    <script>
      var v = $3Dmol.createViewer(document.getElementById('v3d'),
                                  {{backgroundColor:'#FAFBFC'}});
      v.addModel(`{pdb_str}`,'pdb');
      v.setStyle({{}}, {{stick:{{colorscheme:'Jmol', radius:0.15}}}});
      v.addStyle({{resn:'GST'}}, {{stick:{{colorscheme:'cyanCarbon', radius:0.22}}}});
      v.addStyle({{resn:'GST'}}, {{sphere:{{colorscheme:'cyanCarbon', radius:0.14}}}});
      var infoBox = document.getElementById('v3d-info');
      v.setClickable({{}}, true, function(atom) {{
        var tag = atom.resn === 'GST' ? ' [guest]' : ' [host]';
        var lines = [
          'Element: ' + (atom.elem  || '?') + tag,
          'Atom:    ' + (atom.atom  || '?'),
          'Residue: ' + (atom.resn  || '?') + ' ' + (atom.resi || ''),
          'Coords:  (' +
            (atom.x ? atom.x.toFixed(2) : '?') + ', ' +
            (atom.y ? atom.y.toFixed(2) : '?') + ', ' +
            (atom.z ? atom.z.toFixed(2) : '?') + ')'
        ];
        infoBox.innerHTML = lines.join('<br>');
        infoBox.style.display = 'block';
        setTimeout(function(){{ infoBox.style.display='none'; }}, 4000);
        v.render();
      }});
      v.zoomTo();
      {rotate}
      v.render();
    </script>"""


# ─── PubChem name search ──────────────────────────────────────────────────────
@st.cache_data(show_spinner=False, ttl=3600)
def pubchem_search_by_name(name: str, max_results: int = 5):
    """Search PubChem for a compound by name and return a list of matches.

    Uses PubChem PUG REST (https://pubchem.ncbi.nlm.nih.gov/rest/pug).
    No API key required. Results are cached for 1 hour per query.

    Returns a list of dicts like:
        [{"cid": 2244, "name": "Aspirin",
          "smiles": "CC(=O)OC1=CC=CC=C1C(=O)O",
          "iupac": "...", "formula": "...", "mw": 180.16,
          "image_url": "...", "pubchem_url": "..."}]
    or [] if nothing found. Raises no exceptions — errors become st.warning.
    """
    import urllib.request, urllib.parse, urllib.error, json as _json

    name = (name or "").strip()
    if not name:
        return []

    base = "https://pubchem.ncbi.nlm.nih.gov/rest/pug"
    headers = {"User-Agent": "DFDD/1.0 (molecular-dynamics-wizard)"}

    def _get(url, timeout=15):
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.read().decode("utf-8", errors="replace")

    # 1) Resolve name → list of CIDs
    try:
        q = urllib.parse.quote(name, safe="")
        cids_txt = _get(f"{base}/compound/name/{q}/cids/TXT")
        cids = [c.strip() for c in cids_txt.splitlines() if c.strip().isdigit()]
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return []
        raise RuntimeError(f"PubChem error ({e.code}): {e.reason}")
    except Exception as e:
        raise RuntimeError(f"Network error: {e}")

    if not cids:
        return []

    cids = cids[:max_results]
    cid_list = ",".join(cids)

    # 2) Bulk fetch properties. Try new property names first, fall back to old.
    #    (PubChem renamed CanonicalSMILES → SMILES, IsomericSMILES → ConnectivitySMILES
    #     in 2024–25.)
    props_new = "SMILES,IUPACName,MolecularFormula,MolecularWeight,Title"
    props_old = "CanonicalSMILES,IsomericSMILES,IUPACName,MolecularFormula,MolecularWeight,Title"

    rows = None
    for props in (props_new, props_old):
        try:
            js = _get(f"{base}/compound/cid/{cid_list}/property/{props}/JSON")
            data = _json.loads(js)
            rows = data.get("PropertyTable", {}).get("Properties", [])
            if rows:
                break
        except urllib.error.HTTPError:
            continue
        except Exception:
            continue

    if not rows:
        return []

    out = []
    for r in rows:
        cid = r.get("CID")
        if cid is None:
            continue
        # SMILES: prefer isomeric (stereo) when available
        smi = (r.get("IsomericSMILES")
               or r.get("SMILES")
               or r.get("CanonicalSMILES")
               or r.get("ConnectivitySMILES")
               or "")
        out.append({
            "cid":         cid,
            "name":        r.get("Title") or name,
            "smiles":      smi,
            "iupac":       r.get("IUPACName", ""),
            "formula":     r.get("MolecularFormula", ""),
            "mw":          r.get("MolecularWeight", ""),
            "image_url":   f"{base}/compound/cid/{cid}/PNG?image_size=200x200",
            "pubchem_url": f"https://pubchem.ncbi.nlm.nih.gov/compound/{cid}",
        })
    return out


# ─── Step names for progress bar ──────────────────────────────────────────────
STEP_LABELS = [
    "Install",
    "Host",
    "Guest",
    "Build & Solvate",
    "Minimize",
    "LB-PaCS-MD",
    "Analysis",
    "cMD",
    "MM-PBSA",
    "DBFE",
    "Download",
]

def render_stepper(current):
    """Render the DFDD phase stepper bar with 5 phase groups."""
    PHASES = [
        {"label": "Setup",              "steps": [0],       "num": "1"},
        {"label": "System Preparation", "steps": [1,2,3,4], "num": "2"},
        {"label": "LB-PaCS-MD",         "steps": [5,6],     "num": "3"},
        {"label": "cMD",                "steps": [7,8,9],   "num": "4"},
        {"label": "Download",           "steps": [10],      "num": "5"},
    ]
    html = '<div class="phase-strip">'
    for i, phase in enumerate(PHASES):
        is_active = current in phase["steps"]
        is_done   = current > max(phase["steps"])
        chip_cls  = "phase-chip active" if is_active else ("phase-chip done" if is_done else "phase-chip")
        circ_cls  = "phase-circle active" if is_active else ("phase-circle done" if is_done else "phase-circle")
        icon      = "✓" if is_done else phase["num"]
        html += (
            f'<div class="{chip_cls}">'
            f'<div class="{circ_cls}">{icon}</div>'
            f'{phase["label"]}'
            f'</div>'
        )
        if i < len(PHASES) - 1:
            conn_cls = "phase-connector done" if is_done else "phase-connector"
            html += f'<div class="{conn_cls}"></div>'
    html += "</div>"
    st.markdown(html, unsafe_allow_html=True)


def render_topbar(step_label: str, step_idx: int):
    """Render the DFDD topbar with breadcrumb and workspace pill."""
    ws = st.session_state.get("workdir", "~/dfdd_workspace")
    ws_short = ws.replace(os.path.expanduser("~"), "~")
    st.markdown(
        f'''<div class="topbar">
          <div class="topbar-breadcrumb">
            <span style="color:var(--text-tertiary);font-size:13px;">DFDD</span>
            <span class="bc-sep">›</span>
            <span>{step_label}</span>
          </div>
          <div style="display:flex;gap:8px;align-items:center;">
            <div class="ws-pill">
              <span>📁</span>
              <span style="font-family:'JetBrains Mono',monospace;">{ws_short}</span>
            </div>
          </div>
        </div>''',
        unsafe_allow_html=True,
    )


# ══════════════════════════════════════════════════════════════════════════════
# STEP 0 — Install remaining packages (mamba already set up by Colab cell)
# ══════════════════════════════════════════════════════════════════════════════

def _conda_prefix():
    """Return the conda base prefix, checking common Miniforge/condacolab locations."""
    for path in [
        "/usr/local",           # condacolab default
        os.path.expanduser("~/miniforge3"),
        os.path.expanduser("~/conda"),
        "/opt/conda",
        "/usr/local/miniforge3",
    ]:
        if os.path.exists(os.path.join(path, "bin", "mamba")):
            return path
        if os.path.exists(os.path.join(path, "bin", "conda")):
            return path
    return None


def _mamba_available():
    prefix = _conda_prefix()
    if prefix and os.path.exists(os.path.join(prefix, "bin", "mamba")):
        return True
    rc, _ = core.run_cmd(["bash", "-lc", "which mamba"], timeout=10)
    return rc == 0


def _conda_run(conda_cmd, **kwargs):
    """Run a mamba/conda command after sourcing conda init."""
    prefix = _conda_prefix() or "/usr/local"
    init   = f"source {prefix}/etc/profile.d/conda.sh 2>/dev/null || true"
    full   = f"{init} && {conda_cmd}"
    return core.run_cmd(["bash", "-lc", full], **kwargs)


def _tools_ready():
    """Return True if key scientific tools are already on PATH."""
    prefix = _conda_prefix() or "/usr/local"
    init   = f"source {prefix}/etc/profile.d/conda.sh 2>/dev/null || true"
    for tool in ["antechamber", "tleap", "cpptraj", "obabel"]:
        rc, _ = core.run_cmd(["bash", "-lc", f"{init} && which {tool}"], timeout=5)
        if rc != 0:
            return False
    return True


def _run_install_step(cmd, desc, pct, progress, log_area, log, conda_cmd=None):
    """Run one install command. Use conda_cmd (string) for mamba calls."""
    progress.progress(pct, text=f"📦 {desc}…")
    if conda_cmd:
        rc, out = _conda_run(conda_cmd, timeout=1800)
    else:
        rc, out = core.run_cmd(cmd, cwd=WD(), timeout=1800)
    log += f"\n{'='*40}\n{desc}\n{out}"
    log_area.code(log[-4000:])
    return log, rc == 0


def page_install():
    render_topbar("Install dependencies", 0)
    render_stepper(0)
    st.markdown('<div class="content-pad step-body">', unsafe_allow_html=True)
    section_header("Install dependencies", "Installing scientific packages. This runs automatically — please wait.", step_num=0)

    # ── Already fully done this session ──────────────────────────────────────
    if st.session_state["install_done"]:
        st.markdown("""
        <div class="done-bar" style="margin:24px 0;max-width:480px;">
          <span class="done-icon">✅</span>
          <div><div class="done-text">Environment ready</div>
          <div class="done-file">All packages installed successfully</div></div>
        </div>""", unsafe_allow_html=True)
        next_button(1, "Next → Select host →")
        return

    # ── Package list preview ─────────────────────────────────────────────────
    PACKAGES = [
        ("AmberTools", "antechamber · tleap · cpptraj"),
        ("OpenBabel",  "obabel file conversion"),
        ("RDKit",      "cheminformatics toolkit"),
        ("xtb",        "semiempirical QM"),
        ("PaCS-Q",     "LB-PaCS-MD engine"),
        ("py3Dmol",    "in-browser 3D viewer"),
        ("dimorphite_dl", "protonation states"),
        ("netCDF4",    "trajectory storage"),
    ]
    pkg_items = "".join(
        f'<div style="display:flex;gap:8px;padding:5px 0;border-bottom:1px solid var(--border);">'
        f'<span style="font-family:JetBrains Mono,monospace;font-size:12px;color:var(--accent);flex:0 0 140px;">{name}</span>'
        f'<span style="font-size:12px;color:var(--text-tertiary);">{note}</span></div>'
        for name, note in PACKAGES
    )
    st.markdown(
        f'<div class="glass-card" style="max-width:480px;margin:0 auto 24px;padding:14px 18px;">' +
        pkg_items + '</div>',
        unsafe_allow_html=True,
    )

    # ── Check mamba ───────────────────────────────────────────────────────────
    if not _mamba_available():
        st.error(
            "❌ **mamba not found.**  \n\n"
            "Run **Cell 1** in your Colab notebook first:\n"
            "```python\n"
            "!pip install -q condacolab\n"
            "import condacolab\n"
            "condacolab.install()   # kernel restarts — then run Cell 2\n"
            "```"
        )
        st.stop()

    # ── If AmberTools / obabel are already installed, skip straight through ───
    progress_bar = st.progress(0, text="Checking installed tools…")
    log_area     = st.empty()
    log          = ""

    if _tools_ready():
        # Scientific tools present — just run the fast pip step to make sure
        # Python packages are also installed, then mark done.
        progress_bar.progress(80, text="Tools already present — running pip top-up…")
        log, ok = _run_install_step(
            [sys.executable, "-m", "pip", "install", "-q",
             "py3Dmol", "netCDF4", "cftime", "deeptime",
             "dimorphite_dl", "pkapredict", "PaCS-Q", "parmed"],
            "pip packages (top-up)", 85, progress_bar, log_area, log
        )
        progress_bar.progress(100, text="Ready!")
        st.session_state["log_install"]  = log
        st.session_state["install_done"] = True
        st.success("✅ Environment ready!")
        next_button(1, "Next → Select host")
        return

    # ── Full install ──────────────────────────────────────────────────────────
    phases = st.empty()

    # Phase 1 — AmberTools + RDKit + xtb
    phases.info("**Phase 1/3** — Installing AmberTools, RDKit, xtb…  ☕ ~5–8 min")
    log, ok = _run_install_step(
        None, "AmberTools + RDKit + xtb", 10, progress_bar, log_area, log,
        conda_cmd="mamba install -n base -c conda-forge -y ambertools openbabel rdkit xtb 2>&1 | tail -20"
    )
    if not ok:
        st.error("❌ mamba install (AmberTools/RDKit/xtb) failed — see log.")
        st.session_state["log_install"] = log
        log_expander("log_install"); return

    # Phase 2 — OpenFF + NGLView (non-fatal)
    phases.info("**Phase 2/3** — Installing OpenFF toolkit + NGLView…")
    log, ok = _run_install_step(
        None, "OpenFF + NGLView", 55, progress_bar, log_area, log,
        conda_cmd="mamba install -n base -c conda-forge -y openff-toolkit nglview 2>&1 | tail -10"
    )
    if not ok:
        st.warning("⚠️ OpenFF/NGLView had errors (non-fatal). Continuing…")

    # Phase 3 — pip packages
    phases.info("**Phase 3/3** — Installing Python packages via pip…")
    log, ok = _run_install_step(
        [sys.executable, "-m", "pip", "install", "-q",
         "py3Dmol", "netCDF4", "cftime", "deeptime",
         "dimorphite_dl", "pkapredict", "PaCS-Q", "parmed"],
        "pip packages", 80, progress_bar, log_area, log
    )
    if not ok:
        st.error("❌ pip install of Python packages failed — see log.")
        st.session_state["log_install"] = log
        log_expander("log_install"); return

    # ── Done ─────────────────────────────────────────────────────────────────
    progress_bar.progress(100, text="Installation complete!")
    phases.empty()
    st.session_state["log_install"]  = log
    st.session_state["install_done"] = True
    st.success("✅ All dependencies installed!")
    next_button(1, "Next → Select host")


# ══════════════════════════════════════════════════════════════════════════════
# STEP 1 — Select host
# ══════════════════════════════════════════════════════════════════════════════

HOST_PREVIEW_URLS = {
    "β-CD (DFT)":     "https://raw.githubusercontent.com/nyelidl/host-guest/main/BCD-n/BCD.pdb",
    "β-CD (GLYCAM)":  "https://raw.githubusercontent.com/nyelidl/DFDD/main/GLYCAM/gBCD.pdb",
    "DM-β-CD":        "https://raw.githubusercontent.com/nyelidl/DFDD/main/GLYCAM/gDMBCD.pdb",
    "M-β-CD":         "https://raw.githubusercontent.com/nyelidl/DFDD/main/GLYCAM/gMBCD.pdb",
    "HP-β-CD":        "https://raw.githubusercontent.com/nyelidl/DFDD/main/GLYCAM/g6tetraHPBCD.pdb",
}

HOST_OPTIONS_MAP = {
    "β-CD (DFT)":    "DFT",
    "β-CD (GLYCAM)": "Native β-CD (GLYCAM)",
    "DM-β-CD":       "Dimethylated β-CD (GLYCAM)",
    "M-β-CD":        "Methylated β-CD (GLYCAM)",
    "HP-β-CD":       "6-tetra HP β-CD (GLYCAM)",
}

HOST_FULL_NAMES = {
    "β-CD (DFT)":    "Default β-CD — DFT-derived charges (recommended)",
    "β-CD (GLYCAM)": "Native β-CD — GLYCAM-06, 7 glucose units",
    "DM-β-CD":       "Dimethylated β-CD — GLYCAM-06, O2/O6 methylation",
    "M-β-CD":        "Methylated β-CD — GLYCAM-06, O6 methylation",
    "HP-β-CD":       "6-tetra HP-β-CD — GLYCAM-06, 4 hydroxypropyl groups",
}


def _fetch_preview_pdb(url):
    try:
        import urllib.request
        with urllib.request.urlopen(url, timeout=8) as r:
            return r.read().decode("utf-8", errors="ignore")
    except Exception:
        return None


def page_host():
    render_topbar("Select Host", 1)
    render_stepper(1)
    st.markdown('<div class="content-pad step-body">', unsafe_allow_html=True)
    section_header("Select host molecule", "Choose the cyclodextrin host. The 3D structure loads automatically.", step_num=1)

    abbrevs = list(HOST_OPTIONS_MAP.keys())

    # Default selection
    prev = st.session_state.get("host_option_abbrev", abbrevs[0])
    if prev not in abbrevs:
        prev = abbrevs[0]

    # Host card colors matching prototype
    HOST_COLORS = {
        "β-CD (DFT)":    "#6366f1",
        "β-CD (GLYCAM)": "#8b5cf6",
        "DM-β-CD":       "#a855f7",
        "M-β-CD":        "#d946ef",
        "HP-β-CD":       "#ec4899",
    }
    HOST_TAGS = {
        "β-CD (DFT)":    "DFT",
        "β-CD (GLYCAM)": "GLYCAM",
        "DM-β-CD":       "GLYCAM",
        "M-β-CD":        "GLYCAM",
        "HP-β-CD":       "GLYCAM",
    }

    col_left, col_right = st.columns([1, 1], gap="large")

    with col_left:
        st.markdown('<div class="group-label">Host molecule</div>', unsafe_allow_html=True)
        for abbrev in abbrevs:
            is_sel   = abbrev == prev
            color    = HOST_COLORS.get(abbrev, "#6366f1")
            tag      = HOST_TAGS.get(abbrev, "")
            sel_style = (
                f"border:2px solid {color};background:rgba({','.join(str(int(color[i:i+2],16)) for i in (1,3,5))},0.06);"
                if is_sel else ""
            )
            check = f'<span style="color:{color};font-weight:700;margin-left:auto;">✓</span>' if is_sel else ""
            st.markdown(
                f'<div class="host-card {"selected" if is_sel else ""}" style="{sel_style}">'
                f'<div class="host-color-dot" style="background:{color};"></div>'
                f'<div class="host-name">{abbrev}</div>'
                f'<div class="host-tag" style="color:{color};background:rgba({",".join(str(int(color[i:i+2],16)) for i in (1,3,5))},0.1);">{tag}</div>'
                f'{check}'
                f'</div>',
                unsafe_allow_html=True,
            )
            if st.button(f"Select {abbrev}", key=f"host_btn_{abbrev}",
                         type="primary" if is_sel else "secondary",
                         use_container_width=True):
                if abbrev != st.session_state.get("host_option_abbrev"):
                    st.session_state["host_option_abbrev"] = abbrev
                    st.session_state["host_option"] = HOST_FULL_NAMES[abbrev]
                    st.session_state["host_path"] = None
                    st.session_state["host_type"] = None
                    st.rerun()

        selected = st.session_state.get("host_option_abbrev", abbrevs[0])
        st.session_state["host_option_abbrev"] = selected
        st.session_state["host_option"] = HOST_FULL_NAMES[selected]
        st.markdown(
            f'<div class="glass-card" style="margin-top:8px;padding:12px 16px;">'
            f'<div style="font-size:11px;color:var(--text-tertiary);margin-bottom:4px;font-weight:700;text-transform:uppercase;letter-spacing:.06em;">Description</div>'
            f'<div style="font-size:13px;color:var(--text-primary);">{HOST_FULL_NAMES[selected]}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )

    with col_right:
        # ── 3D preview ────────────────────────────────────────────────────────
        prepared_path = st.session_state.get("host_path")
        if prepared_path and os.path.exists(prepared_path):
            preview_pdb   = core.read_file(prepared_path)
            preview_label = "Prepared structure"
        else:
            cache_key   = f"host_preview_pdb_{selected}"
            preview_pdb = st.session_state.get(cache_key)
            if not preview_pdb:
                url = HOST_PREVIEW_URLS.get(selected)
                if url:
                    with st.spinner("Loading 3D preview…"):
                        preview_pdb = _fetch_preview_pdb(url)
                    if preview_pdb:
                        st.session_state[cache_key] = preview_pdb
            preview_label = f"Preview — {selected}"

        st.markdown(
            f'<div style="font-size:11px;font-weight:700;text-transform:uppercase;'
            f'letter-spacing:.06em;color:var(--text-tertiary);margin-bottom:8px;">'
            f'{preview_label}</div>',
            unsafe_allow_html=True,
        )
        if preview_pdb:
            st.components.v1.html(py3dmol_html(preview_pdb, 480, 380, side_view=True), height=390)
        else:
            st.markdown(
                '<div class="glass-card" style="height:340px;display:flex;align-items:center;'
                'justify-content:center;color:var(--text-tertiary);font-size:13px;">'
                '3D preview unavailable</div>',
                unsafe_allow_html=True,
            )

    st.divider()

    # ── Prepare / Next ────────────────────────────────────────────────────────
    host_ready = (
        st.session_state.get("host_path")
        and os.path.exists(st.session_state.get("host_path") or "")
        and st.session_state.get("host_type") is not None
    )

    if host_ready:
        st.success(f"✅ Host ready: `{st.session_state['host_path']}`")
        next_button(2, "Next → Prepare guest", key_suffix="_done")
    else:
        if st.button("▶ Prepare host", type="primary"):
            host_key = HOST_OPTIONS_MAP[selected]
            with st.spinner(f"Preparing {selected}…"):
                if host_key == "DFT":
                    result, log, err = core.prepare_host_dft(WD())
                else:
                    result, log, err = core.prepare_host_glycam(host_key, WD())
            st.session_state["log_host"] = log
            if err:
                st.error(f"❌ {err}")
                log_expander("log_host")
            else:
                for k, v in result.items():
                    st.session_state[k] = v
                st.success(f"✅ Host ready: `{result['host_path']}`")
                next_button(2, "Next → Prepare guest", key_suffix="_prepared")

    log_expander("log_host")


# ══════════════════════════════════════════════════════════════════════════════
# STEP 2 — Guest preparation
# ══════════════════════════════════════════════════════════════════════════════

def _try_import_ketcher():
    try:
        from streamlit_ketcher import st_ketcher
        return st_ketcher
    except ImportError:
        return None


def _charge_from_file(path):
    """Try to read formal charge from a PDB or mol2 file via RDKit; return 0 on failure."""
    try:
        from rdkit import Chem
        ext = os.path.splitext(path)[1].lower()
        if ext == ".mol2":
            mol = Chem.MolFromMol2File(path, removeHs=False)
        else:
            mol = Chem.MolFromPDBFile(path, removeHs=False)
        if mol is not None:
            return Chem.GetFormalCharge(mol)
    except Exception:
        pass
    return 0


def page_guest():
    render_topbar("Prepare Guest", 2)
    render_stepper(2)
    st.markdown('<div class="content-pad step-body">', unsafe_allow_html=True)
    section_header("Prepare guest molecule", "Provide your guest ligand by SMILES, file upload, or draw with Ketcher.", step_num=2)

    # Tab-bar styled radio
    _MODES = ["SMILES", "Search by name (PubChem)", "Draw (Ketcher)", "File upload (.pdb / .mol2)"]
    _MODE_ICONS = {"SMILES": "📝 SMILES", "Search by name (PubChem)": "🔬 PubChem",
                   "Draw (Ketcher)": "✏️ Ketcher", "File upload (.pdb / .mol2)": "📁 Upload"}
    input_type = st.radio(
        "Input method",
        _MODES,
        format_func=lambda x: _MODE_ICONS.get(x, x),
        horizontal=True,
        index=_MODES.index(
            st.session_state.get("guest_input_type", "SMILES")
            if st.session_state.get("guest_input_type", "SMILES") in _MODES else "SMILES"
        ),
        key="guest_input_radio",
        label_visibility="collapsed",
    )
    st.session_state["guest_input_type"] = input_type

    smiles_in     = ""
    uploaded_file = None

    # ── SMILES ────────────────────────────────────────────────────────────────
    if input_type == "SMILES":

        # Example guests
        EXAMPLES = {
            "Aspirin":      "CC(=O)OC1=CC=CC=C1C(=O)O",
            "Caffeine":     "Cn1cnc2c1c(=O)n(c(=O)n2C)C",
            "Ibuprofen":    "CC(C)Cc1ccc(cc1)C(C)C(=O)O",
            "Naproxen":     "COc1ccc2cc(ccc2c1)C(C)C(=O)O",
            "Glucose":      "OC[C@H]1OC(O)[C@H](O)[C@@H](O)[C@@H]1O",
            "Testosterone": "O=C1CC[C@H]2[C@@H]3CCc4cc(O)cc[C@@]4(C)[C@H]3CC[C@@]12C",
        }

        st.markdown("<div class='group-label'>Quick examples</div>", unsafe_allow_html=True)
        ex_cols = st.columns(len(EXAMPLES))
        for col, (name, smi) in zip(ex_cols, EXAMPLES.items()):
            with col:
                if st.button(name, key=f"ex_{name}", use_container_width=True):
                    st.session_state["guest_smiles"] = smi
                    st.rerun()

        st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
        smiles_in = st.text_input(
            "SMILES string",
            value=st.session_state.get("guest_smiles", "CC(=O)OC1=CC=CC=C1C(=O)O"),
            help="Paste any valid SMILES or click an example above",
            key="guest_smiles_input",
            placeholder="e.g. CC(=O)OC1=CC=CC=C1C(=O)O",
        )
        if smiles_in:
            st.markdown(
                f'<div style="font-family:JetBrains Mono,monospace;font-size:11px;'
                f'color:var(--accent);padding:4px 0;">{smiles_in}</div>',
                unsafe_allow_html=True,
            )

    # ── PubChem name search ───────────────────────────────────────────────────
    elif input_type == "Search by name (PubChem)":
        st.markdown(
            "Type a compound name (common, IUPAC, or trade name) and DFDD will "
            "fetch the structure from the "
            "[PubChem](https://pubchem.ncbi.nlm.nih.gov/) database."
        )

        sc1, sc2 = st.columns([3, 1])
        with sc1:
            query = st.text_input(
                "Compound name",
                value=st.session_state.get("guest_pubchem_query", ""),
                placeholder="e.g. aspirin, caffeine, ibuprofen, paracetamol…",
                key="guest_pubchem_query_input",
                label_visibility="collapsed",
            )
        with sc2:
            do_search = st.button("🔍 Search", use_container_width=True,
                                  key="btn_pubchem_search")

        if do_search and query.strip():
            st.session_state["guest_pubchem_query"] = query.strip()
            with st.spinner(f"Searching PubChem for “{query.strip()}”…"):
                try:
                    results = pubchem_search_by_name(query.strip(), max_results=5)
                    st.session_state["guest_pubchem_results"] = results
                    st.session_state["guest_pubchem_error"]   = None
                except Exception as e:
                    st.session_state["guest_pubchem_results"] = []
                    st.session_state["guest_pubchem_error"]   = str(e)

        err = st.session_state.get("guest_pubchem_error")
        if err:
            st.error(f"PubChem lookup failed: {err}")

        results = st.session_state.get("guest_pubchem_results", [])

        if results:
            st.caption(f"Found {len(results)} match(es) — click **Use this** to load.")

            # Pre-select first result if nothing chosen
            sel_cid = st.session_state.get("guest_pubchem_selected_cid")
            if sel_cid is None:
                sel_cid = results[0]["cid"]
                st.session_state["guest_pubchem_selected_cid"] = sel_cid

            for r in results:
                is_sel = (r["cid"] == sel_cid)
                with st.container(border=True):
                    rc1, rc2, rc3 = st.columns([1, 3, 1])
                    with rc1:
                        try:
                            st.image(r["image_url"], width=120)
                        except Exception:
                            st.caption("(no image)")
                    with rc2:
                        st.markdown(f"**{r['name']}**  \n"
                                    f"CID `{r['cid']}` · {r['formula']} · "
                                    f"MW {r['mw']}")
                        if r.get("iupac"):
                            st.caption(f"IUPAC: {r['iupac']}")
                        if r.get("smiles"):
                            st.code(r["smiles"], language="text")
                    with rc3:
                        label = "✓ Selected" if is_sel else "Use this"
                        if st.button(label,
                                     key=f"pc_pick_{r['cid']}",
                                     type="primary" if is_sel else "secondary",
                                     use_container_width=True,
                                     disabled=is_sel):
                            st.session_state["guest_pubchem_selected_cid"] = r["cid"]
                            st.session_state["guest_smiles"] = r["smiles"]
                            st.rerun()
                        st.markdown(
                            f"[View on PubChem ↗]({r['pubchem_url']})",
                            help="Open the compound page in a new tab",
                        )

            # Resolve selected SMILES
            chosen = next((r for r in results
                           if r["cid"] == st.session_state.get("guest_pubchem_selected_cid")),
                          results[0])
            smiles_in = chosen["smiles"]
            st.session_state["guest_smiles"] = smiles_in
            st.success(f"Using **{chosen['name']}** (CID {chosen['cid']}) — "
                       f"SMILES loaded.")
        elif st.session_state.get("guest_pubchem_query") and not err:
            st.info("No matches. Try a different spelling or a more common name.")

    # ── Ketcher draw ──────────────────────────────────────────────────────────
    elif input_type == "Draw (Ketcher)":
        st_ketcher = _try_import_ketcher()

        if st_ketcher is None:
            # Auto-install streamlit-ketcher if not present
            with st.spinner("Installing streamlit-ketcher…"):
                core.run_cmd(
                    [sys.executable, "-m", "pip", "install", "-q", "streamlit-ketcher"],
                    timeout=120
                )
            st.info("✅ streamlit-ketcher installed — please click **Draw (Ketcher)** again.")
            st.stop()

        st.markdown("**Draw your molecule below. SMILES updates automatically.**")
        # Pre-load with last used SMILES if available
        init_smiles = st.session_state.get("guest_smiles", "")
        drawn_smiles = st_ketcher(init_smiles, height=500, key="ketcher_editor")

        if drawn_smiles and drawn_smiles.strip():
            smiles_in = drawn_smiles.strip()
            st.session_state["guest_smiles"] = smiles_in
            st.caption(f"Current SMILES: `{smiles_in}`")
        else:
            smiles_in = ""
            st.caption("Draw a structure above — SMILES will appear here.")

    # ── File upload ───────────────────────────────────────────────────────────
    else:
        uploaded_file = st.file_uploader(
            "Upload molecule file (.pdb or .mol2)",
            type=["pdb", "mol2"],
            help="PDB or Mol2 format only. Must contain 3D coordinates.",
            key="guest_file_upload",
        )
        if uploaded_file:
            st.caption(f"Uploaded: `{uploaded_file.name}`")

    st.divider()

    # ── pH / protonation ──────────────────────────────────────────────────────
    st.markdown("#### 🧫 Protonation state")

    pc1, pc2, pc3 = st.columns([1.2, 1, 1.5])
    with pc1:
        apply_ph = st.checkbox(
            "Adjust protonation at pH",
            value=st.session_state.get("guest_apply_ph", True),
            help="Applies only to SMILES/Ketcher input (not to uploaded 3D files).",
            key="guest_apply_ph_chk",
        )
        st.session_state["guest_apply_ph"] = apply_ph

    with pc2:
        pH_val = st.slider(
            "Target pH",
            2.0, 12.0,
            st.session_state.get("guest_pH", 7.4),
            0.1,
            disabled=not apply_ph,
            key="guest_pH_slider",
        )
        st.session_state["guest_pH"] = pH_val

    with pc3:
        pH_range = st.slider(
            "pH range (± around target)",
            0.1, 2.0,
            st.session_state.get("guest_pH_range", 0.5),
            0.1,
            disabled=not apply_ph,
            help="Lower = strict protonation; higher = includes minor microspecies.",
            key="guest_pH_range_slider",
        )
        st.session_state["guest_pH_range"] = pH_range

    # Live protonation preview (SMILES / Ketcher only)
    if apply_ph and smiles_in and smiles_in.strip() and not input_type.startswith("File"):
        if st.button("🔬 Preview protonated SMILES", key="btn_preview_proton"):
            with st.spinner("Scoring protonation states via Henderson–Hasselbalch…"):
                new_smi, changed, err = core.protonate_smiles_at_ph(
                    smiles_in.strip(), pH=pH_val, pH_range=pH_range
                )
            if err:
                st.warning(f"⚠️ Protonation unavailable: {err}")
            else:
                st.session_state["guest_smiles_protonated"] = new_smi
                # Compute formal charge on result
                charge_str = ""
                try:
                    from rdkit import Chem
                    m = Chem.MolFromSmiles(new_smi)
                    if m:
                        fc = sum(a.GetFormalCharge() for a in m.GetAtoms())
                        charge_str = f"  |  Charge: **{fc:+d}**"
                except Exception:
                    pass

                if changed:
                    st.success(
                        f"✅ Rank-1 microstate at pH {pH_val}:  "
                        f"`{new_smi}`{charge_str}"
                    )
                    st.caption(
                        f"Input: `{smiles_in.strip()}` → selected by HH score "
                        f"(pKaNET-style ranking)"
                    )
                else:
                    st.info(
                        f"No protonation change at pH {pH_val} — "
                        f"input already matches rank-1 state.{charge_str}"
                    )

        if st.session_state.get("guest_smiles_protonated"):
            st.caption(f"Selected microstate: `{st.session_state['guest_smiles_protonated']}`")

    st.divider()

    # ── Parameters ────────────────────────────────────────────────────────────
    c1, c2 = st.columns(2)
    with c1:
        st.info("**Guest residue name:** `GST` (fixed)")
        output_name = "GST"

    with c2:
        st.info("**Charge method:** AM1-BCC (GAFF2)")

        # Charge options depend on input method
        if input_type.startswith("File"):
            charge_mode = st.radio(
                "Charge",
                ["Auto-detect from file", "Set manually"],
                horizontal=True,
                key="guest_charge_mode",
            )
            manual_charge = st.number_input(
                "Manual charge",
                -10, 10, 0,
                disabled=(charge_mode == "Auto-detect from file"),
                key="guest_manual_charge",
            )
        else:
            charge_mode = st.radio(
                "Charge",
                ["Auto-detect (RDKit)", "Set manually"],
                horizontal=True,
                key="guest_charge_mode",
            )
            manual_charge = st.number_input(
                "Manual charge",
                -10, 10, 0,
                disabled=(charge_mode != "Set manually"),
                key="guest_manual_charge",
            )

    # ── Prepare ───────────────────────────────────────────────────────────────
    if st.button("▶ Prepare guest", type="primary"):
        log = ""
        with st.spinner("Preparing guest molecule…"):

            # File upload path
            if input_type.startswith("File") and uploaded_file:
                dest = wpath(uploaded_file.name)
                with open(dest, "wb") as f:
                    f.write(uploaded_file.read())
                mol_in    = dest
                smiles_in = None

                # Charge from file or manual
                if charge_mode == "Auto-detect from file":
                    detected = _charge_from_file(dest)
                    log += f"Charge read from file: {detected}\n"
                else:
                    detected = manual_charge
            else:
                mol_in   = None
                detected = 0

            # SMILES / Ketcher path
            if smiles_in and smiles_in.strip():
                smi_to_use = smiles_in.strip()

                # Apply pH-based protonation
                if st.session_state.get("guest_apply_ph", True):
                    new_smi, changed, err = core.protonate_smiles_at_ph(
                        smi_to_use,
                        pH=st.session_state.get("guest_pH", 7.4),
                        pH_range=st.session_state.get("guest_pH_range", 0.5),
                    )
                    if err:
                        log += f"pH adjustment skipped: {err}\n"
                    else:
                        if changed:
                            log += f"pH {st.session_state['guest_pH']}: {smi_to_use}  →  {new_smi}\n"
                            st.info(f"Protonation adjusted at pH {st.session_state['guest_pH']}:  `{smi_to_use}`  →  `{new_smi}`")
                        else:
                            log += f"SMILES unchanged at pH {st.session_state['guest_pH']}\n"
                        smi_to_use = new_smi

                pdb_raw = wpath("guest_raw.pdb")
                sdf_raw = wpath("guest_raw.sdf")
                detected, err = core.smiles_to_3d_pdb(smi_to_use, pdb_raw, sdf_raw,
                                                       workdir=WD())
                if err:
                    st.error(f"❌ RDKit error: {err}")
                    st.stop()
                mol_in = sdf_raw if os.path.exists(sdf_raw) else pdb_raw
                log   += f"RDKit detected charge: {detected}\n"
                # Persist the final SMILES used
                st.session_state["guest_smiles_protonated"] = smi_to_use
                if charge_mode == "Set manually":
                    detected = manual_charge

            if mol_in is None:
                st.error("❌ No molecule provided.")
                st.stop()

            final_charge = detected

            # Convert to PDB for workspace copy
            guest_pdb  = wpath(f"{output_name}.pdb")
            prep_out   = wpath(f"{output_name}.prep")
            frcmod_out = wpath(f"{output_name}.frcmod")

            # Run antechamber with AM1-BCC (writes prep file with correct atom names)
            ok, ac_log = core.run_antechamber(
                mol_in, prep_out, frcmod_out, final_charge, WD(),
                charge_method="bcc"
            )
            log += ac_log

            if not ok:
                st.error("❌ Antechamber failed")
                st.session_state["log_guest"] = log
                log_expander("log_guest")
                st.stop()

            # Write guest PDB with correct residue name matching the prep file.
            # antechamber -fo pdb is tried first (gives correct atom names),
            # then obabel with residue name patch as fallback.
            _pdb_ok = False
            ext_in  = os.path.splitext(mol_in)[1].lower()
            fi_flag = "mdl" if ext_in == ".sdf" else "pdb"

            rc_pdb, out_pdb = core.run_cmd(
                ["antechamber",
                 "-i", mol_in, "-fi", fi_flag,
                 "-o", guest_pdb, "-fo", "pdb",
                 "-rn", output_name, "-at", "gaff2", "-dr", "no"],
                cwd=WD(), timeout=120
            )
            log += f"=== antechamber PDB ===\n{out_pdb}\n"
            if rc_pdb == 0 and os.path.exists(guest_pdb) and os.path.getsize(guest_pdb) > 10:
                _pdb_ok = True

            if not _pdb_ok:
                # Fallback: obabel then patch residue name
                core.run_cmd(["obabel", mol_in, "-O", guest_pdb, "-h"], cwd=WD())
                log += "Guest PDB written via obabel (patching residue name)\n"
                # Patch MOL/LIG/UNK → output_name in the PDB
                _bad = {"MOL","LIG","UNL","UNK","LGN","DRG","CPD","HET"}
                if os.path.exists(guest_pdb):
                    _lines = []
                    with open(guest_pdb) as _f:
                        for _ln in _f:
                            if _ln.startswith(("ATOM","HETATM")):
                                _rn = _ln[17:20].strip()
                                if _rn in _bad or (_rn and _rn != output_name):
                                    _ln = _ln[:17] + output_name[:3].ljust(3) + _ln[20:]
                            _lines.append(_ln)
                    with open(guest_pdb, "w") as _f:
                        _f.writelines(_lines)

            st.session_state["guest_path"]      = guest_pdb
            st.session_state["guest_prep"]       = prep_out
            st.session_state["guest_frcmod"]     = frcmod_out
            st.session_state["guest_smiles"]     = smiles_in or ""
            st.session_state["detected_charge"]  = final_charge
            st.session_state["log_guest"]        = log

        st.success(f"✅ Guest ready!   Charge: **{final_charge}**   Method: AM1-BCC")
        gp = st.session_state.get("guest_path")
        # Show SDF (with H) if available, fall back to PDB
        sdf_path = wpath("guest_raw.sdf")
        if os.path.exists(sdf_path):
            mol_str  = core.read_file(sdf_path)
            mol_fmt  = "sdf"
        elif gp and os.path.exists(gp):
            mol_str  = core.read_file(gp)
            mol_fmt  = "pdb"
        else:
            mol_str, mol_fmt = None, None

        if mol_str:
            st.components.v1.html(
                py3dmol_html_fmt(mol_str, mol_fmt, 680, 360),
                height=370
            )
            st.caption("🖱️ Left-drag = rotate · Scroll = zoom · Right-drag = pan")
        next_button(3, "Next → Build complex & solvate", key_suffix="_new")

    if st.session_state.get("guest_path") and os.path.exists(st.session_state["guest_path"]):
        st.info(f"Guest already prepared: `{st.session_state['guest_path']}`")
        next_button(3, "Next → Build complex & solvate", key_suffix="_done")
    log_expander("log_guest")


# ══════════════════════════════════════════════════════════════════════════════
# STEP 3 — Build complex + solvation
# ══════════════════════════════════════════════════════════════════════════════

@st.cache_data(show_spinner=False)
def _build_preview_cached(hp, gp, distance, _mtime_h, _mtime_g):
    import tempfile
    tmp = os.path.join(tempfile.gettempdir(),
                       f"_dfdd_prev_{abs(hash((hp, gp, distance)))}.pdb")
    ok, msg = core.build_host_guest_complex(hp, gp, distance, tmp)
    if not ok or not os.path.exists(tmp):
        return None, msg
    return core.read_file(tmp), msg


def _py3dmol_complex(pdb_str, width=560, height=480, distance=0):
    """Fixed-camera 3D viewer for host-guest complex.

    Camera is set once to show the full ~55 Å Z-extent centered at origin.
    It does NOT follow the ligand — the view stays fixed so the user can see
    the ligand moving up/down as they adjust Z.

    The Z-position bar on the right of the viewer is purely decorative (updates
    via the Streamlit slider outside).  Click any atom for element info.
    """
    # Percentage for the Z-position indicator inside the viewer
    # Map -20..+20 Ang → 0..100% (bottom to top)
    zpct = int((distance + 20) / 40 * 100)
    z_label = f"{distance:+d} Å"
    above_below = "above cavity" if distance < 0 else ("at cavity" if distance == 0 else "below cavity")

    return f"""
<script src="https://3Dmol.org/build/3Dmol-min.js"></script>
<div style="display:flex;gap:0;width:{width+64}px;height:{height}px;
            border-radius:12px;overflow:hidden;border:1px solid #E5E7EB;">

  <!-- ── 3D viewer ───────────────────────────────────────────── -->
  <div style="position:relative;flex:1;background:#FAFBFC;">
    <div id="v3dc" style="width:100%;height:100%;"></div>

    <!-- atom info popup -->
    <div id="v3dc-info" style="
         display:none;position:absolute;top:10px;left:10px;
         background:rgba(91,63,209,0.93);color:#fff;
         font-size:11px;font-family:monospace;padding:5px 10px;
         border-radius:7px;pointer-events:none;line-height:1.6;
         box-shadow:0 2px 8px rgba(0,0,0,0.2);max-width:200px;z-index:10;"></div>

    <!-- camera hint -->
    <div style="position:absolute;bottom:8px;left:10px;font-size:10px;color:#999;
         background:rgba(255,255,255,0.8);padding:2px 7px;border-radius:4px;
         pointer-events:none;">
      Left-drag: rotate &nbsp;·&nbsp; Scroll: zoom &nbsp;·&nbsp; Click: info
    </div>
  </div>

  <!-- ── Z-axis bar (right panel) ────────────────────────────── -->
  <div style="width:64px;background:#F3F4F6;display:flex;flex-direction:column;
              align-items:center;justify-content:space-between;
              padding:10px 0;border-left:1px solid #E5E7EB;">

    <!-- label top (+20) -->
    <div style="font-size:10px;color:#6B7280;font-weight:500;">+20 Å</div>

    <!-- track -->
    <div style="position:relative;width:20px;flex:1;margin:6px 0;
                background:#E5E7EB;border-radius:10px;overflow:hidden;">
      <!-- filled portion below indicator -->
      <div style="position:absolute;bottom:0;left:0;right:0;
                  height:{zpct}%;background:#C7EDE2;border-radius:10px;
                  transition:height .15s ease;"></div>
      <!-- indicator pill -->
      <div style="position:absolute;left:0;right:0;
                  bottom:calc({zpct}% - 12px);height:24px;
                  background:#8B6CE8;border-radius:10px;
                  box-shadow:0 1px 4px rgba(29,158,117,0.5);
                  transition:bottom .15s ease;"></div>
    </div>

    <!-- label bottom (-20) -->
    <div style="font-size:10px;color:#6B7280;font-weight:500;">-20 Å</div>

    <!-- current value -->
    <div style="margin-top:6px;text-align:center;line-height:1.3;">
      <div style="font-size:13px;font-weight:700;color:#5B3FD1;">{z_label}</div>
      <div style="font-size:9px;color:#9CA3AF;margin-top:1px;">{above_below}</div>
    </div>
  </div>

</div>

<script>
var v = $3Dmol.createViewer(document.getElementById("v3dc"),
                            {{backgroundColor:"#FAFBFC"}});
v.addModel(`{pdb_str}`,"pdb");
v.setStyle({{}}, {{stick:{{colorscheme:"Jmol", radius:0.15}}}});
v.addStyle({{resn:"GST"}}, {{stick:{{colorscheme:"cyanCarbon", radius:0.24}}}});
v.addStyle({{resn:"GST"}}, {{sphere:{{colorscheme:"cyanCarbon", radius:0.16}}}});

/* ── Fixed camera: always shows 55 Å window centred at origin ─────────── */
/* Rotate 90° around X first so Z-axis = screen vertical */
v.rotate(90, {{x:1, y:0, z:0}});
/* Set a fixed zoom level — slab from -27.5 to +27.5 Å in the new Z direction.
   zoomTo() is intentionally NOT called so the camera does not follow the ligand. */
v.zoom(0.85);          /* tweak: smaller = more zoomed out */
v.setView([0, 0, 0,   /* centre of rotation x,y,z */
           0, 0, 0,   /* camera x,y offset */
           40]);       /* camera distance — ~55 Å field of view */

/* atom click */
var infoBox = document.getElementById("v3dc-info");
v.setClickable({{}}, true, function(atom) {{
  var tag = atom.resn === "GST" ? " [guest]" : " [host]";
  infoBox.innerHTML = [
    "Elem: " + (atom.elem||"?") + tag,
    "Atom: " + (atom.atom||"?"),
    "Res:  " + (atom.resn||"?") + " " + (atom.resi||""),
    "XYZ: (" + (atom.x||0).toFixed(1) + ", " +
               (atom.y||0).toFixed(1) + ", " +
               (atom.z||0).toFixed(1) + ")"
  ].join("<br>");
  infoBox.style.display = "block";
  setTimeout(function(){{ infoBox.style.display="none"; }}, 3500);
  v.render();
}});
v.render();
</script>"""


def page_build():
    render_topbar("Build & Solvate", 3)
    render_stepper(3)
    st.markdown('<div class="content-pad step-body">', unsafe_allow_html=True)
    section_header("Build complex & solvate", "Place guest inside host, add water box, prepare for simulation.", step_num=3)

    hp = st.session_state.get("host_path")
    gp = st.session_state.get("guest_path")

    if not (hp and os.path.exists(hp or "") and gp and os.path.exists(gp or "")):
        st.warning("Complete Steps 1 (host) and 2 (guest) first.")
        return

    pc1, pc2 = st.columns(2)
    with pc1:
        st.info(f"**Host:** `{os.path.basename(hp)}`")
    with pc2:
        st.info(f"**Guest:** `{os.path.basename(gp)}`")

    # Already done shortcut
    if st.session_state.get("topo_done") and os.path.exists(wpath("complex.top")):
        st.success("Complex & topology already built.")
        mc1, mc2, mc3 = st.columns(3)
        for col, fname in zip([mc1, mc2, mc3],
                              ["complex.top", "complex.crd", "complex_leap.pdb"]):
            p = wpath(fname)
            with col:
                st.metric(fname, f"{core.file_mb(p):.2f} MB" if os.path.exists(p) else "---")
        next_button(4, "Next → Minimization & heating", key_suffix="_done")
        return

    # ══════════════════════════════════════════════════════════════════════════
    # STAGE 1 — Z-axis positioning
    # ══════════════════════════════════════════════════════════════════════════
    st.markdown("### 📐 Stage 1 — Position guest along Z-axis")
    st.caption(
        "Use the **+** / **−** buttons or type a value to slide the guest along the "
        "cavity axis. The 3D view and the Z-bar update live."
    )

    # ── Z controller row (above viewer) ──────────────────────────────────────
    cur_dist = st.session_state.get("build_distance", -15)

    zc1, zc2, zc3, zc4, zc5 = st.columns([1, 1, 2, 1, 1])
    with zc1:
        if st.button("−5", key="z_m5", use_container_width=True):
            st.session_state["build_distance"] = max(-20, cur_dist - 5)
            st.rerun()
    with zc2:
        if st.button("−1", key="z_m1", use_container_width=True):
            st.session_state["build_distance"] = max(-20, cur_dist - 1)
            st.rerun()
    with zc3:
        new_val = st.number_input(
            "Z offset (Å)", min_value=-20, max_value=20,
            value=cur_dist, step=1, label_visibility="collapsed",
            key="z_num",
        )
        if new_val != cur_dist:
            st.session_state["build_distance"] = new_val
            st.rerun()
    with zc4:
        if st.button("+1", key="z_p1", use_container_width=True):
            st.session_state["build_distance"] = min(20, cur_dist + 1)
            st.rerun()
    with zc5:
        if st.button("+5", key="z_p5", use_container_width=True):
            st.session_state["build_distance"] = min(20, cur_dist + 5)
            st.rerun()

    distance = st.session_state.get("build_distance", -15)

    # ── Live 3D preview ───────────────────────────────────────────────────────
    mh, mg = os.path.getmtime(hp), os.path.getmtime(gp)
    with st.spinner("Updating…"):
        preview_pdb, pmsg = _build_preview_cached(hp, gp, float(distance), mh, mg)

    if preview_pdb:
        # Full-width viewer with integrated Z-bar on the right
        st.components.v1.html(
            _py3dmol_complex(preview_pdb, 580, 480, distance),
            height=490
        )
    else:
        st.error(f"Preview failed: {pmsg}")

    # Stage 1 confirm
    dist_confirmed = st.session_state.get("build_dist_confirmed", False)
    if not dist_confirmed:
        col_btn, _, _ = st.columns([1, 1, 1])
        with col_btn:
            if st.button("✅ Confirm position → set up water", type="primary",
                         key="btn_dist_ok", use_container_width=True):
                st.session_state["build_dist_confirmed"] = True
                st.rerun()
        return
    else:
        c_ok, c_edit = st.columns([3, 1])
        with c_ok:
            st.success(f"✅ Guest position confirmed: Z = **{distance} Å**  ({('above' if distance < 0 else 'at/below')} cavity)")
        with c_edit:
            if st.button("✏️ Change", key="btn_dist_edit", use_container_width=True):
                st.session_state["build_dist_confirmed"] = False
                st.rerun()

    st.divider()

    # STAGE 2 - Solvation
    st.markdown("### Stage 2 -- Add water box")

    sc1, sc2, sc3 = st.columns(3)
    with sc1:
        water_type = st.selectbox(
            "Water model", ["TIP3P", "OPC"],
            index=0 if st.session_state.get("build_water_type", "TIP3P") == "TIP3P" else 1,
            key="build_water_sel",
        )
        st.session_state["build_water_type"] = water_type
    with sc2:
        box_buf = st.slider("Water padding (Ang)", 4, 25,
            st.session_state.get("build_box_buf", 5), step=1, key="build_box_buf_sl")
        st.session_state["build_box_buf"] = box_buf
        unit_xy = st.slider("Unit cell X/Y (Ang)", 12, 25,
            st.session_state.get("build_unit_xy", 13), step=1, key="build_uxy_sl")
        st.session_state["build_unit_xy"] = unit_xy
    with sc3:
        unit_z = st.slider("Unit cell Z (Ang)", 30, 60,
            st.session_state.get("build_unit_z", 35), step=1, key="build_uz_sl")
        st.session_state["build_unit_z"] = unit_z
        translate_z = st.slider("Z-translation (Ang)", -20, 20,
            st.session_state.get("build_translate_z", 0), step=1, key="build_tz_sl")
        st.session_state["build_translate_z"] = translate_z

    st.caption(
        f"{water_type} | padding {box_buf} Ang | "
        f"cell {unit_xy}x{unit_xy}x{unit_z} Ang | Z-shift {translate_z} Ang"
    )

    water_ff  = "leaprc.water.tip3p" if water_type == "TIP3P" else "leaprc.water.opc"
    water_box = "TIP3PBOX"           if water_type == "TIP3P" else "OPCBOX"

    if st.button("OK -- build complex & add water", type="primary", key="btn_solvate"):
        cx_out = wpath("complex.pdb")
        with st.spinner("Building complex..."):
            ok, msg = core.build_host_guest_complex(hp, gp, distance, cx_out)
        if not ok:
            st.error(f"Build failed: {msg}"); st.stop()
        st.success("Complex built")

        ht  = st.session_state.get("host_type", "BCD_DFT")
        hff = st.session_state.get("host_forcefield", "DFT")
        if hff == "GLYCAM06":
            core.insert_ter_records(cx_out)

        with st.spinner("Running tleap... (~30 s)"):
            script = core.write_tleap_script(
                workdir=WD(), host_forcefield=hff,
                host_prep=st.session_state.get("host_prep", ""),
                host_frcmod=st.session_state.get("host_frcmod", ""),
                host_type=ht, water_ff=water_ff, water_box=water_box,
                box_buf=box_buf, unit_xy=unit_xy, unit_z=unit_z,
                translate_z=translate_z, cx_pdb=cx_out,
                out_top=wpath("complex.top"), out_crd=wpath("complex.crd"),
                out_pdb=wpath("complex_leap.pdb"),
                guest_prep=st.session_state.get("guest_prep"),
                guest_frcmod=st.session_state.get("guest_frcmod"),
            )
            rc, out = core.run_cmd(["tleap", "-f", script], cwd=WD())
        st.session_state["log_tleap"] = out

        if rc != 0:
            st.error("tleap failed")
            log_expander("log_tleap"); st.stop()

        st.session_state["build_done"] = True
        st.session_state["topo_done"]  = True
        st.success("Solvated system ready!")

        mc1, mc2, mc3 = st.columns(3)
        for col, fname in zip([mc1, mc2, mc3],
                              ["complex.top", "complex.crd", "complex_leap.pdb"]):
            p = wpath(fname)
            with col:
                st.metric(fname, f"{core.file_mb(p):.2f} MB" if os.path.exists(p) else "---")
        next_button(4, "Next -> Minimization & heating", key_suffix="_built")

    log_expander("log_tleap")


def page_minimize():
    render_topbar("Minimize", 4)
    render_stepper(4)
    st.markdown('<div class="content-pad step-body">', unsafe_allow_html=True)
    section_header("Minimize & heat", "Energy minimization, NVT heating 0→300 K, short equilibration.", step_num=4)

    st.markdown('<div class="glass-card" style="margin-bottom:20px;">', unsafe_allow_html=True)
    c1, c2, c3 = st.columns(3)
    with c1:
        min_iters  = st.number_input("Max minimization steps", 100, 50000, 5000)
    with c2:
        heat_steps = st.number_input("Steps per heating stage (×6)", 1000, 50000, 10000)
        nvt_steps  = st.number_input("NVT steps", 10000, 500000, 50000)
    with c3:
        prod_steps = st.number_input("Restrained production steps", 10000, 500000, 100000)
    st.markdown('</div>', unsafe_allow_html=True)

    total_ns = (heat_steps * 6 + nvt_steps + prod_steps) * 2 / 1e6
    st.markdown(
        f'<div class="summary-card">'
        f'Est. simulation time: <b>{total_ns:.2f} ns</b> &nbsp;·&nbsp; ~1–2 min on GPU'
        f'</div>',
        unsafe_allow_html=True,
    )

    if st.session_state.get("min_done") and os.path.exists(wpath("last_frame.rst7")):
        st.markdown(
            f'<div class="done-bar"><span class="done-icon">✅</span>'
            f'<div><div class="done-text">Minimization complete</div>'
            f'<div class="done-file">last_frame.rst7 · {core.file_mb(wpath("last_frame.rst7")):.2f} MB</div></div></div>',
            unsafe_allow_html=True,
        )
        next_button(5, "Next → LB-PaCS-MD →")
        return

    if st.button("▶ Run minimization & heating", type="primary"):
        waiting_card("Running OpenMM minimization + heating",
                     "This takes ~1–2 minutes on GPU. Please don't close this tab.", icon="⏳")

        progress = st.progress(0, text="Starting OpenMM…")

        progress.progress(10, text="Minimizing energy…")
        ok, out = core.run_minimize_heat(
            WD(), wpath("complex.top"), wpath("complex.crd"), wpath("last_frame.rst7"),
            min_iters=min_iters, heat_steps=heat_steps,
            nvt_steps=nvt_steps, prod_steps=prod_steps,
        )
        st.session_state["log_min"] = out

        if ok:
            progress.progress(100, text="Done!")
            st.session_state["min_done"] = True
            st.markdown(
                '<div class="done-bar"><span class="done-icon">✅</span>'
                '<div><div class="done-text">Minimization complete</div>'
                '<div class="done-file">last_frame.rst7 saved</div></div></div>',
                unsafe_allow_html=True,
            )
            next_button(5, "Next → LB-PaCS-MD")
        else:
            progress.progress(100, text="Failed")
            st.error("❌ Minimization failed")
            log_expander("log_min")

    log_expander("log_min")


# ══════════════════════════════════════════════════════════════════════════════
# STEP 5 — LB-PaCS-MD  (config + waiting page)
# ══════════════════════════════════════════════════════════════════════════════
def page_pacsmd():
    render_topbar("LB-PaCS-MD", 5)
    render_stepper(5)
    st.markdown('<div class="content-pad step-body">', unsafe_allow_html=True)
    section_header("LB-PaCS-MD sampling", "Configure and run the LB-PaCS-MD enhanced sampling cycles.", step_num=5)

    st.markdown('<div class="glass-card" style="margin-bottom:20px;">', unsafe_allow_html=True)
    c1, c2, c3 = st.columns(3)
    with c1:
        cycle    = st.slider("Cycles", 2, 100,
                             st.session_state.get("pacsmd_cycles", 40), key="sl_cycle")
        candi    = st.slider("Candidates / cycle", 2, 10,
                             st.session_state.get("pacsmd_candi", 3), key="sl_candi")
    with c2:
        sim_time = st.slider("Sim time / cycle (ps)", 1, 100,
                             st.session_state.get("pacsmd_sim_time", 10), key="sl_time")
        timestep = st.slider("Time step (fs)", 1, 4,
                             st.session_state.get("pacsmd_timestep", 1), key="sl_ts")
    with c3:
        temperature = st.number_input("Temperature (K)", value=float(st.session_state.get("pacsmd_temp", 300.0)))
        pressure    = st.number_input("Pressure (bar)",  value=float(st.session_state.get("pacsmd_pressure", 1.0)))
    st.markdown('</div>', unsafe_allow_html=True)

    steps_cycle = int(sim_time / (timestep / 1000))
    total_ns    = sim_time * cycle / 1000
    st.markdown(
        f'<div class="summary-card">'
        f'<b>{cycle}</b> cycles × <b>{sim_time}</b> ps = <b>{total_ns:.2f} ns</b> total'
        f' &nbsp;·&nbsp; <b>{steps_cycle:,}</b> steps / cycle'
        f'</div>',
        unsafe_allow_html=True,
    )

    if st.session_state.get("pacsmd_done") and os.path.exists(wpath("sum.nc")):
        st.markdown(
            f'<div class="done-bar"><span class="done-icon">✅</span>'
            f'<div><div class="done-text">LB-PaCS-MD complete</div>'
            f'<div class="done-file">sum.nc · {core.file_mb(wpath("sum.nc")):.1f} MB</div></div></div>',
            unsafe_allow_html=True,
        )
        next_button(6, "Next → PaCS-MD analysis →")
        return

    if st.button("▶ Run LB-PaCS-MD", type="primary"):
        st.session_state.update({
            "pacsmd_cycles": cycle, "pacsmd_candi": candi,
            "pacsmd_sim_time": sim_time, "pacsmd_timestep": timestep,
            "pacsmd_temp": temperature, "pacsmd_pressure": pressure,
        })

        host_type = st.session_state.get("host_type", "BCD_DFT")
        host_sel  = core.PACSMD_HOST_SEL.get(host_type, "resid 1-7")
        guest_sel = "resname GST"

        waiting_card("Running LB-PaCS-MD",
                     "Enhanced sampling in progress — ~12 min (40 cycles, Colab GPU). Please keep this tab open.",
                     icon="🚀")

        progress = st.progress(0, text=f"Starting {cycle} LB-PaCS-MD cycles…")

        core.write_pacsmd_config(WD(), temperature, pressure, timestep, 1.0, steps_cycle, 100)
        rc, out = core.run_pacsmd(WD(), wpath("last_frame.rst7"), cycle, candi, host_sel, guest_sel)

        st.session_state["log_pacsmd"]    = out
        st.session_state["pacsmd_cycles"] = cycle
        st.session_state["pacsmd_candi"]  = candi

        if rc == 0:
            progress.progress(100, text="LB-PaCS-MD complete!")
            st.session_state["pacsmd_done"] = True
            st.markdown(
                '<div class="done-bar"><span class="done-icon">✅</span>'
                '<div><div class="done-text">LB-PaCS-MD complete!</div></div></div>',
                unsafe_allow_html=True,
            )
            next_button(6, "Next → PaCS-MD analysis →")
        else:
            progress.progress(100, text="Failed")
            st.error("❌ PaCS-Q failed")
            log_expander("log_pacsmd")

    log_expander("log_pacsmd")


# ══════════════════════════════════════════════════════════════════════════════
# STEP 6 — PaCS-MD analysis + optional extend
# ══════════════════════════════════════════════════════════════════════════════
def page_pacsmd_analysis():
    render_topbar("PaCS-MD Analysis", 6)
    render_stepper(6)
    st.markdown('<div class="content-pad step-body">', unsafe_allow_html=True)
    section_header("PaCS-MD analysis", "Evaluate trajectories, distances, RMSD, and radius of gyration.", step_num=6)

    host_type = st.session_state.get("host_type", "BCD_DFT")
    host_mask = core.HOST_SEL_MAP.get(host_type, ":1-7")

    # --- Auto-run CV analysis if not done yet ---
    if not os.path.exists(wpath("dis.dat")) or not os.path.exists(wpath("rg.dat")):
        with st.spinner("Running cpptraj CV analysis…"):
            rc, out = core.run_cpptraj_cv(
                WD(), wpath("complex.top"),
                st.session_state.get("pacsmd_cycles", 40),
                st.session_state.get("pacsmd_candi", 3),
                host_mask, ":GST"
            )
        st.session_state["log_cv"] = out
        if rc != 0:
            st.error("❌ cpptraj failed")
            log_expander("log_cv")
            st.stop()

    # --- Distance profile ---
    dis_dat = wpath("dis_plot.dat")
    last_d  = None

    if os.path.exists(dis_dat) and _numpy_ok:
        dis = np.loadtxt(dis_dat, usecols=0)
        last_d = float(dis[-1])

        # ── Metric cards ──────────────────────────────────────────────────────
        n_cyc = st.session_state.get("pacsmd_cycles", 40)
        total_ps = n_cyc * st.session_state.get("pacsmd_sim_time", 10)
        d_clr = "#10b981" if last_d < 5 else ("#f59e0b" if last_d < 10 else "#6366f1")
        m1, m2, m3 = st.columns(3)
        with m1:
            st.markdown(
                f'<div class="metric-card"><div class="metric-value" style="color:{d_clr};">{last_d:.1f}'
                f'<span class="metric-unit">Å</span></div>'
                f'<div class="metric-label">Final COM distance<br>host–guest</div></div>',
                unsafe_allow_html=True,
            )
        with m2:
            st.markdown(
                f'<div class="metric-card"><div class="metric-value" style="color:#8b5cf6;">{n_cyc}'
                f'<span class="metric-unit">cyc</span></div>'
                f'<div class="metric-label">LB-PaCS-MD cycles<br>completed</div></div>',
                unsafe_allow_html=True,
            )
        with m3:
            st.markdown(
                f'<div class="metric-card"><div class="metric-value" style="color:#06b6d4;">{total_ps/1000:.2f}'
                f'<span class="metric-unit">ns</span></div>'
                f'<div class="metric-label">Total simulation time<br>sampled</div></div>',
                unsafe_allow_html=True,
            )
        st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)

        if _plotly_ok:
            fig = go.Figure(go.Scatter(
                x=list(range(1, len(dis) + 1)), y=dis.tolist(),
                mode="lines+markers",
                line=dict(color="#6366f1", width=2),
                marker=dict(size=4, color="#6366f1"),
                fill="tozeroy",
                fillcolor="rgba(99,102,241,0.08)",
            ))
            fig.add_hline(y=5, line_dash="dot", line_color="#ef4444",
                          annotation_text="5 Å threshold",
                          annotation_font_color="#ef4444")
            fig.update_layout(
                xaxis_title="Cycle", yaxis_title="COM Distance (Å)",
                title="Host–Guest COM Distance Profile",
                height=320,
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(255,255,255,0.6)",
                font=dict(family="Noto Sans, sans-serif", size=12),
                xaxis=dict(gridcolor="rgba(99,102,241,0.08)"),
                yaxis=dict(gridcolor="rgba(99,102,241,0.08)"),
                margin=dict(l=0, r=0, t=36, b=0),
            )
            st.plotly_chart(fig, use_container_width=True)

        if last_d < 5:
            st.markdown(
                '<div class="done-bar"><span class="done-icon">🎉</span>'
                f'<div><div class="done-text">Guest complexed!</div>'
                f'<div class="done-file">Final COM distance = {last_d:.1f} Å</div></div></div>',
                unsafe_allow_html=True,
            )
        elif last_d < 10:
            st.info(f"Guest approaching cavity — distance = **{last_d:.1f} Å**")
        else:
            st.warning(f"Guest not yet complexed — distance = **{last_d:.1f} Å**")
    else:
        st.info("`dis_plot.dat` not found — generated automatically after PaCS-Q finishes.")

    # --- 2D FEL ---
    rg_path  = wpath("rg.dat")
    dis_path = wpath("dis.dat")
    if os.path.exists(dis_path) and os.path.exists(rg_path) and _plotly_ok and _numpy_ok:
        with st.expander("📈 2D Free Energy Landscape"):
            dis_arr = np.loadtxt(dis_path, comments=["#","@"], usecols=1)
            rg_arr  = np.loadtxt(rg_path,  comments=["#","@"], usecols=2)
            fig2d = go.Figure(go.Histogram2dContour(
                x=dis_arr, y=rg_arr, colorscale="Teal",
                contours_coloring="fill", ncontours=20,
            ))
            fig2d.update_layout(
                xaxis_title="Host–Guest Distance (Å)", yaxis_title="Host Rg (Å)",
                title="2D Free Energy Landscape", height=420,
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(255,255,255,0.6)",
                font=dict(family="Noto Sans, sans-serif", size=12),
            )
            st.plotly_chart(fig2d, use_container_width=True)

    # --- Extend? ---
    st.divider()
    if last_d is None or last_d >= 5:
        st.markdown('<div class="group-label" style="margin-top:20px;">Extend simulation?</div>', unsafe_allow_html=True)
        want_extend = st.radio(
            "Guest has not fully complexed. Do you want to extend the simulation?",
            ["Yes, extend", "No, continue to cMD"],
            key="extend_radio"
        )
        if want_extend == "Yes, extend":
            ext_cycle = st.number_input(
                "Extend to total cycles",
                min_value=st.session_state.get("pacsmd_cycles", 40) + 5,
                max_value=300,
                value=st.session_state.get("pacsmd_cycles", 40) + 30,
            )
            if st.button("▶ Extend LB-PaCS-MD", type="primary"):
                host_type = st.session_state.get("host_type", "BCD_DFT")
                host_sel  = core.PACSMD_HOST_SEL.get(host_type, "resid 1-7")
                ts        = st.session_state.get("pacsmd_timestep", 1)
                st_c      = st.session_state.get("pacsmd_sim_time", 10)
                steps_c   = int(st_c / (ts / 1000))

                waiting_card("Extending LB-PaCS-MD…", "Running additional cycles. Please wait.", icon="🔄")

                core.write_pacsmd_config(
                    WD(),
                    st.session_state.get("pacsmd_temp", 300.0),
                    st.session_state.get("pacsmd_pressure", 1.0),
                    ts, 1.0, steps_c, 100
                )
                rc, out = core.run_pacsmd(
                    WD(), wpath("last_frame.rst7"),
                    int(ext_cycle),
                    st.session_state.get("pacsmd_candi", 3),
                    host_sel, "resname GST", rerun=True
                )
                st.session_state["log_pacsmd"] += "\n" + out
                st.session_state["pacsmd_cycles"] = int(ext_cycle)

                if rc == 0:
                    st.session_state["pacsmd_extended"] = True
                    st.success(f"✅ Extended to {ext_cycle} cycles!")
                    st.rerun()
                else:
                    st.error("❌ Extension failed")
                    log_expander("log_pacsmd")
        else:
            next_button(7, "Next → Classical MD")
    else:
        # Guest complexed
        st.markdown(
            '<div class="done-bar"><span class="done-icon">🎉</span>'
            '<div><div class="done-text">Guest complexed — ready for cMD</div></div></div>',
            unsafe_allow_html=True,
        )
        next_button(7, "Next → Classical MD")

    log_expander("log_cv")


# ══════════════════════════════════════════════════════════════════════════════
# STEP 7 — Classical MD  (ask length + waiting page)
# ══════════════════════════════════════════════════════════════════════════════
def page_cmd():
    render_topbar("Classical MD", 7)
    render_stepper(7)
    st.markdown('<div class="content-pad step-body">', unsafe_allow_html=True)
    section_header("Classical MD (NPT)", "Run unbiased NPT molecular dynamics from the best PaCS-MD frame.", step_num=7)

    if st.session_state.get("cmd_done") and os.path.exists(wpath("md.dcd")):
        st.markdown(
            f'<div class="done-bar"><span class="done-icon">✅</span>'
            f'<div><div class="done-text">cMD complete</div>'
            f'<div class="done-file">md.dcd · {core.file_mb(wpath("md.dcd")):.1f} MB</div></div></div>',
            unsafe_allow_html=True,
        )
        next_button(8, "Next → Analysis & MM-PBSA →")
        return

    st.markdown('<div class="glass-card" style="margin-bottom:20px;">', unsafe_allow_html=True)
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        length_ns   = st.number_input("Simulation length (ns)", 0.1, 100.0, 2.0, step=0.5)
    with c2:
        temperature = st.number_input("Temperature (K)", value=300.0)
    with c3:
        pressure    = st.number_input("Pressure (bar)", value=1.0)
    with c4:
        report_int  = st.number_input("Reporter interval (steps)", 1000, 50000, 5000)
    st.markdown('</div>', unsafe_allow_html=True)

    steps_est = int(length_ns * 1e6 / 2)
    st.markdown(
        f'<div class="summary-card">'
        f'<b>{length_ns}</b> ns &nbsp;·&nbsp; '
        f'<b>{steps_est:,}</b> steps at dt=2 fs &nbsp;·&nbsp; '
        f'est. <b>{length_ns*7:.0f}–{length_ns*15:.0f} min</b> on GPU'
        f'</div>',
        unsafe_allow_html=True,
    )

    if st.button("▶ Run cMD", type="primary"):
        waiting_card(
            f"Running {length_ns} ns cMD (NPT)",
            f"~{length_ns*7:.0f}–{length_ns*15:.0f} min on Colab GPU. Please keep this tab open.",
            icon="🔬",
        )

        progress = st.progress(0, text="Extracting last PaCS-MD frame…")

        with st.spinner("Extracting last frame…"):
            core.extract_last_rst_from_pacsmd(WD(), wpath("complex.top"), wpath("sum.nc"))

        rst = wpath("last.rst")
        if not os.path.exists(rst):
            st.error("❌ `last.rst` not created — check sum.nc exists")
            st.stop()

        progress.progress(5, text=f"Running {length_ns} ns cMD…")

        ok, out = core.run_cmd_simulation(
            WD(),
            wpath("complex.top"), rst,
            wpath("md.dcd"),
            length_ns=length_ns,
            temperature=temperature,
            pressure=pressure,
            traj_int=int(report_int),
            report_int=int(report_int),
        )
        st.session_state["log_cmd"] = out

        if ok:
            progress.progress(100, text="cMD complete!")
            st.session_state["cmd_done"] = True
            st.markdown(
                '<div class="done-bar"><span class="done-icon">✅</span>'
                '<div><div class="done-text">cMD complete</div></div></div>',
                unsafe_allow_html=True,
            )
            next_button(8, "Next → Analysis & MM-PBSA →")
        else:
            progress.progress(100, text="Failed")
            st.error("❌ cMD failed")
            log_expander("log_cmd")

    log_expander("log_cmd")


# ══════════════════════════════════════════════════════════════════════════════
# STEP 8 — cMD Analysis + MM-PBSA/GBSA (auto-run all)
# ══════════════════════════════════════════════════════════════════════════════
def page_analysis():
    render_topbar("Analysis & MM-PBSA", 8)
    render_stepper(8)
    st.markdown('<div class="content-pad step-body">', unsafe_allow_html=True)
    section_header("Analysis & binding energy", "RMSD · Rg · distance analysis and MM-PBSA/GBSA binding free energy.", step_num=8)

    host_type = st.session_state.get("host_type", "BCD_DFT")
    host_mask = core.HOST_SEL_MAP.get(host_type, ":1-7")

    # --- Auto-run cpptraj if needed ---
    if not os.path.exists(wpath("rmsd.dat")):
        with st.spinner("Running cpptraj analysis (RMSD, Rg, distance)…"):
            rc, out = core.run_cpptraj_cmd_analysis(
                WD(), wpath("complex.top"), wpath("md.dcd"),
                wpath("complex.crd"), host_mask, ":GST"
            )
        if rc != 0:
            st.error("❌ cpptraj failed"); st.code(out[-2000:]); st.stop()
        st.markdown(
            '<div class="done-bar" style="margin-bottom:16px;">'
            '<span class="done-icon">✅</span>'
            '<div><div class="done-text">Trajectory analysis done</div></div></div>',
            unsafe_allow_html=True,
        )

    # --- Plots ---
    if _plotly_ok and _numpy_ok:
        plot_cfg = [
            ("rmsd.dat", 1, "RMSD (Å)",     "RMSD over time"),
            ("rg.dat",   2, "Rg (Å)",        "Radius of Gyration"),
            ("dis.dat",  1, "Distance (Å)",  "Host–Guest COM Distance"),
        ]
        charts = []
        for fname, col_idx, ylabel, title in plot_cfg:
            fpath = wpath(fname)
            if os.path.exists(fpath):
                try:
                    data = np.loadtxt(fpath, comments=["#","@"])
                    charts.append((data[:, 0], data[:, col_idx], ylabel, title))
                except Exception:
                    pass

        if charts:
            colors = ["#6366f1", "#06b6d4", "#10b981"]
            fig = make_subplots(
                rows=len(charts), cols=1,
                subplot_titles=[c[3] for c in charts],
                vertical_spacing=0.07,
            )
            for i, (x, y, ylabel, _) in enumerate(charts, 1):
                fig.add_trace(
                    go.Scatter(x=x.tolist(), y=y.tolist(), mode="lines",
                               line=dict(color=colors[i-1], width=1.5)),
                    row=i, col=1
                )
                fig.update_yaxes(title_text=ylabel, row=i, col=1)
                fig.update_xaxes(title_text="Frame", row=i, col=1)
            fig.update_layout(
                height=300 * len(charts), showlegend=False,
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(255,255,255,0.6)",
                font=dict(family="Noto Sans, sans-serif", size=12),
            )
            for i in range(1, len(charts)+1):
                fig.update_xaxes(gridcolor="rgba(99,102,241,0.08)", row=i, col=1)
                fig.update_yaxes(gridcolor="rgba(99,102,241,0.08)", row=i, col=1)
            st.plotly_chart(fig, use_container_width=True)

    st.divider()

    # --- Auto-run MM-PBSA if not done ---
    if not st.session_state.get("mmpbsa_done"):
        st.markdown('<div class="group-label">MM-PBSA / GBSA Binding Energy</div>', unsafe_allow_html=True)
        c1, c2 = st.columns(2)
        with c1:
            n_frames = st.number_input("Last N frames to analyse", 5, 100, 10)
            igb_val  = st.selectbox("GB model (igb)", ["2", "5", "1", "7", "8"])
        with c2:
            salt_conc = st.text_input("Salt concentration (M)", "0")
            do_pb     = st.checkbox("Also run MM-PBSA", value=True)

        if st.button("▶ Run MM-PBSA/GBSA", type="primary"):
            top = wpath("complex.top")
            with st.spinner("Running ante-MMPBSA + MMPBSA.py…"):
                ok, log, gb, pb = core.run_mmpbsa(
                    WD(), top, wpath("md.dcd"), n_frames,
                    igb_val, salt_conc, do_pb, label="cMD"
                )
            st.session_state["log_mmpbsa"] = log
            st.session_state["gb_result"]  = gb
            st.session_state["pb_result"]  = pb

            if not ok:
                st.error("❌ MMPBSA.py failed"); log_expander("log_mmpbsa"); st.stop()

            st.session_state["mmpbsa_done"] = True
            st.rerun()
    else:
        # Show results
        gb = st.session_state.get("gb_result")
        pb = st.session_state.get("pb_result")

        st.markdown(
            '<div class="group-label" style="margin-top:8px;">MM-PBSA / MM-GBSA Binding Free Energy</div>',
            unsafe_allow_html=True,
        )
        c1, c2 = st.columns(2)
        with c1:
            if gb:
                delta_clr = "metric-delta-neg" if gb[0] < 0 else "metric-delta-pos"
                delta_arr = "▼" if gb[0] < 0 else "▲"
                st.markdown(
                    f'<div class="metric-card">'
                    f'<div class="metric-value" style="color:#6366f1;">{gb[0]:.2f}'
                    f'<span class="metric-unit">kcal/mol</span></div>'
                    f'<div class="{delta_clr}">{delta_arr} ±{gb[1]:.2f} kcal/mol</div>'
                    f'<div class="metric-label">ΔG (MM-GBSA)<br>Generalized Born</div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )
        with c2:
            if pb:
                delta_clr = "metric-delta-neg" if pb[0] < 0 else "metric-delta-pos"
                delta_arr = "▼" if pb[0] < 0 else "▲"
                st.markdown(
                    f'<div class="metric-card">'
                    f'<div class="metric-value" style="color:#06b6d4;">{pb[0]:.2f}'
                    f'<span class="metric-unit">kcal/mol</span></div>'
                    f'<div class="{delta_clr}">{delta_arr} ±{pb[1]:.2f} kcal/mol</div>'
                    f'<div class="metric-label">ΔG (MM-PBSA)<br>Poisson-Boltzmann</div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )

        # Energy decomposition bar chart
        if _plotly_ok:
            dat_path = wpath("FINAL_RESULTS_MMPBSA_cMD.dat")
            gb_d, pb_d = core.parse_mmpbsa_components(dat_path)

            def _bar(title, comps, color):
                labels = list(comps.keys())
                vals   = [v if v is not None else 0.0 for v in comps.values()]
                fig = go.Figure(go.Bar(
                    x=labels, y=vals,
                    marker_color=[color if v <= 0 else "#E24B4A" for v in vals],
                    text=[f"{v:.2f}" for v in vals],
                    textposition="outside",
                ))
                fig.add_hline(y=0, line_width=1, line_dash="dot")
                fig.update_layout(
                    title=title, height=360,
                    yaxis_title="kcal/mol",
                    paper_bgcolor="rgba(0,0,0,0)",
                    plot_bgcolor="rgba(255,255,255,0.6)",
                    font=dict(family="Noto Sans, sans-serif", size=12),
                    xaxis=dict(gridcolor="rgba(99,102,241,0.08)"),
                    yaxis=dict(gridcolor="rgba(99,102,241,0.08)"),
                )
                return fig

            if any(v is not None for v in gb_d.values()):
                st.plotly_chart(_bar("MM-GBSA components", {
                    "ΔEVDW": gb_d["VDWAALS"], "ΔEele": gb_d["EEL"],
                    "ΔEGB": gb_d["EGB"], "ΔESURF": gb_d["ESURF"],
                    "ΔG total": gb_d["DELTA TOTAL"],
                }, "#8B6CE8"), use_container_width=True)

        st.divider()
        next_button(9, "Next → DBFE")

    log_expander("log_mmpbsa")


# ══════════════════════════════════════════════════════════════════════════════
# STEP 9 — DBFE (ask first)
# ══════════════════════════════════════════════════════════════════════════════
def page_dbfe():
    render_topbar("DBFE", 9)
    render_stepper(9)
    st.markdown('<div class="content-pad step-body">', unsafe_allow_html=True)
    section_header("DBFE — absolute binding free energy", "BAR-based absolute binding free energy calculation.", step_num=9)

    # Ask once
    if not st.session_state.get("dbfe_asked"):
        st.markdown("""
        **DBFE** uses the BAR estimator with a translational/rotational entropy correction (ΔG_TR),
        giving an absolute binding free energy — unlike MM-PBSA/GBSA.

        It requires additional computation (~10 min).
        """)

        c1, c2 = st.columns(2)
        with c1:
            if st.button("✅ Yes, run DBFE", type="primary", use_container_width=True):
                st.session_state["dbfe_asked"] = True
                st.session_state["dbfe_want"]  = True
                st.rerun()
        with c2:
            if st.button("⏭ Skip, go to download", use_container_width=True):
                st.session_state["dbfe_asked"] = True
                st.session_state["dbfe_want"]  = False
                go_step(10)
        return

    if not st.session_state.get("dbfe_want"):
        go_step(10)
        return

    # --- Run DBFE ---
    st.markdown("""
    **Thermodynamic cycle:**
    ```
    ΔG_bind = ΔG_inter + ΔG_std_state − ΔG_sym
    ```
    """)

    tab1, tab2, tab3 = st.tabs(["Step 1: Install", "Step 2: Prepare", "Step 3: Compute"])

    with tab1:
        if st.button("📦 Install DBFE package"):
            with st.spinner("Installing…"):
                rc, out = core.run_cmd([
                    sys.executable, "-m", "pip", "install", "-q",
                    "git+https://github.com/molecularmodelinglab/dbfe.git",
                    "pymbar>=4.0", "spyrmsd", "scikit-learn", "pyquaternion",
                ])
            if rc == 0:
                st.success("✅ DBFE installed!")
            else:
                st.error("Installation failed"); st.code(out)

    with tab2:
        c1, c2 = st.columns(2)
        with c1:
            use_lb   = st.checkbox("Use LB-PaCS-MD (sum.nc)", value=True)
            use_cmd2 = st.checkbox("Use cMD (md-cMD.dcd)", value=False)
            indep_ns = st.number_input("Independent MD per component (ns)", value=10.0)
        with c2:
            igb_folder = st.selectbox("MM-PBSA igb folder", ["2","5","1","7","8"])
            temp_K     = st.number_input("Temperature (K)", value=300)

        if st.button("▶ Prepare DBFE trajectories"):
            py = os.path.join(WD(), "run_dbfe_prep.py")
            with open(py, "w") as f:
                f.write(f"import os; os.chdir('{WD()}')\n"
                        f"use_lb={use_lb}\nuse_cmd={use_cmd2}\n"
                        f"indep_md_ns={indep_ns}\ntemperature_K={temp_K}\n"
                        f"igb_folder='{igb_folder}'\n"
                        f"print('DBFE prep — edit and run this script manually.')\n")
            st.info("Prep script written. Check log.")
            st.code(core.read_file(py))

    with tab3:
        std_conc  = st.number_input("Standard concentration (M)", value=1.0)
        n_equil   = st.slider("Equilibration fraction", 0.0, 0.5, 0.2)
        max_pairs = st.number_input("Max BAR frame pairs", value=2000)

        if st.button("▶ Compute DBFE"):
            py = os.path.join(WD(), "run_dbfe_bar.py")
            with open(py, "w") as f:
                f.write(f"import os; os.chdir('{WD()}')\n"
                        f"standard_conc_M={std_conc}\nn_equil_frac={n_equil}\n"
                        f"max_pairs={int(max_pairs)}\nprint('DBFE BAR stub — extend as needed.')\n")
            rc, out = core.run_cmd([sys.executable, py], cwd=WD())
            st.code(out)

        res_path = wpath("DBFE_results.json")
        if os.path.exists(res_path):
            st.markdown(
                '<div class="done-bar"><span class="done-icon">✅</span>'
                '<div><div class="done-text">DBFE results ready</div></div></div>',
                unsafe_allow_html=True,
            )
            results = json.loads(core.read_file(res_path))
            cols = st.columns(len(results)) if results else []
            for col, r in zip(cols, results):
                dg = r.get("dG_bind", 0)
                delta_clr = "metric-delta-neg" if dg < 0 else "metric-delta-pos"
                delta_arr = "▼" if dg < 0 else "▲"
                binding_txt = "favorable" if dg < 0 else "unfavorable"
                col.markdown(
                    f'<div class="metric-card">'
                    f'<div class="metric-value" style="color:#6366f1;">{dg:.2f}'
                    f'<span class="metric-unit">kcal/mol</span></div>'
                    f'<div class="{delta_clr}">{delta_arr} binding {binding_txt}</div>'
                    f'<div class="metric-label">ΔG_bind ({r.get("source","?")})</div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )
            st.session_state["dbfe_done"] = True

    st.divider()
    next_button(10, "Next → Download results")


# ══════════════════════════════════════════════════════════════════════════════
# STEP 10 — Download results
# ══════════════════════════════════════════════════════════════════════════════
def page_download():
    render_topbar("Download", 10)
    render_stepper(10)
    st.markdown('<div class="content-pad step-body">', unsafe_allow_html=True)
    section_header("Download results", "All generated files are listed below.", step_num=10)

    FILE_GROUPS = {
        "System Files": {
            "color": "#6366f1",
            "files": {
                "complex.top":       "Topology (solvated complex)",
                "complex.crd":       "Coordinates (solvated complex)",
                "complex.pdb":       "Complex PDB (dry)",
                "complex_leap.pdb":  "Complex PDB (solvated)",
                "host.pdb":          "Host PDB",
                "guest.pdb":         "Guest PDB",
                "guest.prep":        "Guest PREP (AmberTools)",
                "guest.frcmod":      "Guest FRCMOD",
                "last_frame.rst7":   "Restart after heating",
            },
        },
        "Trajectories": {
            "color": "#06b6d4",
            "files": {
                "sum.nc":            "LB-PaCS-MD trajectory (NetCDF)",
                "md.dcd":            "cMD trajectory (DCD)",
                "md-cMD.dcd":        "cMD processed trajectory",
            },
        },
        "Analysis Data": {
            "color": "#10b981",
            "files": {
                "dis_plot.dat":      "PaCS-MD distance vs cycle",
                "dis.dat":           "Host–guest COM distance",
                "rg.dat":            "Host radius of gyration",
                "rmsd.dat":          "RMSD data",
            },
        },
        "Energy Results": {
            "color": "#f59e0b",
            "files": {
                "FINAL_RESULTS_MMPBSA_LB.dat":  "MM-PBSA results (LB-PaCS-MD)",
                "FINAL_RESULTS_MMPBSA_cMD.dat": "MM-PBSA results (cMD)",
                "DBFE_results.json":             "DBFE results",
            },
        },
    }

    # Count all files
    all_files = {k: v for g in FILE_GROUPS.values() for k, v in g["files"].items()}
    found   = {k: wpath(k) for k in all_files if os.path.exists(wpath(k))}
    missing = [k for k in all_files if k not in found]
    total_mb = sum(os.path.getsize(p) for p in found.values()) / 1024 / 1024

    # ── Summary bar ───────────────────────────────────────────────────────────
    st.markdown(
        f'<div class="glass-card" style="display:flex;align-items:center;gap:24px;padding:14px 22px;margin-bottom:20px;">'
        f'<div style="text-align:center;"><div style="font-size:26px;font-weight:700;color:#6366f1;'
        f'font-family:\'JetBrains Mono\',monospace;">{len(found)}</div>'
        f'<div style="font-size:11px;color:var(--text-tertiary);margin-top:2px;">files ready</div></div>'
        f'<div style="text-align:center;"><div style="font-size:26px;font-weight:700;color:#06b6d4;'
        f'font-family:\'JetBrains Mono\',monospace;">{total_mb:.1f}</div>'
        f'<div style="font-size:11px;color:var(--text-tertiary);margin-top:2px;">MB total</div></div>'
        f'<div style="margin-left:auto;">',
        unsafe_allow_html=True,
    )

    # ZIP bundle button
    if found:
        import io, zipfile
        zip_buf = io.BytesIO()
        with zipfile.ZipFile(zip_buf, "w", zipfile.ZIP_DEFLATED) as zf:
            for fname, path in found.items():
                zf.write(path, fname)
        zip_buf.seek(0)
        st.download_button(
            "⬇ Download all as ZIP",
            data=zip_buf,
            file_name="dfdd_results.zip",
            mime="application/zip",
            type="primary",
            key="dl_zip_all",
        )

    st.markdown("</div></div>", unsafe_allow_html=True)

    # ── File groups ───────────────────────────────────────────────────────────
    for group_name, group_data in FILE_GROUPS.items():
        color = group_data["color"]
        files = group_data["files"]
        group_found = {k: v for k, v in files.items() if k in found}
        if not group_found:
            continue

        st.markdown(
            f'<div class="group-label" style="color:{color};">{group_name}</div>',
            unsafe_allow_html=True,
        )
        st.markdown(f'<div class="glass-card" style="padding:4px 18px;">', unsafe_allow_html=True)

        for fname, desc in files.items():
            if fname not in found:
                continue
            path = found[fname]
            mb   = os.path.getsize(path) / 1024 / 1024
            c1, c2, c3, c4 = st.columns([3, 5, 1.5, 1.2])
            with c1:
                st.markdown(
                    f'<div class="file-name" style="color:{color};padding:8px 0;">{fname}</div>',
                    unsafe_allow_html=True,
                )
            with c2:
                st.markdown(
                    f'<div class="file-desc" style="padding:8px 0;">{desc}</div>',
                    unsafe_allow_html=True,
                )
            with c3:
                st.markdown(
                    f'<div class="file-size" style="padding:8px 0;">{mb:.2f} MB</div>',
                    unsafe_allow_html=True,
                )
            with c4:
                with open(path, "rb") as f:
                    st.download_button(
                        "⬇", data=f, file_name=fname,
                        key=f"dl_{fname}",
                        use_container_width=True,
                    )

        st.markdown("</div>", unsafe_allow_html=True)

    if missing:
        with st.expander(f"⬜ {len(missing)} files not yet generated"):
            for m in missing:
                st.caption(f"— {m}  ·  {all_files[m]}")

    st.divider()
    st.subheader("🗜️ Download everything as ZIP")
    if st.button("Create ZIP bundle"):
        with st.spinner("Zipping…"):
            zip_path, added = core.create_results_zip(WD())
        st.success(f"ZIP ready: {len(added)} files, {core.file_mb(zip_path):.1f} MB")
        with open(zip_path, "rb") as f:
            st.download_button(
                "⬇ Download DFDD_results.zip",
                data=f,
                file_name="DFDD_results.zip",
                mime="application/zip",
            )


# ══════════════════════════════════════════════════════════════════════════════
# SIDEBAR — minimal nav + status
# ══════════════════════════════════════════════════════════════════════════════
with st.sidebar:
    cur_step = st.session_state["step"]

    # ── Logo + header ─────────────────────────────────────────────────────────
    st.markdown("""
    <div style="padding:18px 14px 14px; border-bottom:1px solid oklch(21% 0.055 274); margin-bottom:6px;">
      <div style="font-size:17px; font-weight:700; color:#fff; letter-spacing:-0.3px; margin-bottom:2px;">🧬 DFDD</div>
      <div style="font-size:10px; color:oklch(48% 0.04 274); line-height:1.4;">
        Cyclodextrin–Drug Binding<br>Free Energy Wizard
      </div>
    </div>
    """, unsafe_allow_html=True)

    # ── Phase nav groups ──────────────────────────────────────────────────────
    NAV_GROUPS = [
        ("Setup", [
            ("0", "Install", 0),
        ]),
        ("System Preparation", [
            ("1", "Host", 1),
            ("2", "Guest", 2),
            ("3", "Build & Solvate", 3),
            ("4", "Minimize", 4),
        ]),
        ("LB-PaCS-MD", [
            ("5", "LB-PaCS-MD", 5),
            ("6", "Analysis", 6),
        ]),
        ("cMD", [
            ("7", "cMD", 7),
            ("8", "MM-PBSA", 8),
            ("9", "DBFE", 9),
        ]),
        ("Download", [
            ("10", "Download", 10),
        ]),
    ]

    # Track which steps are done
    STEP_DONE = {
        0:  st.session_state.get("install_done", False),
        1:  bool(st.session_state.get("host_path")),
        2:  bool(st.session_state.get("guest_path")),
        3:  st.session_state.get("build_done", False),
        4:  st.session_state.get("min_done", False),
        5:  st.session_state.get("pacsmd_done", False),
        6:  st.session_state.get("pacsmd_done", False),
        7:  st.session_state.get("cmd_done", False),
        8:  st.session_state.get("mmpbsa_done", False),
        9:  st.session_state.get("dbfe_done", False),
        10: False,
    }

    for grp_label, steps in NAV_GROUPS:
        # Group label
        st.markdown(
            f'<div style="font-size:9px;font-weight:700;text-transform:uppercase;'
            f'letter-spacing:.1em;color:oklch(38% 0.04 274);padding:9px 9px 3px;">'
            f'{grp_label}</div>',
            unsafe_allow_html=True,
        )
        for num, label, idx in steps:
            is_cur  = cur_step == idx
            is_done = STEP_DONE.get(idx, False)
            pill_bg = "#6366f1" if is_cur else ("#10b981" if is_done else "oklch(21% 0.06 274)")
            pill_clr= "#fff" if (is_cur or is_done) else "oklch(55% 0.04 274)"
            pill_lbl= "✓" if is_done else num
            if st.button(
                f"  {pill_lbl}  {label}",
                key=f"nav_{idx}",
                type="primary" if is_cur else "secondary",
                use_container_width=True,
            ):
                go_step(idx)

    # ── Status panel ──────────────────────────────────────────────────────────
    st.markdown("""
    <div style="border-top:1px solid oklch(20% 0.055 274); margin-top:8px; padding:13px 14px 8px;">
      <div style="font-size:9px;font-weight:700;text-transform:uppercase;letter-spacing:.1em;
                  color:oklch(37% 0.04 274);margin-bottom:8px;">Status</div>
    </div>
    """, unsafe_allow_html=True)

    checks = [
        ("Host",     bool(st.session_state.get("host_path") and os.path.exists(st.session_state.get("host_path") or ""))),
        ("Guest",    bool(st.session_state.get("guest_path") and os.path.exists(st.session_state.get("guest_path") or ""))),
        ("Complex",  os.path.exists(wpath("complex.pdb"))),
        ("Topology", os.path.exists(wpath("complex.top"))),
        ("Minimized",os.path.exists(wpath("last_frame.rst7"))),
        ("PaCS-MD",  os.path.exists(wpath("sum.nc"))),
        ("cMD",      os.path.exists(wpath("md.dcd"))),
        ("MM-PBSA",  st.session_state.get("mmpbsa_done", False)),
    ]
    status_html = ""
    for lbl, ok in checks:
        dot_clr = "#10b981" if ok else "oklch(28% 0.04 274)"
        dot_shadow = "box-shadow:0 0 5px #10b98155;" if ok else ""
        status_html += (
            f'<div style="display:flex;align-items:center;gap:8px;padding:3px 14px;'
            f'font-size:11px;color:oklch(48% 0.03 274);">'
            f'<div style="width:5px;height:5px;border-radius:50%;background:{dot_clr};{dot_shadow}flex-shrink:0;"></div>'
            f'{lbl}</div>'
        )
    st.markdown(status_html, unsafe_allow_html=True)

    # ── Workspace ──────────────────────────────────────────────────────────────
    st.markdown('<div style="border-top:1px solid oklch(18% 0.05 274);padding:8px 14px 0;margin-top:8px;"></div>', unsafe_allow_html=True)
    new_wd = st.text_input("Workspace path", value=WD(), key="_wd_in", label_visibility="collapsed")
    if st.button("Set workspace", key="set_wd"):
        os.makedirs(new_wd, exist_ok=True)
        st.session_state["workdir"] = new_wd
        st.rerun()

    # ── Citation ───────────────────────────────────────────────────────────────
    st.markdown("""
    <div style="border-top:1px solid oklch(18% 0.05 274);padding:10px 14px;margin-top:8px;">
      <div style="font-size:9px;color:oklch(32% 0.04 274);line-height:1.55;">
        Hengphasatporn et al.<br>
        <em>J. Chem. Inf. Model.</em> 2026, <strong>66</strong>, 4, 1955–1963<br>
        <a href="https://doi.org/10.1021/acs.jcim.5c02852"
           style="color:oklch(46% 0.06 274);text-decoration:none;">
          doi:10.1021/acs.jcim.5c02852
        </a>
      </div>
    </div>
    """, unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# MAIN ROUTER
# ══════════════════════════════════════════════════════════════════════════════
step = st.session_state["step"]

if   step == 0:  page_install()
elif step == 1:  page_host()
elif step == 2:  page_guest()
elif step == 3:  page_build()
elif step == 4:  page_minimize()
elif step == 5:  page_pacsmd()
elif step == 6:  page_pacsmd_analysis()
elif step == 7:  page_cmd()
elif step == 8:  page_analysis()
elif step == 9:  page_dbfe()
elif step == 10: page_download()
