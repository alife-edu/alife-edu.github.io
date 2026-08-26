# Adding or archiving an event

Every event card on the home page — and its nav entry — comes from one file in this folder.

## Archiving an event (the common case)

Find the event's file (e.g. `tal-2026.md`) and change one line:

```yaml
archived: false
```
to
```yaml
archived: true
```

That single flip:
- Moves its card from "Upcoming Events" to "Previous Events" on the home page (and changes its card color to match).
- Moves its nav link out of the top nav bar and into the "Event Archive" dropdown.
- Adds a "this event has concluded" banner to the top of the event's own page (using its `concluded_message`).

Nothing else needs to change.

## Adding a new event

1. Copy `tal-2026.md` (simple, no sub-links) or `aedu-2026.md` (has sub-links, e.g. multiple schedule archive pages) as a starting point.
2. Rename it, e.g. `my-event-2027.md`.
3. Fill in the fields below.

| Field | Required? | Notes |
|---|---|---|
| `nav_label` | yes | Top-level nav link text, e.g. `"TAL Workshop 2026"`. Also used as the card title if `card_title` isn't set. |
| `card_title` | no | Card title on the home page, if it should read differently than `nav_label` (e.g. `"TAL — Teaching Artificial Life"` vs. the shorter nav text). Falls back to `nav_label` if omitted. |
| `group_label` | yes | Short label shown as a header in the "Event Archive" dropdown once archived, e.g. `"TAL"`. |
| `event_url` | yes | The event's own page, e.g. `"tal-alife-2026.html"`. **No leading slash** — this is a plain filename like everywhere else on this site. (Note: the field is called `event_url`, not `url` — `url` is a reserved word Jekyll uses internally and won't work here.) |
| `archived` | yes | `false` = upcoming, `true` = archived. See above. |
| `order` | no | Sort key (lower = earlier). Leave gaps of 10. |
| `eyebrow` | yes | Small label on the card, e.g. `"In-Person · August 2026"`. |
| `dates` | yes | Date line on the card. |
| `description` | yes | Card body text. |
| `link_text` | yes | Card call-to-action text, e.g. `"View TAL workshop →"`. |
| `children` | no | Only needed if the event has its own sub-pages (like AEDU's West/East schedule archives). A list of `{label, url}` — shown under the event's `group_label` in the Event Archive dropdown once archived. |
| `concluded_message` | no | Shown in the banner on the event's own page once archived. |

You do **not** need to edit `index.html` or the nav — both are generated from these files automatically.
