# alife-edu.github.io
A website for hosting content and events related to Artificial Life Education at https://alife-edu.github.io/.


# To Make Updates
We use a combination of custom HTML and Jekyll to make adding typical things easier while having the website as a whole more flexible than a basic Jekyll page.

## Resources
To add to the [resources](https://alife-edu.github.io/resources.html) page, add a file to the `_resources` folder and see the `README.md` therein for details.

## Events
To add an event (talk, meetup, workshop), add a `.md` file to the `_events` folder and see the `README.md` therein for details. It automatically gets its own page and shows up in the upcoming events schedule on the homepage, then moves to "Previous Events" once its date has passed.

If a workshop needs a detailed session-by-session schedule, also create a folder in the `_schedules` directory and follow the directions in the `README.md` therein.

# Other folders
Here is an overview of the purpose of the other folders:
* `_includes`: HTML for various units like nav bar, resource cards, etc
* `_layouts`: HTML for full page layouts
* `_assets`: Miscellaneous pictures etc
* `_css`: The cascading style sheets that govern the style of the website
* `_presentations`: PDFs of slides linked from schedules, etc
