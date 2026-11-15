module PersonalBlog
  class LegacyRoutes < Jekyll::Generator
    safe true
    def generate(site)
      site.data.fetch('redirects', {}).each do |old_path, target|
        page = Jekyll::PageWithoutAFile.new(site, site.source, old_path.sub(%r{^/}, ''), 'index.html')
        page.content = ''
        page.data.merge!('layout' => 'redirect', 'target' => target)
        site.pages << page
      end
    end
  end
end
