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

### Setup

```bash
bundle install
bundle exec jekyll serve --livereload
```

The site will be available at `http://localhost:4000`.

### Docker

```bash
docker-compose up
```

This starts the site at `http://localhost:8080`.

## Deployment

Pushing to `main` triggers the GitHub Actions workflow (`.github/workflows/deploy.yml`), which builds the site and deploys it to the `gh-pages` branch.

## License

The content of this site is © Sebastian Daza. The underlying theme is based on [al-folio](https://github.com/alshedivat/al-folio), available under the [MIT License](https://opensource.org/licenses/MIT).
