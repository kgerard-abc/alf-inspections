"""List RIDOH reports that have reached the alf-reports repo but aren't handled yet.

  python3 tools/pending.py ../alf-reports            JSON list of reports waiting
  python3 tools/pending.py ../alf-reports --map      rebuild data/folder_map.json from the site and the log

A report is waiting when the collector sent it to GitHub, its file is in incoming/,
it isn't on the site, and it isn't listed in data/handled.json.
"""
import argparse
import csv
import datetime
import json
import re
import sys
from pathlib import Path

from alf import FOLDER_MAP, HANDLED, file_id, load, save


def parse_exit_date(name):
    m = re.search(r"(\d{1,2})[-./](\d{1,2})[-./](\d{2,4})", name)
    if not m:
        return None
    mo, dy, yr = (int(x) for x in m.groups())
    yr += 2000 if yr < 100 else 0
    try:
        return datetime.date(yr, mo, dy).isoformat()
    except ValueError:
        return None


def kind(name):
    n = name.upper()
    if re.search(r"\bPOC\b|PLAN OF CORRECTION", n):
        return "POC"
    if re.search(r"\bSOD\b|STATEMENT OF DEFICIENC", n):
        return "SOD"
    return "unknown"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("reports_repo")
    ap.add_argument("--map", action="store_true")
    args = ap.parse_args()
    repo = Path(args.reports_repo)
    log = list(csv.DictReader(open(repo / "log.csv", encoding="utf-8")))
    facilities = load()
    on_site = {}
    for f in facilities:
        for r in f["reports"]:
            on_site[file_id(r["link"])] = f["key"]

    if args.map:
        mapping, conflicts = {}, []
        for row in log:
            key = on_site.get(row["RIDOH file ID"])
            if not key:
                continue
            folder = row["Facility folder ID"]
            if mapping.get(folder, key) != key:
                conflicts.append(f"{folder}: {mapping[folder]} vs {key}")
            mapping.setdefault(folder, key)
        old = load(FOLDER_MAP) if FOLDER_MAP.exists() else {}
        old.update(mapping)
        save(dict(sorted(old.items())), FOLDER_MAP)
        print(f"{len(old)} folders mapped; conflicts: {conflicts or 'none'}")
        return

    handled = load(HANDLED) if HANDLED.exists() else {}
    folder_map = load(FOLDER_MAP) if FOLDER_MAP.exists() else {}
    by_key = {f["key"]: f for f in facilities}
    out = []
    for row in log:
        rid = row["RIDOH file ID"]
        if not row.get("Sent to GitHub") or rid in on_site or rid in handled:
            continue
        pdf = next(iter(sorted((repo / "incoming").glob(rid + ".*"))), None)
        key = folder_map.get(row["Facility folder ID"])
        exit_date = parse_exit_date(row["File name"])
        fac = by_key.get(key)
        same_date = []
        if fac and exit_date:
            for r in fac["reports"]:
                if r["date"] == exit_date:
                    same_date.append({"type": r["type"], "tier": r["tier"], "headline": r["headline"][:160],
                                      "file_id": file_id(r["link"])})
        out.append({
            "ridoh_id": rid,
            "file_name": row["File name"],
            "kind": kind(row["File name"]),
            "exit_date_from_name": exit_date,
            "collector_facility": row["Facility"],
            "facility_key": key,
            "facility_name": fac["name"] if fac else None,
            "license_no": fac.get("license_no") if fac else None,
            "pdf": str(pdf) if pdf else None,
            "link": row["RIDOH link"],
            "site_entries_same_date": same_date,
        })
    json.dump(out, sys.stdout, indent=1)
    print()
    missing = [o for o in out if not o["pdf"]]
    unmapped = [o for o in out if not o["facility_key"]]
    print(f"# {len(out)} waiting; {len(missing)} without a PDF yet; {len(unmapped)} from a folder not matched to a facility",
          file=sys.stderr)


if __name__ == "__main__":
    main()
