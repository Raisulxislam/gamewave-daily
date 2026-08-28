#!/usr/bin/env python3
"""
GameWave rewrite + Bangla translation step.

For every Hugo post that isn't rewritten yet, batch-call opencode headlessly
(`opencode run --format json`) to produce:
  - an entirely original English rewrite (GameWave magazine style),
  - a natural Bangla translation of that rewrite.
The English body and the Bangla body (content_bn) are written back to the
post's front matter. Falls back silently (publish draft content as-is) if the
LLM call fails.

Self-contained Python stderr/stdout note: this Termux build loses sys.stdout,
so every line is also written with os.write(1, ...).
"""
import os
import re
import sys
import json
import subprocess
from datetime import datetime

HOME = os.path.expanduser("~")
ROOT = os.path.join(HOME, "gamewave-daily")
POSTS = os.path.join(ROOT, "content", "posts")
LOG = os.path.join(HOME, ".gwi", "run.log")
OPENCODE = "/data/data/com.termux/files/usr/bin/opencode"

EXPORT_PATH = os.path.join(HOME, ".gwi", "rewrite_out.jsonl")
BATCH = 6
TIMEOUT = 900

PROMPT_TMPL = """You are the senior editor of GameWave, an independent gaming news site.

Rewrite each story below from scratch in GameWave's house style: punchy magazine prose, 2-4 short paragraphs, one or two bold takes, written in fresh original sentences. Use ONLY the factual information given — never copy or closely paraphrase the original headline or body, never invent facts. Keep claims attributable to what the story actually says.

Also produce title_bn and body_bn: a natural, fluent Bangla (Bengali) translation of YOUR English rewrite (not a word-for-word mechanical one) plus its Bangla headline.

Return ONLY a JSON array, nothing else (no markdown fences). One object per story in the same order:
[{{"slug": "<slug>", "title": "<rewritten English headline>", "title_bn": "<bangla headline>", "body": "<english markdown body>", "body_bn": "<bangla markdown body>"}}]

Stories:
{stories}
"""


def log(msg):
    line = f"[{datetime.now().strftime('%H:%M:%S')}] {msg}"
    print(line)
    try:
        os.write(1, (line + "\n").encode())
    except Exception:
        pass


def load_pending():
    pending = []
    limit = os.environ.get("GW_LIMIT")
    limit = int(limit) if limit else 0
    for f in sorted(os.listdir(POSTS)):
        if not f.endswith(".md"):
            continue
        if limit and len(pending) >= limit:
            break
        path = os.path.join(POSTS, f)
        txt = open(path, encoding="utf-8").read()
        if "rewritten: true" in txt and "content_bn:" in txt:
            continue  # already rewritten
        fm, body = split_fm(txt)
        if not fm:
            continue
        fm["path"] = path
        fm["slug"] = f[:-3]
        fm["body_draft"] = summarize(body)
        pending.append(fm)
    return pending


def split_fm(txt):
    lines = txt.split("\n")
    if not lines or lines[0].strip() != "---":
        return None, txt
    fm = {}
    body_start = None
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            body_start = i + 1
            break
        m = re.match(r"^([A-Za-z_]+):\s*(.*)$", lines[i])
        if m:
            fm[m.group(1)] = m.group(2).strip()
    body = "\n".join(lines[body_start:]).strip() if body_start else ""
    return fm, body


def key(fm, k, default=""):
    v = fm.get(k) or default
    return v.strip('"').strip()


def summarize(body):
    # First paragraph only, trimmed - that's the raw draft lead the model edits.
    first = body.split("\n\n")[0] if body else ""
    return first[:900] if first else "No summary available."


def build_prompt(pending):
    stories = []
    for fm in pending:
        stories.append(
            f"- slug: {fm['slug']}\n"
            f"  title: {key(fm, 'title')}\n"
            f"  date: {key(fm, 'date')}\n"
            f"  tags: {key(fm, 'tags')}\n"
            f"  summary: {summarize(fm['body_draft'])}"
        )
    return PROMPT_TMPL.format(stories="\n".join(stories))


def run_opencode(prompt):
    # make sure HOME env is set for the child; shell script already does.
    env = dict(os.environ)
    env["HOME"] = HOME
    cmd = [OPENCODE, "run", "--pure", "--format", "json",
           "--agent", "build", prompt]
    with open(EXPORT_PATH, "w", encoding="utf-8") as out:
        proc = subprocess.run(cmd, stdout=out, stderr=subprocess.DEVNULL,
                              env=env, timeout=TIMEOUT)
    if proc.returncode != 0:
        raise RuntimeError(f"opencode exited {proc.returncode}")
    text_parts = []
    with open(EXPORT_PATH, encoding="utf-8") as fh:
        for line in fh:
            try:
                ev = json.loads(line)
            except Exception:
                continue
            if ev.get("type") == "text":
                part = ev.get("part", {}) or {}
                if part.get("type") == "text" and part.get("text"):
                    text_parts.append(part["text"])
    return "".join(reversed(text_parts)).strip()


def extract_json(text):
    text = re.sub(r"```(?:json)?", "", text).strip("` \n\t")
    try:
        data = json.loads(text)
    except Exception:
        m = re.search(r"\[.*\]", text, re.S)
        if not m:
            m = re.search(r"\{.*\}", text, re.S)
        if not m:
            return None
        try:
            data = json.loads(m.group(0))
        except Exception:
            return None
    return data if isinstance(data, list) else [data]


def esc(s):
    return s.replace("\\", "\\\\").replace('"', '\\"')


def write_back(fm, item, body_en):
    # Keep existing metadata, swap title, add bilingual bodies + marker,
    # strip any legacy source_* keys.
    keep = {k: fm.get(k) for k in ("date", "tags", "draft", "feature")}
    lines = ["---"]
    lines.append(f"title: \"{esc(item.get('title', key(fm, 'title')))}\"")
    for k in ("date", "tags", "draft", "feature"):
        if keep.get(k) is not None:
            lines.append(f"{k}: {keep[k]}")
    bn = (item.get("body_bn") or "").strip()
    lines.append("content_bn: |")
    for para in bn.split("\n"):
        lines.append("  " + para if para.strip() else "")
    lines.append("rewritten: true")
    lines.append("---")
    lines.append("")
    lines.append((body_en or item.get("body", "")).strip())
    lines.append("")
    with open(fm["path"], "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines))


def main():
    pending = load_pending()
    if not pending:
        log("rewrite: nothing to rewrite")
        return 0
    log(f"rewrite: {len(pending)} post(s) pending")
    done = restored = 0
    for start in range(0, len(pending), BATCH):
        batch = pending[start:start + BATCH]
        try:
            prompt = build_prompt(batch)
            log(f"rewrite: calling opencode for {len(batch)} post(s)...")
            raw = run_opencode(prompt)
            items = extract_json(raw)
            if not items:
                log("rewrite: no valid JSON returned; keeping drafts")
                continue
        except Exception as e:
            log(f"rewrite: opencode failed ({e}); keeping draft content")
            continue
        by_slug = {str(it.get("slug", "")).strip(): it for it in items}
        for fm in batch:
            item = by_slug.get(fm["slug"])
            if not item:
                log(f"rewrite: no result for {fm['slug']}; left as draft")
                restored += 1
                continue
            try:
                write_back(fm, item, fm["body_draft"])
                done += 1
                log(f"rewrite: {fm['slug']} -> done (+ বাংলা)")
            except Exception as e:
                log(f"rewrite: write error {fm['slug']}: {e}")
                restored += 1
    log(f"rewrite: {done} rewritten, {restored} kept as draft")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:
        log(f"rewrite FATAL: {e}")
        sys.exit(0)