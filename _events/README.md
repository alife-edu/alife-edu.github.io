# Adding an event

Every event on the site — its row in the home page's "Upcoming Events" schedule, its card under "Previous Events", its nav link, and (usually) its own page — comes from one `.md` file in this folder.

## Adding a new event

1. Copy `interdisciplinary-2026.md` as a starting point and rename it, e.g. `my-talk-2027.md`.
2. Fill in the fields between the `---` lines (see the table below). The most important one is `date`.
3. Below the closing `---`, write the full event description in Markdown — abstract, speaker bio, agenda, whatever you like.
4. Save it. That's it.

The file becomes its own page at `my-talk-2027.html` (named after the file), and the home page schedule links to it. You do **not** need to edit `index.html`, the nav, or make an `.html` file.

## Upcoming vs. previous is automatic

Events are sorted by `date`. Once an event's `end_date` (or `date`, for a one-day event) is in the past, the site automatically:
- Moves it from the "Upcoming Events" schedule to the "Previous Events" cards on the home page.
- Moves its nav link from the "Upcoming Events" dropdown into the "Event Archive" dropdown.
- Adds a "this event has concluded" banner (with its `concluded_message`) to the top of the event's page.

**Note:** GitHub Pages only rebuilds the site when something is pushed, so an event moves to "Previous" on the first push after it ends. To archive one early, add `archived: true`.

## Fields

| Field | Required? | Notes |
|---|---|---|
| `date` | yes | Start date, as `YYYY-MM-DD` (no quotes), e.g. `2027-03-14`. Used for sorting, the date shown on the schedule, and deciding when it's over. |
| `end_date` | no | Last day, for multi-day events, e.g. `2027-03-16`. |
| `date_tbd` | no | `true` if only the month is known — the schedule shows the month with "TBD" instead of a day. |
| `nav_label` | yes | Short name shown in the nav dropdowns (under its date in "Upcoming Events"), e.g. `"TAL Workshop 2026"`. Also used as the title if `card_title` isn't set. |
| `card_title` | no | Full event title, used on the schedule, card, and event page. Falls back to `nav_label`. |
| `group_label` | yes | Short header shown in the "Event Archive" dropdown once it's over, e.g. `"Monthly Meetup"`. |
| `eyebrow` | yes | Small label above the title, e.g. `"Virtual · Oct 2026"`. |
| `dates` | yes | Human-readable date/time line, e.g. `"October 29th, 2026 9AM EDT on Zoom"`. |
| `description` | yes | A short (2–3 sentence) blurb for the schedule row and card. Put the long version in the body below the `---`. |
| `link_text` | yes | Call-to-action text on the schedule row/card, e.g. `"Talk details"`. |
| `links` | no | Buttons at the top of the event page — a list of `{text, url}`, e.g. a Zoom link or registration form. |
| `concluded_message` | no | Shown in the "this event has concluded" banner once it's over. |
| `event_url` | no | Only if the event's page lives somewhere else — a hand-built `.html` page (like `tal-alife-2026.html`) or an external site. The schedule, card, and nav then link there instead. **No leading slash.** (Called `event_url`, not `url`, because Jekyll reserves `url`.) |
| `children` | no | Only for events with several sub-pages (like AEDU's West/East schedule archives). A list of `{label, url}` shown under the event in the nav. |
| `archived` | no | `true` forces an event into "Previous Events" before its date passes. |

## Example

```yaml
---
nav_label: "Swarm Robotics Talk"
card_title: "Teaching Swarm Robotics on a Budget"
group_label: "Monthly Meetup"
date: 2026-11-19
eyebrow: "Virtual · Nov 2026"
dates: "November 19th, 2026 · 10AM EST on Zoom"
description: "A short blurb that shows on the home page schedule."
link_text: "Talk details"
links:
  - text: "Join on Zoom ↗"
    url: "https://zoom.us/j/123456789"
concluded_message: "Thanks to everyone who came!"
---

The full abstract goes here, in normal **Markdown**.

## About the speaker

...
```

Heads-up: since each event becomes `<filename>.html` at the top level of the site, don't give an event file the same name as an existing top-level page (e.g. `resources.md`).
