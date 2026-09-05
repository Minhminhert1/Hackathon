import os
import subprocess

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEBUG_HTML = os.path.join(REPO_ROOT, "scratch", "debug_test.html")

html = """<!DOCTYPE html>
<html>
<head></head>
<body>
<div id="conversation-container">
  <div class="ChatroomName">FXVN</div>
  <div class="incoming-message" data-message-id="msg-101" data-sender-name="Nguyet Anh Phan" data-company="Taipei Fubon" data-timestamp="11:05:37" data-date="5/9/2026">
    <div data-testid="parsed-raw-message">tks bạn iu</div>
  </div>
</div>
<script>
window.onerror = function(msg, url, line) {
  console.log("JS_ERROR: " + msg + " at " + line);
};
</script>
<script src="../extension/config.js"></script>
<script src="../extension/content.js"></script>
<script>
console.log("SEEN_IDS_LENGTH:", typeof seenMessageIds !== 'undefined' ? seenMessageIds.size : 'undefined');
console.log("PENDING_QUEUE:", typeof pendingQueue !== 'undefined' ? pendingQueue.length : 'undefined');
</script>
</body>
</html>"""

with open(DEBUG_HTML, "w", encoding="utf-8") as f:
    f.write(html)

cmd = [
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    "--headless=new",
    "--enable-logging=stderr",
    "--v=1",
    "--allow-file-access-from-files",
    DEBUG_HTML
]

proc = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
print("STDERR:")
for line in proc.stderr.splitlines():
    if "CONSOLE" in line or "JS_ERROR" in line:
        print(line)
