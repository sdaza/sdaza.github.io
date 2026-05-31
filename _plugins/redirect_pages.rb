require 'set'

module LegacyRedirects
  class RedirectPage < Jekyll::PageWithoutAFile
    def initialize(site, from_path, target_path)
      dir, name = self.class.path_parts(from_path)
      super(site, site.source, dir, name)
      self.content = ''
      self.data['layout'] = 'redirect'
      self.data['redirect_to'] = target_path
      self.data['sitemap'] = false
    end

    def self.path_parts(path)
      clean_path = path.to_s.strip.sub(%r{\A/+}, '')

      if clean_path.empty? || clean_path.end_with?('/') || File.extname(clean_path).empty?
        return [clean_path.sub(%r{/+\z}, ''), 'index.html']
      end

      dirname = File.dirname(clean_path)
      dirname = '' if dirname == '.'
      [dirname, File.basename(clean_path)]
    end
  end

  class RedirectGenerator < Jekyll::Generator
    safe true
    priority :low

    def generate(site)
      redirects = exact_redirects(site) + legacy_post_redirects(site)
      existing_urls = existing_site_urls(site)
      generated_urls = Set.new

      redirects.each do |from_path, target_path|
        next if from_path.to_s.empty? || target_path.to_s.empty?
        next if all_dot_segment?(from_path)

        url = normalize_url(from_path)
        output_key = output_path_key(from_path)
        next if existing_urls.include?(url) || generated_urls.include?(output_key)

        site.pages << RedirectPage.new(site, from_path, target_path)
        generated_urls.add(output_key)
      end
    end

    private

    def exact_redirects(site)
      Array(site.data['redirects']).map do |redirect|
        [redirect['from'], redirect['to']]
      end
    end

    def legacy_post_redirects(site)
      site.posts.docs.flat_map do |post|
        post_tags(post).map do |tag|
          legacy_section = Jekyll::Utils.slugify(tag, mode: 'default')
          next if legacy_section.empty?

          ["/#{legacy_section}/#{post.date.strftime('%Y/%m/%d')}/#{post_slug(post)}/", post.url]
        end
      end.compact
    end

    def post_tags(post)
      raw_tags = post.data['tags'] || post.data['tag'] || post.data['categories'] || post.data['category']

      Array(raw_tags).flat_map { |tag| tag.to_s.split(',') }
                     .map(&:strip)
                     .reject(&:empty?)
                     .uniq
    end

    def post_slug(post)
      post.data['slug'] || post.basename_without_ext.sub(%r{\A\d{4}-\d{2}-\d{2}-}, '')
    end

    def existing_site_urls(site)
      urls = Set.new
      site.pages.each { |page| urls.add(normalize_url(page.url)) }
      site.collections.each_value do |collection|
        collection.docs.each { |doc| urls.add(normalize_url(doc.url)) if doc.write? }
      end
      urls
    end

    def normalize_url(path)
      "/#{path.to_s.sub(%r{\A/+}, '')}"
    end

    def output_path_key(path)
      RedirectPage.path_parts(path).join('/')
    end

    def all_dot_segment?(path)
      path.to_s.split('/').any? { |segment| segment.match?(%r{\A\.+\z}) }
    end
  end
end
