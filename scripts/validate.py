#!/usr/bin/env python3
"""Validate migrated publication paths, media, private-data exclusions, and feeds."""
from html.parser import HTMLParser
import hashlib
import json
from pathlib import Path
import re
import sys
from urllib.parse import unquote, urlparse
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parent.parent


class Document(HTMLParser):
    def __init__(self, article=False):
        super().__init__()
        self.article = article
        self.depth = 0
        self.skip = 0
        self.parts = []
        self.links = []
        self.images = []

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag in ('style', 'script'):
            self.skip += 1
        if self.article and tag == 'div':
            if self.depth:
                self.depth += 1
            elif 'e-content' in a.get('class', '').split():
                self.depth = 1
        for field in ('src', 'href'):
            if a.get(field):
                self.links.append(a[field])
        if tag == 'img' and a.get('src'):
            self.images.append(a['src'])

    def handle_endtag(self, tag):
        if tag in ('style', 'script'):
            self.skip -= 1
        if self.article and tag == 'div' and self.depth:
            self.depth -= 1

    def handle_data(self, data):
        if not self.skip and (not self.article or self.depth):
            self.parts.append(data)

    def digest(self):
        return hashlib.sha256(re.sub(r'\s+', '', ''.join(self.parts)).encode()).hexdigest()


def main():
    site = ROOT / '_site'
    manifest = json.loads((ROOT / 'migration-manifest.json').read_text())
    errors = []
    for record in manifest['items']:
        target = site / record['permalink'].lstrip('/') / 'index.html'
        if not target.is_file():
            errors.append('Missing original URL: ' + record['permalink'])
    checked = 0
    all_images = set()
    for file in site.rglob('*.html'):
        if file.parent.name == 'feed':
            continue
        doc = Document()
        doc.feed(file.read_text())
        checked += 1
        all_images.update(doc.images)
        for link in doc.links:
            u = urlparse(link)
            if u.scheme or u.netloc or not u.path.startswith('/blog/'):
                continue
            path = unquote(u.path[len('/blog/'):])
            target = site / path
            if not target.is_file() and not (target / 'index.html').is_file():
                errors.append(f'{file.relative_to(site)} -> {u.path}')
    for src in all_images:
        if not src.startswith('/blog/'):
            errors.append('Image still relies on an external host: ' + src)
    for name in ('feed.xml', 'feed/index.html', 'sitemap.xml'):
        ET.parse(site / name)
    for record in json.loads((ROOT / 'media-manifest.json').read_text()):
        target = site / record['path']
        if not target.is_file() or hashlib.sha256(target.read_bytes()).hexdigest() != record['sha256']:
            errors.append('Media missing or altered: ' + record['path'])
    forbidden = ['wordpress.xml', 'README.md', 'scripts', 'Gemfile', '.git', '_drafts',
                 'migration-manifest.json', 'media-manifest.json']
    for name in forbidden:
        if (site / name).exists():
            errors.append('Private or development file included: ' + name)
    # Optional import-time comparison against the private local public-API snapshot.
    comparisons = 0
    if len(sys.argv) == 2:
        public = {}
        for file in Path(sys.argv[1]).glob('posts-*.json'):
            public.update({p['id']: p for p in json.loads(file.read_text())})
        for record in manifest['items']:
            if record['type'] != 'post':
                continue
            original = Document()
            original.feed(public[record['id']]['content']['rendered'])
            generated = Document(article=True)
            generated.feed((site / record['permalink'].strip('/') / 'index.html').read_text())
            if original.digest() != generated.digest():
                errors.append('Post text changed: ' + record['permalink'])
            comparisons += 1
    report = {'original_posts': manifest['published_posts'], 'original_pages': manifest['published_pages'],
              'html_pages_checked': checked, 'unique_displayed_images': len(all_images),
              'original_text_comparisons': comparisons, 'errors': sorted(set(errors))}
    (ROOT / 'validation.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))
    return 1 if errors else 0


if __name__ == '__main__':
    raise SystemExit(main())
