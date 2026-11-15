# Personal blog

Jekyll source for Diego Petrucci's personal blog. The initial import contains
247 published posts and one published page from WordPress. Personal writing
remains editable Markdown; GitHub Actions builds and deploys it on every push
to `main`.

## Write a post

Add `_posts/YYYY-MM-DD-your-title.markdown` with:

```yaml
---
layout: post
title: "Your title"
date: 2026-11-15 12:00:00 +0000
permalink: /your-title/
---

Write your post here in Markdown.
```

Add images under `assets/` and link them as `/blog/assets/filename.jpg`.
Commit and push to `main` to publish. Pagination, the archive, and feeds update
automatically. Keep unpublished writing outside this public repository.

## Preview and check

Ruby 3.4.9 is used by both the local build and GitHub Actions.

```sh
source /opt/homebrew/opt/chruby/share/chruby/chruby.sh
chruby 3.4.9
bundle install
bundle exec jekyll serve --host 127.0.0.1 --port 4015
```

Open `http://127.0.0.1:4015/blog/`.

```sh
bundle exec jekyll build
python3 scripts/validate.py
```

## Migration

- Published post titles, dates, original paths, and categories/tags are retained.
- WordPress galleries were expanded from public rendered content before
  conversion to Markdown. Posts are checked against original visible text.
- All 25 media-library originals were saved locally. The public site contains
  58 files, including referenced image sizes and seven external Tumblr images,
  recorded with SHA-256. Two draft-only images remain in the private backup.
- Old Tumblr post paths and attachment-page paths are redirected using
  `_data/redirects.json`. These are HTML redirects, not HTTP 301 responses.
- `/feed/` retains an RSS representation with the original WordPress GUIDs;
  `/feed.xml` provides the standard Jekyll Atom feed. GitHub Pages serves the
  legacy `index.html` RSS file with an HTML content type; strict feed clients
  should use `/feed.xml`. An HTTP redirect for `/feed/` is preferable when a
  routing service is available at domain cutover.
- One pre-existing link points to a post currently in draft. A neutral unavailable
  page preserves that link without publishing the draft.
- Old submission and WordPress-admin URLs have explanatory landing pages.
- The WXR export, drafts, private metadata, and unapproved comments are kept
  outside this repository. They are not part of the published site.

The import script requires Pandoc, Python 3, curl, the private WXR export, and a
matching public WordPress REST API snapshot. It is a migration tool, not part of
routine publishing. Do not re-run it after editing imported posts: it overwrites
the imported files.

## Domain cutover

The initial deployment uses `https://diegopetrucci.github.io/blog/`. All original
`/blog/<slug>/` paths can be retained when `www.diegopetrucci.it` is connected to
the account's main GitHub Pages site. That requires migrating/checking the main
homepage and configuring the account site, rather than assigning the same
hostname independently to this project site. The existing `/dev` project must
also be checked when the user-site custom domain changes.

Before transferring the registrar away from Tophost, move and verify existing
email, back up the hosting/database/mail, and inventory DNS records. The blog's
WXR export is not a full hosting or mailbox backup.

## Theme attribution

`assets/less-reloaded.css` comes from the existing Less Reloaded WordPress theme
by Morteza Geransayeh, based on Less by Jared Erickson. Its GPL-3.0-or-later
notice is preserved; see `LICENSE-theme.txt`. The new layout retains the blog's
minimal design. This license notice does not relicense the blog's writing or
third-party images.
