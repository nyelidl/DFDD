# DFDD - Distance-Guided Fully Dynamic Docking
Version 1.3.1

[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/drive/1FfTuVSykgsstjzN0nJN0ZQo1_tw0WXSe?usp=sharing)
[![DOI](https://img.shields.io/badge/DOI-10.1021%2Facs.jcim.5c02852-blue)](https://doi.org/10.1021/acs.jcim.5c02852)
[![License](https://img.shields.io/badge/License-Academic-green.svg)]()

This notebook presents a **cloud-friendly workflow** for performing **fully dynamic docking** using OpenMM and an implementation of the **LB-PaCS-MD** (Ligand Binding Path Sampling based on Parallel Cascade Selection MD) strategy. The goal is to provide an accessible way for students and researchers to explore how host–guest systems undergo spontaneous binding in explicit solvent using enhanced MD sampling on Google Colab.

This notebook is a supplementary material of the paper ***"DFDD: A Cloud-Ready Tool for Distance-Guided Fully Dynamic Docking in Host–Guest Complexation"*** published in the *Journal of Chemical Information and Modeling* (2026): [DOI 10.1021/acs.jcim.5c02852](https://doi.org/10.1021/acs.jcim.5c02852). We encourage everyone to read it before using this pipeline.

Rather than relying on static docking or predefined poses, this workflow demonstrates how cloud computing can be used to observe natural binding and unbinding events, capture multiple inclusion modes, and explore realistic association pathways with minimal setup.

![DFDD Workflow](./wf.png)

---

---

## ✨ New Feature: HF/RESP Ligand Optimization

DFDD now includes **Hartree-Fock based RESP charge fitting** for quantum-level ligand parameterization:

### **Why HF/RESP?**

🔬 **Quantum-Level Accuracy** — HF/6-31G* electrostatic potential calculations using **Psi4**  
⚡ **RESP Charge Fitting** — Industry-standard restrained electrostatic potential protocol  
🎯 **GAFF2 Integration** — Complete force field generation via **AmberTools**  
☁️ **Cloud-Native** — All QM calculations run seamlessly on **Google Colab**  
📊 **Automated Validation** — Topology checks and energy minimization included  

### **Automated Workflow**

```
SMILES → 3D Structure → HF Geometry Optimization → ESP Calculation → RESP Fitting → GAFF2 Parameters
```

**Typical Performance** (Google Colab T4 GPU):
- HF geometry optimization: 5-15 minutes
- ESP calculation & RESP fitting: 2-5 minutes
- **Total ligand setup: ~20 minutes**

### **Technical Details**

- **QM Method**: Hartree-Fock (HF/6-31G* — standard AMBER protocol)
- **QM Engine**: Psi4
- **Charge Fitting**: AmberTools RESP module
- **Force Field**: GAFF2 (General Amber Force Field)
- **Output**: Complete .mol2 and .frcmod files for AMBER

### **Quick Ligand Preparation**

For rapid ligand setup with protonation state prediction:  
[![Streamlit](https://img.shields.io/badge/Streamlit-pKaNET_Cloud-brightgreen?logo=streamlit)](https://pkanetcloud.streamlit.app/)

---

## 🎯 Supported Host Systems

DFDD provides **comprehensive support for cyclodextrin host molecules**, enabling exploration of host–guest complexation across a diverse family of supramolecular systems:

### **β-Cyclodextrin Family** (7 glucose units)
- ✅ **Native β-CD** — Unmodified 7-membered ring
  - GLYCAM-06 force field
  - DFT-derived parameters (alternative)
- ✅ **Dimethylated β-CD (DMBCD)** — Fully methylated at O2 and O6 positions (14 substituents)
- ✅ **Methylated β-CD (MBCD)** — Partially methylated variant (13 substituents)
- ✅ **Hydroxypropyl β-CD (HPBCD)** — Partial O6-hydroxypropyl substitution (4 substituents)
- ✅ **6-Tetra-hydroxypropyl β-CD** — O6 position variant (4 substituents)

Each host type is **automatically detected** during the workflow, with appropriate force field parameters, ring closure bonds, and substituent bonding patterns applied seamlessly. This enables users to compare binding behaviors across different cyclodextrin architectures without manual parameter adjustments.

**Force Field Support:**
- **GLYCAM-06** for all cyclodextrin variants
- **DFT-derived parameters** for β-CD (alternative option)

Future versions may expand to additional host frameworks beyond cyclodextrins.

---

## ✨ Key Features

- 🔬 **HF/RESP QM Ligand Optimization** for high-accuracy atomic charges
- 🧬 **5 Cyclodextrin Host Types** with automatic detection
- 🧪 **SMILES-based Guest Input** with automated GAFF2 parameterization
- 🚀 **GPU-Accelerated MD** via OpenMM on Google Colab
- 📈 **Enhanced Sampling** using LB-PaCS-MD for binding pathways
- 📊 **Automatic Analysis** including RMSD, Rg, distance metrics, and 2D free energy landscapes
- ☁️ **Cloud-Ready** — runs entirely in the browser, no local installation needed
- 🎓 **Educational** — designed for users with no prior MD experience  

---

## 🚀 Quick Start

1. Click the **"Open in Colab"** badge above
2. Select your cyclodextrin host from the dropdown (5 options available)
3. Input your guest molecule as a SMILES string
4. **Optional**: Enable HF/RESP QM optimization for high-accuracy charges
5. Run the cells in order
6. Analyze binding pathways and free energy landscapes

**No coding experience required!** The workflow handles everything automatically.

---

## 📖 Workflow Overview

1. **Host Selection** — Choose from 5 cyclodextrin variants
2. **Guest Preparation** — Input SMILES, generate 3D structure
3. **QM Optimization** (Optional) — HF/RESP charge fitting with Psi4
4. **Force Field Assignment** — Automated GAFF2 parameterization
5. **Complex Building** — Position guest along host axis
6. **System Setup** — Solvation, neutralization, and topology generation
7. **Equilibration** — Energy minimization and heating with restraints
8. **Enhanced Sampling** — LB-PaCS-MD to capture binding pathways
9. **Analysis** — Trajectory visualization, free energy landscapes, binding mode identification

Each step provides **visual feedback** and **diagnostic output** to help users understand molecular-level interactions.

---

## 📋 Requirements

- Google account (for Colab access)
- Modern web browser
- Internet connection

**No local software installation needed!** Everything runs in the cloud.

**Included Software:**
- OpenMM (GPU-accelerated MD engine)
- Psi4 (Quantum chemistry for HF/RESP)
- AmberTools (Parameterization, RESP fitting, MM-PBSA)
- ParmEd, MDAnalysis (Topology and trajectory handling)
- NumPy, Deeptime (Data analysis)
- py3Dmol (3D molecular visualization)

**Compute Resources:**
- Designed for Google Colab's free tier
- GPU acceleration available (T4/V100/A100)
- For production-scale studies, consider Colab Pro or HPC resources

---

## 📝 A Quick Note

This notebook is designed as an **interactive learning tool**, not a full production-grade MD workflow. Its goal is to walk users through the core ideas behind fully dynamic docking, showing—step by step—how a host and guest naturally associate in explicit solvent using the LB-PaCS-MD approach.

**Importantly**, this notebook is meant for **everyone**: computational chemists, experimental researchers, students, and even users with no prior experience in molecular simulations. The interface guides the user from structure preparation to MD simulation, inclusion pathway sampling, and binding free-energy estimation.

---

## 📚 Citation

If you use this workflow in your research, please cite:

```bibtex
@article{DFDD2026,
  title={DFDD: A Cloud-Ready Tool for Distance-Guided Fully Dynamic Docking in Host–Guest Complexation},
  author={Hengphasatporn K, Lian D, Harada R, Shigeta Y},
  journal={Journal of Chemical Information and Modeling},
  year={2026},
  doi={10.1021/acs.jcim.5c02852}
}
```

For GLYCAM-06 parameters, please also cite:
```bibtex
@article{GLYCAM2008,
  title={GLYCAM06: A generalizable biomolecular force field. Carbohydrates},
  author={Kirschner, Karl N and Yongye, Austin B and Tschampel, Shane M and González-Outeiriño, Jorge and Daniels, Charlisa R and Foley, B Lachele and Woods, Robert J},
  journal={Journal of Computational Chemistry},
  volume={29},
  number={4},
  pages={622--655},
  year={2008}
}
```

If you use HF/RESP parameterization, please also cite:
```bibtex
@article{RESP1993,
  title={A well-behaved electrostatic potential based method using charge restraints for deriving atomic charges: the RESP model},
  author={Bayly, Christopher I and Cieplak, Piotr and Cornell, Wendy D and Kollman, Peter A},
  journal={The Journal of Physical Chemistry},
  volume={97},
  number={40},
  pages={10269--10280},
  year={1993}
}
```

---

## Related Publications

### DFDD (Main Paper)
**"DFDD: A Cloud-Ready Tool for Distance-Guided Fully Dynamic Docking in Host–Guest Complexation"**  
*Journal of Chemical Information and Modeling* (2026)  
DOI: [10.1021/acs.jcim.5c02852](https://doi.org/10.1021/acs.jcim.5c02852)

---

### PaCS-Q and LB-PaCS-MD: Path Sampling Frameworks (Recommended Reading)

1. Ligand Binding Path Sampling (LB-PaCS-MD)
   Hiroki Aida, Yasuteru Shigeta, and Ryuhei Harada
   Ligand Binding Path Sampling Based on Parallel Cascade Selection
   Molecular Dynamics (LB-PaCS-MD)
   Materials 2022, 15 (4), 1490
   DOI: 10.3390/ma15041490

2. PaCS-Q Automated Toolkit
   Lian Duan, Kowit Hengphasatporn, and Yasuteru Shigeta
   PaCS-Q: Python Toolkits for Path Sampling in MD and QM/MM MD Simulation
   Journal of Chemical Information and Modeling 2025, 65 (13), 6441–6445
   DOI: 10.1021/acs.jcim.5c00936

These works establish the methodological foundation of the PaCS framework,
supporting both LB-PaCS-MD for ligand binding/unbinding processes and
PaCS-Q for automated MD and QM/MM MD reaction path sampling.

Related Application in Host–Guest Systems
S. Ali, A. Aman, K. Hengphasatporn, et al.
Evaluating solubility, stability, and inclusion complexation of
oxyresveratrol with various β-cyclodextrin derivatives using advanced
computational techniques and experimental validation
Computational Biology and Chemistry 2024, 112, 108111
DOI: 10.1016/j.compbiolchem.2024.108111

---

## 🐛 Reporting Issues

If you encounter errors or unexpected behavior, please report them through the [GitHub issue tracker](https://github.com/nyelidl/DFDD/issues).

When reporting issues, please include:
- Host type being used
- Whether HF/RESP optimization was enabled
- Error messages (full text)
- Steps to reproduce
- Browser and Colab environment info

We welcome:
- Bug reports
- Feature requests
- Documentation improvements
- HF/RESP workflow questions
- Parameter compatibility questions

---

## 🙏 Acknowledgments

We gratefully acknowledge:

- The **OpenMM team** for providing an exceptional open-source MD engine with robust GPU support
- The **Psi4 developers** for accessible quantum chemistry tools
- The developers of **AmberTools**, **ParmEd**, **MDAnalysis**, **NumPy**, and **Deeptime**
- **David Koes** for creating **py3Dmol**, the elegant molecular viewer used throughout
- The **Woods Research Group** at the University of Georgia for GLYCAM-06 force field parameters
- Community efforts to make MD simulations more accessible through cloud-based platforms

---

## 🌟 Special Thanks

We gratefully acknowledge **Arantes et al.** — **Pablo R. Arantes** ([@pablitoarantes](https://twitter.com/pablitoarantes)), **Marcelo D. Polêto** ([@mdpoleto](https://twitter.com/mdpoleto)), **Conrado Pedebos** ([@ConradoPedebos](https://twitter.com/ConradoPedebos)), and **Rodrigo Ligabue-Braun** ([@ligabue_braun](https://twitter.com/ligabue_braun)) for developing the **Making It Rain: Cloud-Based Molecular Simulations for Everyone** framework, which served as the foundational inspiration for this work.

---

## 📄 License

This educational workflow is provided for **academic and educational purposes**. Commercial users should verify licensing compatibility for all included tools and force fields.

---

## 🔗 Related Tools

For quick ligand preparation and pKa/protonation-based conversion, check out:
- **pKaNET_Cloud** via Streamlit: [![Streamlit](https://img.shields.io/badge/Streamlit-pKaNET_Cloud-brightgreen?logo=streamlit)](https://pkanetcloud.streamlit.app/)

---

## 📊 Version History

- **v1.3** (2026-02) — **HF/RESP QM ligand optimization** added
- **v1.2** — Complete beta-cyclodextrin support (all 5 types with auto-detection)
- **v1.1** — Added GLYCAM-06 support for β-CD variants
- **v1.0** — Initial release (DFT β-CD only)

---

## 🤝 Contributing

Contributions are welcome! Please feel free to submit:
- Bug fixes
- New host types
- Documentation improvements
- Feature enhancements

Open an issue or pull request to get started.

---

## 📧 Contact

For questions or collaboration opportunities, please:
1. Check the documentation first
2. Search existing GitHub issues
3. Open a new issue if needed
4. Refer to the publication for methodology questions

---

**Ready to explore host–guest binding?** 👉 [Open in Colab](https://colab.research.google.com/drive/1FfTuVSykgsstjzN0nJN0ZQo1_tw0WXSe?usp=sharing)

---

*Last updated: February 2026 | DFDD v1.3 — HF/RESP QM Ligand Optimization*
