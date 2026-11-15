# Keep WordPress pagination paths working, including when new posts are added.
module PersonalBlog
  class Pagination < Jekyll::Generator
    safe true
    priority :low
    def generate(site)
      total = [(site.posts.docs.length / 10.0).ceil, 1].max
      site.pages.reject! { |page| page.data['layout'] == 'home' }
      (1..total).each do |number|
        directory = number == 1 ? '' : "page/#{number}"
        page = Jekyll::PageWithoutAFile.new(site, site.source, directory, 'index.html')
        page.content = ''
        page.data.merge!('layout' => 'home', 'page_number' => number, 'total_pages' => total)
        site.pages << page
      end
    end
  end
end
