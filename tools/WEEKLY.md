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

## Standing site rules (do not undo these)

- **Badges use the last 3 years only.** Most serious, Serious, Minor, and No concerns found
  count only reports from the last 3 years. Older reports stay in each timeline. The page
  recomputes badges live from the report dates, `recompute()` in `tools/alf.py` does the same
  for the stored badge, and the footer and hover text say so. Do not change one without the others.
  A stored badge can lag as reports age out; `build.py` refreshes it without changing the
  "Data last updated" date. That date changes only when real report data changes.
- **Badges show a count.** Each badge reads like "Serious concerns · 3 inspections": how many
  inspections in the last 3 years had a finding at the facility's top level (clean badges show no
  number). `badgeText()` in `index.html` computes it live, and the note above the filters explains it.
- **No "Operating without a license" label, filter, or note.** Removed at kg's request.
- **Heather Gardens** (key `SCANDINAVIAN HOME`) shows the line "(Formerly Scandinavian Home,
  under new ownership by PACE since 2026)" under its name. It lives in that facility's
  `name_note` in `data/facilities.json`. Any facility can have a `name_note`.
- `check_site.py` fails if any of these are lost. If kg asks to change one on purpose, update
  the check and this section in the same pull request.

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

- **most_serious**: kg's judgment of what would very likely have been an immediate jeopardy (IJ)
  citation had it happened in a nursing home. The standard is noncompliance that caused, or was
  likely to cause, serious injury, harm, impairment, or death to a resident (42 CFR 489.3; CMS
  levels J, K, L). Assisted living rules do not use the term "immediate jeopardy," which is why
  the site calls this "most serious" and says it is ABC-RI's own judgment using the nursing home
  standard. Never describe it as RIDOH's own rating. kg's four sheets of IJ-level findings (2023,
  2024, 2025, 2026 to date) are the reference. Findings she put there include: injury,
  hospitalization, or death after a care failure; abuse, sexual abuse, or abuse not investigated;
  elopements, and a secure-unit resident placed in an unsecured setting; physician orders not
  followed or medications missed or wrong (when it reached a resident); unsecured hazardous
  chemicals or medications in a dementia unit; code status errors (DNR vs. full code); a missed
  response to stroke or other acute change; unlicensed staff giving medications; no medication
  staff on a shift; resident threats with weapons not investigated; fire hazards. When a new
  report has a finding like these, tag it most_serious and put it at the top of the review list
  for kg, who makes the final call.
- **serious**: a failure in a resident's care or safety that could lead to harm but kg has not
  judged to be at the level above. Examples: an assessment or service plan missing a safety need
  with no event; outbreak infection control not followed; no CPR-certified staff on a shift; no
  background check for direct-care staff; door locks that block emergency entry; abuse or
  neglect allegations handled late or incompletely with no harm described.
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
