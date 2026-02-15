---
layout: page
title: projects
permalink: /projects/
description:
nav: false
nav_order: 2
display_categories: [current, previous]
horizontal: false
---

<div class="projects">
{%- if site.enable_project_categories and page.display_categories %}
  {%- for category in page.display_categories %}
  <h2 class="category">{{ category }}</h2>
  {%- assign categorized_projects = site.projects | where: "category", category -%}
  {%- assign sorted_projects = categorized_projects | sort: "importance" %}
  <div class="project-grid">
    {%- for project in sorted_projects -%}
      {% include projects.html %}
    {%- endfor %}
  </div>
  {% endfor %}
{%- else -%}
  {%- assign sorted_projects = site.projects | sort: "importance" -%}
  <div class="project-grid">
    {%- for project in sorted_projects -%}
      {% include projects.html %}
    {%- endfor %}
  </div>
{%- endif -%}
</div>
