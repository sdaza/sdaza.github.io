{% extends 'markdown/index.md.j2' %}

{%- block header -%}
---
layout: post
author: Sebastian Daza
giscus_comments: true
---
{%- endblock header -%}

{% block input %}
{% if 'hide-input' not in cell.metadata.get('tags', []) %}
{{ '{% highlight python %}' }}
{{ cell.source }}
{{ '{% endhighlight %}' }}
{% endif %}
{% endblock input %}

{% block markdowncell scoped %}
{{ cell.source }}
{% endblock markdowncell %}

{% block headingcell scoped %}
{{ '#' * cell.level }} {{ cell.source | replace('\n', ' ') }}
{% endblock headingcell %}
