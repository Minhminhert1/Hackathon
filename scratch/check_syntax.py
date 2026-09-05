import subprocess
import os

from _chrome import find_chrome

html = """<!DOCTYPE html>
<html>
<head></head>
<body>
<script src="../extension/config.js"></script>
<script src="../extension/content.js"></script>
<script>
setTimeout(() => {
  window.close();
}, 1500);
</script>
</body>
</html>"""

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
scratch_dir = os.path.join(REPO_ROOT, "scratch")
html_path = os.path.join(scratch_dir, "test_page.html")
with open(html_path, "w", encoding="utf-8") as f:
    f.write(html)

chrome = find_chrome()
cmd = [
    chrome,
    "--headless=new",
    "--enable-logging=stderr",
    "--v=1",
    "--allow-file-access-from-files",
    html_path
]

try:
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
    returncode, stdout, stderr = proc.returncode, proc.stdout, proc.stderr
except subprocess.TimeoutExpired as exc:
    # Without this the script hangs forever when the fixture fails to close.
    print("WARNING: Chrome did not exit within 15s; showing partial output.")
    returncode, stdout, stderr = None, exc.stdout or "", exc.stderr or ""

print("Return code:", returncode)
print("STDOUT:", stdout[:500])
print("STDERR:", stderr[:500])
