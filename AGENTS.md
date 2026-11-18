# Personal blog

- Use Ruby 3.4.9, Jekyll, and Markdown, matching the `/dev` publishing workflow.
- Preserve imported wording, dates, article permalinks, and legacy redirects.
- Never commit WXR/database exports, drafts, private metadata, or pending comments.
- Run `bundle exec jekyll build` and `python3 scripts/validate.py` after changes.
- Do not re-run the import script over edited posts without reviewing the diff.
- DNS, mail migration, and registrar transfer need their own concrete review.
- Do not change the existing `/dev` checkout as part of personal-blog edits.
- The Pages workflow automatically refreshes the original subdomain's feeds after deployment and waits for that deployment to succeed. Verify the `refresh-legacy-feeds` job passes; it needs `LEGACY_FEED_REFRESH_TOKEN` (Actions read/write on `personal-blog-redirects` only). If it fails, diagnose the job and use the manual recovery commands in README.md; do not dispatch a duplicate after a successful automatic refresh.
