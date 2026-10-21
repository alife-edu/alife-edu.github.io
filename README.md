# alife-edu.github.io
A website for hosting content and events related to Artificial Life Education at https://alife-edu.github.io/.


# To Make Updates
We use a combination of custom HTML and Jekyll to make adding typical things easier while having the website as a whole more flexible than a basic Jekyll page.

## Resources
To add to the [resources](https://alife-edu.github.io/resources.html) page, add a file to the `_resources` folder and see the `README.md` therein for details.

## Events
To add an event (talk, meetup, workshop), add a `.md` file to the `_events` folder and see the `README.md` therein for details. It automatically gets its own page and shows up in the upcoming events schedule on the homepage, then moves to "Previous Events" once its date has passed.

If a workshop needs a detailed session-by-session schedule, also create a folder in the `_schedules` directory and follow the directions in the `README.md` therein.

# Previewing a redesign
For changes big enough that co-organizers should see them before they go live, work on a branch and publish it at https://alife-edu.github.io/preview/. GitHub Pages only serves one branch, so the preview is a built copy of your branch committed to `main` under `preview/`.

1. Make your changes on a branch, e.g. `git checkout -b my-redesign`, and commit them.
2. Switch to `main` and build the branch into `preview/`:
   ```
   git checkout main
   scripts/preview.sh my-redesign
   git add preview && git commit -m "Preview my-redesign" && git push
   ```
   After a minute or two it's live at `/preview/`. Preview pages are marked `noindex` so search engines skip them, but anyone with the link can see them. They use the live site's `assets/` and `presentations/` files, so new PDFs or images on the branch won't show up until they're on `main`.
3. To update the preview after more changes on the branch, repeat step 2.
4. When everyone's happy, merge the branch and put the placeholder back:
   ```
   git merge my-redesign
   scripts/preview.sh --clear
   git add -A preview && git commit -m "Clear the preview" && git push
   ```

The script needs the same Ruby setup as a local build (`bundle exec jekyll serve`). If `bundle` isn't on your PATH, run it as `BUNDLE=/path/to/bundle scripts/preview.sh my-redesign`.

# Other folders
Here is an overview of the purpose of the other folders:
* `_includes`: HTML for various units like nav bar, resource cards, etc
* `_layouts`: HTML for full page layouts
* `_assets`: Miscellaneous pictures etc
* `_css`: The cascading style sheets that govern the style of the website
* `_presentations`: PDFs of slides linked from schedules, etc
