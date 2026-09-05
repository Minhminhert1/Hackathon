"""Locate a Chrome/Chromium binary for the headless scratch tests.

Set CHROME_BIN to point at a specific browser; otherwise the first candidate
that exists on this machine wins.
"""
import os
import shutil
import sys

WINDOWS_CANDIDATES = [
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    os.path.join(os.environ.get("LOCALAPPDATA", ""), r"Google\Chrome\Application\chrome.exe"),
]
MACOS_CANDIDATES = [
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
]
ON_PATH = ["google-chrome", "google-chrome-stable", "chromium", "chromium-browser"]


def find_chrome():
    """Return a usable Chrome/Chromium path, or exit with instructions."""
    override = os.environ.get("CHROME_BIN")
    if override:
        return override

    if sys.platform == "win32":
        candidates = WINDOWS_CANDIDATES
    elif sys.platform == "darwin":
        candidates = MACOS_CANDIDATES
    else:
        candidates = []

    for path in candidates:
        if path and os.path.isfile(path):
            return path

    for name in ON_PATH:
        found = shutil.which(name)
        if found:
            return found

    raise SystemExit(
        "Chrome not found. Install Chrome, or set CHROME_BIN to the executable:\n"
        '  Windows: set CHROME_BIN="C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe"\n'
        "  macOS:   export CHROME_BIN='/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'\n"
        "  Linux:   export CHROME_BIN=/usr/bin/google-chrome"
    )
