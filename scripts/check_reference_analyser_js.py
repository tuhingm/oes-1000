from pathlib import Path
import re
import subprocess
import tempfile

html_path = Path(__file__).resolve().parents[1] / "reference-analyser" / "index.html"
html = html_path.read_text(encoding="utf-8")
scripts = re.findall(r"<script(?:\\s[^>]*)?>([\\s\\S]*?)</script>", html, flags=re.IGNORECASE)
if not scripts:
    raise SystemExit("No inline JavaScript block found in Reference Analyser.")
source = scripts[-1]
with tempfile.NamedTemporaryFile("w", suffix=".js", encoding="utf-8") as handle:
    handle.write(source)
    handle.flush()
    result = subprocess.run(["node", "--check", handle.name], check=False)
if result.returncode:
    raise SystemExit(result.returncode)
print("Reference Analyser inline JavaScript syntax: OK")
