# DFDD
[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](
https://colab.research.google.com/drive/1CHNVIQqp4fFmnLem_Jf4a99i2L00XhMA?usp=sharing)

This notebook presents a cloud-friendly workflow for performing fully dynamic docking using OpenMM and an implementation of the LB-PaCS-MD (Ligand Binding Path Sampling based on Parallel Cascade Selection MD) strategy. The goal is to provide an accessible way for students and researchers to explore how host–guest systems undergo spontaneous binding in explicit solvent using enhanced MD sampling on Google Colab. This notebook is a supplementary material of the paper "Distance-guided fully dynamic docking for in silico host–guest complexation" (link here) and we encourage everyone to read it before using this pipeline.

Rather than relying on static docking or predefined poses, this workflow demonstrates how cloud computing can be used to observe natural binding and unbinding events, capture multiple inclusion modes, and explore realistic association pathways with minimal setup.

**A quick note**

This notebook is designed as an interactive learning tool, not a full production-grade MD workflow. Its goal is to walk users through the core ideas behind fully dynamic docking, showing—step by step—how a host and guest naturally associate in explicit solvent using the LB-PaCS-MD approach.

Importantly, this notebook is meant for everyone: computational chemists, experimental researchers, students, and even users with no prior experience in molecular simulations. The interface guides the user from structure preparation to MD simulation, inclusion pathway sampling, and binding free-energy estimation.

The current release supports β-cyclodextrin (β-CD) as the host system, enabling users to explore host–guest complexation in an accessible and reproducible environment. Future versions will expand to additional host frameworks.

**Reporting issues**

If you encounter errors or unexpected behavior, please feel free to report them through the GitHub issue tracker referenced in the manuscript. https://github.com/nyelidl/DFDD

**Acknowledgments**

We gratefully acknowledge the OpenMM team for providing an exceptional open-source MD engine with robust GPU support.

We also thank the developers of the tools that make this workflow possible, including AmberTools, ParmEd, MDAnalysis, NumPy, and Deeptime.

Visualization throughout the notebook uses py3Dmol, an elegant molecular viewer created by David Koes.

This work was inspired by community efforts to make MD simulations more accessible through cloud-based platforms, especially educational initiatives demonstrating how Colab can be used for hands-on computational chemistry training.

**Last but not least**

We gratefully acknowledge Arantes et al. Pablo R. Arantes (@pablitoarantes), Marcelo D. Polêto (@mdpoleto), Conrado Pedebos (@ConradoPedebos) and Rodrigo Ligabue-Braun (@ligabue_braun) for developing the Making It Rain: Cloud-Based Molecular Simulations for Everyone framework, which served as the foundational inspiration for this work.
