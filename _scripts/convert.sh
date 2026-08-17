#!/bin/bash
#
# Convert Jupyter notebook files (in _jupyter folder) to markdown files (in _drafts folder).
#
# Arguments:
# $1 filename (excluding extension)
# Install:
# brew install gnu-sed
# Example:
# _scripts/convert.sh segregation

# Use the project venv from `uv sync`.
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
JUPYTER="$ROOT/.venv/bin/jupyter"
if [[ ! -x "$JUPYTER" ]]; then
  echo "Missing $JUPYTER — run: uv sync" >&2
  exit 1
fi

# Set Jupyter data path for templates (needed on some Homebrew installations)
export JUPYTER_PATH=/opt/homebrew/share/jupyter

# Generate a filename with today's date.
filename=$(date +%Y-%m-%d)-$1

# Jupyter will put all the assets associated with the notebook in a folder with this naming convention.
foldername=$filename"_files"

# Do the conversion.
"$JUPYTER" nbconvert ./_jupyter/$1.ipynb --to markdown --output-dir=./_posts --output=$filename --template=./_scripts/jekyll.tpl

# Move the images.
echo "Moving images..."
mv ./_posts/$foldername ./assets/img/

# Remove the now empty folder.
# rmdir ./_posts/$foldername

# Gets the title of the post
echo "What's the title of this post going to be?"
read ttl
gsed -ie "4 i title: \"$ttl\"" ./_posts/$filename.md
gsed -ie "5 i date: $(date +%Y-%m-%d)" ./_posts/$filename.md

echo "added title $ttl in line 4"
rm ./_posts/$filename.mde

echo "folder name $foldername"

# Go through the markdown file and rewrite image paths.
# echo "Rewriting image paths..."

# gsed -i.tmp -e "/assets/img/$foldername/" ./_posts/$filename.md
# 2018-02-08-segregation_files/2018-02-08-segregation_7_0.png
# gsed -i.tmp -e "s/_post/$foldername/\/assets/img/$foldername/" ./_posts/$filename.md
# gsed  -i.tmp 's|$foldername|new_path|g' ./_posts/$filename.md
# gsed -i 's|2023-07-31-statistical-power_files/|assets/img/2023-07-31-statistical-power_files/|' your_markdown_file.md
gsed -i.tmp -e 's/'"$foldername"'/'"\/assets\/img\/$foldername"'/g' ./_posts/$filename.md

# Remove backup file created by sed command.
rm ./_posts/$filename.md.tmp
rm -r ./_posts/$foldername

# nbconvert pads every output block, so cells that both print and return a value
# end up separated by several blank lines. Collapse runs of blank lines and drop
# trailing whitespace.
"$ROOT/.venv/bin/python" - "./_posts/$filename.md" <<'PY'
import re
import sys
from pathlib import Path

path = Path(sys.argv[1])
text = path.read_text()
text = "\n".join(line.rstrip() for line in text.splitlines())
text = re.sub(r"\n{3,}", "\n\n", text)
text = re.sub(r"\A(---\n.*?\n---\n)\n?", r"\1\n", text, flags=re.DOTALL)
path.write_text(text.rstrip() + "\n")
PY
# Check if the conversion has left a blank line at the top of the file.
# firstline=$(head -n 1 ./_posts/$filename.md)
# if [ "$firstline" = "" ]; then
#   # If it has, get rid of it.
#   tail -n +2 "./_posts/$filename.md" > "./_posts/$filename.tmp" && mv "./_posts/$filename.tmp" "./_posts/$filename.md"
# fi

echo "Done converting."
