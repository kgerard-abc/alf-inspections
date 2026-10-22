# Weekly assisted living update

This is the procedure Claude follows each week (and whenever kg asks) to add new RIDOH
assisted living reports to alinspections.abc-ri.org. kg reviews and merges the pull request;
nothing is published until she does.

## How reports get here

kg's "ALF report collector" Apps Script checks RIDOH's facility folders every morning. Each new
report is copied to her Drive and sent to the private repo `kgerard-abc/alf-reports`:
`incoming/<RIDOH file ID>.pdf`, plus `log.csv` (one row per RIDOH file, with the facility
folder it came from).

`data/facilities.json` in this repo is the master copy of the site's data. Never edit the data
inside `index.html` by hand; `tools/build.py` writes it there.

## Steps

1. Clone `kgerard-abc/alf-inspections` and `kgerard-abc/alf-reports` side by side, with push access.
2. `cd alf-inspections && python3 tools/pending.py ../alf-reports > /tmp/pending.json`
   - Nothing waiting: stop. Report "No new assisted living reports this week." Do not open a pull request.
   - A row with `facility_key: null` came from a folder not yet matched to a facility. Read the
     report's facility name and address, find the facility in `data/facilities.json`, add the
     folder to `data/folder_map.json`, and rerun. A facility not on the site at all: leave it out
     and list it in the pull request for kg.
3. Read every waiting PDF in full. Most are scans: use `pdftotext -layout` first; if that gives
   little text, OCR it (`pdftoppm -r 220 -gray -png`, then `tesseract <page> - --psm 4`). The
   findings are in the left column of RIDOH's form; cropping each page to its left 53% before OCR
   gives much cleaner text. Look at a page image when a number or date matters and the OCR is unclear.
4. For each file decide:
   - **New survey** (no site entry for that facility with the same survey date and the same
     findings): write an entry (below).
   - **Same survey already on the site** (typically the plan of correction for a statement of
     deficiencies already listed, or a cover page): record it in `handled` as `same_survey`
     with a one-line note.
   - **RIDOH re-posted a file already on the site** under a new file ID (same facility, date,
     and findings, often after RIDOH replaced a folder): add it to `relink` so the existing
     entry keeps its summary and points at the live file.
   - Check the facility name and address printed on the report, not only the folder. RIDOH
     occasionally files a report in the wrong facility's folder.
5. Write the entries and skips into a JSON file in the shape `tools/apply.py` documents, then run
   `python3 tools/apply.py that.json`. It refuses entries that break the rules and rebuilds
   `index.html`. Then run `python3 tools/build.py --check` and `python3 .github/scripts/check_site.py`.
6. Commit on a new branch named `alf-update-YYYY-MM-DD`, push, and open a pull request (see below).
7. Rebuild the master spreadsheet into the private repo and push it to `main` there:
   `python3 tools/build.py --xlsx ../alf-reports/master/ALF_reports_master.xlsx`
   (it reflects the pull request's version; kg's copy to work from).

## Writing an entry

- `date`: the "(X3) Date survey completed" on the form. Use the file name's date only if the form's is unreadable.
- `type`: one of `Complaint/Incident Investigation`, `Routine/Biennial Inspection`,
  `Routine/Biennial Inspection, Complaint/Incident Investigation`,
  `Complaint/Incident Investigation (Follow-Up)`.
- No deficiencies: `no_findings: true`, `tier: null`, `headline: "No deficiencies identified"`, `paragraphs: []`.
- Otherwise one paragraph per deficiency (or closely related group), most severe first:
  `"S###: Short plain title / What happened, in 1 to 4 plain sentences."` Use facts from the
  survey findings column only, not the facility's own plan of correction. Numbers, dates,
  and quantities as written. No resident or staff names, no em dashes, plain words a family
  member would understand. `headline` = the title (before " / ") of the most severe paragraph.
- `link`: `https://drive.google.com/file/d/<RIDOH file ID>/view`.

### Severity (kg reviews every serious and most serious call)

- **most_serious**: a resident was harmed or put in real danger, or abuse or neglect occurred.
  Examples: injury; a dangerous event that actually happened (fire, a lit cigarette, an
  elopement); a medication error that reached a resident; a doctor's safety order not followed;
  immediate jeopardy cited by RIDOH; repeat kitchen violations with pests or contamination.
- **serious**: a failure in a resident's care or safety that could lead to harm. Examples: an
  abuse allegation or incident not investigated or reported; a service plan missing a resident's
  safety or care needs (wander alarms, care being given by another resident); outbreak
  infection control not followed; no CPR-certified staff on a shift; a resident's scheduled
  medication unavailable or unsafely shared; chemicals reachable in a dementia unit; no
  background check for direct-care staff.
- **minor**: everything else: paperwork, assessments not updated without a safety gap, food
  code, postings, fire drills, quality plans, as-needed or expired medications.

## The pull request

Title: `Assisted living update: N new reports (date)`. Body, in plain language, no em dashes:

1. **Severe findings to review first**: every most serious and serious entry: facility, date,
   headline, and why it got that rating.
2. **Facility ratings that change**: badge before and after.
3. **Other new reports**: facility, date, headline.
4. **Files not added**: same-survey skips and relinks, one line each.
5. **Anything needing kg**: unmatched folders, unreadable pages, questions.

End with: "Merging publishes the site. To change a rating or summary, comment here or tell Claude."
