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

def smiles_to_3d_pdb(smiles, output_pdb, output_sdf=None):
    """Convert SMILES → 3D PDB + SDF using RDKit. Returns (charge, error)."""
    try:
        from rdkit import Chem
        from rdkit.Chem import AllChem

        mol = Chem.MolFromSmiles(smiles.strip())
        if mol is None:
            return None, "Invalid SMILES"
        molH = Chem.AddHs(mol)

        # Never pass a params object — conda-forge RDKit has an ABI mismatch
        # with ETKDGv3()/ETKDG() across some builds.  Keyword-only calls are safe.
        rc = AllChem.EmbedMolecule(
            molH,
            useExpTorsionAnglePrefs=True,
            useBasicKnowledge=True,
            randomSeed=42,
        )
        if rc != 0:
            rc = AllChem.EmbedMolecule(molH, useRandomCoords=True, randomSeed=42)
        if rc != 0:
            return None, "3D embedding failed — try a different SMILES or upload a file"

        try:
            AllChem.UFFOptimizeMolecule(molH)
        except Exception:
            pass  # optimisation is optional

        charge = Chem.GetFormalCharge(molH)
        Chem.MolToPDBFile(molH, output_pdb)
        if output_sdf:
            w = Chem.SDWriter(output_sdf)
            w.write(molH)
            w.close()
        return charge, None

    except Exception as e:
        return None, str(e)


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


# ─── Complex Building ─────────────────────────────────────────────────────────

def build_host_guest_complex(host_pdb, guest_pdb, distance, output_pdb):
    """
    SVD-based cavity-axis detection; translate guest by `distance` Å
    along that axis. Returns (ok, log).
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

        shifted_pdb = output_pdb + "_tmp_guest.pdb"
        with open(shifted_pdb, "w") as f:
            for i, atom in enumerate(pdb_guest.topology.atoms()):
                x, y, z = guest_shifted[i]
                f.write(
                    f"ATOM  {i+1:5d} {atom.name:>4s} GST A   1    "
                    f"{x:8.3f}{y:8.3f}{z:8.3f}  1.00  0.00           "
                    f"{atom.element.symbol:>2s}\n"
                )
            f.write("END\n")

        pdb_gs = PDBFile(shifted_pdb)
        mod = Modeller(pdb_host.topology, pdb_host.positions)
        mod.add(pdb_gs.topology, pdb_gs.positions)
        with open(output_pdb, "w") as f:
            PDBFile.writeFile(mod.topology, mod.positions, f)

        os.remove(shifted_pdb)
        return True, f"Complex saved to {output_pdb}"

    except Exception as e:
        return False, str(e)


# ─── Topology (tleap) ─────────────────────────────────────────────────────────

def write_tleap_script(
    workdir, host_forcefield, host_prep, host_frcmod, host_type,
    water_ff, water_box, box_buf, unit_xy, unit_z, translate_z,
    cx_pdb, out_top, out_crd, out_pdb
):
    """Write tleap input script; return path to script."""
    script = os.path.join(workdir, "tleap_complex.in")
    guest_prep   = os.path.join(workdir, "guest.prep")
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
simulation = Simulation(prmtop.topology, system, integrator)
simulation.context.setPositions(inpcrd.positions)

# Position restraints — heavy atoms of first 30 residues
k = 10000 * kilojoule_per_mole / nanometer**2
posres = CustomExternalForce("0.5*k*((x-x0)^2+(y-y0)^2+(z-z0)^2)")
posres.addPerParticleParameter("k")
posres.addPerParticleParameter("x0")
posres.addPerParticleParameter("y0")
posres.addPerParticleParameter("z0")

pos0 = simulation.context.getState(getPositions=True)\\
         .getPositions(asNumpy=True).value_in_unit(nanometer)

n_restrained = 0
for atom in prmtop.topology.atoms():
    if atom.residue.index >= 30:
        break
    if atom.element and atom.element.symbol != "H":
        x, y, z = pos0[atom.index]
        posres.addParticle(atom.index, [k, x, y, z])
        n_restrained += 1

system.addForce(posres)
simulation.context.reinitialize(preserveState=True)
print(f"Restrained {{n_restrained}} heavy atoms")

print("Minimizing...")
simulation.minimizeEnergy(maxIterations={min_iters})
print("Heating 0 → 300 K...")
simulation.context.setVelocitiesToTemperature(0*kelvin)
for T in [50, 100, 150, 200, 250, 300]:
    integrator.setTemperature(T*kelvin)
    simulation.step({heat_steps})
    print(f"  {{T}} K done")

print("NVT equilibration...")
simulation.step({nvt_steps})
print("Restrained production...")
simulation.step({prod_steps})

# Save restart
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
