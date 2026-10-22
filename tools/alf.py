"""Shared helpers for the ALF inspections site data.

data/facilities.json is the master copy of everything the site shows.
tools/build.py writes it into index.html; never edit the data in index.html by hand.
"""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "facilities.json"
HANDLED = ROOT / "data" / "handled.json"
FOLDER_MAP = ROOT / "data" / "folder_map.json"
INDEX = ROOT / "index.html"

SCRIPT_RE = re.compile(r'(<script id="facility-data" type="application/json">)(.*?)(</script>)', re.S)
TIER_RANK = {"minor": 1, "serious": 2, "most_serious": 3}
REPORT_KEYS = {"date", "type", "tier", "no_findings", "headline", "paragraphs", "link"}
NO_FINDINGS = "No deficiencies identified"
TYPES = [
    "Complaint/Incident Investigation",
    "Routine/Biennial Inspection",
    "Routine/Biennial Inspection, Complaint/Incident Investigation",
    "Complaint/Incident Investigation (Follow-Up)",
]


def file_id(link):
    """The Google Drive file ID inside a report link."""
    m = re.search(r"/d/([A-Za-z0-9_-]{20,})", link or "") or re.search(r"[?&]id=([A-Za-z0-9_-]{20,})", link or "")
    return m.group(1) if m else None


def load(path=DATA):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def save(obj, path):
    Path(path).write_text(json.dumps(obj, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")


def compact(facilities):
    """Exactly how the data is written inside index.html."""
    return json.dumps(facilities, separators=(",", ":"), ensure_ascii=False)


def from_index(path=INDEX):
    m = SCRIPT_RE.search(Path(path).read_text(encoding="utf-8"))
    if not m:
        raise SystemExit("facility-data script not found in index.html")
    return json.loads(m.group(2))


def recompute(facilities):
    """Report order, counts, most recent date, and badge all follow from the reports."""
    for f in facilities:
        f["reports"].sort(key=lambda r: r["date"], reverse=True)  # stable: same-date order is kept
        f["report_count"] = len(f["reports"])
        f["most_recent_date"] = f["reports"][0]["date"] if f["reports"] else None
        if f.get("badge") != "unlicensed":
            top = max((TIER_RANK.get(r["tier"], 0) for r in f["reports"]), default=0)
            f["badge"] = {3: "most_serious", 2: "serious"}.get(top, "minor")
    return facilities
