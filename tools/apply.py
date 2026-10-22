"""Add new report entries (and record skipped files), then rebuild the site.

  python3 tools/apply.py new.json

new.json:
{
  "reports": [ {"ridoh_id": "...", "facility_key": "...", "entry": {date, type, tier, no_findings, headline, paragraphs, link}} ],
  "handled": [ {"ridoh_id": "...", "facility_key": "...", "status": "same_survey" | "excluded", "note": "why"} ],
  "relink": [ {"ridoh_id": "...", "old_file_id": "...", "note": "why"} ]
}
"same_survey" = this file is another copy of a survey already on the site (for example the plan of
correction for a statement of deficiencies already listed). "excluded" = deliberately left off.
"relink" = RIDOH re-posted a report already on the site as a new file; the existing entry keeps its
summary and its link moves to the new file.
"""
import json
import subprocess
import sys
from pathlib import Path

from alf import DATA, HANDLED, NO_FINDINGS, REPORT_KEYS, TIER_RANK, TYPES, file_id, load, recompute, save


def main():
    new = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    facilities = load(DATA)
    by_key = {f["key"]: f for f in facilities}
    handled = load(HANDLED) if HANDLED.exists() else {}
    problems = []
    for item in new.get("reports", []):
        e, rid, key = item["entry"], item["ridoh_id"], item["facility_key"]
        where = f"{key} {e.get('date')}"
        if key not in by_key:
            problems.append(f"{where}: unknown facility key")
            continue
        if set(e) != REPORT_KEYS:
            problems.append(f"{where}: fields must be exactly {sorted(REPORT_KEYS)}")
            continue
        if file_id(e["link"]) != rid:
            problems.append(f"{where}: link does not point to file {rid}")
        if e["type"] not in TYPES:
            problems.append(f"{where}: type must be one of {TYPES}")
        if e["no_findings"]:
            if e["headline"] != NO_FINDINGS or e["paragraphs"] or e["tier"] is not None:
                problems.append(f"{where}: a no-findings entry needs headline {NO_FINDINGS!r}, no findings, tier null")
        else:
            if not e["headline"].strip() or not e["paragraphs"]:
                problems.append(f"{where}: needs a headline and at least one finding")
            elif any(p.get("tier") not in TIER_RANK or not p.get("text", "").strip() for p in e["paragraphs"]):
                problems.append(f"{where}: every finding needs text and a severity")
            elif e["tier"] != max(e["paragraphs"], key=lambda p: TIER_RANK[p["tier"]])["tier"]:
                problems.append(f"{where}: report severity must equal its most severe finding")
        text = e["headline"] + " ".join(p.get("text", "") for p in e["paragraphs"])
        if "—" in text:
            problems.append(f"{where}: contains an em dash; use a colon or a period")
    for h in new.get("handled", []):
        if h.get("status") not in ("same_survey", "excluded") or not h.get("note"):
            problems.append(f"handled {h.get('ridoh_id')}: needs status same_survey or excluded, and a note")
    link_of = {}
    for f in facilities:
        for r in f["reports"]:
            link_of[file_id(r["link"])] = r
    for x in new.get("relink", []):
        if x.get("old_file_id") not in link_of or not x.get("note"):
            problems.append(f"relink {x.get('ridoh_id')}: old file not on the site, or no note")
    if problems:
        print("\n".join("ERROR: " + p for p in problems))
        sys.exit(1)

    for item in new.get("reports", []):
        by_key[item["facility_key"]]["reports"].append(item["entry"])
    for x in new.get("relink", []):
        link_of[x["old_file_id"]]["link"] = "https://drive.google.com/file/d/" + x["ridoh_id"] + "/view"
    for h in new.get("handled", []):
        handled[h["ridoh_id"]] = {"status": h["status"], "facility_key": h.get("facility_key"), "note": h["note"]}
    save(recompute(facilities), DATA)
    save(dict(sorted(handled.items())), HANDLED)
    print(f"added {len(new.get('reports', []))} report(s); relinked {len(new.get('relink', []))}; "
          f"recorded {len(new.get('handled', []))} skipped file(s)")
    subprocess.run([sys.executable, str(Path(__file__).with_name("build.py"))], check=True)


if __name__ == "__main__":
    main()
