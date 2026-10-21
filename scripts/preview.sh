#!/usr/bin/env bash
# Publish a branch at https://alife-edu.github.io/preview/ so it can be
# reviewed before merging. See "Previewing a redesign" in README.md.
#
#   scripts/preview.sh <branch>   build <branch> into preview/
#   scripts/preview.sh --clear    put the "no preview" placeholder back
#
# Run it on main, then commit preview/ and push.
set -euo pipefail

BUNDLE=${BUNDLE:-bundle}
root=$(git rev-parse --show-toplevel)
cd "$root"

if [ "$(git branch --show-current)" != main ]; then
  echo "Run this on main; GitHub Pages publishes preview/ from main." >&2
  exit 1
fi
arg=${1:?usage: scripts/preview.sh <branch> | --clear}

if [ "$arg" = --clear ]; then
  rm -rf preview
  mkdir preview
  cat > preview/index.html <<'EOF'
<!doctype html>
<html lang="en">
<head>
  <meta name="robots" content="noindex, nofollow">
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>No preview right now · ALife-Edu</title>
  <link rel="stylesheet" href="../css/base.css">
</head>
<body style="padding: 4rem 1.5rem; max-width: 36rem; margin: 0 auto;">
  <h1 style="font-family: var(--font-display); margin-bottom: 1rem;">No preview right now</h1>
  <p>This address shows proposed redesigns of the ALife-Edu site while they're being reviewed. Nothing is under review at the moment.</p>
  <p style="margin-top: 1rem;"><a href="../index.html">Go to the ALife-Edu site</a></p>
</body>
</html>
EOF
  echo "preview/ reset to the placeholder. Commit it and push."
  exit 0
fi

git rev-parse --verify --quiet "$arg^{commit}" >/dev/null || { echo "No branch or commit named $arg" >&2; exit 1; }

tmp=$(mktemp -d)
trap 'git worktree remove --force "$tmp/src" >/dev/null 2>&1 || true; rm -rf "$tmp"' EXIT
git worktree add --quiet --detach "$tmp/src" "$arg"
"$BUNDLE" exec jekyll build --quiet -s "$tmp/src" -d "$tmp/site"

# Slides and images are large and the same on every branch, so the preview
# links to the live site's copies instead of carrying its own.
rm -rf "$tmp/site/assets" "$tmp/site/presentations" "$tmp/site/preview"
find "$tmp/site" -name '*.html' -exec perl -pi -e '
  s#((?:href|src)="|src: \x27)(assets|presentations)/#$1../$2/#g;
  s#<head>#<head>\n  <meta name="robots" content="noindex, nofollow">#;
' {} +

rm -rf preview
cp -R "$tmp/site" preview
echo "Built $arg ($(git rev-parse --short "$arg")) into preview/. Commit it and push."
