#!/usr/bin/env bash
set -euo pipefail

# Fine-grained token: only personal-blog-redirects, Actions read/write.
# The normal GITHUB_TOKEN is restricted to the calling repository.
if [[ -z "${GH_TOKEN:-}" ]]; then
  echo '::error::Set LEGACY_FEED_REFRESH_TOKEN in diegopetrucci/blog (Actions read/write on personal-blog-redirects only).'
  exit 1
fi
: "${GITHUB_SHA:?Run this after the blog deployment in GitHub Actions}"
if [[ ! "$GITHUB_SHA" =~ ^[0-9a-f]{40}$ ]]; then
  echo '::error::Invalid blog commit SHA.'
  exit 1
fi

repo=diegopetrucci/personal-blog-redirects
title="Refresh feeds after blog ${GITHUB_SHA}"

# GitHub may disable the daily schedule after a long period without posts.
gh workflow enable pages.yml --repo "$repo"
previous_id=$(gh run list --repo "$repo" --workflow pages.yml \
  --event workflow_dispatch --branch main --limit 1 \
  --json databaseId --jq '.[0].databaseId // 0')
gh workflow run pages.yml --repo "$repo" --ref main --field "source_sha=$GITHUB_SHA"

# Dispatch does not return a run ID. Match the title carrying this deployment's
# SHA and select the latest run, including when a deployment is retried.
run_id=''
for attempt in {1..24}; do
  run_id=$(gh run list --repo "$repo" --workflow pages.yml \
    --event workflow_dispatch --branch main --limit 30 \
    --json databaseId,displayTitle,createdAt \
    --jq "[.[] | select(.displayTitle == \"$title\" and .databaseId > $previous_id)] | sort_by(.databaseId) | last | .databaseId // empty")
  if [[ -n "$run_id" ]]; then
    break
  fi
  sleep 5
done
if [[ -z "$run_id" ]]; then
  echo '::error::Legacy feed refresh was requested, but its workflow run could not be found.'
  exit 1
fi
echo "Legacy feed refresh: https://github.com/$repo/actions/runs/$run_id"
# Poll the Actions API directly: gh run watch requires permissions that some
# fine-grained tokens cannot provide. Actions read/write is sufficient here.
for attempt in {1..144}; do
  result=$(gh api "repos/$repo/actions/runs/$run_id" \
    --jq '[.status, (.conclusion // "pending")] | @tsv')
  IFS=$'\t' read -r status conclusion <<< "$result"
  if [[ "$status" == completed ]]; then
    if [[ "$conclusion" == success ]]; then
      echo 'Legacy feeds deployed successfully.'
      exit 0
    fi
    echo "::error::Legacy feed deployment finished with status: $conclusion"
    exit 1
  fi
  sleep 5
done
echo '::error::Timed out waiting for legacy feed deployment; inspect the linked run.'
exit 1
