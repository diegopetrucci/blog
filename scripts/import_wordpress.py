#!/usr/bin/env python3
"""Import only published content; keep the WXR and drafts outside this checkout.

Uses WordPress's public rendered HTML to expand galleries before Pandoc converts
it to editable Markdown. The WXR supplies publication status and metadata.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
from html import unescape
from html.parser import HTMLParser
import json
import math
from pathlib import Path
import re
import subprocess
from urllib.parse import unquote, urlparse
import xml.etree.ElementTree as ET

NS = {'wp': 'http://wordpress.org/export/1.2/',
      'content': 'http://purl.org/rss/1.0/modules/content/'}
SITE_HOSTS = {'www.diegopetrucci.it', 'diegopetrucci.it', 'blog.diegopetrucci.it'}


class Assets(HTMLParser):
    def __init__(self):
        super().__init__()
        self.urls = set()

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag in ('img', 'source', 'video', 'audio') and a.get('src'):
            self.urls.add(a['src'])
        if a.get('poster'):
            self.urls.add(a['poster'])
        for part in a.get('srcset', '').split(','):
            if part.strip():
                self.urls.add(part.strip().split()[0])
        if tag == 'a' and '/wp-content/uploads/' in a.get('href', ''):
            self.urls.add(a['href'])


def path_for(url):
    parsed = urlparse(unescape(url))
    if parsed.scheme not in ('http', 'https') or parsed.username or parsed.password:
        raise ValueError('Unsupported asset URL')
    if parsed.hostname in SITE_HOSTS and '/wp-content/uploads/' in parsed.path:
        result = 'wp-content/uploads/' + parsed.path.split('/wp-content/uploads/', 1)[1]
    elif parsed.hostname == '64.media.tumblr.com':
        result = 'assets/imported/' + hashlib.sha256(url.encode()).hexdigest()[:12] + '-' + parsed.path.rsplit('/', 1)[-1]
    else:
        raise ValueError('Unexpected asset host: ' + str(parsed.hostname))
    if '..' in Path(unquote(result)).parts:
        raise ValueError('Unsafe asset path')
    return unquote(result)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--export', required=True, type=Path)
    ap.add_argument('--rendered', required=True, type=Path)
    ap.add_argument('--site', required=True, type=Path)
    args = ap.parse_args()
    site = args.site.resolve()
    tree = ET.parse(args.export)
    items = tree.findall('./channel/item')
    def value(item, field):
        return item.findtext('wp:' + field, default='', namespaces=NS)
    published = [i for i in items if value(i, 'status') == 'publish' and value(i, 'post_type') in ('post', 'page')]
    rendered = {}
    for file in sorted(args.rendered.glob('*.json')):
        data = json.loads(file.read_text())
        if isinstance(data, list):
            rendered.update({str(p['id']): p for p in data if 'content' in p})
    missing = [value(i, 'post_id') for i in published if value(i, 'post_id') not in rendered]
    if missing:
        raise ValueError('Missing public rendering for IDs: ' + ','.join(missing))
    # Refuse to substitute rendering from a different revision.
    for item in published:
        public = rendered[value(item, 'post_id')]
        if value(item, 'post_modified').replace(' ', 'T') != public['modified']:
            raise ValueError('Export/rendered revision mismatch for ' + value(item, 'post_id'))
    assets = Assets()
    for item in published:
        assets.feed(rendered[value(item, 'post_id')]['content']['rendered'])
    # Keep attachments belonging only to drafts out of a public repository.
    public_ids = {value(i, 'post_id') for i in published}
    attachments = [i for i in items if value(i, 'post_type') == 'attachment'
                   and (value(i, 'post_parent') in public_ids or value(i, 'attachment_url') in assets.urls)]
    for item in attachments:
        url = value(item, 'attachment_url')
        if url:
            assets.urls.add(url)
    mappings = {url: path_for(url) for url in sorted(assets.urls)}
    redirects = {}
    tumblr_ids = {}
    for item in published:
        destination = urlparse(item.findtext('link')).path
        for meta in item.findall('wp:postmeta', NS):
            key = meta.findtext('wp:meta_key', default='', namespaces=NS)
            val = meta.findtext('wp:meta_value', default='', namespaces=NS)
            if key == 'tumblr_diegopetrucci_id':
                tumblr_ids[val] = destination
                redirects['/post/' + val + '/'] = destination
            elif key == 'tumblr_diegopetrucci_permalink':
                old_path = urlparse(val).path
                if old_path.startswith('/post/'):
                    redirects[old_path.rstrip('/') + '/'] = destination
            elif key == '_wp_old_slug' and val:
                redirects['/' + val + '/'] = destination
    for item in attachments:
        url = value(item, 'attachment_url')
        link = item.findtext('link') or ''
        if url in mappings and urlparse(link).path.startswith('/blog/') and urlparse(link).path != '/blog/':
            redirects[urlparse(link).path[len('/blog'):].rstrip('/') + '/'] = '/blog/' + mappings[url]
    by_path = {}
    for url, dest in mappings.items():
        by_path.setdefault(dest, url)

    def fetch(pair):
        dest, url = pair
        target = site / dest
        target.parent.mkdir(parents=True, exist_ok=True)
        if not target.exists():
            # Public downloads only. No browser cookies or authentication.
            result = subprocess.run(['curl', '--fail', '--silent', '--show-error', '--location',
                                     '--proto', '=https,http', '--proto-redir', '=https,http',
                                     '--connect-timeout', '10', '--max-time', '45',
                                     '--retry', '1', '--output', str(target) + '.part', url],
                                    capture_output=True, text=True)
            if result.returncode:
                Path(str(target) + '.part').unlink(missing_ok=True)
                return {'path': dest, 'url': url, 'error': result.stderr.strip()}
            Path(str(target) + '.part').replace(target)
        raw = target.read_bytes()
        if not raw or raw.lstrip().lower().startswith((b'<!doctype html', b'<html')):
            raise ValueError('Asset was empty or HTML: ' + dest)
        return {'path': dest, 'url': url, 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}

    with ThreadPoolExecutor(max_workers=4) as pool:
        media = list(pool.map(fetch, by_path.items()))
    (site / 'media-manifest.json').write_text(json.dumps(media, indent=2) + '\n')
    failures = [m for m in media if 'error' in m]
    if failures:
        raise ValueError(f'{len(failures)} assets could not be downloaded; see media-manifest.json')
    records = []
    for item in published:
        ident = value(item, 'post_id')
        public = rendered[ident]
        content = public['content']['rendered']
        # Inline gallery CSS and WP block markers are platform details, not writing.
        content = re.sub(r'<style\b[^>]*>.*?</style>', '', content, flags=re.S | re.I)
        content = re.sub(r'<!--.*?-->', '', content, flags=re.S)
        content = re.sub(r'<h[1-6]\b[^>]*>\s*</h[1-6]>', '', content, flags=re.I)
        content = re.sub(r'\s(?:srcset|sizes|loading|decoding|fetchpriority)=["\'][^"\']*["\']', '', content)
        for url, dest in sorted(mappings.items(), key=lambda x: -len(x[0])):
            content = content.replace(url, '/blog/' + dest)
        for host in SITE_HOSTS:
            for scheme in ('http', 'https'):
                content = content.replace(scheme + '://' + host + '/blog/', '/blog/')
        # Subdomain-root links are the same blog, not the main homepage.
        content = re.sub(r'https?://blog\.diegopetrucci\.it/(?!blog/)', '/blog/', content)
        def old_post(match):
            ident = match.group(1)
            return tumblr_ids.get(ident, match.group(0))
        content = re.sub(r'/blog/post/(\d+)(?:/[^"\'<>\s]*)?', old_post, content)
        for old, target in redirects.items():
            content = content.replace('/blog' + old, target)
        converted = subprocess.run(['pandoc', '-f', 'html', '-t', 'gfm-raw_html', '--wrap=none'],
                                   input=content, capture_output=True, text=True, check=True).stdout
        # Use Markdown's two-space hard breaks rather than Pandoc's backslash form.
        converted = converted.replace('\\\n', '  \n')
        # Drop presentation-only wrappers so Markdown is parsed consistently by Jekyll.
        link = item.findtext('link')
        path = urlparse(link).path
        if not path.startswith('/blog/') or '..' in Path(path).parts:
            raise ValueError('Unexpected permalink: ' + path)
        permalink = path[len('/blog'):]
        date = value(item, 'post_date')
        date_gmt = value(item, 'post_date_gmt')
        is_post = value(item, 'post_type') == 'post'
        slug = value(item, 'post_name')
        if not re.fullmatch(r'[A-Za-z0-9_%.-]+', slug):
            raise ValueError('Unexpected slug: ' + slug)
        filename = ('_posts/' + date[:10] + '-' + slug + '.markdown') if is_post else ('pages/' + slug + '.markdown')
        front = {
            'layout': 'post' if is_post else 'page',
            'title': unescape(item.findtext('title') or ''),
            'date': date_gmt + ' +0000' if date_gmt and not date_gmt.startswith('0000') else date,
            'permalink': permalink,
            'wordpress_id': int(ident),
            'wordpress_guid': item.findtext('guid') or link,
            'render_with_liquid': False,
            'categories': [c.text for c in item.findall('category') if c.get('domain') == 'category'],
            'tags': [c.text for c in item.findall('category') if c.get('domain') == 'post_tag'],
        }
        # Tumblr photo/quote posts often had no title. Keep that choice in the
        # article, but give archive and navigation links meaningful labels.
        plain = re.sub(r'\s+', ' ', unescape(re.sub(r'<[^>]*>', ' ', content))).strip()
        front['display_title'] = front['title'] or (plain[:80].rstrip() + ('…' if len(plain) > 80 else '')) or ('Photo — ' + date[:10])
        target = site / filename
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text('---\n' + '\n'.join(k + ': ' + json.dumps(v, ensure_ascii=False) for k, v in front.items()) + '\n---\n\n' + converted)
        records.append({'id': int(ident), 'type': value(item, 'post_type'), 'original_url': link,
                        'permalink': permalink, 'file': filename,
                        'public_rendered_sha256': hashlib.sha256(public['content']['rendered'].encode()).hexdigest()})
    # Preserve old WordPress pagination paths, ten articles per page.
    count = sum(r['type'] == 'post' for r in records)
    pages = math.ceil(count / 10)
    for n in range(1, pages + 1):
        target = site / ('index.html' if n == 1 else f'page/{n}/index.html')
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(f'---\nlayout: home\npage_number: {n}\ntotal_pages: {pages}\n---\n')
    (site / 'migration-manifest.json').write_text(json.dumps({'published_posts': count, 'published_pages': len(records) - count,
        'drafts_excluded': sum(value(i, 'status') == 'draft' for i in items),
        'approved_comments': sum(c.findtext('wp:comment_approved', namespaces=NS) == '1' for i in items for c in i.findall('wp:comment', NS)),
        'items': records}, ensure_ascii=False, indent=2) + '\n')
    (site / '_data').mkdir(exist_ok=True)
    (site / '_data/redirects.json').write_text(json.dumps(redirects, indent=2) + '\n')
    print(json.dumps({'published_posts': count, 'published_pages': len(records) - count,
                      'downloaded_assets': len(media), 'bytes': sum(m['bytes'] for m in media)}))


if __name__ == '__main__':
    main()
