"""
app.py — DFDD Streamlit UI  (wizard / linear-flow rewrite)
All computation is delegated to core.py
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
    page_title="DFDD",
    page_icon="🧬",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── Global CSS ───────────────────────────────────────────────────────────────
st.markdown("""
<style>
/* ── Global font size boost ───────────────────────────────────────────────── */
html, body, [class*="css"] {
    font-size: 17px !important;
}
/* Streamlit main content text */
.stMarkdown p, .stMarkdown li, .stMarkdown td, .stMarkdown th,
.stText, .stCaption, label, .stSelectbox, .stNumberInput,
.stRadio label, .stCheckbox label, .stTextInput input,
.stSelectbox select, div[data-testid="stWidgetLabel"] {
    font-size: 1rem !important;
}
/* Sidebar text */
section[data-testid="stSidebar"] * {
    font-size: 0.97rem !important;
}
/* Primary buttons — green */
button[kind="primary"], .stButton > button[kind="primary"] {
    background-color: #1D9E75 !important;
    border-color: #1D9E75 !important;
    color: #ffffff !important;
    font-size: 1rem !important;
}
button[kind="primary"]:hover, .stButton > button[kind="primary"]:hover {
    background-color: #0F6E56 !important;
    border-color: #0F6E56 !important;
}
button[kind="primary"]:active, .stButton > button[kind="primary"]:active {
    background-color: #085041 !important;
    border-color: #085041 !important;
}
/* Secondary buttons */
button[kind="secondary"] { font-size: 1rem !important; }
/* Code blocks */
code, pre { font-size: 0.9rem !important; }

/* ── Progress stepper ─────────────────────────────────────────────────────── */
.stepper{display:flex;align-items:center;gap:0;margin-bottom:2rem;overflow-x:auto;padding:0.5rem 0}
.step-item{display:flex;flex-direction:column;align-items:center;flex:1;min-width:64px}
.step-circle{width:36px;height:36px;border-radius:50%;display:flex;align-items:center;
  justify-content:center;font-size:15px;font-weight:600;transition:all .3s}
.step-done  .step-circle{background:#1D9E75;color:#fff}
.step-active .step-circle{background:#1D9E75;color:#fff;box-shadow:0 0 0 4px #E1F5EE}
.step-todo  .step-circle{background:#f0f0f0;color:#999}
.step-label{font-size:12px;margin-top:5px;text-align:center;color:#666;max-width:72px}
.step-line{flex:1;height:2px;background:#e0e0e0;margin:0 2px;margin-bottom:20px}
.step-line.done{background:#1D9E75}

/* ── Waiting card ─────────────────────────────────────────────────────────── */
.wait-card{background:#f8fffe;border:1px solid #c7ede2;border-radius:12px;
  padding:2rem;text-align:center;margin:1rem 0}
.wait-title{font-size:1.6rem;font-weight:600;color:#0F6E56;margin-bottom:.5rem}
.wait-sub{color:#555;font-size:1.1rem}

/* ── Section header ───────────────────────────────────────────────────────── */
.sec-header{font-size:1.75rem;font-weight:700;color:#0F6E56;margin-bottom:.25rem}
.sec-sub{color:#666;font-size:1.05rem;margin-bottom:1.5rem}

/* ── Molecule card ────────────────────────────────────────────────────────── */
.mol-card{background:#f9f9f9;border:1px solid #e0e0e0;border-radius:10px;padding:1rem}

/* ── Choice card ──────────────────────────────────────────────────────────── */
.choice-card{border:2px solid #e0e0e0;border-radius:10px;padding:1.1rem;cursor:pointer;
  transition:all .2s;background:#fff;font-size:1rem}
.choice-card.selected{border-color:#1D9E75;background:#f0faf6}

/* ── Result metric ────────────────────────────────────────────────────────── */
.res-metric{background:#f0faf6;border:1px solid #c7ede2;border-radius:10px;
  padding:1.1rem 1.6rem;text-align:center}
.res-value{font-size:2rem;font-weight:700;color:#0F6E56}
.res-label{color:#555;font-size:1rem;margin-top:.3rem}
</style>
""", unsafe_allow_html=True)

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
    "detected_charge":   0,
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
    st.markdown("<div style='height:1.5rem'></div>", unsafe_allow_html=True)
    col = st.columns([2, 1, 2])[1]
    with col:
        if st.button(label, key=f"next_to_{next_step}{key_suffix}", type="primary",
                     use_container_width=True):
            go_step(next_step)


def py3dmol_html(pdb_str, width=680, height=420, side_view=False):
    """Render a PDB string with 3Dmol.js.
    side_view=True rotates the camera 90° around X so cyclodextrin
    hosts appear as a side/cone view instead of top-down.
    """
    rotate = "v.rotate(90, {x:1, y:0, z:0});" if side_view else ""
    return f"""
    <script src="https://3Dmol.org/build/3Dmol-min.js"></script>
    <div id="v3d" style="width:{width}px;height:{height}px;position:relative;border-radius:10px;overflow:hidden"></div>
    <script>
      var v = $3Dmol.createViewer(document.getElementById('v3d'),{{backgroundColor:'#f8f9fa'}});
      v.addModel(`{pdb_str}`,'pdb');
      v.setStyle({{}},{{stick:{{colorscheme:'grayCarbon',radius:0.2}}}});
      v.addStyle({{resn:'GST'}},{{stick:{{colorscheme:'cyanCarbon',radius:0.25}}}});
      v.zoomTo();
      {rotate}
      v.render();
    </script>"""

# ─── Step names for progress bar ──────────────────────────────────────────────
STEP_LABELS = [
    "Install",      # 0
    "Host",         # 1
    "Guest",        # 2
    "Build+Solvate",# 3
    "Min & Heat",   # 4
    "LB-PaCS-MD",   # 5
    "Analysis",     # 6
    "cMD",          # 7
    "MM-PBSA",      # 8
    "DBFE",         # 9
    "Download",     # 10
]

def render_stepper(current):
    """Render a horizontal step progress bar."""
    html = '<div class="stepper">'
    for i, label in enumerate(STEP_LABELS):
        if i < current:
            cls = "step-done"
            icon = "✓"
        elif i == current:
            cls = "step-active"
            icon = str(i + 1)
        else:
            cls = "step-todo"
            icon = str(i + 1)

        html += f'<div class="step-item {cls}"><div class="step-circle">{icon}</div><div class="step-label">{label}</div></div>'
        if i < len(STEP_LABELS) - 1:
            line_cls = "done" if i < current else ""
            html += f'<div class="step-line {line_cls}"></div>'

    html += "</div>"
    st.markdown(html, unsafe_allow_html=True)


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
    render_stepper(0)
    st.markdown('<div class="sec-header">🔧 Setting up environment</div>', unsafe_allow_html=True)
    st.markdown('<div class="sec-sub">Installing scientific packages. This runs automatically — please wait.</div>', unsafe_allow_html=True)

    # ── Already fully done this session ──────────────────────────────────────
    if st.session_state["install_done"]:
        st.success("✅ Environment ready!")
        next_button(1, "Next → Select host")
        return

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
    render_stepper(1)
    st.markdown('<div class="sec-header">🏗️ Select host</div>', unsafe_allow_html=True)
    st.markdown('<div class="sec-sub">Choose the cyclodextrin host. The 3D structure loads automatically.</div>', unsafe_allow_html=True)

    abbrevs = list(HOST_OPTIONS_MAP.keys())

    # Default selection
    prev = st.session_state.get("host_option_abbrev", abbrevs[0])
    if prev not in abbrevs:
        prev = abbrevs[0]

    # ── Single-row compact radio ──────────────────────────────────────────────
    selected = st.radio(
        "Host molecule",
        abbrevs,
        index=abbrevs.index(prev),
        horizontal=True,
        key="host_radio",
    )

    # Update session and clear preview cache if selection changed
    if selected != st.session_state.get("host_option_abbrev"):
        st.session_state["host_option_abbrev"] = selected
        st.session_state["host_option"] = HOST_FULL_NAMES[selected]
        # Clear prepared host if user switches to a different one
        if st.session_state.get("host_type") is not None:
            prev_key = HOST_OPTIONS_MAP.get(prev)
            new_key  = HOST_OPTIONS_MAP.get(selected)
            if prev_key != new_key:
                st.session_state["host_path"] = None
                st.session_state["host_type"] = None
    else:
        st.session_state["host_option_abbrev"] = selected
        st.session_state["host_option"] = HOST_FULL_NAMES[selected]

    # Full name description
    st.caption(HOST_FULL_NAMES[selected])

    # ── 3D preview ────────────────────────────────────────────────────────────
    prepared_path = st.session_state.get("host_path")
    if prepared_path and os.path.exists(prepared_path):
        preview_pdb   = core.read_file(prepared_path)
        preview_label = "**Prepared structure**"
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
        preview_label = f"**Preview — {selected}**"

    if preview_pdb:
        st.markdown(preview_label)
        st.components.v1.html(py3dmol_html(preview_pdb, 680, 420, side_view=True), height=430)
    else:
        st.info("3D preview unavailable — check internet connection.")

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
    render_stepper(2)
    st.markdown('<div class="sec-header">\U0001f9ea Prepare guest molecule</div>', unsafe_allow_html=True)
    st.markdown('<div class="sec-sub">Provide your guest ligand by SMILES, file upload, or draw with Ketcher.</div>', unsafe_allow_html=True)

    input_type = st.radio(
        "Input method",
        ["SMILES", "Draw (Ketcher)", "File upload (.pdb / .mol2)"],
        horizontal=True,
        index=["SMILES", "Draw (Ketcher)", "File upload (.pdb / .mol2)"].index(
            st.session_state.get("guest_input_type", "SMILES")
        ),
        key="guest_input_radio",
    )
    st.session_state["guest_input_type"] = input_type

    smiles_in     = ""
    uploaded_file = None

    # ── SMILES ────────────────────────────────────────────────────────────────
    if input_type == "SMILES":

        # Example guests
        EXAMPLES = {
            "Aspirin":      "CC(=O)OC1=CC=CC=C1C(=O)O",
            "Ibuprofen":    "CC(C)Cc1ccc(cc1)C(C)C(=O)O",
            "Naproxen":     "COc1ccc2cc(ccc2c1)C(C)C(=O)O",
            "Caffeine":     "Cn1cnc2c1c(=O)n(c(=O)n2C)C",
            "Glucose":      "OC[C@H]1OC(O)[C@H](O)[C@@H](O)[C@@H]1O",
            "Testosterone": "O=C1CC[C@H]2[C@@H]3CCc4cc(O)cc[C@@]4(C)[C@H]3CC[C@@]12C",
        }

        st.markdown("**Quick examples** — click to load:")
        ex_cols = st.columns(len(EXAMPLES))
        for col, (name, smi) in zip(ex_cols, EXAMPLES.items()):
            with col:
                if st.button(name, key=f"ex_{name}", use_container_width=True):
                    st.session_state["guest_smiles"] = smi
                    st.rerun()

        smiles_in = st.text_input(
            "SMILES string",
            value=st.session_state.get("guest_smiles", "CC(=O)OC1=CC=CC=C1C(=O)O"),
            help="Paste any valid SMILES or click an example above",
            key="guest_smiles_input",
        )
        if smiles_in:
            st.caption(f"`{smiles_in}`")

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
                pdb_raw = wpath("guest_raw.pdb")
                sdf_raw = wpath("guest_raw.sdf")
                detected, err = core.smiles_to_3d_pdb(smiles_in.strip(), pdb_raw, sdf_raw)
                if err:
                    st.error(f"❌ RDKit error: {err}")
                    st.stop()
                mol_in = sdf_raw if os.path.exists(sdf_raw) else pdb_raw
                log   += f"RDKit detected charge: {detected}\n"
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

            # Copy/convert to workspace PDB
            if mol_in.endswith(".pdb"):
                import shutil
                shutil.copy(mol_in, guest_pdb)
            else:
                core.run_cmd(["obabel", mol_in, "-O", guest_pdb], cwd=WD())

            # Run antechamber with AM1-BCC
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

            st.session_state["guest_path"]      = guest_pdb
            st.session_state["guest_smiles"]    = smiles_in or ""
            st.session_state["detected_charge"] = final_charge
            st.session_state["log_guest"]       = log

        st.success(f"✅ Guest ready!   Charge: **{final_charge}**   Method: AM1-BCC")
        gp = st.session_state.get("guest_path")
        if gp and os.path.exists(gp):
            pdb = core.read_file(gp)
            st.components.v1.html(py3dmol_html(pdb, 680, 340), height=350)
        next_button(3, "Next → Build complex & solvate", key_suffix="_new")

    if st.session_state.get("guest_path") and os.path.exists(st.session_state["guest_path"]):
        st.info(f"Guest already prepared: `{st.session_state['guest_path']}`")
        next_button(3, "Next → Build complex & solvate", key_suffix="_done")
    log_expander("log_guest")



# ══════════════════════════════════════════════════════════════════════════════
# STEP 3 — Build complex + solvation (steps 4+5 merged)
# ══════════════════════════════════════════════════════════════════════════════
def page_build():
    render_stepper(3)
    st.markdown('<div class="sec-header">🔗 Build complex & solvate</div>', unsafe_allow_html=True)
    st.markdown('<div class="sec-sub">Place guest above host cavity, then generate topology and solvated box.</div>', unsafe_allow_html=True)

    hp = st.session_state.get("host_path")
    gp = st.session_state.get("guest_path")

    c1, c2 = st.columns(2)
    with c1:
        st.info(f"**Host:** `{os.path.basename(hp) if hp else '—'}`")
    with c2:
        st.info(f"**Guest:** `{os.path.basename(gp) if gp else '—'}`")

    st.subheader("Complex geometry")
    distance = st.slider(
        "Guest initial offset along cavity axis (Å) — negative = placed above opening",
        -20, 20, -15
    )

    st.subheader("Solvation")
    col1, col2, col3 = st.columns(3)
    with col1:
        water_type = st.selectbox("Water model", ["TIP3P", "OPC"])
        box_buf    = st.slider("Box buffer (Å)", 5, 15, 5)
    with col2:
        unit_xy    = st.slider("Unit cell X/Y (Å)", 12, 25, 13)
        unit_z     = st.slider("Unit cell Z (Å)", 30, 50, 35)
    with col3:
        translate_z = st.slider("Z-translation (Å)", -20, 20, 0)

    water_ff  = "leaprc.water.tip3p" if water_type == "TIP3P" else "leaprc.water.opc"
    water_box = "TIP3PBOX"           if water_type == "TIP3P" else "OPCBOX"

    if st.button("▶ Build & Solvate", type="primary"):
        cx_out = wpath("complex.pdb")

        # --- Build complex ---
        with st.spinner("Building host–guest complex…"):
            ok, msg = core.build_host_guest_complex(hp, gp, distance, cx_out)
        st.session_state["log_complex"] = msg

        if not ok:
            st.error(f"❌ Build failed: {msg}")
            st.stop()
        st.success("✅ Complex built")

        # Show 3D
        pdb = core.read_file(cx_out)
        st.components.v1.html(py3dmol_html(pdb, 680, 380, side_view=True), height=390)

        # --- Topology ---
        with st.spinner("Running tleap (topology + solvation)…"):
            ht  = st.session_state.get("host_type", "BCD_DFT")
            hff = st.session_state.get("host_forcefield", "DFT")
            if hff == "GLYCAM06":
                core.insert_ter_records(cx_out)

            script = core.write_tleap_script(
                workdir=WD(),
                host_forcefield=hff,
                host_prep=st.session_state.get("host_prep", ""),
                host_frcmod=st.session_state.get("host_frcmod", ""),
                host_type=ht,
                water_ff=water_ff, water_box=water_box,
                box_buf=box_buf, unit_xy=unit_xy, unit_z=unit_z,
                translate_z=translate_z,
                cx_pdb=cx_out,
                out_top=wpath("complex.top"),
                out_crd=wpath("complex.crd"),
                out_pdb=wpath("complex_leap.pdb"),
            )
            rc, out = core.run_cmd(["tleap", "-f", script], cwd=WD())
        st.session_state["log_tleap"] = out

        if rc != 0:
            st.error("❌ tleap failed")
            log_expander("log_tleap")
            st.stop()

        st.session_state["build_done"] = True
        st.session_state["topo_done"]  = True
        st.success("✅ Topology & solvated box generated!")

        c1, c2, c3 = st.columns(3)
        for col, fname in zip([c1,c2,c3], ["complex.top","complex.crd","complex_leap.pdb"]):
            p = wpath(fname)
            with col:
                st.metric(fname, f"{core.file_mb(p):.2f} MB" if os.path.exists(p) else "—")

        next_button(4, "Next → Minimization & heating")

    if st.session_state.get("topo_done") and os.path.exists(wpath("complex.top")):
        st.info("Complex already built.")
        next_button(4, "Next → Minimization & heating")

    log_expander("log_tleap")


# ══════════════════════════════════════════════════════════════════════════════
# STEP 4 — Minimization & Heating  (waiting page)
# ══════════════════════════════════════════════════════════════════════════════
def page_minimize():
    render_stepper(4)
    st.markdown('<div class="sec-header">🔥 Minimization & heating</div>', unsafe_allow_html=True)
    st.markdown('<div class="sec-sub">Energy minimization, NVT heating 0→300 K, short equilibration.</div>', unsafe_allow_html=True)

    c1, c2 = st.columns(2)
    with c1:
        min_iters  = st.number_input("Max minimization steps", 100, 50000, 5000)
        heat_steps = st.number_input("Steps per heating stage (×6)", 1000, 50000, 10000)
    with c2:
        nvt_steps  = st.number_input("NVT steps", 10000, 500000, 50000)
        prod_steps = st.number_input("Restrained production steps", 10000, 500000, 100000)

    total_ns = (heat_steps * 6 + nvt_steps + prod_steps) * 2 / 1e6
    st.info(f"Estimated time: **{total_ns:.2f} ns**  (~1–2 min on GPU)")

    if st.session_state.get("min_done") and os.path.exists(wpath("last_frame.rst7")):
        st.success(f"✅ Already minimized — `last_frame.rst7` ({core.file_mb(wpath('last_frame.rst7')):.2f} MB)")
        next_button(5, "Next → LB-PaCS-MD")
        return

    if st.button("▶ Run minimization & heating", type="primary"):
        st.markdown("""
        <div class="wait-card">
            <div class="wait-title">⏳ Running OpenMM minimization + heating</div>
            <div class="wait-sub">This takes ~1–2 minutes on GPU. Please don't close this tab.</div>
        </div>
        """, unsafe_allow_html=True)

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
            st.success("✅ Minimization complete!  `last_frame.rst7` saved.")
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
    render_stepper(5)
    st.markdown('<div class="sec-header">🚀 LB-PaCS-MD sampling</div>', unsafe_allow_html=True)
    st.markdown('<div class="sec-sub">Configure and run the LB-PaCS-MD enhanced sampling cycles.</div>', unsafe_allow_html=True)

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

    steps_cycle = int(sim_time / (timestep / 1000))
    total_ns    = sim_time * cycle / 1000
    st.info(f"Steps / cycle: **{steps_cycle:,}**  |  Total: **{total_ns:.2f} ns**")

    if st.session_state.get("pacsmd_done") and os.path.exists(wpath("sum.nc")):
        st.success(f"✅ LB-PaCS-MD done — `sum.nc` ({core.file_mb(wpath('sum.nc')):.1f} MB)")
        next_button(6, "Next → PaCS-MD analysis")
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

        st.markdown("""
        <div class="wait-card">
            <div class="wait-title">🚀 Running LB-PaCS-MD</div>
            <div class="wait-sub">Enhanced sampling in progress. Each cycle selects candidates closest to the host cavity.<br>
            This takes ~12 min (40 cycles, Colab GPU). Please keep this tab open.</div>
        </div>
        """, unsafe_allow_html=True)

        progress = st.progress(0, text=f"Starting {cycle} LB-PaCS-MD cycles…")

        core.write_pacsmd_config(WD(), temperature, pressure, timestep, 1.0, steps_cycle, 100)
        rc, out = core.run_pacsmd(WD(), wpath("last_frame.rst7"), cycle, candi, host_sel, guest_sel)

        st.session_state["log_pacsmd"]    = out
        st.session_state["pacsmd_cycles"] = cycle
        st.session_state["pacsmd_candi"]  = candi

        if rc == 0:
            progress.progress(100, text="LB-PaCS-MD complete!")
            st.session_state["pacsmd_done"] = True
            st.success("✅ LB-PaCS-MD complete!")
            next_button(6, "Next → PaCS-MD analysis")
        else:
            progress.progress(100, text="Failed")
            st.error("❌ PaCS-Q failed")
            log_expander("log_pacsmd")

    log_expander("log_pacsmd")


# ══════════════════════════════════════════════════════════════════════════════
# STEP 6 — PaCS-MD analysis + optional extend
# ══════════════════════════════════════════════════════════════════════════════
def page_pacsmd_analysis():
    render_stepper(6)
    st.markdown('<div class="sec-header">📊 PaCS-MD analysis</div>', unsafe_allow_html=True)

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

        if _plotly_ok:
            fig = go.Figure(go.Scatter(
                x=list(range(1, len(dis) + 1)), y=dis.tolist(),
                mode="lines+markers",
                line=dict(color="#1D9E75", width=2),
                marker=dict(size=4),
            ))
            fig.add_hline(y=5, line_dash="dot", line_color="#E24B4A",
                          annotation_text="5 Å threshold")
            fig.update_layout(
                xaxis_title="Cycle", yaxis_title="COM Distance (Å)",
                title="Host–Guest COM Distance Profile",
                height=380, plot_bgcolor="white",
            )
            st.plotly_chart(fig, use_container_width=True)

        if last_d < 5:
            st.success(f"🎉 Guest complexed! Final distance = **{last_d:.1f} Å**")
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
                title="2D Free Energy Landscape", height=440
            )
            st.plotly_chart(fig2d, use_container_width=True)

    # --- Extend? ---
    st.divider()
    if last_d is None or last_d >= 5:
        st.subheader("🔄 Extend simulation?")
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

                st.markdown("""
                <div class="wait-card">
                    <div class="wait-title">🔄 Extending LB-PaCS-MD…</div>
                    <div class="wait-sub">Running additional cycles. Please wait.</div>
                </div>
                """, unsafe_allow_html=True)

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
        st.success("Guest is complexed. Proceeding to cMD.")
        next_button(7, "Next → Classical MD")

    log_expander("log_cv")


# ══════════════════════════════════════════════════════════════════════════════
# STEP 7 — Classical MD  (ask length + waiting page)
# ══════════════════════════════════════════════════════════════════════════════
def page_cmd():
    render_stepper(7)
    st.markdown('<div class="sec-header">🔬 Classical MD (NPT)</div>', unsafe_allow_html=True)
    st.markdown('<div class="sec-sub">Run unbiased NPT molecular dynamics from the best PaCS-MD frame.</div>', unsafe_allow_html=True)

    if st.session_state.get("cmd_done") and os.path.exists(wpath("md.dcd")):
        st.success(f"✅ cMD done — `md.dcd` ({core.file_mb(wpath('md.dcd')):.1f} MB)")
        next_button(8, "Next → Analysis & MM-PBSA")
        return

    c1, c2 = st.columns(2)
    with c1:
        length_ns   = st.number_input("Simulation length (ns)", 0.1, 100.0, 2.0, step=0.5)
        temperature = st.number_input("Temperature (K)", value=300.0)
    with c2:
        pressure    = st.number_input("Pressure (bar)", value=1.0)
        report_int  = st.number_input("Reporter interval (steps)", 1000, 50000, 5000)

    steps_est = int(length_ns * 1e6 / 2)
    st.info(f"{length_ns} ns ≈ **{steps_est:,}** steps at dt=2 fs")

    if st.button("▶ Run cMD", type="primary"):
        st.markdown(f"""
        <div class="wait-card">
            <div class="wait-title">🔬 Running {length_ns} ns cMD</div>
            <div class="wait-sub">
                NPT simulation in progress.<br>
                Estimated time: ~{length_ns*7:.0f}–{length_ns*15:.0f} min on Colab GPU.<br>
                Please keep this tab open.
            </div>
        </div>
        """, unsafe_allow_html=True)

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
            st.success("✅ cMD complete!")
            next_button(8, "Next → Analysis & MM-PBSA")
        else:
            progress.progress(100, text="Failed")
            st.error("❌ cMD failed")
            log_expander("log_cmd")

    log_expander("log_cmd")


# ══════════════════════════════════════════════════════════════════════════════
# STEP 8 — cMD Analysis + MM-PBSA/GBSA (auto-run all)
# ══════════════════════════════════════════════════════════════════════════════
def page_analysis():
    render_stepper(8)
    st.markdown('<div class="sec-header">📈 Analysis & binding energy</div>', unsafe_allow_html=True)
    st.markdown('<div class="sec-sub">RMSD · Rg · distance analysis and MM-PBSA/GBSA binding free energy — running automatically.</div>', unsafe_allow_html=True)

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
        st.success("✅ Trajectory analysis done")

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
            colors = ["#1D9E75", "#D85A30", "#378ADD"]
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
            fig.update_layout(height=300 * len(charts), showlegend=False,
                              plot_bgcolor="white")
            st.plotly_chart(fig, use_container_width=True)

    st.divider()

    # --- Auto-run MM-PBSA if not done ---
    if not st.session_state.get("mmpbsa_done"):
        st.subheader("⚡ MM-PBSA/GBSA binding energy")
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

        st.subheader("⚡ MM-PBSA/GBSA results")
        c1, c2 = st.columns(2)
        with c1:
            if gb:
                st.markdown(
                    f'<div class="res-metric"><div class="res-value">{gb[0]:.2f} kcal/mol</div>'
                    f'<div class="res-label">ΔG (MM-GBSA)  ±{gb[1]:.2f}</div></div>',
                    unsafe_allow_html=True
                )
        with c2:
            if pb:
                st.markdown(
                    f'<div class="res-metric"><div class="res-value">{pb[0]:.2f} kcal/mol</div>'
                    f'<div class="res-label">ΔG (MM-PBSA)  ±{pb[1]:.2f}</div></div>',
                    unsafe_allow_html=True
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
                fig.update_layout(title=title, height=360,
                                  yaxis_title="kcal/mol", plot_bgcolor="white")
                return fig

            if any(v is not None for v in gb_d.values()):
                st.plotly_chart(_bar("MM-GBSA components", {
                    "ΔEVDW": gb_d["VDWAALS"], "ΔEele": gb_d["EEL"],
                    "ΔEGB": gb_d["EGB"], "ΔESURF": gb_d["ESURF"],
                    "ΔG total": gb_d["DELTA TOTAL"],
                }, "#1D9E75"), use_container_width=True)

        st.divider()
        next_button(9, "Next → DBFE")

    log_expander("log_mmpbsa")


# ══════════════════════════════════════════════════════════════════════════════
# STEP 9 — DBFE (ask first)
# ══════════════════════════════════════════════════════════════════════════════
def page_dbfe():
    render_stepper(9)
    st.markdown('<div class="sec-header">🧮 DBFE — absolute binding free energy</div>', unsafe_allow_html=True)

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
            st.success("✅ DBFE results found!")
            results = json.loads(core.read_file(res_path))
            cols = st.columns(len(results)) if results else []
            for col, r in zip(cols, results):
                with col:
                    st.markdown(
                        f'<div class="res-metric">'
                        f'<div class="res-value">{r.get("dG_bind", 0):.2f}</div>'
                        f'<div class="res-label">ΔG_bind ({r.get("source","?")})<br>kcal/mol</div>'
                        f'</div>', unsafe_allow_html=True
                    )
            st.session_state["dbfe_done"] = True

    st.divider()
    next_button(10, "Next → Download results")


# ══════════════════════════════════════════════════════════════════════════════
# STEP 10 — Download results
# ══════════════════════════════════════════════════════════════════════════════
def page_download():
    render_stepper(10)
    st.markdown('<div class="sec-header">📦 Download results</div>', unsafe_allow_html=True)
    st.markdown('<div class="sec-sub">All generated files are listed below.</div>', unsafe_allow_html=True)

    FILE_DESC = {
        "complex.top":                   "Topology (solvated complex)",
        "complex.crd":                   "Coordinates (solvated complex)",
        "complex.pdb":                   "Complex PDB (dry)",
        "complex_leap.pdb":              "Complex PDB (solvated)",
        "host.pdb":                      "Host PDB",
        "guest.pdb":                     "Guest PDB",
        "guest.prep":                    "Guest PREP (AmberTools)",
        "guest.frcmod":                  "Guest FRCMOD",
        "last_frame.rst7":               "Restart after heating",
        "sum.nc":                        "LB-PaCS-MD trajectory (NetCDF)",
        "md.dcd":                        "cMD trajectory (DCD)",
        "md-cMD.dcd":                    "cMD processed trajectory",
        "dis_plot.dat":                  "PaCS-MD distance vs cycle",
        "dis.dat":                       "Host–guest COM distance",
        "rg.dat":                        "Host radius of gyration",
        "rmsd.dat":                      "RMSD data",
        "FINAL_RESULTS_MMPBSA_LB.dat":   "MM-PBSA results (LB-PaCS-MD)",
        "FINAL_RESULTS_MMPBSA_cMD.dat":  "MM-PBSA results (cMD)",
        "DBFE_results.json":             "DBFE results",
    }

    found   = {k: wpath(k) for k in FILE_DESC if os.path.exists(wpath(k))}
    missing = [k for k in FILE_DESC if k not in found]

    st.metric("Files ready", f"{len(found)} / {len(FILE_DESC)}")
    st.divider()

    for fname, path in found.items():
        c1, c2, c3 = st.columns([4, 1, 1])
        with c1:
            st.write(f"**{FILE_DESC[fname]}**  —  `{fname}`")
        with c2:
            st.caption(f"{core.file_mb(path):.2f} MB")
        with c3:
            with open(path, "rb") as f:
                st.download_button("⬇", data=f, file_name=fname, key=f"dl_{fname}")

    if missing:
        with st.expander(f"⬜ {len(missing)} files not yet generated"):
            for m in missing:
                st.caption(f"- {m}")

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
    st.markdown("## 🧬 DFDD")
    st.markdown(
        "Hengphasatporn et al., *JCIM* 2026  \n"
        "Cite this: *J. Chem. Inf. Model.* 2026, **66**, 4, 1955–1963  \n"
        "[https://doi.org/10.1021/acs.jcim.5c02852](https://doi.org/10.1021/acs.jcim.5c02852)"
    )

    st.divider()
    st.markdown("**Jump to step**")
    step_map = {
        "0 · Install":          0,
        "1 · Host":             1,
        "2 · Guest":            2,
        "3 · Build & Solvate":  3,
        "4 · Minimize":         4,
        "5 · LB-PaCS-MD":       5,
        "6 · PaCS-MD Analysis": 6,
        "7 · cMD":              7,
        "8 · Analysis + PBSA":  8,
        "9 · DBFE":             9,
        "10 · Download":        10,
    }
    for label, idx in step_map.items():
        is_cur = st.session_state["step"] == idx
        if st.button(label, key=f"nav_{idx}",
                     type="primary" if is_cur else "secondary",
                     use_container_width=True):
            go_step(idx)

    st.divider()
    st.markdown("**Status**")
    checks = [
        ("Host",     st.session_state.get("host_path") and os.path.exists(st.session_state.get("host_path") or "")),
        ("Guest",    st.session_state.get("guest_path") and os.path.exists(st.session_state.get("guest_path") or "")),
        ("Complex",  os.path.exists(wpath("complex.pdb"))),
        ("Topology", os.path.exists(wpath("complex.top"))),
        ("Minimized",os.path.exists(wpath("last_frame.rst7"))),
        ("PaCS-MD",  os.path.exists(wpath("sum.nc"))),
        ("cMD",      os.path.exists(wpath("md.dcd"))),
        ("MM-PBSA",  st.session_state.get("mmpbsa_done", False)),
    ]
    for label, ok in checks:
        st.markdown(f"{'✅' if ok else '⬜'} {label}")

    st.divider()
    new_wd = st.text_input("Workspace path", value=WD(), key="_wd_in")
    if st.button("Set workspace"):
        os.makedirs(new_wd, exist_ok=True)
        st.session_state["workdir"] = new_wd
        st.rerun()


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
