import os
import subprocess
import sys

from _chrome import find_chrome

sys.stdout.reconfigure(encoding='utf-8')

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

cmd = [
    find_chrome(),
    "--headless=new",
    "--enable-logging=stderr",
    "--v=1",
    "--allow-file-access-from-files",
    os.path.join(REPO_ROOT, "scratch", "test_switch.html")
]

proc = subprocess.run(cmd, capture_output=True, timeout=5)
stderr_text = proc.stderr.decode("utf-8", errors="ignore")
print("CHROME LOGS:")
for line in stderr_text.splitlines():
    if "CONSOLE" in line:
        print(line)
