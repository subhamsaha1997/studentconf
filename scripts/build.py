#!/usr/bin/env python3
"""Build the conference site from committee-owned JSON and CSV files."""

from __future__ import annotations

import argparse
import csv
import html
import json
import re
import shutil
from collections import OrderedDict
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONTENT = ROOT / "content"
DIST = ROOT / "dist"


def read_json(name):
    with (CONTENT / name).open(encoding="utf-8") as file:
        return json.load(file)


def text(value):
    """Escape editorial content; convert paragraph breaks to paragraphs."""
    return "<br><br>".join(
        html.escape(p.strip()) for p in value.strip().split("\n\n") if p.strip()
    )


def url_or_text(label, url):
    return (
        f'<a href="{html.escape(url, quote=True)}" rel="noopener">{html.escape(label)}</a>'
        if url
        else html.escape(label)
    )


def anchor(*parts):
    """Make a stable fragment identifier from the visible program information."""
    value = "-".join(parts).lower()
    value = re.sub(r"[^a-z0-9]+", "-", value).strip("-")
    return value or "talk"


def load_program():
    required = {"day", "session", "start", "end", "kind", "speaker", "title"}
    with (CONTENT / "program.csv").open(encoding="utf-8", newline="") as file:
        rows = list(csv.DictReader(file))
    if not rows or not required.issubset(rows[0]):
        missing = required - set(rows[0] if rows else [])
        raise ValueError(
            f"program.csv is missing columns: {', '.join(sorted(missing))}"
        )
    for number, row in enumerate(rows, 2):
        if row["kind"] not in {"talk", "plenary", "event"}:
            raise ValueError(
                f"program.csv row {number}: kind must be talk, plenary, or event"
            )
        if not row["day"] or not row["session"] or not row["start"]:
            raise ValueError(
                f"program.csv row {number}: day, session, and start are required"
            )
    return rows


def load_talks():
    talks = read_json("talks.json")
    required = {"speaker", "title", "abstract"}
    for number, talk in enumerate(talks, 1):
        missing = required - set(talk)
        if missing:
            raise ValueError(
                f"talks.json entry {number} is missing: {', '.join(sorted(missing))}"
            )
    return talks


def unique_index(items, key, label):
    indexed = {}
    for item in items:
        value = key(item)
        if value in indexed:
            raise ValueError(
                f"Duplicate {label}: {' — '.join(value) if isinstance(value, tuple) else value}"
            )
        indexed[value] = item
    return indexed


def required_talk(talks, row):
    key = (row["speaker"], row["title"])
    if key not in talks:
        raise ValueError(f"No talks.json entry for {key[0]} — {key[1]}")
    return talks[key]


def page(site, title, body, active):
    nav = [
        ("index.html", "Home"),
        ("program.html", "Program"),
        ("plenary-talks.html", "Plenary Talks"),
        ("abstracts.html", "Student Talks"),
    ]
    links = "".join(
        f'<a href="{path}"{ " aria-current=\"page\"" if path == active else ""}>{label}</a>'
        for path, label in nav
    )
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="description" content="{html.escape(site['description'], quote=True)}">
  <title>{html.escape(site['short_name'])} {html.escape(site['year'])} — {html.escape(title)}</title>
  <script>
    (() => {{
      const requested = new URLSearchParams(location.search).get('theme');
      let saved = null;
      try {{ saved = localStorage.getItem('lidsconf-theme'); }} catch (_) {{}}
      const theme = ['light', 'dark'].includes(requested) ? requested : (saved || (matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'));
      document.documentElement.dataset.theme = theme;
    }})();
  </script>
  <link rel="stylesheet" href="assets/site.css">
  <style>
    .news-feed {{ overflow-y: auto; overscroll-behavior: contain; }}
  </style>
</head>
<body>
  <header class="site-header"><nav class="nav" aria-label="Primary navigation">
    <a class="brand" href="index.html"><img src="assets/images/lids-logo-maroon.png" alt="LIDS logo"><div>{html.escape(site['name'])}<br><span>{html.escape(site['year'])}</span></div></a>
    <div class="links">{links}</div><button class="theme-toggle" type="button" aria-label="Toggle color theme" title="Toggle light and dark theme"></button>
  </nav></header>
  <main>{body}</main>
  <footer class="footer"><div class="wrap"><span>{html.escape(site['name'])} {html.escape(site['year'])}</span><span><a href="https://accessibility.mit.edu/">Accessibility at MIT</a> · <a href="mailto:{html.escape(site['contact_email'], quote=True)}">Contact organizers</a></span></div></footer>
  <script>
    const themeKey = 'lidsconf-theme';
    const button = document.querySelector('.theme-toggle');
    const applyTheme = (theme) => {{
      document.documentElement.dataset.theme = theme;
      button.textContent = theme === 'dark' ? '☀' : '☾';
      button.setAttribute('aria-pressed', String(theme === 'dark'));
      document.querySelectorAll('a[href]').forEach((link) => {{
        const raw = link.getAttribute('href');
        if (!raw || /^(https?:|mailto:|#)/.test(raw)) return;
        const url = new URL(raw, location.href);
        if (url.pathname.endsWith('.html')) {{
          url.searchParams.set('theme', theme);
          link.href = url.href;
        }}
      }});
    }};
    applyTheme(document.documentElement.dataset.theme);
    button.addEventListener('click', () => {{
      const theme = document.documentElement.dataset.theme === 'dark' ? 'light' : 'dark';
      applyTheme(theme);
      try {{ localStorage.setItem(themeKey, theme); }} catch (_) {{}}
    }});
    window.addEventListener('storage', (event) => {{
      if (event.key === themeKey && event.newValue) applyTheme(event.newValue);
    }});
    const organizers = document.querySelector('#organizer-list');
    if (organizers) {{
      const people = Array.from(organizers.children);
      for (let index = people.length - 1; index > 0; index -= 1) {{
        const swap = Math.floor(Math.random() * (index + 1));
        [people[index], people[swap]] = [people[swap], people[index]];
      }}
      people.forEach((person) => organizers.appendChild(person));
    }}
    const newsFeed = document.querySelector('.news-feed');
    if (newsFeed) {{
      const showNewestThree = () => {{
        const items = Array.from(newsFeed.querySelectorAll('article'));
        if (items.length <= 3) return;
        const feedTop = newsFeed.getBoundingClientRect().top;
        const third = items[2].getBoundingClientRect();
        newsFeed.style.maxHeight = `${{third.bottom - feedTop}}px`;
      }};
      showNewestThree();
      addEventListener('resize', showNewestThree);
    }}
  </script>
</body>
</html>"""


def home(site, speakers, organizers, news):
    speaker_list = "".join(
        f"<li>{url_or_text(s['name'], s.get('url', ''))} <span class=\"muted\">— {html.escape(s['affiliation'])}</span></li>"
        for s in speakers
    )
    organizer_list = "".join(
        f"<li>{url_or_text(o['name'], o.get('url', ''))}</li>" for o in organizers
    )

    # Keep the newest announcements at the top.  The page shows the first
    # three initially; older items remain available by scrolling the feed.
    def announcement_date(item):
        try:
            return datetime.strptime(item.get("date", ""), "%B %d, %Y")
        except ValueError:
            return datetime.min

    news_items = "".join(
        f"<article><h3>{html.escape(n['title'])}</h3><p>{html.escape(n['text'])}</p><div class=\"date\">{html.escape(n.get('date', ''))}</div></article>"
        for n in sorted(news, key=announcement_date, reverse=True)
    )
    years = ", ".join(
        f'<a href="{html.escape(y["url"], quote=True)}" rel="noopener">{html.escape(y["year"])}</a>'
        for y in site.get("past_years", [])
    )
    body = f"""<div class="wrap hero"><section>
  <div class="eyebrow">{html.escape(site['dates'])} · {html.escape(site['venue'])}</div>
  <h1>{html.escape(site['ordinal'])} Annual {html.escape(site['short_name'])}</h1>
  <p class="lead">{html.escape(site['tagline'])}</p><p>{html.escape(site['description'])}</p>
  <div class="actions"><a class="button" href="{html.escape(site['registration_url'], quote=True)}">Register to attend</a><a class="button secondary" href="{html.escape(site['submission_url'], quote=True)}">Submit a student talk</a></div>
  <p class="muted">Past conferences: {years}</p>
  <section class="section"><h2>Plenary speakers</h2><ul>{speaker_list}</ul></section>
  <section class="section"><h2>Organizing committee</h2><p>Questions? <a href="mailto:{html.escape(site['contact_email'], quote=True)}">Contact the conference co-chairs</a>.</p><ul id="organizer-list">{organizer_list}</ul></section>
</section><aside class="news"><h2>News</h2><div class="news-feed" tabindex="0" aria-label="Conference news">{news_items}</div></aside></div>"""
    return page(site, "Home", body, "index.html")


def talks(site, speakers, rows, talk_details):
    cards = []
    for entry in (row for row in rows if row["kind"] == "plenary"):
        if entry["speaker"] not in speakers:
            raise ValueError(
                f"No speakers.json profile for plenary speaker: {entry['speaker']}"
            )
        speaker = speakers[entry["speaker"]]
        detail = required_talk(talk_details, entry)
        image = speaker.get("image", "")
        portrait = (
            f'<img class="portrait" src="assets/images/{html.escape(image, quote=True)}" alt="Portrait of {html.escape(speaker["name"], quote=True)}">'
            if image
            else '<div class="portrait placeholder">Photo to be added</div>'
        )
        cards.append(
            f"""<article class="speaker" id="{anchor('plenary', speaker['name'])}"><div>{portrait}</div><div>
          <h2>{url_or_text(speaker['name'], speaker.get('url', ''))}</h2><p class="muted">{html.escape(speaker.get('role', 'Plenary speaker'))}<br>{html.escape(speaker['affiliation'])}</p>
          <h3 class="talk-title">{html.escape(entry['title'])}</h3><h3>Abstract</h3><p>{text(detail['abstract'])}</p><h3>Biography</h3><p>{text(speaker['bio'])}</p>
        </div></article>"""
        )
    return page(
        site,
        "Plenary Talks",
        '<div class="wrap"><div class="eyebrow">Conference program</div><h1>Plenary speakers</h1>'
        + "".join(cards)
        + "</div>",
        "plenary-talks.html",
    )


def grouped(rows):
    result = OrderedDict()
    for row in rows:
        result.setdefault(row["day"], OrderedDict()).setdefault(
            row["session"], []
        ).append(row)
    return result


def program(site, rows):
    days = []
    for day, sessions in grouped(rows).items():
        blocks = []
        for session, entries in sessions.items():
            items = [
                f'<tr class="session-row"><td colspan="2">{html.escape(session)}</td></tr>'
            ]
            for r in entries:
                time = html.escape(r["start"] + (f"–{r['end']}" if r["end"] else ""))
                speaker = (
                    f'<strong>{html.escape(r["speaker"])}</strong><br>'
                    if r["speaker"]
                    else ""
                )
                title = (
                    f'<span class="talk-title">{html.escape(r["title"])}</span>'
                    if r["title"]
                    else ""
                )
                if r["kind"] == "talk":
                    target = (
                        f'abstracts.html#{anchor("talk", r["speaker"], r["title"])}'
                    )
                    details = f'<a href="{target}" aria-label="Read abstract for {html.escape(r["title"], quote=True)}">{speaker}{title}</a>'
                elif r["kind"] == "plenary":
                    target = f'plenary-talks.html#{anchor("plenary", r["speaker"])}'
                    details = f'<a href="{target}" aria-label="Read plenary details for {html.escape(r["speaker"], quote=True)}">{speaker}{title}</a>'
                else:
                    details = speaker + title
                items.append(f'<tr><td class="time">{time}</td><td>{details}</td></tr>')
            blocks.append('<table class="program">' + "".join(items) + "</table>")
        days.append(
            f'<section class="program-day"><h2>{html.escape(day)}</h2>{"".join(blocks)}</section>'
        )
    return page(
        site,
        "Program",
        '<div class="wrap"><div class="eyebrow">Conference program</div><h1>Schedule</h1><p class="lead">Times and details are maintained in one program spreadsheet.</p>'
        + "".join(days)
        + "</div>",
        "program.html",
    )


def abstracts(site, rows, talk_details):
    sessions = []
    for day, day_sessions in grouped(rows).items():
        for session, entries in day_sessions.items():
            talks = [r for r in entries if r["kind"] == "talk"]
            if not talks:
                continue
            items = "".join(
                f'<article id="{anchor("talk", r["speaker"], r["title"])}"><h3>{html.escape(r["title"])}</h3><p class="muted">{html.escape(r["speaker"])} · {html.escape(day)}</p><p>{text(required_talk(talk_details, r)["abstract"] or "Abstract to be announced.")}</p></article>'
                for r in talks
            )
            sessions.append(
                f'<section class="section"><h2>{html.escape(session)}</h2>{items}</section>'
            )
    return page(
        site,
        "Student Talks",
        '<div class="wrap"><div class="eyebrow">Conference program</div><h1>Student talks</h1><p class="lead">Abstracts are linked to the published schedule by speaker name and talk title.</p>'
        + "".join(sessions)
        + "</div>",
        "abstracts.html",
    )


def validate_links():
    missing = []
    pattern = re.compile(r'(?:href|src)="([^"#?]+)"')
    for file in DIST.glob("*.html"):
        for reference in pattern.findall(file.read_text(encoding="utf-8")):
            if reference.startswith(("http://", "https://", "mailto:")):
                continue
            if not (file.parent / reference).exists():
                missing.append(f"{file.name} → {reference}")
    if missing:
        raise ValueError("Missing local references:\n" + "\n".join(missing))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--check", action="store_true", help="Build and validate local links"
    )
    parser.parse_args()
    site, speaker_list, organizers, news, rows, talk_list = (
        read_json("site.json"),
        read_json("speakers.json"),
        read_json("organizers.json"),
        read_json("announcements.json"),
        load_program(),
        load_talks(),
    )
    speakers = unique_index(
        speaker_list, lambda speaker: speaker["name"], "speaker name"
    )
    talk_details = unique_index(
        talk_list,
        lambda talk: (talk["speaker"], talk["title"]),
        "speaker and talk title",
    )
    if not site["contact_email"] or not re.match(
        r"^[^@\s]+@[^@\s]+\.[^@\s]+$", site["contact_email"]
    ):
        raise ValueError("site.json needs a valid contact_email")
    if DIST.exists():
        shutil.rmtree(DIST)
    shutil.copytree(ROOT / "assets", DIST / "assets")
    pages = {
        "index.html": home(site, speaker_list, organizers, news),
        "program.html": program(site, rows),
        "plenary-talks.html": talks(site, speakers, rows, talk_details),
        "abstracts.html": abstracts(site, rows, talk_details),
    }
    for name, output in pages.items():
        (DIST / name).write_text(output, encoding="utf-8")
    validate_links()
    print(f"Built and checked {len(pages)} pages in {DIST}")


if __name__ == "__main__":
    main()
