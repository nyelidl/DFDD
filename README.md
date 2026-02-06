# DFDD — Distance-Guided Fully Dynamic Docking
Version 1.3.2

<img src="https://raw.githubusercontent.com/nyelidl/DFDD/main/Udo-san.gif">

[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/drive/1FfTuVSykgsstjzN0nJN0ZQo1_tw0WXSe?usp=sharing)
[![DOI](https://img.shields.io/badge/DOI-10.1021%2Facs.jcim.5c02852-blue)](https://doi.org/10.1021/acs.jcim.5c02852)
[![License](https://img.shields.io/badge/License-Academic-green.svg)]()

This notebook provides a **cloud-friendly workflow** for **fully dynamic host–guest docking** using OpenMM and the **LB-PaCS-MD** (Ligand Binding Path Sampling based on Parallel Cascade Selection MD) strategy.  
It enables students and researchers to explore **spontaneous binding and unbinding processes in explicit solvent** using enhanced molecular dynamics on **Google Colab**, with minimal setup.

This notebook accompanies the paper  
**“DFDD: A Cloud-Ready Tool for Distance-Guided Fully Dynamic Docking in Host–Guest Complexation”**  
(*Journal of Chemical Information and Modeling*, 2026)  
https://doi.org/10.1021/acs.jcim.5c02852

Rather than relying on static docking poses, DFDD captures **natural binding pathways, multiple inclusion modes, and realistic association dynamics** through unbiased MD sampling.

![DFDD Workflow](./wf.png)

---

## 🔧 Ligand Parameterization (AM1-BCC, Default & Recommended)

DFDD adopts a **single, robust ligand parameterization pathway** optimized for **stability and reproducibility in cloud environments**.

### AM1-BCC (AmberTools standard)
- Fast and reliable (seconds per ligand)
- Fully compatible with **GAFF2**
- Applicable to neutral and charged ligands
- No QM dependencies (Colab-safe)
- Widely accepted in biomolecular MD studies

> AM1-BCC is recommended for **the vast majority of host–guest systems** and ensures smooth execution on free Colab resources.

---

## 🔬 Ligand Preparation Workflow

1. **Input**
   - SMILES string or structure file (`PDB`, `MOL2`, `SDF`)
2. **Optional pH handling**
   - pKa prediction and microspecies selection
3. **3D structure generation**
   - RDKit (ETKDG + UFF minimization)
4. **Charge assignment**
   - AM1-BCC via AmberTools (`antechamber -c bcc`)
5. **Force-field completion**
   - GAFF2 atom typing + `parmchk2`
6. **Validation**
   - Charge and topology consistency checks

For rapid ligand preparation and protonation handling, see:  
👉 **pKaNET_Cloud** (Streamlit): https://pkanetcloud.streamlit.app/

---

## 🧬 Fully Dynamic Docking Engine

- **LB-PaCS-MD sampling** for unbiased binding pathway exploration
- **Explicit solvent MD** (TIP3P water + neutralizing ions)
- **GPU acceleration** via OpenMM on Google Colab
- **Ensemble binding modes**, not limited to a single pose

---

## 🧪 Supported Host Systems (Cyclodextrins)

DFDD supports a broad range of cyclodextrin hosts with **automatic detection and setup**:

### β-Cyclodextrin Family
- Native β-CD  
  - GLYCAM-06 force field  (BCD)
  - DFT-derived parameters (default)
- Dimethylated β-CD (DMBCD)
- Methylated β-CD (MBCD)
- Hydroxypropyl β-CD (HPBCD)
- 6-Tetra-hydroxypropyl β-CD

All hosts are prepared automatically with correct bonding, ring closure, and force-field assignments.

---

## 📊 Outputs

- Optional pH-adjusted ligand structures
- GAFF2 parameters (`.prep`, `.frcmod`)
- AMBER topology and coordinates (`.prmtop`, `.inpcrd`)
- MD trajectories (NetCDF)
- Binding mode structures (PDB)
- Distance and free-energy analyses
- MM-PBSA / MM-GBSA binding energy estimates
- Downloadable ZIP result bundle

---

## ⏱️ Typical Runtime (Google Colab)

- Ligand preparation: **30–60 s**
- Equilibration: **10–20 min**
- One LB-PaCS-MD cycle: **15–30 min**
- Full run (3–5 cycles): **~1.5–3 h**

---

## 🚀 Quick Start

1. Click **Open in Colab**
2. Select the cyclodextrin host
3. Provide the guest molecule (SMILES)
4. Run the notebook cells sequentially
5. Analyze binding pathways and free-energy landscapes

No local installation or coding experience required.

---

## Note

If you are interested in performing docking using **AutoDock Vina v1.2.7** for **protein–ligand** or **cyclodextrin–guest** systems, you may also find the following repository useful:

https://github.com/nyelidl/Docking_workshop

---

## 📚 Citation

If you use DFDD or pKaNET Cloud, please cite:

```bibtex
@article{DFDD2026,
  title={DFDD: A Cloud-Ready Tool for Distance-Guided Fully Dynamic Docking in Host–Guest Complexation},
  author={Hengphasatporn, K. and Duan, L. and Harada, R. and Shigeta, Y.},
  journal={Journal of Chemical Information and Modeling},
  year={2026},
  doi={10.1021/acs.jcim.5c02852}
}


