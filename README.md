# sdaza.github.io

Personal website of Sebastian Daza — [sdaza.com](https://sdaza.com)

Built with [Jekyll](https://jekyllrb.com/) and hosted on [GitHub Pages](https://pages.github.com/).

## Sections

- **About** — Bio and contact info
- **Blog** — Posts on data science, demography, and statistics
- **Publications** — Academic publications (managed via Jekyll-Scholar)
- **Projects** — Selected project portfolio
- **Repositories** — GitHub repos with live star counts
- **CV** — Web-based resume with PDF downloads

## Local Development

### Prerequisites

- Ruby 3.2+
- Bundler (`gem install bundler`)
- [uv](https://docs.astral.sh/uv/) (for Jupyter notebooks under `_jupyter/`)

### Setup

```bash
bundle install
bundle exec jekyll serve --livereload
```

The site will be available at `http://localhost:4000`.

### Notebooks

Python deps for `_jupyter/` notebooks are defined in `pyproject.toml`. Create the
venv and install packages with:

```bash
uv sync
```

That creates `.venv/` (Python from `.python-version`). Activate or call tools
directly:

```bash
source .venv/bin/activate
# or
.venv/bin/jupyter lab
.venv/bin/python -m jupyter nbconvert ...
```

Convert a notebook to a Jekyll post (requires `.venv` from `uv sync`):

```bash
_scripts/convert.sh raking-weightpipe
```

### Docker

```bash
docker-compose up
```

This starts the site at `http://localhost:8080`.

## Deployment

Pushing to `main` triggers the GitHub Actions workflow (`.github/workflows/deploy.yml`), which builds the site and deploys it to the `gh-pages` branch.

## License

The content of this site is © Sebastian Daza. The underlying theme is based on [al-folio](https://github.com/alshedivat/al-folio), available under the [MIT License](https://opensource.org/licenses/MIT).
