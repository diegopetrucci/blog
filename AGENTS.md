# Personal blog

- Use Ruby 3.4.9, Jekyll, and Markdown, matching the `/dev` publishing workflow.
- Preserve imported wording, dates, article permalinks, and legacy redirects.
- Never commit WXR/database exports, drafts, private metadata, or pending comments.
- Run `bundle exec jekyll build` and `python3 scripts/validate.py` after changes.
- Do not re-run the import script over edited posts without reviewing the diff.
- DNS, mail migration, and registrar transfer need their own concrete review.
- Do not change the existing `/dev` checkout as part of personal-blog edits.
- After a successful production deployment, refresh the original subdomain's feeds: run `gh workflow enable pages.yml --repo diegopetrucci/personal-blog-redirects`, then `gh workflow run pages.yml --repo diegopetrucci/personal-blog-redirects`, and verify that deployment succeeds. This also handles GitHub disabling scheduled workflows during long periods without posts.
