"""
core.py — DFDD backend logic
All subprocess calls, file I/O, and scientific computation functions.
"""

import os
import sys
import json
import math
import shutil
import zipfile
import subprocess
import urllib.request
import numpy as np

# ─── Constants ────────────────────────────────────────────────────────────────
GLYCAM_REPO = "https://raw.githubusercontent.com/nyelidl/DFDD/main/GLYCAM/"
HOST_GUEST_REPO = "https://github.com/nyelidl/host-guest.git"

GLYCAM_HOST_CONFIGS = {
    "Native β-CD (GLYCAM)":       {"type": "BCD",         "pdb": "gBCD.pdb",        "n_glc": 7},
    "Dimethylated β-CD (GLYCAM)": {"type": "DMBCD",       "pdb": "gDMBCD.pdb",      "n_glc": 7},
    "Methylated β-CD (GLYCAM)":   {"type": "MBCD",        "pdb": "gMBCD.pdb",       "n_glc": 7},
    "6-tetra HP β-CD (GLYCAM)":   {"type": "6tetraHPBCD", "pdb": "g6tetraHPBCD.pdb","n_glc": 7},
}

HOST_SEL_MAP = {
    "BCD_DFT":      ":1",
    "BCD":          ":1-7",
    "DMBCD":        ":1-7",
    "MBCD":         ":1-7",
    "HPBCD":        ":1-11",
    "6tetraHPBCD":  ":1-11",
}

PACSMD_HOST_SEL = {
    "BCD_DFT":      "resid 1",
    "BCD":          "resid 1-7",
    "DMBCD":        "resid 1-7",
    "MBCD":         "resid 1-7",
    "HPBCD":        "resid 1-7",
    "6tetraHPBCD":  "resid 1-7",
}

FREEZE_RESIDS = {
    "BCD_DFT":     ["1", "2"],
    "BCD":         ["1:7", "8"],
    "DMBCD":       ["1:21", "22"],
    "MBCD":        ["1:20", "21"],
    "HPBCD":       ["1:11", "12"],
    "6tetraHPBCD": ["1:11", "12"],
}

MBONDI_MAP = {"1": "mbondi", "2": "mbondi2", "5": "mbondi2", "7": "bondi", "8": "mbondi3"}


# ─── Utility ──────────────────────────────────────────────────────────────────

def run_cmd(cmd, cwd=None, shell=False, timeout=600):
    """Run a command; return (returncode, stdout+stderr string)."""
    result = subprocess.run(
        cmd, cwd=cwd, capture_output=True, text=True,
        shell=shell, timeout=timeout
    )
    return result.returncode, result.stdout + "\n" + result.stderr


def read_file(path):
    try:
        with open(path) as f:
            return f.read()
    except Exception:
        return ""


def file_mb(path):
    return os.path.getsize(path) / 1e6 if os.path.exists(path) else 0.0


def download_file(filename, dest_dir, base_url=GLYCAM_REPO):
    dest = os.path.join(dest_dir, filename)
    if os.path.exists(dest):
        return dest, f"✓ {filename} already exists"
    url = base_url + filename
    urllib.request.urlretrieve(url, dest)
    return dest, f"✓ Downloaded {filename} ({file_mb(dest):.2f} MB)"


def insert_ter_records(pdb_path):
    """Insert TER after each residue change — required for GLYCAM tleap."""
    lines_out, last_key = [], None
    with open(pdb_path) as fin:
        for line in fin:
            if line.startswith(("ATOM", "HETATM")):
                key = (line[21], line[22:26])
                if last_key and key != last_key:
                    lines_out.append("TER\n")
                last_key = key
            lines_out.append(line)
    if last_key and not lines_out[-1].startswith("TER"):
        lines_out.append("TER\n")
    with open(pdb_path, "w") as fout:
        fout.writelines(lines_out)


def check_tools():
    """Return dict of {tool: path_or_None}."""
    tools = ["antechamber", "tleap", "parmchk2", "cpptraj",
             "obabel", "pacs_q_md", "git"]
    result = {}
    for tool in tools:
        rc, out = run_cmd(["which", tool])
        result[tool] = out.strip() if rc == 0 else None
    return result


# ─── Host Preparation ─────────────────────────────────────────────────────────

def prepare_host_dft(workdir):
    """Clone host-guest repo and copy DFT β-CD files."""
    repo_dir = os.path.join(workdir, "host-guest")
    log = ""

    if not os.path.exists(repo_dir):
        rc, out = run_cmd(["git", "clone", HOST_GUEST_REPO, repo_dir])
        log += out
        if rc != 0:
            return None, log, f"Git clone failed (code {rc})"

    src = {
        "pdb":    os.path.join(repo_dir, "BCD-n", "BCD.pdb"),
        "prep":   os.path.join(repo_dir, "BCD-n", "BCD.prep"),
        "frcmod": os.path.join(repo_dir, "BCD-n", "BCD.frcmod"),
    }
    for k, fp in src.items():
        if not os.path.exists(fp):
            return None, log, f"Missing: {fp}"

    dest_pdb = os.path.join(workdir, "host.pdb")
    shutil.copy(src["pdb"], dest_pdb)

    return {
        "host_path":       dest_pdb,
        "host_prep":       src["prep"],
        "host_frcmod":     src["frcmod"],
        "host_forcefield": "DFT",
        "host_type":       "BCD_DFT",
    }, log, None


def prepare_host_glycam(host_option, workdir):
    """Download GLYCAM files and build ring via tleap."""
    cfg = GLYCAM_HOST_CONFIGS[host_option]
    host_type  = cfg["type"]
    pdb_fname  = cfg["pdb"]
    prep_fname = "Glycam_06tk.prep"
    dat_fname  = "Glycam_06g-1.dat"
    log = ""

    for fname in [pdb_fname, prep_fname, dat_fname]:
        _, msg = download_file(fname, workdir)
        log += msg + "\n"

    pdb_path  = os.path.join(workdir, pdb_fname)
    prep_path = os.path.join(workdir, prep_fname)
    dat_path  = os.path.join(workdir, dat_fname)

    leap_script = _write_glycam_leap(
        host_type, pdb_fname, prep_fname, dat_fname, workdir
    )

    rc, out = run_cmd(["tleap", "-f", leap_script], cwd=workdir)
    log += out
    if rc != 0:
        return None, log, f"tleap failed (code {rc})"

    host_pdb = os.path.join(workdir, "host.pdb")
    if not os.path.exists(host_pdb):
        return None, log, "host.pdb was not created by tleap"

    return {
        "host_path":       host_pdb,
        "host_prep":       prep_path,
        "host_frcmod":     dat_path,
        "host_forcefield": "GLYCAM06",
        "host_type":       host_type,
    }, log, None


def _write_glycam_leap(host_type, pdb_fname, prep_fname, dat_fname, workdir):
    """Write a tleap script for GLYCAM ring-building; return script filename."""
    script_name = f"build_{host_type}.leap"
    with open(os.path.join(workdir, script_name), "w") as f:
        f.write("source leaprc.protein.ff19SB\n")
        f.write("source leaprc.water.tip3p\n")
        f.write("source leaprc.gaff2\n\n")
        f.write('addAtomTypes {\n  { "nv"  "N" "sp2" }\n}\n\n')
        f.write(f"loadAmberPrep {prep_fname}\n")
        f.write(f"loadAmberParams {dat_fname}\n\n")
        f.write(f"w = loadpdb {pdb_fname}\n\n")

        # Glycosidic ring
        for i in range(1, 8):
            f.write(f"bond w.{i}.O4 w.{(i % 7) + 1}.C1\n")
        f.write("\n")

        # Substituent bonds
        if host_type == "DMBCD":
            for i in range(1, 8):
                f.write(f"bond w.{i}.O6 w.{i+7}.CH3\n")
            for i in range(1, 8):
                f.write(f"bond w.{i}.O2 w.{i+14}.CH3\n")
        elif host_type == "MBCD":
            for i in range(1, 8):
                f.write(f"bond w.{i}.O6 w.{i+7}.CH3\n")
            for i in range(1, 7):
                f.write(f"bond w.{i}.O2 w.{i+14}.CH3\n")
        elif host_type in ("HPBCD", "6tetraHPBCD"):
            for i, res in [(1, 8), (3, 9), (5, 10), (7, 11)]:
                f.write(f"bond w.{i}.O6 w.{res}.CA\n")

        f.write("\nset w box { 13 13 40 }\n")
        f.write("translate w { 0, 0, 10 }\n\n")
        f.write("savepdb w host.pdb\n")
        f.write("saveamberparm w host.prmtop host.inpcrd\n\n")
        f.write("quit\n")
    return script_name


# ─── Guest Preparation ────────────────────────────────────────────────────────

# ── Ionisable site SMARTS (subset of pKaNET, covers common drug-like groups) ─
_ION_SITES = [
    # label,              SMARTS,                                   heuristic_pKa, type
    ("sulfonic_acid",     "[SX4](=O)(=O)[OX2H1]",                  1.0,  "acid"),
    ("carboxylic_acid",   "[CX3](=O)[OX2H1]",                      4.5,  "acid"),
    ("tetrazole",         "c1nn[nH]n1",                             4.9,  "acid"),
    ("phosphonate",       "[PX4](=O)([OX2H1])[OX2H1,OX1-]",        6.5,  "acid"),
    ("thiol_arom",        "c[SX2H1]",                               6.5,  "acid"),
    ("imidazole_NH",      "c1cn[nH]c1",                             6.0,  "acid"),
    ("phenol_EWG",        "[OX2H1][c;R]:[c;R][$([NX3](=O)=O),$([CX3]=O),$(C#N)]",
                                                                    7.2,  "acid"),
    ("sulfonamide_NH",    "[SX4](=O)(=O)[NX3;H1]",                 10.1, "acid"),
    ("phenol",            "c[OX2H1]",                              10.0, "acid"),
    ("thiol_aliph",       "[CX4][SX2H1]",                          10.5, "acid"),
    ("amide_NH",          "[CX3](=O)[NX3;H1,H2;!$([N]~N)]",       15.0, "acid"),
    ("aniline",           "c[NX3;H1,H2;!$(N~[!#6])]",              4.6,  "base"),
    ("pyridine_like",     "[$([nX2]1:[c,n]:c:[c,n]:c1),$([nX2]:c:n)]",
                                                                    5.2,  "base"),
    ("aliphatic_amine",   "[NX3;H1,H2;!$(NC=O);!$(N~[!#6;!H]);!$([nH])]",
                                                                    9.5,  "base"),
    ("amidine",           "[CX3](=[NX2;H0,H1])[NX3;H1,H2]",       12.4, "base"),
    ("guanidine",         "[NX3][CX3](=[NX2])[NX3]",              13.0, "base"),
]

_ION_COMPILED = []
for _lbl, _sma, _pka, _typ in _ION_SITES:
    _p = None
    try:
        from rdkit import Chem as _C
        _p = _C.MolFromSmarts(_sma)
    except Exception:
        pass
    if _p is not None:
        _ION_COMPILED.append((_lbl, _p, _pka, _typ))


def _find_ion_sites(mol):
    """Return list of {label, heuristic_pka, site_type} for a molecule."""
    seen = set()
    sites = []
    for lbl, pat, pka, stype in _ION_COMPILED:
        try:
            for match in mol.GetSubstructMatches(pat):
                k = frozenset(match)
                if k not in seen:
                    seen.add(k)
                    sites.append({"label": lbl, "heuristic_pka": pka, "site_type": stype})
        except Exception:
            pass
    return sites


def _hh_score(smiles, sites, pH, ref_mol=None):
    """Henderson–Hasselbalch score: reward/penalise charge state vs pKa at pH.
    Higher = more likely. Also penalises aromatic ring loss vs ref.
    """
    try:
        from rdkit import Chem
        from rdkit.Chem import rdMolDescriptors
        mol = Chem.MolFromSmiles(smiles)
        if mol is None:
            return -999.0
    except Exception:
        return -999.0

    # Formal charge map
    fc_map = {a.GetIdx(): a.GetFormalCharge() for a in mol.GetAtoms()}
    net_charge = sum(fc_map.values())

    score = 0.0

    # Per-site HH consistency
    for site in sites:
        pka  = site["heuristic_pka"]
        stype = site["site_type"]
        dpH  = abs(pH - pka)
        if stype == "acid":
            f_dep = 1.0 / (1.0 + 10.0 ** (pka - pH))   # fraction deprotonated
            expect_neg = f_dep > 0.5
            has_neg = net_charge < 0
            decisive = f_dep >= 0.65 or f_dep <= 0.35
            mul = 1.6 if decisive else 1.0
            if expect_neg and has_neg:
                score += min(1.5, dpH * 0.55 * mul) + 0.15
            elif expect_neg and not has_neg:
                score -= min(1.5, dpH * 0.45 * mul) + 0.15
            else:
                score += 0.1
        else:  # base
            f_prot = 1.0 / (1.0 + 10.0 ** (pH - pka))  # fraction protonated
            expect_pos = f_prot > 0.5
            has_pos = net_charge > 0
            decisive = f_prot >= 0.65 or f_prot <= 0.35
            mul = 1.6 if decisive else 1.0
            if expect_pos and has_pos:
                score += min(1.5, dpH * 0.55 * mul) + 0.15
            elif expect_pos and not has_pos:
                score -= min(1.5, dpH * 0.45 * mul) + 0.15
            else:
                score += 0.1

    # Penalise aromatic ring loss vs input
    if ref_mol is not None:
        try:
            from rdkit.Chem import rdMolDescriptors
            lost = max(0, rdMolDescriptors.CalcNumAromaticRings(ref_mol)
                          - rdMolDescriptors.CalcNumAromaticRings(mol))
            score -= 8.0 * lost
        except Exception:
            pass

    # Small penalty for high net charge
    score -= 0.12 * max(0, abs(net_charge) - 1)

    return score


def _dimorphite_enumerate(smiles, ph_min, ph_max):
    """Call dimorphite-dl via Python API or CLI. Returns list of canonical SMILES."""
    try:
        from rdkit import Chem
    except ImportError:
        return [smiles]

    results = []

    # ── Python API (multiple possible signatures) ────────────────────────────
    try:
        from dimorphite_dl import protonate_smiles as _dim_fn
        import inspect
        kwarg_variants = [
            {"ph_min": ph_min, "ph_max": ph_max, "precision": 1.0, "max_variants": 128},
            {"min_ph": ph_min, "max_ph": ph_max, "pka_precision": 1.0, "max_variants": 128},
            {"ph_min": ph_min, "ph_max": ph_max},
            {"min_ph": ph_min, "max_ph": ph_max},
        ]
        raw = []
        for kw in kwarg_variants:
            try:
                r = _dim_fn(smiles, **kw)
                raw = [r] if isinstance(r, str) else list(r or [])
                if raw:
                    break
            except TypeError:
                continue
        if not raw:
            # Introspect signature
            sig = inspect.signature(_dim_fn)
            kw = {}
            for name in sig.parameters:
                lo = name.lower()
                if   lo in {"ph_min", "min_ph"}:           kw[name] = ph_min
                elif lo in {"ph_max", "max_ph"}:           kw[name] = ph_max
                elif lo in {"precision", "pka_precision"}: kw[name] = 1.0
                elif lo == "max_variants":                 kw[name] = 128
            r = _dim_fn(smiles, **kw)
            raw = [r] if isinstance(r, str) else list(r or [])
        results = [s for s in raw if s and s.strip()]
    except ImportError:
        pass
    except Exception:
        pass

    # ── CLI fallback ─────────────────────────────────────────────────────────
    if not results:
        try:
            res = subprocess.run(
                ["dimorphite_dl", "--smiles", smiles,
                 "--min_ph", str(ph_min), "--max_ph", str(ph_max)],
                capture_output=True, text=True, timeout=60,
            )
            for line in res.stdout.strip().splitlines():
                line = line.strip()
                if line and not line.startswith("#"):
                    results.append(line.split()[0])
        except Exception:
            pass

    # Deduplicate and canonicalise
    seen = set()
    out  = []
    for smi in [smiles] + results:          # always include original
        try:
            from rdkit import Chem
            can = Chem.MolToSmiles(Chem.MolFromSmiles(smi))
            if can and can not in seen:
                seen.add(can); out.append(can)
        except Exception:
            if smi not in seen:
                seen.add(smi); out.append(smi)
    return out or [smiles]


def protonate_smiles_at_ph(smiles, pH=7.4, pH_range=0.5):
    """Select the best protonation state at the given pH using a
    Henderson–Hasselbalch scorer identical to pKaNET rank-1 logic.

    Returns (best_smiles, changed, error).
    """
    smiles = (smiles or "").strip()
    if not smiles:
        return smiles, False, "Empty SMILES"

    try:
        from rdkit import Chem
        ref_mol = Chem.MolFromSmiles(smiles)
        if ref_mol is None:
            return smiles, False, "Invalid SMILES"
    except ImportError:
        return smiles, False, "RDKit not available"

    ph_min = max(0.0,  pH - pH_range)
    ph_max = min(14.0, pH + pH_range)

    # Enumerate protonation states
    candidates = _dimorphite_enumerate(smiles, ph_min, ph_max)

    # Find ionisable sites on the reference molecule
    sites = _find_ion_sites(ref_mol)

    # Score each candidate and pick rank-1
    scored = []
    for smi in candidates:
        sc = _hh_score(smi, sites, pH, ref_mol=ref_mol)
        scored.append((sc, smi))

    if not scored:
        return smiles, False, None

    scored.sort(key=lambda x: -x[0])
    best_smi = scored[0][1]

    try:
        from rdkit import Chem
        input_can = Chem.MolToSmiles(ref_mol)
        changed   = (best_smi != input_can)
    except Exception:
        changed = (best_smi != smiles)

    return best_smi, changed, None


def smiles_to_3d_pdb(smiles, output_pdb, output_sdf=None, workdir=None):
    """Convert SMILES → 3D PDB + SDF, **preserving formal charges**.

    Strategy:
      1. RDKit: parse SMILES (respects [O-], [N+], etc.), embed 3D, write SDF.
         RDKit preserves formal charges through embedding & MMFF optimisation.
      2. obabel SDF → PDB for downstream antechamber compatibility.
      3. obabel fallback if RDKit embed fails.

    The previous version used `obabel -:smi --gen3d -h` which adds hydrogens
    based on default valences and **silently neutralises charged groups**
    (e.g. [O-] → OH).  This broke the protonation state from Dimorphite-DL.

    Returns (charge, error).
    """
    import subprocess as _sp

    smiles = (smiles or "").strip()
    if not smiles:
        return None, "Empty SMILES"

    cwd = workdir or os.path.dirname(output_pdb) or "."
    sdf_out = output_sdf or output_pdb + "_tmp.sdf"

    # ── Step 1: RDKit embed (preserves charges) ──────────────────────────────
    rdkit_ok = False
    charge = 0
    try:
        from rdkit import Chem
        from rdkit.Chem import AllChem
        mol = Chem.MolFromSmiles(smiles)
        if mol is None:
            raise ValueError("RDKit could not parse SMILES")
        # Capture formal charge BEFORE adding Hs
        charge = Chem.GetFormalCharge(mol)
        # Add explicit Hs — RDKit respects formal charges here, unlike obabel -h
        molH = Chem.AddHs(mol)
        # 3D embedding
        params = AllChem.ETKDGv3()
        params.randomSeed = 42
        cid = AllChem.EmbedMolecule(molH, params)
        if cid < 0:
            # Fallback to less strict embedding
            cid = AllChem.EmbedMolecule(molH, useRandomCoords=True, randomSeed=42)
        if cid < 0:
            raise ValueError("RDKit could not generate 3D coordinates")
        # MMFF optimisation (gentle — keeps charged geometry)
        try:
            AllChem.MMFFOptimizeMolecule(molH, maxIters=200)
        except Exception:
            pass
        # Write SDF
        writer = Chem.SDWriter(sdf_out)
        writer.write(molH)
        writer.close()
        if os.path.exists(sdf_out) and os.path.getsize(sdf_out) > 10:
            rdkit_ok = True
    except Exception as e:
        # RDKit failed — fall through to obabel
        rdkit_ok = False

    # ── Step 2: fallback to obabel if RDKit failed ──────────────────────────
    if not rdkit_ok:
        try:
            # Use --gen3d but NOT -h (let SMILES dictate H count from charges)
            _sp.run(
                ["obabel", f"-:{smiles}", "-osdf", "-O", sdf_out,
                 "--gen3d", "--minimize", "--ff", "MMFF94"],
                capture_output=True, text=True, timeout=120, cwd=cwd
            )
            if not os.path.exists(sdf_out) or os.path.getsize(sdf_out) < 10:
                _sp.run(
                    ["obabel", f"-:{smiles}", "-osdf", "-O", sdf_out, "--gen3d"],
                    capture_output=True, text=True, timeout=120, cwd=cwd
                )
        except FileNotFoundError:
            return None, "obabel not found and RDKit embedding failed"
        except Exception as e:
            return None, f"obabel error: {e}"

        if not os.path.exists(sdf_out) or os.path.getsize(sdf_out) < 10:
            return None, "Could not generate 3D structure (RDKit + obabel both failed)"

    # ── Step 3: SDF → PDB via obabel (no -h, preserve SDF state) ────────────
    try:
        _sp.run(
            ["obabel", sdf_out, "-opdb", "-O", output_pdb],
            capture_output=True, text=True, timeout=60, cwd=cwd
        )
    except Exception as e:
        return None, f"obabel SDF→PDB error: {e}"

    if not os.path.exists(output_pdb):
        return None, "obabel could not write PDB file"

    return charge, None


def run_antechamber(mol_in, prep_out, frcmod_out, charge, workdir,
                    charge_method="bcc", residue_name="GST"):
    """Run antechamber + parmchk2; returns (ok, log)."""
    log = ""
    ext = os.path.splitext(mol_in)[1].lower()
    fi_flag = "mdl" if ext == ".sdf" else "pdb"

    cmd_ac = [
        "antechamber",
        "-i", mol_in, "-fi", fi_flag,
        "-o", prep_out, "-fo", "prepi",
        "-rn", residue_name, "-at", "gaff2",
        "-c", charge_method,
        "-nc", str(charge), "-s", "2",
    ]
    rc, out = run_cmd(cmd_ac, cwd=workdir, timeout=1200)
    log += f"=== antechamber ===\n{out}\n"
    if rc != 0:
        return False, log

    rc2, out2 = run_cmd(
        ["parmchk2", "-i", prep_out, "-f", "prepi", "-o", frcmod_out],
        cwd=workdir
    )
    log += f"=== parmchk2 ===\n{out2}\n"
    return (rc2 == 0), log


def antechamber_write_pdb(mol_in, pdb_out, residue_name, workdir):
    """Use antechamber to write a PDB with correct residue name and atom names
    that exactly match the prep file. This avoids the MOL/GST split in tleap.
    Returns (ok, log).
    """
    log = ""
    ext = os.path.splitext(mol_in)[1].lower()
    fi_flag = "mdl" if ext == ".sdf" else "pdb"

    # antechamber -fo pdb writes a PDB with proper residue name + GAFF2 atom names
    rc, out = run_cmd(
        ["antechamber",
         "-i", mol_in, "-fi", fi_flag,
         "-o", pdb_out, "-fo", "pdb",
         "-rn", residue_name, "-at", "gaff2",
         "-dr", "no"],   # -dr no = don't rename, keep as-is
        cwd=workdir, timeout=120
    )
    log += f"=== antechamber PDB ===\n{out}\n"
    if rc == 0 and os.path.exists(pdb_out) and os.path.getsize(pdb_out) > 10:
        return True, log

    # antechamber -fo pdb may not be available in all versions
    # Try obabel + patch residue name
    rc2, out2 = run_cmd(
        ["obabel", mol_in, "-O", pdb_out, "-h"],
        cwd=workdir, timeout=60
    )
    log += f"=== obabel PDB fallback ===\n{out2}\n"
    if rc2 == 0 and os.path.exists(pdb_out):
        fix_pdb_residue_name(pdb_out, residue_name)
        log += f"Residue name patched to {residue_name}\n"
        return True, log

    return False, log


def fix_pdb_residue_name(pdb_path, residue_name):
    """Replace any residue name (MOL, LIG, UNL, UNK, etc.) in a PDB file
    with the given residue_name (e.g. GST). Edits in-place.
    """
    _bad_names = {"MOL", "LIG", "UNL", "UNK", "LGN", "DRG", "CPD", "HET"}
    lines_out = []
    with open(pdb_path) as f:
        for line in f:
            if line.startswith(("ATOM", "HETATM")):
                resn = line[17:20].strip()
                if resn in _bad_names or (resn and resn != residue_name and len(resn) <= 3):
                    # Pad/truncate residue name to 3 chars, right-padded
                    rn3 = residue_name[:3].ljust(3)
                    line = line[:17] + rn3 + line[20:]
            lines_out.append(line)
    with open(pdb_path, "w") as f:
        f.writelines(lines_out)


# ─── Complex Building ─────────────────────────────────────────────────────────

def build_host_guest_complex(host_pdb, guest_pdb, distance, output_pdb):
    """
    SVD-based cavity-axis detection; translate guest by `distance` Å
    along that axis. Returns (ok, log).

    The output PDB includes:
      - Host atoms in chain A
      - Guest atoms in chain B (residue name GST) with CONECT records
        copied from the input guest_pdb so 3D viewers can draw bonds
    """
    try:
        from openmm.app import PDBFile, Modeller
        from openmm import unit

        pdb_host  = PDBFile(host_pdb)
        pdb_guest = PDBFile(guest_pdb)

        host_coords  = np.array(pdb_host.positions.value_in_unit(unit.angstrom))
        guest_coords = np.array(pdb_guest.positions.value_in_unit(unit.angstrom))

        host_center  = host_coords.mean(axis=0)
        _, _, vh     = np.linalg.svd(host_coords - host_center)

        z_axis    = np.array([0., 0., 1.])
        best      = int(np.argmax([abs(np.dot(vh[i], z_axis)) for i in range(3)]))
        normal    = vh[best]

        guest_cent    = guest_coords - guest_coords.mean(axis=0) + host_center
        guest_shifted = guest_cent + normal * distance

        # Write a temporary shifted guest PDB with chain B (avoids residue clash
        # with host chain A, and lets viewers distinguish host vs guest cleanly)
        shifted_pdb = output_pdb + "_tmp_guest.pdb"
        with open(shifted_pdb, "w") as f:
            for i, atom in enumerate(pdb_guest.topology.atoms()):
                x, y, z = guest_shifted[i]
                # Use chain B for guest, residue name GST, residue number 1
                # Element symbol right-justified in cols 77-78
                el = (atom.element.symbol if atom.element else "C")[:2]
                f.write(
                    f"ATOM  {i+1:5d}  {atom.name[:3]:<3s} GST B   1    "
                    f"{x:8.3f}{y:8.3f}{z:8.3f}  1.00  0.00          "
                    f"{el:>2s}\n"
                )
            f.write("END\n")

        pdb_gs = PDBFile(shifted_pdb)
        mod = Modeller(pdb_host.topology, pdb_host.positions)
        mod.add(pdb_gs.topology, pdb_gs.positions)
        with open(output_pdb, "w") as f:
            PDBFile.writeFile(mod.topology, mod.positions, f)

        # ── Append CONECT records for the guest so 3D viewers draw bonds ────
        # OpenMM's PDBFile.writeFile does NOT emit CONECT for non-standard
        # residues by default, leaving guests as disconnected dots in 3Dmol/
        # PyMOL etc.  We extract bonds from the guest topology and append.
        try:
            host_natom = pdb_host.topology.getNumAtoms()
            # Map guest topology atom indices → indices in the merged PDB
            # (host atoms come first, then guest atoms in the same order)
            guest_atoms = list(pdb_gs.topology.atoms())
            # In the output PDB, atom serial numbers start at 1 and increment
            # in topology order: 1..host_natom for host, then guest atoms.
            # PDB CONECT serials are 1-based.
            conect_lines = []
            for bond in pdb_gs.topology.bonds():
                a, b = bond.atom1, bond.atom2
                # Find their position in the guest atom list
                ia = guest_atoms.index(a)
                ib = guest_atoms.index(b)
                # Convert to PDB serial in merged file
                sa = host_natom + ia + 1
                sb = host_natom + ib + 1
                conect_lines.append(f"CONECT{sa:5d}{sb:5d}\n")

            if conect_lines:
                # Insert CONECT records before the END line
                with open(output_pdb) as f:
                    content = f.read()
                if "\nEND\n" in content:
                    content = content.replace(
                        "\nEND\n", "\n" + "".join(conect_lines) + "END\n"
                    )
                elif content.rstrip().endswith("END"):
                    content = content.rstrip()[:-3] + "".join(conect_lines) + "END\n"
                else:
                    content = content + "".join(conect_lines) + "END\n"
                with open(output_pdb, "w") as f:
                    f.write(content)
        except Exception:
            # CONECT generation is best-effort; if it fails the complex is
            # still chemically correct, just visually disconnected.
            pass

        try:
            os.remove(shifted_pdb)
        except OSError:
            pass
        return True, f"Complex saved to {output_pdb}"

    except Exception as e:
        return False, str(e)


# ─── Topology (tleap) ─────────────────────────────────────────────────────────

def write_tleap_script(
    workdir, host_forcefield, host_prep, host_frcmod, host_type,
    water_ff, water_box, box_buf, unit_xy, unit_z, translate_z,
    cx_pdb, out_top, out_crd, out_pdb,
    guest_prep=None, guest_frcmod=None,
):
    """Write tleap input script; return path to script.

    guest_prep / guest_frcmod — explicit paths.  If None, auto-detect:
    scans workdir for any .prep and .frcmod file that is NOT a host file.
    This avoids the hardcoded 'guest.prep' name that fails when antechamber
    writes 'GST.prep' (or any other residue name).
    """
    script = os.path.join(workdir, "tleap_complex.in")

    # ── Auto-detect guest parameter files if not supplied ────────────────────
    def _find_guest_file(ext):
        """Return the first .prep/.frcmod in workdir that isn't a host file."""
        host_stems = {"BCD", "gBCD", "gDMBCD", "gMBCD", "g6tetraHPBCD",
                      "Glycam_06tk", "Glycam_06g-1", "host"}
        for fname in sorted(os.listdir(workdir)):
            if not fname.lower().endswith(ext):
                continue
            stem = os.path.splitext(fname)[0]
            if stem in host_stems:
                continue
            # Skip the host frcmod that was passed in explicitly
            if host_frcmod and os.path.basename(host_frcmod) == fname:
                continue
            if host_prep and os.path.basename(host_prep) == fname:
                continue
            return os.path.join(workdir, fname)
        return None

    if guest_prep is None:
        guest_prep = _find_guest_file(".prep")
    if guest_frcmod is None:
        guest_frcmod = _find_guest_file(".frcmod")

    # Hard fallback — keep old behaviour if detection fails
    if guest_prep is None:
        guest_prep   = os.path.join(workdir, "guest.prep")
    if guest_frcmod is None:
        guest_frcmod = os.path.join(workdir, "guest.frcmod")

    with open(script, "w") as f:
        if host_forcefield == "DFT":
            f.write("source leaprc.gaff2\n")
            f.write(f"source {water_ff}\n\n")
            f.write(f"loadAmberPrep {host_prep}\n")
            f.write(f"loadAmberParams {host_frcmod}\n\n")
        else:
            f.write("source leaprc.protein.ff19SB\n")
            f.write(f"source {water_ff}\n")
            f.write("source leaprc.gaff2\n\n")
            f.write(f"loadAmberPrep {os.path.join(workdir, 'Glycam_06tk.prep')}\n")
            f.write(f"loadAmberParams {os.path.join(workdir, 'Glycam_06g-1.dat')}\n\n")
            f.write('addAtomTypes {\n  { "nv"  "N" "sp2" }\n}\n\n')

        f.write(f"loadAmberPrep {guest_prep}\n")
        f.write(f"loadAmberParams {guest_frcmod}\n\n")
        f.write(f"complex = loadpdb {cx_pdb}\n\n")

        # Ring closure for GLYCAM hosts
        if host_forcefield == "GLYCAM06":
            if host_type in ("BCD", "DMBCD", "HPBCD", "MBCD", "6tetraHPBCD"):
                for i in range(1, 8):
                    f.write(f"bond complex.{i}.O4 complex.{(i%7)+1}.C1\n")
            if host_type == "DMBCD":
                for i in range(1, 8):
                    f.write(f"bond complex.{i}.O6 complex.{i+7}.CH3\n")
                for i in range(1, 8):
                    f.write(f"bond complex.{i}.O2 complex.{i+14}.CH3\n")
            elif host_type == "MBCD":
                for i in range(1, 8):
                    f.write(f"bond complex.{i}.O6 complex.{i+7}.CH3\n")
                for i in range(1, 7):
                    f.write(f"bond complex.{i}.O2 complex.{i+14}.CH3\n")
            elif host_type in ("HPBCD", "6tetraHPBCD"):
                for i, res in [(1, 8), (3, 9), (5, 10), (7, 11)]:
                    f.write(f"bond complex.{i}.O6 complex.{res}.CA\n")

        solvate_arg = str(box_buf)
        f.write(f"\nset complex box {{ {unit_xy} {unit_xy} {unit_z} }}\n")
        f.write(f"translate complex {{ 0, 0, {translate_z} }}\n\n")
        f.write(f"solvateBox complex {water_box} {solvate_arg}\n")
        f.write("setbox complex centers\n\n")
        f.write("addions complex Na+ 0\n")
        f.write("addions complex Cl- 0\n\n")
        f.write(f"savepdb complex {out_pdb}\n")
        f.write(f"saveamberparm complex {out_top} {out_crd}\n\n")
        f.write("quit\n")

    return script


# ─── Minimization & Heating ───────────────────────────────────────────────────

MINIMIZE_HEAT_SCRIPT = """
import sys, os, math
import numpy as np
import parmed as pmd
from openmm.app import *
from openmm import *
from openmm.unit import *

TOP   = "{top}"
CRD   = "{crd}"
RST7  = "{rst7}"

inpcrd = AmberInpcrdFile(CRD)
prmtop = AmberPrmtopFile(TOP, periodicBoxVectors=inpcrd.boxVectors)

system = prmtop.createSystem(
    nonbondedMethod=PME,
    nonbondedCutoff=1.0*nanometer,
    constraints=HBonds,
    rigidWater=True
)
integrator = LangevinMiddleIntegrator(300*kelvin, 1/picosecond, 0.002*picoseconds)
integrator.setConstraintTolerance(1e-5)

# Try GPU first, fall back to CPU
simulation = None
for plat_name in ["CUDA", "OpenCL", "CPU"]:
    try:
        plat = Platform.getPlatformByName(plat_name)
        simulation = Simulation(prmtop.topology, system, integrator, plat)
        print(f"Platform: {{plat_name}}")
        break
    except Exception:
        continue
if simulation is None:
    raise RuntimeError("No OpenMM platform available")

simulation.context.setPositions(inpcrd.positions)

# ─────────────────────────────────────────────────────────────────────
# STEP 1: Minimize WITHOUT restraints (let everything relax)
# ─────────────────────────────────────────────────────────────────────
print("Minimizing (unrestrained)...")
simulation.minimizeEnergy(maxIterations={min_iters})

# Capture post-minimization positions as restraint reference.
# These are used for heating/equilibration so the solute doesn't drift
# while waters thermalise.
pos_min = simulation.context.getState(getPositions=True)\\
            .getPositions(asNumpy=True).value_in_unit(nanometer)

# ─────────────────────────────────────────────────────────────────────
# STEP 2: Add position restraints on SOLUTE heavy atoms only
# (host + guest, NOT water/ions). Reference = post-minimization pos.
# ─────────────────────────────────────────────────────────────────────
SOLVENT_RESN = {{"WAT", "HOH", "TIP3", "OPC", "Na+", "Cl-", "K+", "Mg+", "NA", "CL"}}

k = 1000 * kilojoule_per_mole / nanometer**2  # gentler than 10000 for stability
posres = CustomExternalForce("0.5*k*((x-x0)^2+(y-y0)^2+(z-z0)^2)")
posres.addPerParticleParameter("k")
posres.addPerParticleParameter("x0")
posres.addPerParticleParameter("y0")
posres.addPerParticleParameter("z0")

n_restrained = 0
for atom in prmtop.topology.atoms():
    resn = atom.residue.name.strip().upper()
    if resn in SOLVENT_RESN:
        continue  # never restrain solvent or ions
    if atom.element is None or atom.element.symbol == "H":
        continue  # heavy atoms only
    x, y, z = pos_min[atom.index]
    posres.addParticle(atom.index, [k, x, y, z])
    n_restrained += 1

if n_restrained == 0:
    raise RuntimeError(
        "No solute heavy atoms found to restrain. "
        "Check that the topology has non-solvent residues."
    )

system.addForce(posres)
simulation.context.reinitialize(preserveState=True)
print(f"Restrained {{n_restrained}} solute heavy atoms (k=1000 kJ/mol/nm^2)")

# ─────────────────────────────────────────────────────────────────────
# STEP 3: Heat 0 → 300 K with restraints on
# ─────────────────────────────────────────────────────────────────────
print("Heating 0 -> 300 K...")
simulation.context.setVelocitiesToTemperature(0*kelvin)
for T in [50, 100, 150, 200, 250, 300]:
    integrator.setTemperature(T*kelvin)
    simulation.step({heat_steps})
    print(f"  {{T}} K done")

# ─────────────────────────────────────────────────────────────────────
# STEP 4: NVT equilibration at 300 K with restraints on
# ─────────────────────────────────────────────────────────────────────
print("NVT equilibration (restrained)...")
simulation.step({nvt_steps})

# ─────────────────────────────────────────────────────────────────────
# STEP 5: Production with restraints on (gentle pre-cMD relaxation)
# ─────────────────────────────────────────────────────────────────────
print("Restrained production...")
simulation.step({prod_steps})

# ─────────────────────────────────────────────────────────────────────
# STEP 6: Save final restart (positions, velocities, box)
# ─────────────────────────────────────────────────────────────────────
st2 = simulation.context.getState(getPositions=True, getVelocities=True)
pos_A   = st2.getPositions(asNumpy=True).value_in_unit(nanometer) * 10.0
vel_Aps = st2.getVelocities(asNumpy=True).value_in_unit(nanometer/picosecond) * 10.0

def vlen(v): return float(np.linalg.norm(v))
def vang(u, v):
    c = float(np.dot(u, v) / (vlen(u)*vlen(v)))
    return math.degrees(math.acos(max(-1., min(1., c))))

try:
    a, b, c = st2.getPeriodicBoxVectors(asNumpy=True)
    A = vlen(a)*10; B = vlen(b)*10; C = vlen(c)*10
    alpha = vang(b, c); beta = vang(a, c); gamma = vang(a, b)
except Exception:
    A = B = C = 80; alpha = beta = gamma = 90.0

struct = pmd.load_file(TOP)
struct.coordinates = pos_A
struct.velocities  = vel_Aps
struct.box = [A, B, C, alpha, beta, gamma]
struct.save(RST7, overwrite=True)
print("DONE")
"""


def run_minimize_heat(workdir, top, crd, rst7_out,
                      min_iters=5000, heat_steps=10000,
                      nvt_steps=50000, prod_steps=100000):
    script = MINIMIZE_HEAT_SCRIPT.format(
        top=top, crd=crd, rst7=rst7_out,
        min_iters=min_iters, heat_steps=heat_steps,
        nvt_steps=nvt_steps, prod_steps=prod_steps,
    )
    py_file = os.path.join(workdir, "_min_heat.py")
    with open(py_file, "w") as f:
        f.write(script)
    rc, out = run_cmd([sys.executable, py_file], cwd=workdir, timeout=3600)
    return (rc == 0 and "DONE" in out), out


# ─── LB-PaCS-MD ───────────────────────────────────────────────────────────────

def write_pacsmd_config(workdir, temperature, pressure, timestep_fs,
                        friction, steps_cycle, traj_interval):
    cfg = {
        "temperature": str(temperature),
        "pressure":    str(pressure),
        "timestep":    str(timestep_fs),
        "friction":    str(friction),
        "steps":       str(steps_cycle),
        "traj_interval": str(traj_interval),
    }
    with open(os.path.join(workdir, "config.json"), "w") as f:
        json.dump(cfg, f, indent=2)
    return cfg


def run_pacsmd(workdir, rst7, cycle, candi, host_sel, guest_sel,
               rerun=False, timeout=7200):
    cmd = ["pacs_q_md"]
    if rerun:
        cmd.append("--rerun")
    cmd += [
        "-c", rst7,
        "-cy", str(cycle),
        "-cd", str(candi),
        "-s", host_sel,
        "-s2", guest_sel,
        "-e", "openmm",
        "-cf", "config.json",
    ]
    return run_cmd(cmd, cwd=workdir, timeout=timeout)


# ─── cpptraj helpers ──────────────────────────────────────────────────────────

def run_cpptraj_cv(workdir, top, target_cycle, candi,
                   host_mask, guest_mask):
    """Write and run cpptraj CV script for distance + Rg."""
    script = os.path.join(workdir, "ana_pacsmd.sh")
    dis_out = os.path.join(workdir, "dis.dat")
    rg_out  = os.path.join(workdir, "rg.dat")

    with open(script, "w") as f:
        f.write(f"parm {top}\n")
        for i in range(target_cycle):
            for j in range(1, candi + 1):
                nc = os.path.join(workdir, f"MDrun/{i}/{j}/md{i}_{j}.nc")
                if os.path.exists(nc):
                    f.write(f"trajin {nc}\n")
        f.write(f"\nreference {os.path.join(workdir, 'complex.crd')}\n")
        f.write("autoimage\n")
        f.write(f"distance DIH1 {host_mask} {guest_mask} out {dis_out}\n")
        nosolv = "!(:GST,WAT,TIP3P,OPC,HOH,Na+,Cl-)"
        f.write(f"radgyr out {rg_out} {nosolv} mass\n")

    return run_cmd(["cpptraj", "-i", script], cwd=workdir)


def run_cpptraj_cmd_analysis(workdir, top, dcd, crd, host_mask, guest_mask):
    """cpptraj analysis for cMD: distance, Rg, RMSD, reimage DCD."""
    script = os.path.join(workdir, "ana_cMD.sh")
    center_mask = f"{host_mask},{guest_mask}"

    with open(script, "w") as f:
        f.write(f"parm {top}\n")
        f.write(f"trajin {dcd}\n")
        f.write(f"reference {crd}\n")
        f.write(f"center {center_mask} mass origin\n")
        f.write("image origin center familiar\n")
        f.write(f"distance DIH1 {host_mask} {guest_mask} out {workdir}/dis.dat\n")
        f.write(f"radgyr out {workdir}/rg.dat {host_mask} mass\n")
        f.write(f"rms rmsd {center_mask} out {workdir}/rmsd.dat\n")
        f.write(f"trajout {workdir}/md-cMD.dcd\n")

    return run_cmd(["cpptraj", "-i", script], cwd=workdir)


def extract_last_frames(workdir, top, traj, n_frames, out_nc):
    """Use cpptraj to extract last N frames."""
    script = os.path.join(workdir, "_extract_last.sh")
    with open(script, "w") as f:
        f.write(f"parm {top}\n")
        f.write(f"trajin {traj} -{n_frames} last\n")
        f.write(f"reference {os.path.join(workdir, 'complex.crd')}\n")
        f.write(f"trajout {out_nc} netcdf\n")
        f.write("go\n")
    return run_cmd(["cpptraj", "-i", script], cwd=workdir)


# ─── Classical MD ─────────────────────────────────────────────────────────────

CMD_SCRIPT = """
import sys
from openmm.app import *
from openmm import *
from openmm.unit import *

inpcrd = AmberInpcrdFile("{rst}")
prmtop = AmberPrmtopFile("{top}", periodicBoxVectors=inpcrd.boxVectors)
system = prmtop.createSystem(
    nonbondedMethod=PME,
    nonbondedCutoff=1.0*nanometer,
    constraints=HBonds,
    rigidWater=True
)
system.addForce(MonteCarloBarostat({pressure}*bar, {temperature}*kelvin, 25))
integrator = LangevinMiddleIntegrator(
    {temperature}*kelvin, 1/picosecond, 0.002*picoseconds
)
steps = int({length_ns} * 1000000 / 2)

for plat_name in ["CUDA", "OpenCL", "CPU"]:
    try:
        plat = Platform.getPlatformByName(plat_name)
        simulation = Simulation(prmtop.topology, system, integrator, plat)
        break
    except Exception:
        continue

print(f"Platform: {{simulation.context.getPlatform().getName()}}")
simulation.context.setPositions(inpcrd.positions)
simulation.context.setVelocitiesToTemperature({temperature}*kelvin)
simulation.reporters.append(DCDReporter("{dcd_out}", {traj_int}))
simulation.reporters.append(StateDataReporter(
    sys.stdout, {report_int},
    step=True, potentialEnergy=True, temperature=True,
    remainingTime=True, totalSteps=steps
))
simulation.step(steps)
print("CMD_DONE")
"""


def run_cmd_simulation(workdir, top, rst, dcd_out,
                       length_ns=2.0, temperature=300.0, pressure=1.0,
                       traj_int=5000, report_int=5000, timeout=86400):
    script = CMD_SCRIPT.format(
        top=top, rst=rst, dcd_out=dcd_out,
        length_ns=length_ns, temperature=temperature, pressure=pressure,
        traj_int=traj_int, report_int=report_int,
    )
    py_file = os.path.join(workdir, "_cmd_run.py")
    with open(py_file, "w") as f:
        f.write(script)
    rc, out = run_cmd([sys.executable, py_file], cwd=workdir, timeout=timeout)
    return (rc == 0 and "CMD_DONE" in out), out


def extract_last_rst_from_pacsmd(workdir, top, sum_nc):
    """Extract last frame of sum.nc into last.rst via cpptraj."""
    script = os.path.join(workdir, "_last_pacsmd.sh")
    with open(script, "w") as f:
        f.write(f"parm {top}\n")
        f.write(f"trajin {sum_nc} lastframe\n")
        f.write(f"trajout {workdir}/last.rst restart\n")
        f.write("go\n")
    return run_cmd(["cpptraj", "-i", script], cwd=workdir)


# ─── MM-PBSA/GBSA ─────────────────────────────────────────────────────────────

def run_mmpbsa(workdir, top, traj_file, n_frames, igb, salt_conc,
               do_pb=True, label="run"):
    """Run ante-MMPBSA + MMPBSA.py; return (ok, log, gb_result, pb_result)."""
    log = ""
    out_dat = os.path.join(workdir, f"FINAL_RESULTS_MMPBSA_{label}.dat")
    last_nc = os.path.join(workdir, "last.nc")
    mbondi  = MBONDI_MAP.get(str(igb), "mbondi2")

    # Step 1: extract last frames
    rc1, out1 = extract_last_frames(workdir, top, traj_file, n_frames, last_nc)
    log += out1
    if rc1 != 0:
        return False, log, None, None

    # Step 2: ante-MMPBSA
    com_prmtop = os.path.join(workdir, "com.prmtop")
    rec_prmtop = os.path.join(workdir, "rec.prmtop")
    lig_prmtop = os.path.join(workdir, "ligand.prmtop")
    rc2, out2 = run_cmd(
        ["bash", "-lc",
         f"source /usr/local/amber.sh && "
         f"ante-MMPBSA.py -p {top} "
         f"-c {com_prmtop} -r {rec_prmtop} -l {lig_prmtop} "
         f"-s :WAT:Na+:Cl- -n :GST --radii {mbondi}"],
        cwd=workdir
    )
    log += out2

    # Step 3: write mmpbsa.in
    pb_block = ""
    if do_pb:
        pb_block = (
            f"&pb\n  indi=1.0, exdi=80.0, scale=2.0, linit=1000, prbrad=1.4, "
            f"istrng={salt_conc}, inp=1, cavity_surften=0.0072, "
            f"cavity_offset=0.0, radiopt=0,\n/\n"
        )
    with open(os.path.join(workdir, "mmpbsa.in"), "w") as f:
        f.write(
            f"&general\n  endframe={n_frames}, interval=1, "
            f"strip_mask=:WAT:Na+:Cl-:Mg+:K+,\n/\n"
            f"&gb\n  igb={igb}, saltcon={salt_conc},\n/\n"
            + pb_block
        )

    # Step 4: run MMPBSA.py
    rc3, out3 = run_cmd(
        ["bash", "-lc",
         f"source /usr/local/amber.sh && "
         f"MMPBSA.py -O -i {workdir}/mmpbsa.in -o {out_dat} "
         f"-sp {top} -cp {com_prmtop} -rp {rec_prmtop} "
         f"-lp {lig_prmtop} -y {last_nc}"],
        cwd=workdir
    )
    log += out3

    gb_result, pb_result = parse_mmpbsa_results(out_dat)
    return (rc3 == 0), log, gb_result, pb_result


def parse_mmpbsa_results(dat_path):
    """Parse MMPBSA.py output; return (gb, pb) where each is (mean, stderr) or None."""
    gb, pb, mode = None, None, None
    if not os.path.exists(dat_path):
        return None, None
    with open(dat_path) as f:
        for line in f:
            s = line.strip()
            if s == "GENERALIZED BORN:":    mode = "GB"
            elif s == "POISSON BOLTZMANN:": mode = "PB"
            elif s.startswith("DELTA TOTAL"):
                parts = s.split()
                if len(parts) >= 4:
                    try:
                        mean, stderr = float(parts[2]), float(parts[3])
                        if mode == "GB": gb = (mean, stderr)
                        elif mode == "PB": pb = (mean, stderr)
                    except ValueError:
                        pass
    return gb, pb


def parse_mmpbsa_components(dat_path):
    """
    Parse detailed energy components from MMPBSA output for the bar chart.
    Returns (gb_dict, pb_dict).
    """
    gb = {"VDWAALS": None, "EEL": None, "EGB": None, "ESURF": None, "DELTA TOTAL": None}
    pb = {"VDWAALS": None, "EEL": None, "EPB": None, "ESURF": None,
          "ENPOLAR": None, "DELTA TOTAL": None}
    mode = None
    if not os.path.exists(dat_path):
        return gb, pb
    import re
    with open(dat_path) as f:
        for line in f:
            t = line.strip()
            if t == "GENERALIZED BORN:":    mode = "GB"; continue
            if t == "POISSON BOLTZMANN:":   mode = "PB"; continue
            if mode not in ("GB", "PB"):    continue
            parts = re.split(r"\s+", t)
            if len(parts) < 2: continue
            key = parts[0]
            if key in ("VDWAALS", "EEL", "EGB", "EPB", "ESURF", "ENPOLAR"):
                try:
                    val = float(parts[1])
                    if mode == "GB" and key in gb: gb[key] = val
                    if mode == "PB" and key in pb: pb[key] = val
                except ValueError:
                    pass
            if key == "DELTA" and len(parts) >= 3 and parts[1] == "TOTAL":
                try:
                    val = float(parts[2])
                    if mode == "GB": gb["DELTA TOTAL"] = val
                    elif mode == "PB": pb["DELTA TOTAL"] = val
                except ValueError:
                    pass
    return gb, pb


# ─── Results ZIP ──────────────────────────────────────────────────────────────

RESULT_FILES = [
    "complex.top", "complex.crd", "complex.pdb",
    "complex_leap.pdb", "host.pdb", "guest.pdb",
    "guest.prep", "guest.frcmod",
    "last_frame.rst7", "sum.nc", "md.dcd", "md-cMD.dcd",
    "dis.dat", "rg.dat", "rmsd.dat", "dis_plot.dat",
    "FINAL_RESULTS_MMPBSA_LB.dat",
    "FINAL_RESULTS_MMPBSA_cMD.dat",
    "DBFE_results.json",
]


def create_results_zip(workdir, zip_path=None):
    if zip_path is None:
        zip_path = os.path.join(workdir, "DFDD_results.zip")
    added = []
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for fname in RESULT_FILES:
            fpath = os.path.join(workdir, fname)
            if os.path.exists(fpath):
                zf.write(fpath, arcname=fname)
                added.append(fname)
        # also add all .png files
        for f in os.listdir(workdir):
            if f.endswith(".png") and f not in added:
                zf.write(os.path.join(workdir, f), arcname=f)
                added.append(f)
    return zip_path, added
