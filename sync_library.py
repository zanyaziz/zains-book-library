#!/usr/bin/env python3
"""Sync the book-library page with the episodes that actually exist on disk.

Idempotent. Run any time: it copies finished episode MP3s and summary PDFs
into assets/, keeps books.json in line with the series state and the daily
queue, rebuilds index.html, and commits + pushes only when something changed.

Ground truth, in order of trust:
  1. ~/workspace/podcasts/*-episode-<n>-*/  (nonzero .mp3 = audio ready)
  2. summary PDFs under the goal's files/ dir or ~/workspace/your_files/
  3. ~/workspace/books/series-state.json      (series books + episode numbers)
  4. ~/workspace/books/daily-book-queue.json  (post-series queue + numbering)

Existing books.json entries (title, author, blurb, slug, date) are preserved;
the script only fills in audio/summary_pdf fields that newly become available
and creates minimal entries for finished books that have none yet.
"""
import json, re, shutil, subprocess, sys
from pathlib import Path

HOME = Path.home()
LIB = HOME / "workspace/book-library"
PODCASTS = HOME / "workspace/podcasts"
SUMMARIES_MD = HOME / "workspace/books/summaries"
GOAL_FILES = HOME / "workspace/goals/top-10-books-10-day-podcast-summary-series/files"
YOUR_FILES = HOME / "workspace/your_files"
STATE = HOME / "workspace/books/series-state.json"
QUEUE = HOME / "workspace/books/daily-book-queue.json"

SITE = "https://zanyaziz.github.io/zains-book-library/"


def kebab(text: str) -> str:
    text = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return re.sub(r"^the-", "", text)


def load_json(path, default):
    try:
        return json.loads(path.read_text())
    except FileNotFoundError:
        return default


def first_sentences(md_path: Path, limit=320) -> str:
    """Pull the first sentences of 'The Book in 60 Seconds' as a blurb."""
    if not md_path.exists():
        return ""
    text = md_path.read_text()
    m = re.search(r"## The Book in 60 Seconds\s*(.+?)(?=\n## |\Z)", text, re.S)
    body = (m.group(1) if m else text).strip()
    body = re.sub(r"\s+", " ", body)
    out, count = "", 0
    for sent in re.split(r"(?<=[.!?])\s+", body):
        if count >= 2 or len(out) + len(sent) > limit:
            break
        out = (out + " " + sent).strip()
        count += 1
    return out


def episode_mp3(n: int):
    """Newest nonzero MP3 for episode n, plus its date, or (None, None)."""
    best = None
    for d in PODCASTS.glob(f"*-episode-{n}-*"):
        m = re.search(r"-(\d{4}-\d{2}-\d{2})$", d.name)
        for mp3 in d.glob("*.mp3"):
            if mp3.stat().st_size > 0 and (best is None or mp3.stat().st_mtime > best[0].stat().st_mtime):
                best = (mp3, m.group(1) if m else None)
    return best if best else (None, None)


def summary_pdf(title: str):
    """Find the typeset summary PDF for a title, or None."""
    essence = kebab(title)
    for base in (GOAL_FILES, YOUR_FILES):
        if not base.exists():
            continue
        for pdf in base.glob("*/*.pdf"):
            if essence and essence in kebab(pdf.parent.name):
                return pdf
    return None


def main() -> int:
    data = load_json(LIB / "books.json", {"series": "", "books": [], "upcoming": []})
    state = load_json(STATE, {"books": [], "next_index": 0})
    queue = load_json(QUEUE, {"queue": [], "episode_counter": 1})

    books_by_ep = {b["episode"]: b for b in data["books"]}
    known = {}  # episode -> (title, author)

    for b in state["books"]:
        known[b["n"]] = (b["title"], b.get("author"))

    changes = []

    # --- ensure an entry (with files) for every finished episode -------------
    finished_eps = [b["n"] for b in state["books"][: state["next_index"]]]
    finished_eps += [b["episode"] for b in data["books"]]  # keep existing ones
    for n in sorted(set(finished_eps)):
        mp3, date = episode_mp3(n)
        entry = books_by_ep.get(n)
        title = (known.get(n) or (entry or {}).get("title") or (None, None))[0]
        if not title:
            continue
        pdf = summary_pdf(title)
        if entry is None:
            if not mp3 and not pdf:
                continue  # nothing to show yet
            slug = kebab(title)
            author = (known.get(n) or (None, None))[1]
            entry = {"episode": n, "slug": slug, "title": title}
            if author:
                entry["author"] = author
            blurb = first_sentences(SUMMARIES_MD / f"{kebab(title)}-summary.md")
            if blurb:
                entry["blurb"] = blurb
            if date:
                entry["date"] = date
            data["books"].append(entry)
            books_by_ep[n] = entry
            changes.append(f"new entry ep{n}")
        slug = entry["slug"]
        if mp3:
            dest = LIB / "assets/audio" / f"{slug}.mp3"
            dest.parent.mkdir(parents=True, exist_ok=True)
            if not dest.exists() or dest.stat().st_size != mp3.stat().st_size:
                shutil.copy2(mp3, dest)
                changes.append(f"audio ep{n}")
            entry["audio"] = f"assets/audio/{slug}.mp3"
        if pdf:
            dest = LIB / "assets/summaries" / f"{slug}.pdf"
            dest.parent.mkdir(parents=True, exist_ok=True)
            if not dest.exists() or dest.stat().st_size != pdf.stat().st_size:
                shutil.copy2(pdf, dest)
                changes.append(f"pdf ep{n}")
            entry["summary_pdf"] = f"assets/summaries/{slug}.pdf"

    data["books"].sort(key=lambda b: b["episode"])

    # --- rebuild "coming up next" -------------------------------------------
    upcoming = []
    for b in state["books"][state["next_index"]:]:
        e = {"episode": b["n"], "title": b["title"]}
        if b.get("author"):
            e["author"] = b["author"]
        upcoming.append(e)
    n = queue.get("episode_counter", 1)
    for b in queue.get("queue", []):
        e = {"episode": n, "title": b["title"]}
        if b.get("author"):
            e["author"] = b["author"]
        upcoming.append(e)
        n += 1
    if data["upcoming"] != upcoming:
        data["upcoming"] = upcoming
        changes.append("upcoming list")

    if not changes:
        print(json.dumps({"changed": False, "site": SITE}))
        return 0

    (LIB / "books.json").write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")
    subprocess.run([sys.executable, str(LIB / "build.py")], check=True,
                   cwd=LIB, capture_output=True, text=True)
    subprocess.run(["git", "add", "-A"], cwd=LIB, check=True)
    msg = "Sync library: " + ", ".join(changes)
    subprocess.run(["git", "commit", "-q", "-m", msg], cwd=LIB, check=True)
    push = subprocess.run(["git", "push", "-q", "origin", "main"],
                          cwd=LIB, capture_output=True, text=True)
    ok = push.returncode == 0
    print(json.dumps({"changed": True, "changes": changes, "pushed": ok,
                      "episodes_with_audio": sum(1 for b in data["books"] if b.get("audio")),
                      "site": SITE}))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
