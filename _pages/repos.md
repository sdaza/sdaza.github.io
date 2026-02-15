---
layout: page
permalink: /repos/
title: repos
description:
nav: true
nav_order: 7
---

{% if site.data.repositories.github_repos %}
<div class="repo-grid">
  {% for repo in site.data.repositories.github_repos %}
    {% include repository/repo.liquid repo=repo %}
  {% endfor %}
</div>
{% endif %}

<script>
document.addEventListener("DOMContentLoaded", function () {
  document.querySelectorAll(".repo-card[data-repo]").forEach(function (card) {
    var repo = card.getAttribute("data-repo");
    fetch("https://api.github.com/repos/" + repo)
      .then(function (res) { return res.json(); })
      .then(function (data) {
        if (data.message) return; // API error
        var lang = card.querySelector(".repo-card-lang-name");
        var stars = card.querySelector(".repo-card-stars-count");
        var desc = card.querySelector(".repo-card-desc");
        if (lang && data.language) lang.textContent = data.language;
        if (stars) stars.textContent = data.stargazers_count;
        if (desc && data.description) desc.textContent = data.description;
      })
      .catch(function () {}); // fail silently, keep static fallback
  });
});
</script>
