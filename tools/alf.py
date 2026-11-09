"""Shared helpers for the ALF inspections site data.

data/facilities.json is the master copy of everything the site shows.
tools/build.py writes it into index.html; never edit the data in index.html by hand.
"""
import datetime
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
# Kinds of problem a finding can be about, for the "Repeat problems" box: a residence cited for the
# same kind at 3 or more inspections in the last 3 years. Every finding from the last 3 years has a
# "topics" list (empty when none fits). index.html has the same keys and labels.
TOPICS = {
    "medication_errors": "Medication errors",          # wrong drug, dose, resident, or time; a dose missed or charted but not given
    "elopement": "Elopement and exit-seeking",         # a resident got out or tried to; exits or alarms not working; plan didn't cover it
    "care_plans": "Assessments and care plans",        # comprehensive assessments, nurse reviews, service plans: missing, late, wrong
    "abuse": "Abuse, neglect, and resident-to-resident harm",  # including not reporting or investigating it, and taking residents' money
    "kitchen": "Kitchen and food safety",              # food code, food safety manager, food service training, ordered diets and textures
    "infection_control": "Infection control",          # infection control policies and practice, outbreaks, staff health screening
    "wounds": "Pressure sores and wound care",         # wounds or skin not checked, treated, or tracked
}
REPEAT_MIN = 3  # inspections (distinct report dates) with the same topic

BADGE_WINDOW_YEARS = 3  # badges reflect only reports from this many years back; index.html applies the same rule live


def badge_cutoff(today=None):
    """ISO date BADGE_WINDOW_YEARS before today (Feb 29 becomes Feb 28)."""
    t = today or datetime.date.today()
    try:
        c = t.replace(year=t.year - BADGE_WINDOW_YEARS)
    except ValueError:
        c = t.replace(year=t.year - BADGE_WINDOW_YEARS, day=28)
    return c.isoformat()
TYPES = [
    "Complaint/Incident Investigation",
    "Routine/Biennial Inspection",
    "Routine/Biennial Inspection, Complaint/Incident Investigation",
    "Complaint/Incident Investigation (Follow-Up)",
    "Off-site review",   # RIDOH reviewed documents without visiting, usually to confirm a plan of correction
]
# Working notes that must never reach the public site (checked by build.py).
NOTE_RE = re.compile(r"\?\)|\((does not|doesn.t) (indicate|say)|\b(Most serious|most serious)\s*\n|duplicate\?|appears to be (a )?duplicate|duplicate w/|-->|\(\?\)|\?\?|\[SEE |\[doesn'?t say\]|\bTBD\b|_x00[0-9A-F]{2}_", re.I)


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
    """Report order, counts, most recent date, and badge all follow from the reports.

    The badge looks only at reports from the last BADGE_WINDOW_YEARS years. Older reports
    stay on the site but no longer change the badge."""
    cutoff = badge_cutoff()
    for f in facilities:
        f["reports"].sort(key=lambda r: r["date"], reverse=True)  # stable: same-date order is kept
        f["report_count"] = len(f["reports"])
        f["most_recent_date"] = f["reports"][0]["date"] if f["reports"] else None
        recent = [r for r in f["reports"] if r["date"] >= cutoff]
        top = max((TIER_RANK.get(r["tier"], 0) for r in recent), default=0)
        if top:
            f["badge"] = {3: "most_serious", 2: "serious"}.get(top, "minor")
        else:  # no findings at all in the window: clean if there are reports to say so
            f["badge"] = "clean" if recent else "minor"
    return facilities
