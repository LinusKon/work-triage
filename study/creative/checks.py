#!/usr/bin/env python3
"""Usage: python3 checks.py <motion|sting|scene3d|page|pricing|copy> <run folder> <out folder>

Run after render.mjs (not needed for copy). Prints one JSON object and writes <out>/checks.json.
A check has ok = true, false, or "needs_look" (a script cannot decide, a person must look).
pass = no check is false.
"""
import html as htmlmod
import json
import os
import re
import subprocess
import sys

IGNORED = {".git", ".omp", ".DS_Store"}

MOTION_LINES = ["A FIELD NOTES ORIGINAL", "TIDEWATER", "Six parts. Starting 12 March."]
PAGE_LINES = [
    "Loam",
    "Compost without the compost heap.",
    "Loam turns a week of kitchen scraps into a cup of dry, odourless soil food. Overnight, on your counter.",
    "Reserve yours",
    "$349. Ships in May.",
    "Quiet enough for a studio flat",
    "Runs at 28 dB, about as loud as a fridge.",
    "Nothing to empty for a week",
    "The 3-litre bucket takes what two people cook in seven days.",
    "No smell, no flies",
    "A sealed lid and a carbon filter you replace twice a year.",
    "I stopped apologising for my bin.",
    "Mara, Rotterdam",
    "Loam Home B.V., Amsterdam",
]
STING_LINES = ["KILN", "Fired in small batches."]
PRICING_LINES = [
    "Relay",
    "One update a day. No meeting.",
    "Pick a plan now, change it any time.",
    "Starter", "$0", "per person, per month", "For teams trying it out", "Up to 5 people",
    "30 days of history", "One workspace", "Start free",
    "Team", "$6", "For teams that run on it", "Unlimited people", "Unlimited history",
    "Slack and calendar sync", "Weekly summary by email", "Try Team for 14 days",
    "Company", "$14", "For several teams", "Everything in Team", "Single sign-on", "Audit log",
    "Priority support", "Talk to us",
    "Most teams pick this",
    "Prices in US dollars. Billed monthly.",
    "Relay Labs, Lisbon",
]
PRICING_BUTTONS = ["Start free", "Try Team for 14 days", "Talk to us"]


def norm(s):
    return re.sub(r"\s+", " ", s).strip()


def chk(ok, detail=""):
    return {"ok": ok, "detail": detail}


# ---------- image helpers (ffmpeg decodes to raw rgb24) ----------

def raw(path, w, h):
    cmd = ["ffmpeg", "-loglevel", "error", "-i", path, "-vf", f"scale={w}:{h}:flags=neighbor",
           "-f", "rawvideo", "-pix_fmt", "rgb24", "-"]
    return subprocess.run(cmd, capture_output=True, check=True).stdout


def distinct_colours(path):
    d = raw(path, 640, 360)
    return len({d[i:i + 3] for i in range(0, len(d), 3)})


def diff_fraction(a, b, w=960, h=540, tol=8):
    da, db = raw(a, w, h), raw(b, w, h)
    if da == db:
        return 0.0
    n = len(da) // 3
    bad = 0
    for i in range(0, len(da), 3):
        if (abs(da[i] - db[i]) > tol or abs(da[i + 1] - db[i + 1]) > tol
                or abs(da[i + 2] - db[i + 2]) > tol):
            bad += 1
    return bad / n


def same_render(a, b):
    """identical bytes, or pixel difference below 0.1 %"""
    try:
        if open(a, "rb").read() == open(b, "rb").read():
            return True, "identical PNG bytes"
    except FileNotFoundError as e:
        return False, f"missing file {e.filename}"
    f = diff_fraction(a, b)
    return f < 0.001, f"{f * 100:.4f} % of pixels differ"


def differ(a, b, min_frac=0.002):
    f = diff_fraction(a, b)
    return f >= min_frac, f"{f * 100:.2f} % of pixels differ"


def not_blank(paths):
    bad, info = [], []
    for p in paths:
        if not os.path.exists(p):
            bad.append(os.path.basename(p) + " (missing)")
            continue
        n = distinct_colours(p)
        info.append(f"{os.path.basename(p)}:{n}")
        if n <= 1:
            bad.append(os.path.basename(p))
    return chk(not bad, ("blank: " + ", ".join(bad)) if bad else "distinct colours " + " ".join(info))


# ---------- shared checks ----------

def allowed_files(run, allowed_top, require=("index.html",)):
    if not os.path.isdir(run):
        return chk(False, f"run folder missing: {run}")
    top = {e for e in os.listdir(run) if e not in IGNORED}
    extra = sorted(top - set(allowed_top))
    missing = sorted(set(require) - top)
    if extra or missing:
        return chk(False, f"extra: {extra} missing: {missing}")
    return chk(True, f"top level: {sorted(top)}")


def render_checks(r):
    c = {}
    blocked = r.get("blocked_requests", [])
    c["no_network_requests"] = chk(not blocked, ("blocked: " + "; ".join(sorted(set(blocked))[:5])) if blocked else "none")
    errs = r.get("console_errors", []) + r.get("page_errors", [])
    c["no_console_errors"] = chk(not errs, ("; ".join(sorted(set(errs))[:5])) if errs else "none")
    return c


def main():
    if len(sys.argv) < 4:
        sys.exit(__doc__)
    task, run, out = sys.argv[1], os.path.abspath(sys.argv[2]), os.path.abspath(sys.argv[3])
    os.makedirs(out, exist_ok=True)
    checks = {}

    if task == "copy":
        checks.update(copy_checks(run))
    else:
        rj = os.path.join(out, "render.json")
        if not os.path.exists(rj):
            sys.exit("render.json missing; run render.mjs first")
        r = json.load(open(rj))
        src_path = os.path.join(run, "index.html")
        src = open(src_path, encoding="utf-8", errors="replace").read() if os.path.exists(src_path) else ""
        if task == "motion":
            checks["only_allowed_files"] = allowed_files(run, ["index.html"])
            checks.update(render_checks(r))
            checks.update(motion_checks(r, src, out))
        elif task == "scene3d":
            checks["only_allowed_files"] = allowed_files(run, ["index.html", "vendor"])
            checks.update(render_checks(r))
            checks.update(scene_checks(r, src, out))
        elif task == "sting":
            checks["only_allowed_files"] = allowed_files(run, ["index.html"])
            checks.update(render_checks(r))
            checks.update(sting_checks(r, src, out))
        elif task == "pricing":
            checks["only_allowed_files"] = allowed_files(run, ["index.html"])
            checks.update(render_checks(r))
            checks.update(pricing_checks(r, out))
        elif task == "page":
            checks["only_allowed_files"] = allowed_files(run, ["index.html"])
            checks.update(render_checks(r))
            checks.update(page_checks(r, out))
        else:
            sys.exit("task must be motion, sting, scene3d, page, pricing or copy")

    res = {
        "task": task,
        "pass": all(v["ok"] is not False for v in checks.values()),
        "needs_look": sorted(k for k, v in checks.items() if v["ok"] == "needs_look"),
        "checks": checks,
    }
    s = json.dumps(res, indent=2)
    open(os.path.join(out, "checks.json"), "w").write(s)
    print(s)


# ---------- motion ----------

def motion_checks(r, src, out):
    c = {}
    times = [0.5, 1, 2.5, 4, 5, 6.5, 8, 8.5, 9.5, 10]
    pngs = [os.path.join(out, f"t-{t}.png") for t in times] + [os.path.join(out, "t-4-again.png")]
    c["frames_not_blank"] = not_blank(pngs)
    ok, d = same_render(os.path.join(out, "t-4.png"), os.path.join(out, "t-4-again.png"))
    c["same_t_same_picture"] = chk(ok, d)
    if os.path.exists(os.path.join(out, "t-1.png")) and os.path.exists(os.path.join(out, "t-6.5.png")):
        ok, d = differ(os.path.join(out, "t-1.png"), os.path.join(out, "t-6.5.png"))
        c["t1_differs_from_t6.5"] = chk(ok, d)
    else:
        c["t1_differs_from_t6.5"] = chk(False, "frames missing")

    # stage fits window without scrollbars
    bad = [t for t, f in r.get("frames", {}).items()
           if f.get("scrollWidth", 0) > f.get("innerWidth", 0) or f.get("scrollHeight", 0) > f.get("innerHeight", 0)]
    c["no_scrollbars_1920x1080"] = chk(not bad and bool(r.get("frames")), f"overflow at t={bad}" if bad else "fits")

    flat = re.sub(r"\s+", " ", htmlmod.unescape(src))
    missing = [ln for ln in MOTION_LINES if ln not in flat]
    in_canvas = bool(r.get("text_in_canvas"))
    if missing:
        c["text_lines_in_source"] = chk("needs_look" if in_canvas else False,
                                        f"not found verbatim in source: {missing}")
    else:
        c["text_lines_in_source"] = chk(True, "all three lines present")

    if in_canvas:
        for k in ("line1_timing", "title_timing", "line3_timing", "title_and_line3_at_t10"):
            c[k] = chk("needs_look", "no DOM text found at any t; text is probably drawn on canvas")
        return c

    frames = {float(t): f["visible_text"] for t, f in r["frames"].items()}

    def vis(t, line, min_op=0.05):
        items = [i for i in frames.get(t, []) if i["opacity"] > min_op]
        a = " ".join(i["text"] for i in items)
        b = "".join(i["text"] for i in items)
        hit = [i for i in items if line in norm(i["text"])]
        return bool(hit) or line in norm(a) or line in norm(b), (max([i["opacity"] for i in hit]) if hit else None)

    L1, L2, L3 = MOTION_LINES
    probs = []
    if not (vis(0.5, L1)[0] or vis(1, L1)[0]):
        probs.append("line 1 not visible at t=0.5 or 1")
    probs += [f"line 1 still visible at t={t}" for t in times if t >= 4 and vis(t, L1)[0]]
    c["line1_timing"] = chk(not probs, "; ".join(probs) or "visible by t=1, gone at t=4 and later (sampled)")

    probs, soft = [], []
    for t in [4, 5, 6.5, 8, 8.5, 9.5, 10]:
        v, op = vis(t, L2)
        if not v:
            probs.append(f"title not in DOM text at t={t}")
        elif op is not None and op < 0.95:
            soft.append(f"t={t} opacity {op}")
    if probs:
        # The title can be drawn as SVG, split letters or a pseudo-element, which DOM text does not show.
        c["title_timing"] = chk("needs_look", "; ".join(probs))
    elif soft:
        c["title_timing"] = chk("needs_look", "title present but not fully opaque: " + "; ".join(soft))
    else:
        c["title_timing"] = chk(True, "present, opaque at t=4..10 (sampled). Legibility (contrast, clipping) needs a look")

    probs, soft = [], []
    for t in [8.5, 9.5, 10]:
        v, op = vis(t, L3)
        if not v:
            probs.append(f"line 3 not visible at t={t}")
    probs += [f"line 3 visible at t={t}" for t in [0.5, 1, 2.5, 4, 5, 6.5] if vis(t, L3)[0]]
    c["line3_timing"] = chk(not probs, "; ".join(probs) or "visible at 8.5, 9.5, 10; absent before 8 (sampled)")
    both = vis(10, L2)[0] and vis(10, L3)[0]
    c["title_and_line3_at_t10"] = chk(True if both else "needs_look",
                                      "both in DOM text at t=10" if both else "not both in DOM text at t=10; look at the frame")
    return c


# ---------- sting ----------

def sting_checks(r, src, out):
    c = {}
    times = [0.5, 1.5, 2.5, 3.5, 4.5, 5.5, 6]
    pngs = [os.path.join(out, f"t-{t}.png") for t in times] + [os.path.join(out, "t-3.5-again.png")]
    c["frames_not_blank"] = not_blank(pngs)
    ok, d = same_render(os.path.join(out, "t-3.5.png"), os.path.join(out, "t-3.5-again.png"))
    c["same_t_same_picture"] = chk(ok, d)
    if os.path.exists(os.path.join(out, "t-0.5.png")) and os.path.exists(os.path.join(out, "t-4.5.png")):
        ok, d = differ(os.path.join(out, "t-0.5.png"), os.path.join(out, "t-4.5.png"))
        c["t0.5_differs_from_t4.5"] = chk(ok, d)
    else:
        c["t0.5_differs_from_t4.5"] = chk(False, "frames missing")

    bad = [t for t, f in r.get("frames", {}).items()
           if f.get("scrollWidth", 0) > f.get("innerWidth", 0) or f.get("scrollHeight", 0) > f.get("innerHeight", 0)]
    c["no_scrollbars_1920x1080"] = chk(not bad and bool(r.get("frames")), f"overflow at t={bad}" if bad else "fits")

    flat = re.sub(r"\s+", " ", htmlmod.unescape(src))
    missing = [ln for ln in STING_LINES if ln not in flat]
    in_canvas = bool(r.get("text_in_canvas"))
    if missing:
        # A wordmark may be drawn as shapes (the brief says it "forms"), so a missing literal is a look, not a fail.
        c["text_lines_in_source"] = chk("needs_look", f"not found verbatim in source: {missing}")
    else:
        c["text_lines_in_source"] = chk(True, "both lines present")

    if in_canvas:
        for k in ("wordmark_timing", "line_timing"):
            c[k] = chk("needs_look", "no DOM text found at any t; text is probably drawn on canvas")
        return c

    frames = {float(t): f["visible_text"] for t, f in r["frames"].items()}

    def vis(t, line, min_op=0.05):
        items = [i for i in frames.get(t, []) if i["opacity"] > min_op]
        a = " ".join(i["text"] for i in items)
        b = "".join(i["text"] for i in items)
        hit = [i for i in items if line in norm(i["text"])]
        return bool(hit) or line in norm(a) or line in norm(b), (max([i["opacity"] for i in hit]) if hit else None)

    L1, L2 = STING_LINES
    probs, soft = [], []
    for t in [3.5, 4.5, 5.5, 6]:
        v, op = vis(t, L1)
        if not v:
            probs.append(f"wordmark not in DOM text at t={t}")
        elif op is not None and op < 0.95:
            soft.append(f"t={t} opacity {op}")
    if probs:
        c["wordmark_timing"] = chk("needs_look", "; ".join(probs))
    elif soft:
        c["wordmark_timing"] = chk("needs_look", "wordmark present but not fully opaque: " + "; ".join(soft))
    else:
        c["wordmark_timing"] = chk(True, "present, opaque at t=3.5..6 (sampled). Legibility needs a look")

    probs = []
    for t in [4.5, 5.5, 6]:
        if not vis(t, L2)[0]:
            probs.append(f"line not in DOM text at t={t}")
    if probs:
        c["line_timing"] = chk("needs_look", "; ".join(probs))
    else:
        early = [t for t in [0.5, 1.5, 2.5, 3.5] if vis(t, L2)[0]]
        c["line_timing"] = chk(not early, f"line visible too early at t={early}" if early else "visible at 4.5, 5.5, 6; absent before 4 (sampled)")
    return c


# ---------- scene3d ----------

def scene_checks(r, src, out):
    c = {}
    times = [0, 3, 6, 9]
    pngs = [os.path.join(out, f"t-{t}.png") for t in times] + [os.path.join(out, "t-3-again.png")]
    c["frames_not_blank"] = not_blank(pngs)
    pairs, bad = [], []
    for i, a in enumerate(times):
        for b in times[i + 1:]:
            ok, d = differ(os.path.join(out, f"t-{a}.png"), os.path.join(out, f"t-{b}.png"))
            pairs.append(f"{a}-{b}: {d}")
            if not ok:
                bad.append(f"{a}-{b}")
    c["four_frames_differ_pairwise"] = chk(not bad, ("identical-ish pairs: " + ", ".join(bad)) if bad else "; ".join(pairs))
    ok, d = same_render(os.path.join(out, "t-3.png"), os.path.join(out, "t-3-again.png"))
    c["same_t_same_picture"] = chk(ok, d)

    bad = [t for t, f in r.get("frames", {}).items()
           if f.get("scrollWidth", 0) > f.get("innerWidth", 0) or f.get("scrollHeight", 0) > f.get("innerHeight", 0)]
    c["no_scrollbars_1920x1080"] = chk(not bad and bool(r.get("frames")), f"overflow at t={bad}" if bad else "fits")
    has_canvas = any(f.get("canvases", 0) > 0 for f in r.get("frames", {}).values())
    c["has_canvas"] = chk(has_canvas, "canvas element present" if has_canvas else "no <canvas> found")

    specs = re.findall(r"""(?:import|export)\s[^'"`;]*?from\s*['"]([^'"]+)['"]""", src)
    specs += re.findall(r"""import\s*['"]([^'"]+)['"]""", src)
    specs += re.findall(r"""import\s*\(\s*['"]([^'"]+)['"]""", src)
    specs += re.findall(r"""<script[^>]+src\s*=\s*['"]([^'"]+)['"]""", src)
    specs += re.findall(r"""<link[^>]+href\s*=\s*['"]([^'"]+)['"]""", src)
    urls = re.findall(r"""https?://[^\s'"`)<>]+""", src)
    # `data:` URLs (an empty favicon, say) load nothing from outside and are not imports.
    badspec = [s for s in specs if not s.startswith("./vendor/") and not s.startswith("data:")]
    detail = []
    if badspec:
        detail.append(f"imports/scripts not from ./vendor/: {badspec}")
    if urls:
        detail.append(f"URLs in source: {urls[:5]}")
    if "importmap" in src:
        detail.append("importmap present")
    if not specs:
        detail.append("no import found")
    c["imports_only_from_vendor"] = chk(not detail, "; ".join(detail) or f"imports: {sorted(set(specs))}")
    return c


# ---------- page ----------

def page_checks(r, out):
    c = {}
    pngs = [os.path.join(out, n) for n in ("w1440.png", "w390.png", "w1440-fold.png", "w390-fold.png")]
    c["screens_not_blank"] = not_blank(pngs)
    # innerText follows CSS text-transform, so a line set in capitals by style still counts: compare without case.
    text = norm(r.get("innerText_1440", "")).lower()
    lines = [ln.lower() for ln in PAGE_LINES]
    missing = [ln for ln in PAGE_LINES if ln != "Loam" and ln.lower() not in text]
    if text.count("loam") < 3:
        missing.append("Loam (brand as its own text)")
    c["all_copy_lines_present"] = chk(not missing, f"missing: {missing}" if missing else "all 14 lines found")

    rest = text
    for ln in sorted(lines, key=len, reverse=True):
        rest = rest.replace(ln, " \x00 ")
    left = norm(rest.replace("\x00", " "))
    c["no_extra_visible_text"] = chk(not left, f"leftover text: {left!r}" if left else "none")

    for w in ("1440", "390"):
        i = r.get("widths", {}).get(w, {})
        sw, ww = i.get("scrollWidth", 0), i.get("windowWidth", 0)
        c[f"no_horizontal_scroll_{w}"] = chk(bool(i) and sw <= ww and i.get("bodyScrollWidth", 0) <= ww,
                                             f"scrollWidth {sw}, bodyScrollWidth {i.get('bodyScrollWidth')}, window {ww}")
    for w in ("1440", "390"):
        b = r.get("widths", {}).get(w, {}).get("button", {})
        if not b.get("found"):
            c[f"button_in_first_viewport_{w}"] = chk(False, "no <a>/<button> with text 'Reserve yours'")
        else:
            c[f"button_in_first_viewport_{w}"] = chk(bool(b.get("inside_first_viewport")), f"rect {b.get('rect')}")
    return c


# ---------- pricing ----------

def pricing_checks(r, out):
    c = {}
    pngs = [os.path.join(out, n) for n in ("w1440.png", "w390.png", "w1440-fold.png", "w390-fold.png")]
    c["screens_not_blank"] = not_blank(pngs)
    text = norm(r.get("innerText_1440", "")).lower()
    lines = [ln.lower() for ln in PRICING_LINES]
    missing = [ln for ln in PRICING_LINES if ln != "Relay" and ln.lower() not in text]
    foot = "relay labs, lisbon"
    if text.replace(foot, " ").count("relay") < 1:
        missing.append("Relay (brand as its own text)")
    n = text.count("per person, per month")
    if n != 3:
        missing.append(f"'per person, per month' appears {n} times, expected 3")
    c["all_copy_lines_present"] = chk(not missing, f"missing: {missing}" if missing else f"all {len(PRICING_LINES)} lines found")

    rest = text
    for ln in sorted(lines, key=len, reverse=True):
        rest = rest.replace(ln, " \x00 ")
    left = norm(rest.replace("\x00", " "))
    c["no_extra_visible_text"] = chk(not left, f"leftover text: {left!r}" if left else "none")

    for w in ("1440", "390"):
        i = r.get("widths", {}).get(w, {})
        sw, ww = i.get("scrollWidth", 0), i.get("windowWidth", 0)
        c[f"no_horizontal_scroll_{w}"] = chk(bool(i) and sw <= ww and i.get("bodyScrollWidth", 0) <= ww,
                                             f"scrollWidth {sw}, bodyScrollWidth {i.get('bodyScrollWidth')}, window {ww}")
    pb = r.get("widths", {}).get("1440", {}).get("pricing_buttons", {})
    nf = [b for b in PRICING_BUTTONS if not pb.get(b, {}).get("found")]
    c["three_buttons_are_elements"] = chk(not nf, f"no <a>/<button> with text: {nf}" if nf else "all three found")
    out_v = [b for b in PRICING_BUTTONS if not pb.get(b, {}).get("inside_first_viewport")]
    c["buttons_in_first_viewport_1440"] = chk(not out_v, f"not fully inside 1440x900: {out_v}" if out_v else "all three inside")
    return c


# ---------- copy ----------

EMOJI = re.compile("[\U0001F000-\U0001FAFF\u2190-\u21FF\u2300-\u23FF\u2600-\u27BF\u2B00-\u2BFF\uFE0F\u200D\u20E3\u2122\u00A9\u00AE]")


def copy_checks(run):
    c = {}
    c["only_allowed_files"] = allowed_files(run, ["copy.md"], require=("copy.md",))
    p = os.path.join(run, "copy.md")
    if not os.path.exists(p):
        return c
    md = open(p, encoding="utf-8").read()
    parts = re.split(r"(?m)^(##[ \t]+.*)$", md)
    pre = parts[0].strip()
    heads = [parts[i].strip() for i in range(1, len(parts), 2)]
    bodies = [parts[i].strip() for i in range(2, len(parts), 2)]
    want = ["## Headline", "## Summary", "## Post"]
    ok = heads == want and not pre
    c["three_sections_in_order"] = chk(ok, f"headings {heads}" + (f", text before first heading: {pre[:40]!r}" if pre else ""))
    if heads != want:
        return c
    head, summ, post = bodies
    hl = [l for l in head.splitlines() if l.strip()]
    c["headline_one_line_max_60"] = chk(len(hl) == 1 and len(hl[0].strip()) <= 60, f"{len(hl)} line(s), {len(head)} chars")
    # sentence count: split after . ! ? followed by whitespace; abbreviations like "B.V." do not split
    flat = norm(summ).replace("B.V.", "B\x00V\x00")
    sents = [s for s in re.split(r"(?<=[.!?])[\"')\]]*\s+(?=\S)", flat) if s.strip()]
    ends = bool(re.search(r"[.!?][\"')\]]*$", norm(summ)))
    c["summary_three_sentences"] = chk(len(sents) == 3 and ends, f"{len(sents)} sentences: {[s[:30] for s in sents]}")
    words = len(post.split())
    c["post_100_to_130_words"] = chk(100 <= words <= 130, f"{words} words")
    allt = head + "\n" + summ + "\n" + post
    emo = EMOJI.findall(allt)
    tags = re.findall(r"(?:^|\s)#\w+", allt)
    c["no_emoji_no_hashtags"] = chk(not emo and not tags, f"emoji {emo[:5]} hashtags {tags[:5]}" if emo or tags else "none")
    pl = bool(re.search(r"[*_`\[\]]|(?m:^\s*[-#>])", post))
    c["post_plain_text"] = chk(not pl, "markdown characters in post" if pl else "plain")
    for name, t in (("summary", summ), ("post", post)):
        miss = [k for k in ("Loam", "$349") if k not in t]
        c[f"{name}_has_Loam_and_price"] = chk(not miss, f"missing {miss}" if miss else "both present")
    c["facts_only"] = chk("needs_look", "no invented numbers, claims or features: compare with the fact sheet by hand")
    return c


if __name__ == "__main__":
    main()
