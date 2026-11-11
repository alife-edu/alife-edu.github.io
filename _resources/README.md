# Adding a resource

Every entry on the [Resources page](../resources.html) is one file in this folder. To add a new resource:

1. Copy an existing file in this folder that's closest to what you're adding (e.g. `alife-wiki.md` for an organization/reference card, `cs361-carleton.md` for a course link).
2. Rename it to something short describing your resource, e.g. `my-new-course.md`.
3. Edit the fields at the top (between the `---` lines) — don't touch anything else.
4. Save it. That's it — no other file needs to change.

## Fields

| Field | Required? | Notes |
|---|---|---|
| `title` | yes | The resource's name. |
| `link` | no | Link to the resource. Omit it entirely for a "coming soon" style card with no link. (Note: the field is called `link`, not `url` — `url` is a reserved word Jekyll uses internally and won't work here.) |
| `category` | yes | Which section of the Resources page it appears in: `orgs-and-refs`, `topics`, `courses`, `explorables`, `labs`, `overview`, or `pedagogy`. The sections themselves (their titles, order and intros) are listed in `_data/resource_sections.yml`; add a section there to create a new category. |
| `style` | yes | `card` (a boxed card with an eyebrow/title/body) or `link-item` (a simple one-line list entry). Must match whatever the other entries in that category use. |
| `color` | only for `style: card` | One of the site's four meaning colours: `resources` (the default), `community`, `upcoming` or `archive`. The colours themselves are set in `css/base.css`. (Older files may say `teal`, `indigo` or `gold`; those still work and mean resources, community and upcoming.) |
| `eyebrow` | only for `style: card` | Short label above the title, e.g. "Wiki" or "Conference". |
| `description` | yes | One or two sentences describing the resource. |
| `link_text` | only for `style: card` with a `link` | The call-to-action text, e.g. `"Visit wiki ↗"`. |
| `order` | no | A number controlling sort order within the category (lower = earlier). Leave a gap of 10 between entries so you can insert one later without renumbering everything. |

## Example

```yaml
---
title: "ALife Wiki"
link: "https://alife.org/encyclopedia/"
category: "orgs-and-refs"
style: "card"
color: "resources"
eyebrow: "Wiki"
description: "The community-maintained wiki for Artificial Life — key concepts, history, research areas, and links to seminal papers."
link_text: "Visit wiki ↗"
order: 10
---
```

You can add a resource entirely from GitHub's web interface — go to this folder, click **Add file → Create new file**, and paste in a filled-out copy of the example above.
