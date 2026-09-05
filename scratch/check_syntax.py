import subprocess
import os

html = """<!DOCTYPE html>
<html>
<head></head>
<body>
<script src="../extension/config.js"></script>
<script src="../extension/content.js"></script>
</body>
</html>"""

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
scratch_dir = os.path.join(REPO_ROOT, "scratch")
html_path = os.path.join(scratch_dir, "test_page.html")
with open(html_path, "w", encoding="utf-8") as f:
    f.write(html)

chrome = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
proc = subprocess.run([
    chrome,
    "--headless=new",
    "--enable-logging=stderr",
    "--v=1",
    "--allow-file-access-from-files",
    html_path
], capture_output=True, text=True)

print("Return code:", proc.returncode)
print("STDOUT:", proc.stdout[:500])
print("STDERR:", proc.stderr[:500])
