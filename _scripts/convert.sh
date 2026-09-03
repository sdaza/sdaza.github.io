#!/bin/bash
#
# Convert a Jupyter notebook (in _jupyter) to a Jekyll post (in _posts).
#
# Arguments:
# $1 notebook filename, excluding the extension
# $2 post date as YYYY-MM-DD, optional, defaults to today. Pass the original
#    date when re-converting an existing post so it keeps its filename and URL.
#
# Re-converting an existing post preserves its front matter, so any keys added
# by hand (tags, for instance) survive.
#
# Examples:
# _scripts/convert.sh segregation
# _scripts/convert.sh system-dynamics-marketplace 2026-08-21

set -euo pipefail

# Use the project venv from `uv sync`.
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
JUPYTER="$ROOT/.venv/bin/jupyter"
if [[ ! -x "$JUPYTER" ]]; then
  echo "Missing $JUPYTER — run: uv sync" >&2
  exit 1
fi

# Set Jupyter data path for templates (needed on some Homebrew installations)
export JUPYTER_PATH=/opt/homebrew/share/jupyter

post_date=${2:-$(date +%Y-%m-%d)}
filename=$post_date-$1
post=./_posts/$filename.md

# Jupyter will put all the assets associated with the notebook in a folder with this naming convention.
foldername=$filename"_files"

# Stash the current front matter before nbconvert overwrites the post, and ask
# for a title only when there is nothing to reuse.
previous=$(mktemp)
trap 'rm -f "$previous"' EXIT
if [[ -f $post ]]; then
  cp "$post" "$previous"
  echo "Re-converting $post, keeping its front matter."
  ttl=""
else
  echo "What's the title of this post going to be?"
  read ttl
fi

# Do the conversion.
"$JUPYTER" nbconvert ./_jupyter/$1.ipynb --to markdown --output-dir=./_posts --output=$filename --template=./_scripts/jekyll.tpl

# Move the images, replacing any previous export so re-runs stay idempotent.
echo "Moving images..."
rm -rf ./assets/img/$foldername
mv ./_posts/$foldername ./assets/img/

# The template writes a front matter block without a title or a date. Restore
# the previous one or fill in the missing keys, point the image paths at the
# assets folder, and tidy the spacing nbconvert leaves around output blocks.
"$ROOT/.venv/bin/python" - "$post" "$foldername" "$ttl" "$post_date" "$previous" <<'PY'
import re
import sys
from pathlib import Path

path, foldername, title, date, previous = (
    Path(sys.argv[1]), sys.argv[2], sys.argv[3], sys.argv[4], Path(sys.argv[5]))

FRONT_MATTER = re.compile(r"\A---\n(.*?)\n---\n", flags=re.DOTALL)


def front_matter(text):
    match = FRONT_MATTER.match(text)
    return match.group(1).rstrip("\n") if match else None


text = path.read_text()
match = FRONT_MATTER.match(text)
if not match:
    sys.exit(f"no front matter found in {path}")

# nbconvert emits exactly one front matter block. Replace it in place; writing a
# second one would leave the first to render as body text.
keys = front_matter(previous.read_text()) if previous.stat().st_size else None
if keys is None:
    keys = match.group(1).rstrip("\n")
    if "title:" not in keys:
        keys += f"\ntitle: {title}"
    if "date:" not in keys:
        keys += f"\ndate: {date}"
text = f"---\n{keys}\n---\n\n" + text[match.end():].lstrip("\n")

text = text.replace(foldername, f"/assets/img/{foldername}")
text = "\n".join(line.rstrip() for line in text.splitlines())
text = re.sub(r"\n{3,}", "\n\n", text)
path.write_text(text.rstrip() + "\n")
PY

echo "Done converting: $post"
