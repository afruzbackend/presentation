"""Ma'ruza .docx faylini o'qib, mavzular tuzilmasiga ajratadi.

Tashqi kutubxonasiz: .docx — bu zip ichidagi XML.
"""
import html
import re
import zipfile
import xml.etree.ElementTree as ET

W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"


# ---------------------------------------------------------------- docx o'qish
def run_is_bold(r):
    rpr = r.find(W + "rPr")
    if rpr is None:
        return False
    b = rpr.find(W + "b")
    return b is not None and b.get(W + "val") not in ("0", "false")


def run_color(r):
    rpr = r.find(W + "rPr")
    c = rpr.find(W + "color") if rpr is not None else None
    return c.get(W + "val") if c is not None else None


def para(p):
    """Paragrafni {text, html, bold, color, list} ko'rinishida qaytaradi."""
    ppr = p.find(W + "pPr")
    style = ""
    is_list = False
    if ppr is not None:
        st = ppr.find(W + "pStyle")
        style = st.get(W + "val") if st is not None else ""
        is_list = ppr.find(W + "numPr") is not None or style == "16"
    parts, plain, bolds, colors = [], [], [], set()
    for r in p.iter(W + "r"):
        t = "".join(x.text or "" for x in r.iter(W + "t"))
        if not t:
            continue
        b = run_is_bold(r)
        plain.append(t)
        bolds.append((b, len(t.strip())))
        colors.add(run_color(r))
        parts.append(f"<b>{html.escape(t)}</b>" if b else html.escape(t))
    text = "".join(plain).strip()
    all_bold = bool(bolds) and all(b for b, n in bolds if n)
    h = "".join(parts).strip().replace("</b><b>", "")
    if all_bold:
        h = html.escape(text)
    return {"text": text, "html": h, "bold": all_bold, "colors": colors, "list": is_list, "style": style}


def table(tbl):
    rows = []
    for tr in tbl.findall(W + "tr"):
        row = []
        for tc in tr.findall(W + "tc"):
            cell = [para(p) for p in tc.findall(W + "p")]
            row.append("<br>".join(c["html"] for c in cell if c["text"]))
        rows.append(row)
    return rows


def read_styles(z):
    """uslub id -> nomi (masalan '2' -> 'heading 1')"""
    try:
        root = ET.fromstring(z.read("word/styles.xml"))
    except KeyError:
        return {}
    out = {}
    for st in root.iter(W + "style"):
        name = st.find(W + "name")
        out[st.get(W + "styleId")] = (name.get(W + "val") if name is not None else "").lower()
    return out


def read_blocks(path):
    """docx -> [(turi, ma'lumot)], turi: 'p' yoki 'tbl'. path fayl yo'li yoki ochiq fayl bo'lishi mumkin."""
    z = zipfile.ZipFile(path)
    styles = read_styles(z)
    body = ET.fromstring(z.read("word/document.xml")).find(W + "body")
    blocks = []
    for el in body:
        if el.tag == W + "p":
            p = para(el)
            if p["text"]:
                p["style_name"] = styles.get(p["style"], "")
                blocks.append(("p", p))
        elif el.tag == W + "tbl":
            blocks.append(("tbl", table(el)))
    return blocks


# ---------------------------------------------------------------- matnni tozalash
FIXES = [
    (re.compile(r"[ \u00a0]{2,}"), " "),
    (re.compile(r" ([,.;:!?])(?!\d)"), r"\1"),
]


def clean(s):
    for rx, rep in FIXES:
        s = rx.sub(rep, s)
    return s.strip()


def clean_rows(rows):
    return [[clean(c) for c in r] for r in rows]


# ---------------------------------------------------------------- mavzularga ajratish
TOPIC_RX = re.compile(r"^Mavzu:\s*(Nazariy|Amaliy)\.\s*(.+)$")
SECTION_RX = re.compile(r"^(\d)-REJA BO.YICHA:\s*(.+)$")
OPTION_RX = re.compile(r"^([a-d])\)\s*(.+)$")
QNUM_RX = re.compile(r"^(\d+)\.\s*(.+)$")


def is_subheading(p):
    return p["bold"] and "2E75B6" in p["colors"] and not p["list"]


def uz_title(s):
    """'KOMPYUTER XONASIDAGI ...' -> 'Kompyuter xonasidagi ...'"""
    s = s.strip().rstrip(".")
    low = s.lower()
    return low[:1].upper() + low[1:]


def split_topics(blocks):
    topics, cur = [], None
    head = []
    for kind, b in blocks:
        if kind == "p" and TOPIC_RX.match(b["text"]):
            m = TOPIC_RX.match(b["text"])
            cur = {"type": m.group(1), "title": clean(m.group(2)), "raw": []}
            topics.append(cur)
            continue
        (cur["raw"] if cur else head).append((kind, b))
    return head, topics


def parse_topic(t):
    raw = t["raw"]
    model, xarita = [], []
    reja, sections = [], []
    questions_prev, questions, tests = [], [], []
    grading, mustaqil, adabiyot = [], [], []
    answers_tail = None

    mode = "model"
    sec = None
    for i, (kind, b) in enumerate(raw):
        txt = b["text"] if kind == "p" else ""

        if kind == "p" and txt.startswith("TEST TOPSHIRIQLARINING JAVOBLARI"):
            answers_tail = raw[i + 1:]
            break

        # --- bo'lim almashuvlari
        if mode == "model" and kind == "tbl" and not model:
            model = [r for r in clean_rows(b) if len(r) >= 2]
            continue
        if mode == "model" and kind == "tbl":
            xarita = clean_rows(b)
            continue
        if kind == "p" and txt == "REJA:":
            mode = "reja"
            continue
        m = SECTION_RX.match(txt) if kind == "p" else None
        if m:
            mode = "section"
            sec = {"title": uz_title(m.group(2)), "blocks": []}
            sections.append(sec)
            continue
        if kind == "p" and txt.startswith("1-ILOVA"):
            mode = "ilova1"
            continue
        if kind == "p" and txt.startswith("2-ILOVA"):
            mode = "ilova2"
            continue
        if kind == "p" and txt.startswith("3-ILOVA"):
            mode = "ilova3"
            continue
        if kind == "p" and txt.startswith("Test topshiriqlari"):
            mode = "test"
            continue
        if kind == "p" and txt.startswith("MUSTAQIL TA"):
            mode = "mustaqil"
            continue
        if kind == "p" and txt.startswith("Adabiyotlar"):
            mode = "adabiyot"
            continue

        # --- tarkibni yig'ish
        if mode == "reja" and kind == "p" and b["list"]:
            reja.append(clean(txt))
        elif mode == "section":
            if kind == "tbl":
                sec["blocks"].append({"t": "table", "rows": clean_rows(b)})
            elif is_subheading(b):
                sec["blocks"].append({"t": "h", "text": clean(txt)})
            elif b["list"]:
                last = sec["blocks"][-1] if sec["blocks"] else None
                if not last or last["t"] != "ul":
                    last = {"t": "ul", "items": []}
                    sec["blocks"].append(last)
                last["items"].append(clean(b["html"]))
            else:
                sec["blocks"].append({"t": "p", "html": clean(b["html"])})
        elif mode == "ilova1" and kind == "p" and b["list"]:
            questions_prev.append(clean(txt))
        elif mode == "ilova2" and kind == "tbl":
            grading = clean_rows(b)
        elif mode == "ilova3" and kind == "p" and b["list"]:
            questions.append(clean(txt))
        elif mode == "test" and kind == "p":
            om = OPTION_RX.match(txt)
            qm = QNUM_RX.match(txt)
            if om and tests:
                tests[-1]["options"].append(clean(om.group(2)))
            elif qm:
                tests.append({"q": clean(qm.group(2)), "options": []})
        elif mode == "mustaqil" and kind == "p":
            mustaqil.append(clean(b["html"]))
        elif mode == "adabiyot" and kind == "p":
            adabiyot.append(clean(txt))

    return {
        "type": t["type"],
        "title": t["title"],
        "model": model,
        "xarita": xarita,
        "reja": reja,
        "sections": sections,
        "prevQuestions": questions_prev,
        "questions": questions,
        "tests": tests,
        "grading": grading,
        "mustaqil": mustaqil,
        "adabiyot": adabiyot,
    }, answers_tail


def parse_answers(tail):
    """Javoblar jadvali: 'N-mavzu' dan keyin harflar."""
    answers = {}
    if not tail:
        return answers
    cells = []
    for kind, b in tail:
        if kind == "tbl":
            for r in b:
                cells.extend(re.sub(r"<[^>]+>", "", c).strip() for c in r)
        else:
            cells.append(b["text"])
    cur = None
    for c in cells:
        m = re.match(r"^(\d+)-mavzu$", c)
        if m:
            cur = int(m.group(1))
            answers[cur] = []
        elif cur and re.fullmatch(r"[a-d]", c):
            answers[cur].append("abcd".index(c))
    return answers


def parse_head(head):
    plan, mustaqil_plan = [], []
    target = None
    for kind, b in head:
        if kind == "p" and b["text"].startswith("O‘QUV-TEMATIK REJA"):
            target = plan
        elif kind == "p" and b["text"].startswith("MUSTAQIL TA"):
            target = mustaqil_plan
        elif kind == "tbl" and target is not None:
            target.extend(clean_rows(b)[1:])
            target = None
    return plan, mustaqil_plan


TITLE_CASE_SKIP = {"va", "bo‘yicha", "uchun"}


def nice_case(s):
    """'KOMPYUTER TIZIMLARI' -> 'Kompyuter tizimlari'"""
    s = s.strip()
    if s.upper() != s:
        return s
    low = s.lower()
    return low[:1].upper() + low[1:]


def parse_meta(head):
    """Muqova sahifasidan darslik ma'lumotlari."""
    meta = {"title": "", "module": "", "college": "", "direction": "", "author": "",
            "hours_theory": 0, "hours_practice": 0, "hours_self": 0}
    for kind, b in head:
        if kind != "p":
            continue
        t = b["text"]
        m = re.match(r"^([A-ZА-Я]{2,6}\.?\s*\d+)\.\s*(.+)$", t)
        if m and not meta["module"]:
            meta["module"] = f"{m.group(1)}. {nice_case(m.group(2))}"
            meta["title"] = nice_case(m.group(2))
        elif re.search(r"TEXNIKUM|KOLLEJ|LITSEY|MAKTAB|INSTITUT|UNIVERSITET", t.upper()) and not meta["college"]                 and "VAZIRLIG" not in t.upper() and "BOSHQARMA" not in t.upper():
            meta["college"] = nice_case(t)
        elif t.lower().startswith("ta’lim yo‘nalishi:") or t.lower().startswith("ta'lim yo'nalishi:"):
            meta["direction"] = t.split(":", 1)[1].strip()
        elif "hajmi" in t.lower():
            for key, rx in (("hours_theory", r"nazariy\D{0,4}(\d+)"), ("hours_practice", r"amaliy\D{0,4}(\d+)"),
                            ("hours_self", r"mustaqil ta.lim\D{0,4}(\d+)")):
                mm = re.search(rx, t.lower())
                if mm:
                    meta[key] = int(mm.group(1))
        elif t.lower().startswith(("tuzuvchi:", "muallif:")):
            v = t.split(":", 1)[1].strip(" _")
            if v:
                meta["author"] = v
    return meta


def parse_structured(blocks):
    """Asosiy format: 'Mavzu: Nazariy. ...' + 'N-REJA BO'YICHA:' (o'quv-uslubiy majmua)."""
    head, raw_topics = split_topics(blocks)
    plan, mustaqil_plan = parse_head(head)
    topics, answers = [], {}
    for idx, t in enumerate(raw_topics, 1):
        data, tail = parse_topic(t)
        data["n"] = idx
        topics.append(data)
        if tail:
            answers = parse_answers(tail)
    for t in topics:
        key = answers.get(t["n"], [])
        for qi, q in enumerate(t["tests"]):
            q["a"] = key[qi] if qi < len(key) else None
    return head, topics, mustaqil_plan


def heading_level(p):
    """Word sarlavhalari: 'heading 1' -> 1, 'title' -> 0, aks holda None."""
    name = p.get("style_name", "")
    m = re.match(r"(heading|заголовок)\s*(\d)", name)
    if m:
        return int(m.group(2))
    if name == "title":
        return 0
    return None


def parse_generic(blocks):
    """Boshqa docx: eng katta sarlavha — mavzu, keyingi daraja — reja bo'limi."""
    levels = sorted({heading_level(b) for k, b in blocks if k == "p" and heading_level(b)})
    topic_lv = levels[0] if levels else None
    sec_lv = levels[1] if len(levels) > 1 else None
    topics, head = [], []
    cur = sec = None
    for kind, b in blocks:
        lv = heading_level(b) if kind == "p" else None
        if topic_lv and lv == topic_lv:
            cur = {"title": clean(b["text"]), "type": "Nazariy", "sections": []}
            topics.append(cur)
            sec = None
            continue
        if cur is None:
            head.append((kind, b))
            continue
        if sec_lv and lv == sec_lv:
            sec = {"title": clean(b["text"]), "blocks": []}
            cur["sections"].append(sec)
            continue
        if sec is None:
            sec = {"title": cur["title"], "blocks": []}
            cur["sections"].append(sec)
        if kind == "tbl":
            sec["blocks"].append({"t": "table", "rows": clean_rows(b)})
        elif lv or (b["bold"] and len(b["text"]) < 120):
            sec["blocks"].append({"t": "h", "text": clean(b["text"])})
        elif b["list"]:
            if not sec["blocks"] or sec["blocks"][-1]["t"] != "ul":
                sec["blocks"].append({"t": "ul", "items": []})
            sec["blocks"][-1]["items"].append(clean(b["html"]))
        else:
            sec["blocks"].append({"t": "p", "html": clean(b["html"])})
    if not topics:  # sarlavhasiz hujjat: bitta mavzu
        topics = [{"title": "1-mavzu", "type": "Nazariy", "sections": [{"title": "Asosiy matn", "blocks": [
            {"t": "table", "rows": clean_rows(b)} if k == "tbl" else {"t": "p", "html": clean(b["html"])}
            for k, b in head]}]}]
        head = []
    for i, t in enumerate(topics, 1):
        t.update(n=i, model=[], xarita=[], reja=[s["title"] for s in t["sections"]], prevQuestions=[], questions=[],
                 tests=[], grading=[], mustaqil=[], adabiyot=[])
    return head, topics, []


def parse(path):
    """docx -> {course: {...}, topics: [...], format: 'majmua'|'umumiy', problems: [...]}"""
    blocks = read_blocks(path)
    head, topics, mustaqil_plan = parse_structured(blocks)
    fmt = "majmua"
    if not topics:
        head, topics, mustaqil_plan = parse_generic(blocks)
        fmt = "umumiy"
    meta = parse_meta(head)
    meta["mustaqilPlan"] = mustaqil_plan

    problems = []
    for t in topics:
        for qi, q in enumerate(t["tests"]):
            if q.get("a") is None:
                problems.append(f"{t['n']}-mavzu, {qi + 1}-test: javob kaliti yo'q")
            if len(q["options"]) != 4:
                problems.append(f"{t['n']}-mavzu, {qi + 1}-test: {len(q['options'])} ta variant")
    return {"course": meta, "topics": topics, "format": fmt, "problems": problems}
