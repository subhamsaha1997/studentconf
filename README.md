# LIDS Student Conference website template

This is a small static-site template for the annual Sanjoy K. Mitter LIDS Student Conference. It keeps the familiar maroon, white, and editorial layout, but separates conference content from page layout.

## Fast yearly rollover

1. Update `content/site.json` (year, dates, venue, registration links, contact email).
2. Update the people and announcements files in `content/`.
3. Replace `content/program.csv` with the approved, compact schedule. Add abstracts in `content/talks.json`; its entries use ordinary speaker names and talk titles, not IDs.
4. Add speaker images to `assets/images/` and set each speaker's `image` field.
5. Run `python3 scripts/build.py`.
6. Open `dist/index.html` locally, review every page, then publish the entire `dist/` folder.

No third-party Python packages or JavaScript build tools are required.

## Content files

| File | Committee-owned information |
| --- | --- |
| `site.json` | Conference identity, dates, calls to action, contact information |
| `speakers.json` | Plenary speakers' names, affiliations, biographies, photos |
| `organizers.json` | Committee roster |
| `announcements.json` | Homepage news items |
| `program.csv` | Compact schedule: sessions, events, plenaries, and student talks |
| `talks.json` | Abstracts, matched by speaker name and talk title |

### Program CSV conventions

Each row has `day`, `session`, `start`, `end`, `kind`, `speaker`, and `title`. Reuse the same `session` name for rows belonging to a session. Use `kind=event` for breaks, panels, and meals; `kind=plenary` for plenary talks; and `kind=talk` for student talks. The program page intentionally shows only the schedule, speaker, and title. `talks.json` supplies each long-form abstract by matching its `speaker` and `title` exactly; the builder reports a clear error if one is missing or duplicated.

Student talks in the generated schedule link directly to their abstracts; plenary entries link to their speaker details. Those links are generated automatically from the visible speaker name and title.

The light/dark preference persists site-wide. It is stored in the browser when available and is also carried through internal navigation, so it works when previewing the static files locally.

## Publishing and safeguards

The generated files are deliberately separate from source. Never edit `dist/` directly: it is replaced at every build.

The included GitHub Actions workflow checks that the site builds and that every local page, stylesheet, image, and other referenced file exists. Configure your hosting provider to deploy `dist/` only after that check passes. Keep the finished year's `dist/` as its own archived site; start the next committee from this template's source.
