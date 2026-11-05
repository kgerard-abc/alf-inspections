"""House style for finding text on the assisted living site.

  python3 tools/style.py            rewrite data/facilities.json in the house style, then run build.py
  python3 tools/style.py --report out.html   also write a before/after list of every change

The style, which tools/build.py also checks:
- A finding starts with its RIDOH tag or tags, written "S230: " or "S230/S575: ".
  The first letter after the tag is a capital.
- A finding with a short title is written "S230: Title / What happened".
- Abbreviations a family member would not know are spelled out. Common ones (RN, ER, CPR,
  COPD, DNR, TB, ID, RIDOH) stay.
- No ALL-CAPS words except abbreviations.
- No emoji in the text. The page adds the yellow warning triangle to most serious findings itself.
"""
import argparse
import html
import json
import re
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from alf import DATA, load, save  # noqa: E402

# Abbreviations that stay as they are (also exempt from the ALL-CAPS rule).
KEEP = {"RN", "RNs", "ER", "CPR", "COPD", "DNR", "TB", "ID", "IDs", "RI", "RIDOH", "AM", "PM", "IV", "II", "III",
        "XXX", "MRSA", "COVID", "HIPAA", "EMT", "EMS", "B6", "B12", "D2", "D3", "F1", "F2", "M1", "M2", "BCI", "OK",
        "US", "USA", "AED", "EKG", "ICU", "DOB", "PPE", "CDC", "BMI", "UV", "PCR", "A1C", "HbA1c",
        "BIMS", "MMSE", "MMR", "GPS", "ECT", "Q1", "Q2", "Q3", "Q4", "EC", "CCHO", "EOHHS", "MOLST", "VRE", "NSAID", "NSAIDs", "TDAP", "HIV", "CMS", "OSHA", "ALR", "LTC"}

# Spelled out. Order matters: longer and more specific first.
SPELL = [
    (r"\bPT/OT/SLP\b", "physical, occupational, and speech therapy"),
    (r"\bPT/OT\b", "physical and occupational therapy"),
    (r"\bRA/SP\b", "resident assessment and service plan"),
    (r"\bPRN \(as needed\)", "as-needed"),
    (r"\bPRN\b", "as-needed"),
    (r"\bMOLST\b", "MOLST form (medical orders for life-sustaining treatment)"),
    (r"\bNKA\b", "no known allergies"),
    (r"\bQA\b", "quality assurance"),
    (r"\bQI\b", "quality improvement"),
    (r"\bLPNs\b", "licensed practical nurses"), (r"\bLPN\b", "licensed practical nurse"),
    (r"\bCNAs\b", "certified nursing assistants"), (r"\bCNA\b", "certified nursing assistant"),
    (r"\bCMTs\b", "certified medication technicians"), (r"\bCMT\b", "certified medication technician"),
    (r"\bPCAs\b", "personal care aides"), (r"\bPCA\b", "personal care aide"),
    (r"\bCNP\b", "certified nurse practitioner"), (r"\bNP\b", "nurse practitioner"),
    (r"\bPA\b", "physician assistant"),
    (r"\bPCP\b", "primary care provider"),
    (r"\bMDs\b", "doctors"), (r"\bMD\b", "doctor"),
    (r"\bMARs\b", "medication administration records"), (r"\bMAR\b", "medication administration record"),
    (r"\bLHS\b", "limited health services"),
    (r"\bD?SCU\b", "special care unit"),
    (r"\bDOH\b", "RIDOH"),
    (r"\bADLs\b", "daily living activities"), (r"\bADL\b", "daily living activity"),
    (r"\bOTC\b", "over-the-counter"),
    (r"\bBP\b", "blood pressure"),
    (r"\bO2\b", "oxygen"),
    (r"\bUTIs\b", "urinary tract infections"), (r"\bUTI\b", "urinary tract infection"),
    (r"\bCHF\b", "congestive heart failure"),
    (r"\bTIA\b", "mini-stroke"),
    (r"\bDTI\b", "deep tissue injury"),
    (r"\bVRE\b", "VRE (a drug-resistant infection)"),
    (r"\bDOW\b", "director of wellness"),
    (r"\bSLP\b", "speech therapy"),
    (r"\bOT\b", "occupational therapy"),
    (r"\bPT\b", "physical therapy"),
    (r"\bAL\b", "assisted living"),
    (r"\bNA\b", "nursing assistant"),
    (r"\bBC\b", "because"),
    (r"\bPOC\b", "plan of correction"),
    (r"\b[Mm]gmt\b", "management"),
    (r"\b[Rr]eqs\b", "requirements"),
    (r"\bres\b", "resident"),
    (r"\bPOA \(power of attorney\)", "power of attorney"), (r"\bPOA\b", "power of attorney"),
    (r"\bSN-level\b", "skilled-nursing-level"),
    (r"\bSNF\b", "nursing home"),
    (r"\bSBP\b", "systolic (top number) blood pressure"),
    (r"\bFSMs\b", "certified food safety managers"), (r"\bFSM\b", "certified food safety manager"),
    (r"\bDNS\b", "director of nursing services"),
    (r"\bCOC\b", "continuity of care"),
    (r"\bALF\b", "assisted living"),
    (r"\bEMR\b", "electronic medical record"),
    (r"\bPPM\b", "parts per million"),
    (r"\bBPH\b", "enlarged prostate"),
    (r"\b(\d+) MG\b", r"\1 mg"),
]
SPELLED = sorted({rep for _, rep in SPELL}, key=len, reverse=True)
CONSONANT_START = re.compile(r"\b([Aa])n (?=(?:" + "|".join(sorted({re.escape(r.split()[0]) for r in SPELLED if r[0].lower() not in "aeiou"})) + r")\b)")
LINE_CODE_RE = re.compile(r"(?m)(?<=\n)S\s?(\d{2,4})((?:\s*(?:/|,|&|and)\s*S?\s?\d{2,4})*)\s*(?::|[\u2013\u2014-])?\s*(?=[A-Za-z])")
# "ED" means the executive director when it is the subject of a sentence, and the emergency room otherwise.
ED_SUBJECT = re.compile(r"\b((?:the|The) )?ED (?=(was|did|could|stated|said|confirmed|reported|indicated|acknowledged|provided|is|had|has|failed|verified|revealed|told|asked|agreed|explained|denied)\b)")
CODE_RE = re.compile(r"^\s*S\s?(\d{2,4})((?:\s*(?:/|,|&|and)\s*S?\s?\d{2,4}|S\d{2,4})*)\s*(?::|[–—-])?\s*")
EMOJI_RE = re.compile("[\U0001F300-\U0001FAFF☀-➿️]")
NOTES = [
    (re.compile(r";?\s*\[SEE CPBL[^\]]*\].*$", re.S), ""),   # kg's research note, with a staff member's name
    (re.compile(r"\s*CPBL\?\?\s*"), " "),
    (re.compile(r"\s*SEEMS VERBAL ABUSE ALLEGATION WAS SUBSTANTIATED\? THERE IS NO MENTION OF IT FROM DOH\."), ""),
    (re.compile(r"WAS THERE FOLLOW UP TO ENSURE STAFF ARE CERTIFIED\?;?"), " "),
    (re.compile(r"\s*_x00[0-9A-F]{2}_\s*"), " "),     # characters lost when the old spreadsheet was saved
]


def corpus_words(texts):
    c = Counter()
    for t in texts:
        c.update(re.findall(r"[a-z]+", t.lower()))
    return c


def ocr_fixes(texts):
    """Scanned reports often read an i as an l ("glve", "perlod"). Fix a word only when the i
    version is a common word in the same data and the l version is rare."""
    c = corpus_words(texts); fixes = {}
    for w, n in c.items():
        if "l" not in w or n > 2 or len(w) < 4:
            continue
        for i, ch in enumerate(w):
            if ch == "l":
                cand = w[:i] + "i" + w[i + 1:]
                if c.get(cand, 0) >= 5:
                    fixes[w] = cand
                    break
    return fixes


def norm_code(m):
    nums = re.findall(r"\d{2,4}", m.group(0))
    return "/".join("S" + n for n in nums) + ": "


def cap_first(s):
    for i, ch in enumerate(s):
        if ch.isalpha():
            return s[:i] + ch.upper() + s[i + 1:]
        if ch not in " \"'([":
            return s
    return s


def uncap(text):
    def word(m):
        w = m.group(0)
        if w in KEEP or w.rstrip("s") in KEEP or any(ch.isdigit() for ch in w):
            return w
        return w.lower()
    # 3+ letter ALL-CAPS words, plus short ones (TO, OF, NO) inside an ALL-CAPS run
    text = re.sub(r"\b[A-Z][A-Z']{2,}\b", word, text)
    short = r"\b(IN|A|TO|OF|ON|AT|AS|IT|NO|OR|BY|AN|IS|BE|DO|SO|UP|IF|MY|HE|WE)\b(?= [a-z]|,? [A-Z]{2,}\b)"
    for _ in range(3):   # "Staff A" stays: a short word changes only when the words around it were in capitals
        text = re.sub(r"(?<=[a-z,] )(?<!Staff )(?<!Resident )" + short, lambda m: m.group(0).lower(), text)
    # capital again after a sentence end
    text = re.sub(r"([.!?]\s+)([a-z])", lambda m: m.group(1) + m.group(2).upper(), text)
    return text


SMALL = {"and", "of", "for", "the", "to", "with", "a", "an", "or", "in", "on"}


def title_case(head):
    """True when a heading is written in Title Case (its words after the first are capitalized)."""
    for phrase in SPELLED:   # words this tool spelled out don't count either way
        head = re.sub(r"\b" + re.escape(phrase) + r"\b", " ", head, flags=re.I)
    words = [w for w in re.findall(r"[A-Za-z][A-Za-z'&]*", head)[1:] if len(w) > 3]
    return bool(words) and sum(w[0].isupper() for w in words) / len(words) >= 0.75


def caps_spelled(head):
    for rep in SPELLED:
        head = re.sub(r"\b" + re.escape(rep) + r"\b", lambda mm: " ".join(w if w in SMALL else w[:1].upper() + w[1:] for w in mm.group(0).split(" ")), head)
    return head


def style(text, fixes, headline=False):
    t = text
    t = re.sub(r"\b(NO|NOT|NOR|SIX|IN A)\b(?= [a-z])", lambda m: m.group(0).lower(), t)   # shouted words in a sentence
    for rx, rep in NOTES:
        t = rx.sub(rep, t)
    t = EMOJI_RE.sub("", t)
    t = re.sub(r"\b(NS|DX) \[([^\]]+)\]", r"\2", t)
    t = re.sub(r"\bDirector \(ED\)", "Director", t)
    t = ED_SUBJECT.sub(lambda m: (m.group(1) or "the ") + "executive director ", t)
    t = re.sub(r"\bED\b", "emergency room", t)
    for rx, rep in SPELL:
        abbr = rx[2:-2] if rx.startswith(r"\b") and rx.endswith(r"\b") else None
        if abbr and re.fullmatch(r"[A-Za-z0-9?/]+", abbr):
            # "Certified Medication Technician (CMT)" keeps the words and drops the label
            t = re.sub(r"(?i)(" + re.escape(rep) + r")\s*\(" + abbr + r"\)", r"\1", t)
        t = re.sub(rx, rep, t)
    if re.search(r"\b[A-Z]{3,}\b[ ,'A-Z]*\b[A-Z]{3,}\b", t):
        t = uncap(t)
    else:
        t = re.sub(r"\b[A-Z][A-Z']{3,}\b", lambda m: m.group(0) if m.group(0) in KEEP else m.group(0).lower(), t)
    t = re.sub(r"\b(" + "|".join(map(re.escape, fixes)) + r")\b", lambda m: fixes[m.group(0)], t) if fixes else t
    t = CONSONANT_START.sub(lambda m: m.group(1) + " ", t)            # "an LPN" became "an licensed..."
    t = LINE_CODE_RE.sub(lambda m: norm_code(m), t)                  # tags that start a later line
    m = CODE_RE.match(t)
    code = ""
    if m and m.end() < len(t):
        code, t = norm_code(m), t[m.end():]
    t = cap_first(t)
    # the title: on its own first line, or a short Title Case heading before a colon, becomes "Title / details"
    nl, sl = t.find("\n"), t.find(" / ")
    if 0 < nl <= 140 and not (0 < sl < nl) and not t[:nl].rstrip().endswith((".", ":", ";")):
        t = t[:nl].rstrip() + " / " + t[nl + 1:].lstrip()
    elif sl < 0:
        c = t.find(": ")
        head = t[:c] if 0 < c <= 70 else ""
        if head and len(head.split()) <= 9 and title_case(head):
            t = head + " / " + t[c + 2:]
    sl = t.find(" / ")
    if sl > 0:
        head, body = t[:sl], t[sl + 3:]
        if title_case(head):
            head = caps_spelled(head)
        t = head + " / " + cap_first(body)
    elif headline and title_case(t):
        t = caps_spelled(t)
    t = code + t
    t = re.sub(r"[ \t]{2,}", " ", t)
    t = re.sub(r" ,(?=\S)", ", ", t).replace(" ,", ",")
    t = re.sub(r"(?<!\.)\.\.(?=\s)", ".", t).strip()
    return t


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--report")
    args = ap.parse_args()
    fac = load(DATA)
    texts = [t for f in fac for r in f["reports"] for t in [r["headline"]] + [p["text"] for p in r["paragraphs"]]]
    fixes = ocr_fixes(texts)
    changed = []
    for f in fac:
        for r in f["reports"]:
            if r["no_findings"]:
                continue
            for p in r["paragraphs"]:
                new = style(p["text"], fixes)
                if new != p["text"]:
                    changed.append((f["name"], r["date"], p["tier"], "finding", p["text"], new)); p["text"] = new
            rank = {"most_serious": 0, "serious": 1, "minor": 2}
            order = sorted(r["paragraphs"], key=lambda p: rank.get(p["tier"], 3))
            if order != r["paragraphs"]:
                changed.append((f["name"], r["date"], r["tier"], "order", "findings in the order written", "most serious finding first"))
                r["paragraphs"] = order
            new = style(r["headline"], fixes, headline=True) if r["headline"].strip() else r["headline"]
            if new != r["headline"]:
                changed.append((f["name"], r["date"], r["tier"], "headline", r["headline"], new)); r["headline"] = new
    save(fac, DATA)
    print(f"{len(changed)} texts restyled; spelling fixes used: {fixes}")
    if args.report:
        rank = {"most_serious": 0, "serious": 1, "minor": 2, None: 3}
        rows = "".join(
            f"<tr><td>{html.escape(n)}</td><td>{d}</td><td>{(t or '').replace('_', ' ')}</td><td>{k}</td>"
            f"<td>{html.escape(a)}</td><td>{html.escape(b)}</td></tr>"
            for n, d, t, k, a, b in sorted(changed, key=lambda x: (rank.get(x[2], 3), x[0], x[1])))
        Path(args.report).write_text(
            "<!doctype html><meta charset=utf-8><title>Finding text changes</title>"
            "<style>body{font:13px Helvetica,Arial,sans-serif;margin:16px}table{border-collapse:collapse}"
            "td,th{border:1px solid #999;padding:4px 6px;vertical-align:top;max-width:520px}</style>"
            f"<h1>Finding text changes ({len(changed)})</h1><p>Most serious first, then serious, then minor.</p>"
            "<table><tr><th>Residence</th><th>Date</th><th>Level</th><th>Field</th><th>Before</th><th>After</th></tr>"
            + rows + "</table>", encoding="utf-8")


if __name__ == "__main__":
    main()
