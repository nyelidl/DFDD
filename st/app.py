"""
app.py — DFDD Streamlit UI
All computation is delegated to core.py
"""

import streamlit as st
import os
import sys
import json
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

import core

# ─── Page Config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="DFDD — Dynamic Docking",
    page_icon="🧬",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── Session State Defaults ───────────────────────────────────────────────────
DEFAULTS = {
    "workdir":          os.path.expanduser("~/dfdd_workspace"),
    "host_path":        None,
    "host_prep":        None,
    "host_frcmod":      None,
    "host_forcefield":  None,
    "host_type":        None,
    "guest_path":       None,
    "guest_smiles":     None,
    "detected_charge":  0,
    "system_name":      "complex",
    "pacsmd_cycles":    40,
    "pacsmd_candi":     3,
    # logs
    "log_install": "", "log_host": "", "log_guest": "",
    "log_complex": "", "log_tleap": "", "log_min":   "",
    "log_pacsmd":  "", "log_cmd":   "", "log_cv":    "",
    "log_mmpbsa":  "",
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


def log_expander(key, label="📋 Log"):
    txt = st.session_state.get(key, "")
    if txt.strip():
        with st.expander(label):
            st.code(txt[-4000:])


def py3dmol_html(pdb_str, width=700, height=460):
    return f"""
    <script src="https://3Dmol.org/build/3Dmol-min.js"></script>
    <div id="v3d" style="width:{width}px;height:{height}px;position:relative;"></div>
    <script>
      var v = $3Dmol.createViewer(document.getElementById('v3d'),{{backgroundColor:'white'}});
      v.addModel(`{pdb_str}`,'pdb');
      v.setStyle({{}},{{stick:{{colorscheme:'grayCarbon',radius:0.2}}}});
      v.addStyle({{resn:'GST'}},{{stick:{{colorscheme:'cyanCarbon',radius:0.25}}}});
      v.zoomTo(); v.render();
    </script>"""


def metric_files(*fnames):
    cols = st.columns(len(fnames))
    for col, fname in zip(cols, fnames):
        p = wpath(fname)
        with col:
            st.metric(fname, f"{core.file_mb(p):.2f} MB" if os.path.exists(p) else "—")


# ─── Navigation ───────────────────────────────────────────────────────────────
PAGES = [
    "🏠  Overview",
    "⚙️   1 · Environment",
    "🏗️   2 · Host Preparation",
    "🧪   3 · Guest Preparation",
    "🔗   4 · Build Complex",
    "💧   5 · Topology & Solvation",
    "🔥   6 · Minimization & Heating",
    "🚀   7 · LB-PaCS-MD",
    "📊   8 · PaCS-MD Analysis",
    "🔬   9 · Classical MD",
    "📈  10 · cMD Analysis",
    "⚡  11 · MM-PBSA/GBSA",
    "🧮  12 · DBFE",
    "📦  13 · Download Results",
]

with st.sidebar:
    st.image("https://raw.githubusercontent.com/nyelidl/DFDD/main/Udo-san.gif", width=220)
    st.markdown("## DFDD Workflow")
    page = st.radio("Navigate", PAGES, label_visibility="collapsed")

    st.markdown("---")
    st.markdown(f"**Workspace**")
    new_wd = st.text_input("Path", value=WD(), key="_wd")
    if st.button("Set", key="_set_wd"):
        os.makedirs(new_wd, exist_ok=True)
        st.session_state["workdir"] = new_wd
        st.rerun()

    # Status badges
    st.markdown("---")
    st.markdown("**Status**")
    checks = [
        ("Host",    st.session_state["host_path"] and os.path.exists(st.session_state["host_path"] or "")),
        ("Guest",   st.session_state["guest_path"] and os.path.exists(st.session_state["guest_path"] or "")),
        ("Complex", os.path.exists(wpath("complex.pdb"))),
        ("Topology",os.path.exists(wpath("complex.top"))),
        ("Minimized",os.path.exists(wpath("last_frame.rst7"))),
        ("PaCS-MD", os.path.exists(wpath("sum.nc"))),
        ("cMD",     os.path.exists(wpath("md.dcd"))),
    ]
    for label, ok in checks:
        st.markdown(f"{'✅' if ok else '⬜'} {label}")

    st.markdown("---")
    st.caption("Hengphasatporn et al., *JCIM* 2026  \n[DOI](https://doi.org/10.1021/acs.jcim.5c02852)")


# ══════════════════════════════════════════════════════════════════════════════
# PAGE: Overview
# ══════════════════════════════════════════════════════════════════════════════
if page == "🏠  Overview":
    st.title("🧬 DFDD — Fully Dynamic Docking")
    st.markdown("**v1.4.2** | Hengphasatporn & Duan | University of Tsukuba, Japan")
    st.divider()

    c1, c2 = st.columns(2)
    with c1:
        st.markdown("""
### What is DFDD?
LB-PaCS-MD enhanced sampling for host–guest binding  
without requiring a fixed initial pose.

**Ligand preparation**
- AM1-BCC charges (GAFF2) via AmberTools
- pH-aware protonation via pKaNET

**Host support**
- Native β-CD · DM-β-CD · M-β-CD · HP-β-CD · 6-tetra-HP-β-CD

**Free-energy estimates**
- MM-GBSA · MM-PBSA · DBFE (with ΔG_TR)
""")
    with c2:
        st.markdown("""
### Typical Runtime (Colab GPU)

| Step | Time |
|------|------|
| System prep | ~1 min |
| Min + Heating | ~1 min |
| LB-PaCS-MD (40 cycles) | ~12 min |
| LB-PaCS-MD analysis | ~3 min |
| cMD (10 ns) | ~15 min |
| DBFE post-processing | ~10 min |
""")

    st.info("👈 Use the sidebar to navigate steps **in order**.")


# ══════════════════════════════════════════════════════════════════════════════
# PAGE 1: Environment
# ══════════════════════════════════════════════════════════════════════════════
elif page == "⚙️   1 · Environment":
    st.title("⚙️ Environment Check")

    st.markdown("### 🔍 Verify installed tools")
    if st.button("Check tools"):
        tools = core.check_tools()
        for tool, path in tools.items():
            if path:
                st.success(f"✓ `{tool}` → `{path}`")
            else:
                st.error(f"✗ `{tool}` not found")

    st.divider()
    st.markdown("### 📦 Install (Colab / first-time)")
    st.warning("Only needed once per Colab session. Assumes Miniforge is already installed.")

    if st.button("▶ Install all dependencies", type="primary"):
        cmds = [
            ([sys.executable, "-m", "pip", "install", "-q", "condacolab"], "condacolab"),
            (["bash", "-lc",
              "mamba install -n base -c conda-forge -y ambertools openbabel rdkit xtb 2>&1 | tail -8"],
             "AmberTools + RDKit + xtb"),
            (["bash", "-lc",
              "mamba install -n base -c conda-forge -y openff-toolkit nglview 2>&1 | tail -4"],
             "OpenFF + NGLView"),
            ([sys.executable, "-m", "pip", "install", "-q",
              "py3Dmol", "netCDF4", "cftime", "deeptime",
              "dimorphite_dl", "pkapredict", "PaCS-Q", "parmed"],
             "Python packages"),
        ]
        log = ""
        for cmd, desc in cmds:
            with st.spinner(f"📦 {desc}..."):
                rc, out = core.run_cmd(cmd, cwd=WD())
                log += f"\n{'='*40}\n{desc}\n{out}"
                if rc == 0:
                    st.success(f"✓ {desc}")
                else:
                    st.error(f"✗ {desc} (code {rc})")
        st.session_state["log_install"] = log

    log_expander("log_install", "📋 Install log")


# ══════════════════════════════════════════════════════════════════════════════
# PAGE 2: Host Preparation
# ══════════════════════════════════════════════════════════════════════════════
elif page == "🏗️   2 · Host Preparation":
    st.title("🏗️ Host Preparation")

    HOST_OPTIONS = ["Default β-CD (DFT)"] + list(core.GLYCAM_HOST_CONFIGS.keys())
    host_option = st.selectbox("Select host", HOST_OPTIONS)

    if host_option == "Default β-CD (DFT)":
        st.info("Downloads DFT-derived parameters from `github.com/nyelidl/host-guest`.")
    else:
        cfg = core.GLYCAM_HOST_CONFIGS[host_option]
        st.info(f"Type: **{cfg['type']}**  |  Template PDB: `{cfg['pdb']}`  |  GLYCAM-06 force field")

    if st.button("▶ Prepare Host", type="primary"):
        with st.spinner("Preparing host..."):
            if host_option == "Default β-CD (DFT)":
                result, log, err = core.prepare_host_dft(WD())
            else:
                result, log, err = core.prepare_host_glycam(host_option, WD())

        st.session_state["log_host"] = log

        if err:
            st.error(err)
        else:
            for k, v in result.items():
                st.session_state[k] = v
            st.success(f"✅ Host ready: `{result['host_path']}`")

    # Display
    hp = st.session_state.get("host_path")
    if hp and os.path.exists(hp):
        c1, c2 = st.columns([1, 1])
        with c1:
            st.info(f"""
**Type:** `{st.session_state['host_type']}`  
**PDB:** `{hp}`  
**Force field:** `{st.session_state['host_forcefield']}`  
**PREP:** `{st.session_state['host_prep']}`  
**FRCMOD:** `{st.session_state['host_frcmod']}`
""")
        with c2:
            pdb = core.read_file(hp)
            st.components.v1.html(py3dmol_html(pdb, 430, 360), height=370)

    log_expander("log_host")


# ══════════════════════════════════════════════════════════════════════════════
# PAGE 3: Guest Preparation
# ══════════════════════════════════════════════════════════════════════════════
elif page == "🧪   3 · Guest Preparation":
    st.title("🧪 Guest Preparation")

    input_type  = st.radio("Input type", ["SMILES", "File upload"], horizontal=True)
    output_name = st.text_input("Guest name (residue prefix)", value="guest")
    target_pH   = st.slider("Target pH (for charge detection)", 2.0, 12.0, 7.4, 0.1)

    smiles_in     = ""
    uploaded_file = None
    if input_type == "SMILES":
        smiles_in = st.text_input("SMILES", value="CC(=O)OC1=CC=CC=C1C(=O)O",
                                   help="Default: Aspirin")
    else:
        uploaded_file = st.file_uploader("Upload (.pdb / .mol2 / .sdf)",
                                          type=["pdb", "mol2", "sdf"])

    c1, c2 = st.columns(2)
    with c1:
        auto_charge = st.checkbox("Auto-detect charge via RDKit", value=True)
    with c2:
        manual_charge = st.number_input("Manual charge override", -10, 10, 0,
                                        disabled=auto_charge)
    charge_method = st.selectbox("Charge method", ["bcc (AM1-BCC)", "gas (Gasteiger)"])
    charge_flag   = "bcc" if charge_method.startswith("bcc") else "gas"

    if st.button("▶ Prepare Guest", type="primary"):
        log = ""
        with st.spinner("Preparing guest..."):

            # Handle file upload
            if input_type == "File upload" and uploaded_file:
                ext  = os.path.splitext(uploaded_file.name)[1].lower()
                dest = wpath(uploaded_file.name)
                with open(dest, "wb") as f:
                    f.write(uploaded_file.read())
                # Convert to SDF via obabel
                sdf_tmp = dest + "_ob.sdf"
                rc_ob, ob_out = core.run_cmd(["obabel", dest, "-O", sdf_tmp], cwd=WD())
                log += ob_out
                mol_in = sdf_tmp if (rc_ob == 0 and os.path.exists(sdf_tmp)) else dest
                smiles_in = None
            else:
                mol_in = None

            # Build 3D from SMILES
            if smiles_in:
                pdb_raw = wpath("guest_raw.pdb")
                sdf_raw = wpath("guest_raw.sdf")
                detected, err = core.smiles_to_3d_pdb(smiles_in, pdb_raw, sdf_raw)
                if err:
                    st.error(f"RDKit error: {err}"); st.stop()
                mol_in = sdf_raw if os.path.exists(sdf_raw) else pdb_raw
                log += f"RDKit charge: {detected}\n"
            else:
                detected = 0

            final_charge = detected if auto_charge else manual_charge

            # Antechamber
            prep_out   = wpath(f"{output_name}.prep")
            frcmod_out = wpath(f"{output_name}.frcmod")
            ok, ac_log = core.run_antechamber(
                mol_in, prep_out, frcmod_out, final_charge, WD(),
                charge_method=charge_flag
            )
            log += ac_log

            if not ok:
                st.error("Antechamber failed"); st.session_state["log_guest"] = log
                st.stop()

            # Guest PDB
            guest_pdb = wpath(f"{output_name}.pdb")
            if mol_in.endswith(".pdb"):
                import shutil
                shutil.copy(mol_in, guest_pdb)
            else:
                rc_ob2, _ = core.run_cmd(["obabel", mol_in, "-O", guest_pdb], cwd=WD())

            st.session_state["guest_path"]      = guest_pdb
            st.session_state["guest_smiles"]    = smiles_in or ""
            st.session_state["detected_charge"] = final_charge
            st.session_state["log_guest"]       = log

        st.success(f"✅ Guest ready: `{guest_pdb}`")
        st.info(f"Charge: **{final_charge}**  |  PREP: `{prep_out}`  |  FRCMOD: `{frcmod_out}`")

    gp = st.session_state.get("guest_path")
    if gp and os.path.exists(gp):
        pdb = core.read_file(gp)
        st.components.v1.html(py3dmol_html(pdb, 450, 340), height=350)

    log_expander("log_guest")


# ══════════════════════════════════════════════════════════════════════════════
# PAGE 4: Build Complex
# ══════════════════════════════════════════════════════════════════════════════
elif page == "🔗   4 · Build Complex":
    st.title("🔗 Build Host–Guest Complex")

    hp = st.session_state.get("host_path")
    gp = st.session_state.get("guest_path")
    if not (hp and os.path.exists(hp)):
        st.warning("⚠️ Complete Step 2 first."); st.stop()
    if not (gp and os.path.exists(gp)):
        st.warning("⚠️ Complete Step 3 first."); st.stop()

    st.info(f"Host: `{hp}`  |  Guest: `{gp}`")
    distance = st.slider(
        "Guest initial offset along cavity axis (Å)  "
        "— negative = guest placed above host opening",
        -20, 20, -15
    )

    if st.button("▶ Build Complex", type="primary"):
        cx_out = wpath("complex.pdb")
        with st.spinner("Building complex..."):
            ok, msg = core.build_host_guest_complex(hp, gp, distance, cx_out)
        st.session_state["log_complex"] = msg
        if ok:
            st.success(f"✅ {msg}")
        else:
            st.error(f"Failed: {msg}")

    cx_path = wpath("complex.pdb")
    if os.path.exists(cx_path):
        pdb = core.read_file(cx_path)
        st.markdown("**3D view — host (gray) + guest (cyan)**")
        st.components.v1.html(py3dmol_html(pdb, 680, 460), height=470)

    log_expander("log_complex")


# ══════════════════════════════════════════════════════════════════════════════
# PAGE 5: Topology & Solvation
# ══════════════════════════════════════════════════════════════════════════════
elif page == "💧   5 · Topology & Solvation":
    st.title("💧 Topology & Solvation (tleap)")

    if not os.path.exists(wpath("complex.pdb")):
        st.warning("⚠️ Complete Step 4 first."); st.stop()

    c1, c2, c3 = st.columns(3)
    with c1:
        water_type  = st.selectbox("Water model", ["TIP3P", "OPC"])
        box_buf     = st.slider("Box buffer (Å)", 5, 15, 5)
    with c2:
        unit_xy     = st.slider("Unit cell X/Y (Å)", 12, 25, 13)
        unit_z      = st.slider("Unit cell Z (Å)", 30, 50, 35)
    with c3:
        translate_z = st.slider("Z-translation (Å)", -20, 20, 0)

    water_ff  = "leaprc.water.tip3p" if water_type == "TIP3P" else "leaprc.water.opc"
    water_box = "TIP3PBOX"           if water_type == "TIP3P" else "OPCBOX"

    with st.expander("ℹ️ Parameter guide"):
        st.markdown("""
| Parameter | Default | When to change |
|-----------|---------|----------------|
| Box buffer | 5 Å | ↑ 10 Å for pull/APR sims |
| Unit cell Z | 35 Å | ↑ 40–50 Å for long pull |
| Z translation | 0 | 10 Å to offset complex toward +z |
""")

    if st.button("▶ Generate Topology", type="primary"):
        cx_pdb = wpath("complex.pdb")
        ht = st.session_state.get("host_type", "BCD_DFT")
        hff = st.session_state.get("host_forcefield", "DFT")
        if hff == "GLYCAM06":
            core.insert_ter_records(cx_pdb)

        script = core.write_tleap_script(
            workdir=WD(),
            host_forcefield=hff,
            host_prep=st.session_state.get("host_prep", ""),
            host_frcmod=st.session_state.get("host_frcmod", ""),
            host_type=ht,
            water_ff=water_ff, water_box=water_box,
            box_buf=box_buf, unit_xy=unit_xy, unit_z=unit_z,
            translate_z=translate_z,
            cx_pdb=cx_pdb,
            out_top=wpath("complex.top"),
            out_crd=wpath("complex.crd"),
            out_pdb=wpath("complex_leap.pdb"),
        )
        with st.spinner("Running tleap..."):
            rc, out = core.run_cmd(["tleap", "-f", script], cwd=WD())
        st.session_state["log_tleap"] = out
        if rc != 0:
            st.error("tleap failed"); log_expander("log_tleap"); st.stop()
        st.success("✅ Topology generated!")

    if os.path.exists(wpath("complex.top")):
        metric_files("complex.top", "complex.crd", "complex_leap.pdb")

    log_expander("log_tleap")


# ══════════════════════════════════════════════════════════════════════════════
# PAGE 6: Minimization & Heating
# ══════════════════════════════════════════════════════════════════════════════
elif page == "🔥   6 · Minimization & Heating":
    st.title("🔥 Minimization & Heating")

    if not os.path.exists(wpath("complex.top")):
        st.warning("⚠️ Complete Step 5 first."); st.stop()

    c1, c2 = st.columns(2)
    with c1:
        min_iters  = st.number_input("Max minimization steps", 100, 50000, 5000)
        heat_steps = st.number_input("Steps per heating stage (6 stages)", 1000, 50000, 10000)
    with c2:
        nvt_steps  = st.number_input("NVT equilibration steps", 10000, 500000, 50000,
                                     help="50 000 steps = 100 ps at dt=2 fs")
        prod_steps = st.number_input("Restrained production steps", 10000, 500000, 100000,
                                     help="100 000 steps = 200 ps")

    st.info(f"Total time: "
            f"{(heat_steps*6 + nvt_steps + prod_steps)*2/1e6:.2f} ns")

    if st.button("▶ Run Minimization & Heating", type="primary"):
        with st.spinner("Running OpenMM minimization + heating (~1–2 min)..."):
            ok, out = core.run_minimize_heat(
                WD(),
                wpath("complex.top"),
                wpath("complex.crd"),
                wpath("last_frame.rst7"),
                min_iters=min_iters,
                heat_steps=heat_steps,
                nvt_steps=nvt_steps,
                prod_steps=prod_steps,
            )
        st.session_state["log_min"] = out
        if ok:
            st.success("✅ Done. `last_frame.rst7` saved.")
        else:
            st.error("Failed"); log_expander("log_min"); st.stop()

    rst7 = wpath("last_frame.rst7")
    if os.path.exists(rst7):
        st.success(f"✓ `last_frame.rst7` exists ({core.file_mb(rst7):.2f} MB)")

    log_expander("log_min")


# ══════════════════════════════════════════════════════════════════════════════
# PAGE 7: LB-PaCS-MD
# ══════════════════════════════════════════════════════════════════════════════
elif page == "🚀   7 · LB-PaCS-MD":
    st.title("🚀 LB-PaCS-MD Enhanced Sampling")

    rst7 = wpath("last_frame.rst7")
    if not os.path.exists(rst7):
        st.warning("⚠️ Complete Step 6 first."); st.stop()

    c1, c2, c3 = st.columns(3)
    with c1:
        cycle    = st.slider("Cycles", 2, 100, 40)
        candi    = st.slider("Candidates / cycle", 2, 10, 3)
    with c2:
        sim_time = st.slider("Simulation time / cycle (ps)", 1, 100, 10)
        timestep = st.slider("Time step (fs)", 1, 4, 1)
    with c3:
        temperature = st.number_input("Temperature (K)", value=300.0)
        pressure    = st.number_input("Pressure (bar)", value=1.0)

    host_type = st.session_state.get("host_type", "BCD_DFT")
    host_sel  = core.PACSMD_HOST_SEL.get(host_type, "resid 1-7")
    guest_sel = "resname GST"

    steps_cycle = int(sim_time / (timestep / 1000))
    st.info(
        f"Host sel: `{host_sel}`  |  Guest sel: `{guest_sel}`  |  "
        f"Steps/cycle: **{steps_cycle}**  |  "
        f"Total: **{sim_time * cycle / 1000:.2f} ns**"
    )

    if st.button("▶ Run LB-PaCS-MD", type="primary"):
        core.write_pacsmd_config(
            WD(), temperature, pressure, timestep, 1.0, steps_cycle, 100
        )
        with st.spinner(f"Running {cycle} cycles ({sim_time*cycle/1000:.2f} ns)..."):
            rc, out = core.run_pacsmd(WD(), rst7, cycle, candi, host_sel, guest_sel)

        st.session_state["log_pacsmd"] = out
        st.session_state["pacsmd_cycles"] = cycle
        st.session_state["pacsmd_candi"]  = candi

        if rc == 0:
            st.success("✅ LB-PaCS-MD complete!")
        else:
            st.error("PaCS-Q failed"); log_expander("log_pacsmd"); st.stop()

    st.divider()
    st.markdown("### 🔄 Extend Simulation")
    ext_cycle = st.slider("Extend to total cycle", 5, 200, 70)
    if st.button("▶ Extend"):
        core.write_pacsmd_config(
            WD(), temperature, pressure, timestep, 1.0, steps_cycle, 100
        )
        with st.spinner("Extending..."):
            rc, out = core.run_pacsmd(
                WD(), rst7,
                ext_cycle,
                st.session_state.get("pacsmd_candi", candi),
                host_sel, guest_sel, rerun=True
            )
        st.session_state["log_pacsmd"] += "\n" + out
        if rc == 0:
            st.success(f"✅ Extended to {ext_cycle} cycles!")
        else:
            st.error("Extension failed")

    if os.path.exists(wpath("sum.nc")):
        st.success(f"✓ `sum.nc` ({core.file_mb(wpath('sum.nc')):.1f} MB)")

    log_expander("log_pacsmd")


# ══════════════════════════════════════════════════════════════════════════════
# PAGE 8: PaCS-MD Analysis
# ══════════════════════════════════════════════════════════════════════════════
elif page == "📊   8 · PaCS-MD Analysis":
    st.title("📊 PaCS-MD Analysis")

    if not os.path.exists(wpath("sum.nc")):
        st.warning("⚠️ Complete Step 7 first."); st.stop()

    # Distance profile
    dis_dat = wpath("dis_plot.dat")
    st.markdown("### 📉 Distance profile (COM distance vs cycle)")
    if os.path.exists(dis_dat):
        df = pd.read_csv(dis_dat, sep=r"\s+", header=None)
        dis = df.iloc[:, 0].values
        fig = go.Figure(go.Scatter(
            x=list(range(1, len(dis)+1)), y=dis,
            mode="lines", line=dict(color="#4C78A8", width=2)
        ))
        fig.update_layout(
            xaxis_title="Cycle", yaxis_title="COM Distance (Å)",
            title="LB-PaCS-MD Distance Profile", height=380
        )
        st.plotly_chart(fig, use_container_width=True)
        last_d = dis[-1]
        if last_d < 5:
            st.success(f"🎉 Guest complexed (distance = {last_d:.1f} Å)")
        elif last_d < 10:
            st.info(f"Guest approaching cavity ({last_d:.1f} Å)")
        else:
            st.warning(f"Guest not yet complexed ({last_d:.1f} Å) — extend simulation")
    else:
        st.info("`dis_plot.dat` not found. Generated automatically by pacs_q_md.")

    st.divider()
    st.markdown("### 🔬 2D Free Energy Landscape (CV analysis via cpptraj)")

    c1, c2 = st.columns(2)
    with c1:
        target_cycle = st.number_input(
            "Total cycles to analyse",
            1, 200, st.session_state.get("pacsmd_cycles", 40)
        )
    with c2:
        candi_n = st.number_input(
            "Candidates per cycle",
            1, 20, st.session_state.get("pacsmd_candi", 3)
        )

    host_type = st.session_state.get("host_type", "BCD_DFT")
    host_mask = core.HOST_SEL_MAP.get(host_type, ":1-7")

    if st.button("▶ Run CV Analysis (cpptraj)"):
        with st.spinner("Running cpptraj..."):
            rc, out = core.run_cpptraj_cv(
                WD(), wpath("complex.top"),
                int(target_cycle), int(candi_n),
                host_mask, ":GST"
            )
        st.session_state["log_cv"] = out
        if rc != 0:
            st.error("cpptraj failed"); log_expander("log_cv"); st.stop()
        st.success("✅ CV analysis complete!")

    dis_path = wpath("dis.dat")
    rg_path  = wpath("rg.dat")
    if os.path.exists(dis_path) and os.path.exists(rg_path):
        dis_df = pd.read_csv(dis_path, sep=r"\s+", comment="#")
        rg_df  = pd.read_csv(rg_path,  sep=r"\s+", comment="#")
        dis_arr = dis_df.iloc[:, 1].values
        rg_arr  = rg_df.iloc[:, 2].values

        fig2d = go.Figure(go.Histogram2dContour(
            x=dis_arr, y=rg_arr,
            colorscale="Jet",
            contours_coloring="fill",
            ncontours=20,
        ))
        fig2d.update_layout(
            xaxis_title="Host–Guest Distance (Å)",
            yaxis_title="Host Rg (Å)",
            title="2D Free Energy Landscape",
            height=460
        )
        st.plotly_chart(fig2d, use_container_width=True)

    log_expander("log_cv")


# ══════════════════════════════════════════════════════════════════════════════
# PAGE 9: Classical MD
# ══════════════════════════════════════════════════════════════════════════════
elif page == "🔬   9 · Classical MD":
    st.title("🔬 Classical MD (NPT)")

    sum_nc = wpath("sum.nc")
    if not os.path.exists(sum_nc):
        st.warning("⚠️ Complete Step 7 first."); st.stop()

    c1, c2 = st.columns(2)
    with c1:
        length_ns   = st.number_input("Length (ns)", 0.1, 100.0, 2.0)
        temperature = st.number_input("Temperature (K)", value=300.0)
        pressure    = st.number_input("Pressure (bar)", value=1.0)
    with c2:
        report_int  = st.number_input("Report interval (steps)", 1000, 50000, 5000)
        traj_int    = st.number_input("Trajectory interval (steps)", 1000, 50000, 5000)

    st.info(f"{length_ns} ns  ≈  {int(length_ns*1e6/2):,} steps at dt=2 fs")

    if st.button("▶ Run cMD", type="primary"):
        with st.spinner("Extracting last PaCS-MD frame..."):
            core.extract_last_rst_from_pacsmd(
                WD(), wpath("complex.top"), sum_nc
            )
        rst = wpath("last.rst")
        if not os.path.exists(rst):
            st.error("`last.rst` not created"); st.stop()

        with st.spinner(f"Running {length_ns} ns cMD..."):
            ok, out = core.run_cmd_simulation(
                WD(),
                wpath("complex.top"), rst,
                wpath("md.dcd"),
                length_ns=length_ns,
                temperature=temperature,
                pressure=pressure,
                traj_int=int(traj_int),
                report_int=int(report_int),
            )
        st.session_state["log_cmd"] = out
        if ok:
            st.success("✅ cMD complete!")
        else:
            st.error("cMD failed"); log_expander("log_cmd"); st.stop()

    if os.path.exists(wpath("md.dcd")):
        st.success(f"✓ `md.dcd` ({core.file_mb(wpath('md.dcd')):.1f} MB)")

    log_expander("log_cmd")


# ══════════════════════════════════════════════════════════════════════════════
# PAGE 10: cMD Analysis
# ══════════════════════════════════════════════════════════════════════════════
elif page == "📈  10 · cMD Analysis":
    st.title("📈 cMD Analysis — RMSD · Rg · Distance")

    dcd = wpath("md.dcd")
    if not os.path.exists(dcd):
        st.warning("⚠️ Complete Step 9 first."); st.stop()

    host_type = st.session_state.get("host_type", "BCD_DFT")
    host_mask = core.HOST_SEL_MAP.get(host_type, ":1-7")

    st.info(f"Host mask: `{host_mask}`  |  Guest mask: `:GST`")

    if st.button("▶ Run cpptraj Analysis"):
        with st.spinner("Analysing..."):
            rc, out = core.run_cpptraj_cmd_analysis(
                WD(), wpath("complex.top"), dcd,
                wpath("complex.crd"),
                host_mask, ":GST"
            )
        if rc != 0:
            st.error("cpptraj failed"); st.code(out[-2000:]); st.stop()
        st.success("✅ Analysis complete!")

    # Plots
    plot_cfg = [
        ("rmsd.dat", 1, "RMSD (Å)",        "RMSD over time"),
        ("rg.dat",   2, "Rg (Å)",           "Radius of Gyration"),
        ("dis.dat",  1, "Distance (Å)",     "Host–Guest COM Distance"),
    ]
    charts = []
    for fname, col_idx, ylabel, title in plot_cfg:
        fpath = wpath(fname)
        if os.path.exists(fpath):
            df = pd.read_csv(fpath, sep=r"\s+", comment="#")
            charts.append((df.iloc[:,0].values, df.iloc[:,col_idx].values, ylabel, title))

    if charts:
        fig = make_subplots(
            rows=len(charts), cols=1,
            subplot_titles=[c[3] for c in charts],
            vertical_spacing=0.08,
        )
        colors = ["#4C78A8", "#F58518", "#E45756"]
        for i, (x, y, ylabel, _) in enumerate(charts, 1):
            fig.add_trace(
                go.Scatter(x=x, y=y, mode="lines",
                           line=dict(color=colors[i-1], width=1.5)),
                row=i, col=1
            )
            fig.update_yaxes(title_text=ylabel, row=i, col=1)
            fig.update_xaxes(title_text="Frame", row=i, col=1)

        fig.update_layout(height=320*len(charts), showlegend=False)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Run the analysis above to see plots.")


# ══════════════════════════════════════════════════════════════════════════════
# PAGE 11: MM-PBSA/GBSA
# ══════════════════════════════════════════════════════════════════════════════
elif page == "⚡  11 · MM-PBSA/GBSA":
    st.title("⚡ MM-PBSA/GBSA Binding Energy")

    top = wpath("complex.top")
    traj_options = {}
    for label, fname in [("LB-PaCS-MD (sum.nc)", "sum.nc"), ("cMD (md.dcd)", "md.dcd")]:
        if os.path.exists(wpath(fname)):
            traj_options[label] = wpath(fname)

    if not traj_options:
        st.warning("⚠️ No trajectory files found. Complete Steps 7 or 9."); st.stop()

    traj_label = st.selectbox("Trajectory source", list(traj_options.keys()))
    traj_file  = traj_options[traj_label]
    run_label  = "LB" if "sum" in traj_label else "cMD"

    c1, c2 = st.columns(2)
    with c1:
        n_frames  = st.slider("Last N frames to analyse", 5, 100, 10)
        igb_val   = st.selectbox("GB model (igb)", ["2", "5", "1", "7", "8"])
    with c2:
        salt_conc = st.text_input("Salt concentration (M)", "0")
        do_pb     = st.checkbox("Also run MM-PBSA", value=True)

    if st.button("▶ Run MM-PBSA/GBSA", type="primary"):
        with st.spinner("Running ante-MMPBSA + MMPBSA.py..."):
            ok, log, gb, pb = core.run_mmpbsa(
                WD(), top, traj_file, n_frames,
                igb_val, salt_conc, do_pb, label=run_label
            )
        st.session_state["log_mmpbsa"] = log

        if not ok:
            st.error("MMPBSA.py failed"); log_expander("log_mmpbsa"); st.stop()

        st.success("✅ Analysis complete!")

        # Results metrics
        c1, c2 = st.columns(2)
        with c1:
            if gb:
                st.metric("ΔG (MM-GBSA)", f"{gb[0]:.2f} ± {gb[1]:.2f} kcal/mol")
        with c2:
            if pb:
                st.metric("ΔG (MM-PBSA)", f"{pb[0]:.2f} ± {pb[1]:.2f} kcal/mol")

        # Bar chart — energy decomposition
        dat_path = wpath(f"FINAL_RESULTS_MMPBSA_{run_label}.dat")
        gb_d, pb_d = core.parse_mmpbsa_components(dat_path)

        def _bar_chart(title, components, colors):
            labels = list(components.keys())
            vals   = [v if v is not None else 0.0 for v in components.values()]
            fig = go.Figure(go.Bar(
                x=labels, y=vals,
                marker_color=colors[:len(labels)],
                text=[f"{v:.2f}" for v in vals],
                textposition="outside",
            ))
            fig.add_hline(y=0, line_width=1, line_dash="dot")
            fig.update_layout(title=title, height=380, yaxis_title="kcal/mol")
            return fig

        colors = ["#2ca02c","#d62728","#1f77b4","#aec7e8","#000000"]

        if any(v is not None for v in gb_d.values()):
            gb_plot = {
                "ΔEVDW": gb_d["VDWAALS"], "ΔEele": gb_d["EEL"],
                "ΔEGB": gb_d["EGB"], "ΔESURF": gb_d["ESURF"],
                "ΔG total": gb_d["DELTA TOTAL"],
            }
            st.plotly_chart(_bar_chart("MM-GBSA Components", gb_plot, colors),
                            use_container_width=True)

        if do_pb and any(v is not None for v in pb_d.values()):
            pb_plot = {
                "ΔEVDW": pb_d["VDWAALS"], "ΔEele": pb_d["EEL"],
                "ΔEPB": pb_d["EPB"],
                "ΔEnp": pb_d["ESURF"] or pb_d["ENPOLAR"],
                "ΔG total": pb_d["DELTA TOTAL"],
            }
            st.plotly_chart(_bar_chart("MM-PBSA Components", pb_plot, colors),
                            use_container_width=True)

    log_expander("log_mmpbsa")


# ══════════════════════════════════════════════════════════════════════════════
# PAGE 12: DBFE
# ══════════════════════════════════════════════════════════════════════════════
elif page == "🧮  12 · DBFE":
    st.title("🧮 DBFE — Absolute Binding Free Energy")

    st.markdown("""
**Thermodynamic cycle:**
```
ΔG_bind = ΔG_inter  +  ΔG_std_state  −  ΔG_sym
```
Unlike MM-PBSA/GBSA, DBFE includes the translational + rotational entropy correction (ΔG_TR).

**References:**  
- arXiv: [2603.12253](https://arxiv.org/abs/2603.12253)  
- GitHub: [molecularmodelinglab/dbfe](https://github.com/molecularmodelinglab/dbfe)
""")

    tab1, tab2, tab3 = st.tabs(["Step 1: Install", "Step 2: Prepare Trajectories", "Step 3: Run DBFE"])

    with tab1:
        if st.button("📦 Install DBFE package"):
            with st.spinner("Installing..."):
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

        if st.button("▶ Prepare DBFE Trajectories"):
            st.info("DBFE trajectory preparation requires the full DBFE package. "
                    "Check that Step 1 is complete, then run `python run_dbfe.py` "
                    "from the workspace directory.")
            py = os.path.join(WD(), "run_dbfe_prep.py")
            with open(py, "w") as f:
                f.write(f"# Auto-generated DBFE prep script\n"
                        f"import os; os.chdir('{WD()}')\n"
                        f"use_lb={use_lb}\nuse_cmd={use_cmd2}\n"
                        f"indep_md_ns={indep_ns}\ntemperature_K={temp_K}\n"
                        f"igb_folder='{igb_folder}'\n"
                        f"print('DBFE prep — edit and run this script manually.')\n")
            st.code(core.read_file(py))

    with tab3:
        std_conc  = st.number_input("Standard concentration (M)", value=1.0)
        n_equil   = st.slider("Equilibration fraction", 0.0, 0.5, 0.2)
        max_pairs = st.number_input("Max BAR frame pairs", value=2000)

        if st.button("▶ Compute DBFE"):
            st.info("Running DBFE via Python subprocess...")
            py = os.path.join(WD(), "run_dbfe_bar.py")
            with open(py, "w") as f:
                f.write(f"import os; os.chdir('{WD()}')\n"
                        f"standard_conc_M={std_conc}\nn_equil_frac={n_equil}\n"
                        f"max_pairs={int(max_pairs)}\nprint('DBFE BAR stub — extend as needed.')\n")
            rc, out = core.run_cmd([sys.executable, py], cwd=WD())
            st.code(out)

        # Show existing DBFE results
        res_path = wpath("DBFE_results.json")
        if os.path.exists(res_path):
            st.success("✅ DBFE results found!")
            results = json.loads(core.read_file(res_path))
            for r in results:
                st.metric(
                    f"ΔG_bind ({r.get('source','?')})",
                    f"{r.get('dG_bind', 0):.2f} kcal/mol"
                )


# ══════════════════════════════════════════════════════════════════════════════
# PAGE 13: Download Results
# ══════════════════════════════════════════════════════════════════════════════
elif page == "📦  13 · Download Results":
    st.title("📦 Download Results")

    FILE_DESC = {
        "complex.top":         "Topology (solvated complex)",
        "complex.crd":         "Coordinates (solvated complex)",
        "complex.pdb":         "Complex PDB (dry)",
        "complex_leap.pdb":    "Complex PDB (solvated)",
        "host.pdb":            "Host PDB",
        "guest.pdb":           "Guest PDB",
        "guest.prep":          "Guest PREP (AmberTools)",
        "guest.frcmod":        "Guest FRCMOD",
        "last_frame.rst7":     "Restart after heating",
        "sum.nc":              "LB-PaCS-MD trajectory (NetCDF)",
        "md.dcd":              "cMD trajectory (DCD)",
        "md-cMD.dcd":          "cMD processed trajectory",
        "dis_plot.dat":        "PaCS-MD distance vs cycle",
        "dis.dat":             "Host–guest COM distance",
        "rg.dat":              "Host radius of gyration",
        "rmsd.dat":            "RMSD data",
        "FINAL_RESULTS_MMPBSA_LB.dat":  "MM-PBSA results (LB-PaCS-MD)",
        "FINAL_RESULTS_MMPBSA_cMD.dat": "MM-PBSA results (cMD)",
        "DBFE_results.json":   "DBFE results",
    }

    found = {k: wpath(k) for k in FILE_DESC if os.path.exists(wpath(k))}
    missing = [k for k in FILE_DESC if k not in found]

    st.markdown(f"**{len(found)} / {len(FILE_DESC)} files available**")

    # Individual downloads
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
    st.markdown("### 🗜️ Download Everything as ZIP")
    if st.button("Create ZIP bundle"):
        with st.spinner("Zipping..."):
            zip_path, added = core.create_results_zip(WD())
        st.success(f"ZIP ready: {len(added)} files, {core.file_mb(zip_path):.1f} MB")
        with open(zip_path, "rb") as f:
            st.download_button(
                "⬇ Download DFDD_results.zip",
                data=f,
                file_name="DFDD_results.zip",
                mime="application/zip",
            )
