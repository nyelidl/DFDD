# ─────────────────────────────────────────────────────────────────────────────
# DFDD — Colab launch cell
#
# HOW TO USE:
#   Cell 1 (run alone, then wait for kernel restart):
#       !pip install -q condacolab
#       import condacolab
#       condacolab.install()        # ← triggers kernel restart — this is normal
#
#   Cell 2 (run after kernel restarts):
#       (paste everything below this comment and run it)
# ─────────────────────────────────────────────────────────────────────────────

APP_FILE  = "DFDD/st/app.py"
REPO_DIR  = "DFDD"
PORT      = "8501"

import os, subprocess, time, re
import qrcode
from IPython.display import display, Markdown

# ── Clone repo if not already present ────────────────────────────────────────
if not os.path.exists(REPO_DIR):
    print("Cloning DFDD repository…")
    subprocess.run(
        ["git", "clone", "-q", "https://github.com/nyelidl/DFDD.git"],
        check=True
    )
    print("✓ Repo cloned")
else:
    print(f"✓ {REPO_DIR}/ already exists — skipping clone")

# ── pip install streamlit + qrcode (lightweight, fast) ───────────────────────
subprocess.run(
    ["pip", "install", "-q", "streamlit", "qrcode[pil]"],
    check=True
)
print("✓ streamlit + qrcode ready")

# ── Install cloudflared ───────────────────────────────────────────────────────
cf_bin = "/usr/local/bin/cloudflared"
if not os.path.exists(cf_bin):
    subprocess.run([
        "wget", "-q",
        "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64",
        "-O", cf_bin
    ], check=True)
    os.chmod(cf_bin, 0o755)
    print("✓ cloudflared installed")
else:
    print("✓ cloudflared already present")

# ── Start Streamlit ───────────────────────────────────────────────────────────
print(f"\nStarting Streamlit on port {PORT}…")
streamlit_proc = subprocess.Popen(
    ["streamlit", "run", APP_FILE,
     f"--server.port={PORT}",
     "--server.headless=true"],
    stdout=subprocess.DEVNULL,
    stderr=subprocess.DEVNULL,
)
time.sleep(8)

# ── Start Cloudflare tunnel ───────────────────────────────────────────────────
tunnel_proc = subprocess.Popen(
    ["cloudflared", "tunnel", "--url", f"http://localhost:{PORT}"],
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,
)

url = None
for line in tunnel_proc.stdout:
    line = line.decode("utf-8", errors="ignore")
    match = re.search(r'https://[\w\-]+\.trycloudflare\.com', line)
    if match:
        url = match.group(0)
        break

if url:
    time.sleep(3)
    print(f"\n✅ Open your app here 👉 {url}\n")
    display(Markdown(f"## [▶ Open DFDD app]({url})"))
    display(Markdown("### Scan to open on phone"))
    qr = qrcode.make(url)
    display(qr)
else:
    print("❌ Could not get a Cloudflare URL. Check cloudflared output.")
