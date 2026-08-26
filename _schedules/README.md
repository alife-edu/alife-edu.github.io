# Adding or editing a schedule session

Every session on the schedule pages ([AEDU-East](../schedule-east.html), [AEDU-West](../schedule-west.html), [TAL](../tal-alife-2026.html)) is one file in this folder, organized into subfolders so it doesn't turn into one giant pile:

```
_schedules/
  tal-2026/         one file per TAL session
  aedu-east/        one file per AEDU-East session
  aedu-west/
    day1/           one file per AEDU-West Day 1 session
    day2/           one file per AEDU-West Day 2 session
```

The subfolders are purely for tidiness — Jekyll reads every file in this collection no matter how deeply it's nested, and it's the `event` (and `day`) field *inside* each file, not its folder, that actually determines which page and section it shows up on. So the folder a file lives in should always match its `event`/`day` fields, but moving a file to the "wrong" folder by itself wouldn't change where it renders — keep them in sync by hand.

To add a session:

1. Go to the subfolder for the right event (and day, for AEDU-West), and copy an existing file there that's closest to what you're adding.
2. Rename it to something short, e.g. `07-my-talk.md`. A leading number is a handy way to keep files sorted in the same order they'll appear on the page, but the actual ordering on the site comes from the `order` field below, not the filename.
3. Edit the fields between the `---` lines.
4. Save it. That's it — no other file needs to change.

## Fields (used by every event: `aedu-east`, `aedu-west`, and `tal-2026`)

| Field | Required? | Notes |
|---|---|---|
| `event` | yes | `aedu-east`, `aedu-west`, or `tal-2026`. |
| `day` | AEDU-West only | `day1` or `day2`. |
| `order` | yes | Sort key within the event/day (lower = earlier). Leave gaps of 10. |
| `time` | yes | e.g. `"10:25 AM"`. |
| `row_style` | no | Leave blank for a plain row, or `talk`, `panel`, `break`. |
| `type` | no | Small eyebrow label, e.g. `"Presentation"`, `"Talk"`, `"Activity"`. |
| `title` | yes unless `row_style: break` | Session title. |
| `speakers` | no | A list of speaker lines, e.g. `["Jean Alfonso-Decena"]`. Use two entries for a moderator + panelists row, or one entry with multiple names comma-separated for a group. |
| `notes` | no | A list of `{text, highlight}` — extra note paragraphs (e.g. instructions). `highlight: true` makes it stand out visually. |
| `break_label` | only for `row_style: break` | e.g. `"Break · 10 min"`. |
| `actions` | no | A list of link buttons, e.g. Slides/Video/Demo — `{text, url}` each. If a recording or slide deck isn't up yet, just leave `url` blank (`url: ""`, or omit it) — it automatically shows as a greyed-out, non-clickable placeholder button until you paste in the real link. |
| `talks` | rare | Only for a "lightning talks" row with sub-entries — a list of `{speaker, title, links: [{text, url}]}`. Same rule: an empty `url` in a `links` entry shows as a placeholder. |

## Examples

```yaml
---
event: "aedu-east"
order: 40
time: "10:30 AM"
row_style: "talk"
type: "Talk"
title: "Teaching Cellular Automata"
speakers:
  - "Bert Chan"
actions:
  - text: "Slides ↗"
    url: "presentations/Teaching CA.pdf"
  - text: "Video ↗"
    url: "https://www.youtube.com/watch?v=pJ3Xb_oBrGk&t=1033s"
---
```

```yaml
---
event: "tal-2026"
order: 10
time: "10:00 AM"
title: "Opening"
speakers:
  - "Jason Yoder"
actions:
  - text: "Video ↗"
    url: ""
---
```

Note: the link field inside `actions` and `links` is called `url` — that's fine there (only a *top-level* front-matter field named `url` would break, because Jekyll reserves that one for the page's own address).
