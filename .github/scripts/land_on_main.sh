#!/usr/bin/env bash
# land_on_main.sh — land the current HEAD commit on `main` THROUGH THE FRONT DOOR.
#
# Replaces the old direct push to main in carrier workflows.  Since 2026-10-14
# nothing reaches `main` without the referee's signed verdict (branch ruleset,
# empty bypass list), so a direct push is rejected by GitHub.  This script does
# what a well-behaved agent does instead:
#
#   1. push HEAD to a fresh branch  carrier/<workflow>/<run id>
#   2. open a pull request as the "Brain Automation" GitHub App
#      (NOT with GITHUB_TOKEN: pull requests opened by GITHUB_TOKEN do not
#      trigger other workflows, so the referee would never see them)
#   3. enable auto-merge (squash).  GitHub completes the merge by itself the
#      moment the referee's required check is green — no human in the loop.
#
# It is intentionally silent-but-safe when it cannot land:
#   * not running on main (pull-request runs etc.)      -> exit 0, nothing pushed
#   * automation app not configured yet                 -> exit 1 with a clear message
#   * auto-merge not allowed on the repository          -> PR left open, URL printed, exit 0
#
# Required environment (repository secrets, mapped into `env:` by the workflow):
#   AUTOMATION_APP_ID, AUTOMATION_APP_PRIVATE_KEY   — the Brain Automation app
#   (permissions: Contents read/write, Pull requests read/write; nothing else —
#   this app can NOT post check runs, so a leaked key cannot forge a verdict).
#
# This file is a protected path: changing it fails the referee and requires the
# owner's in-person merge.
set -euo pipefail

say() { printf '[land_on_main] %s\n' "$*" >&2; }

ref="${GITHUB_REF:-}"
event="${GITHUB_EVENT_NAME:-}"
if [ "${ref}" != "refs/heads/main" ] || [ "${event}" = "pull_request" ] || [ "${event}" = "pull_request_target" ]; then
  say "not a main-branch run (ref=${ref:-?} event=${event:-?}); nothing is landed from here."
  exit 0
fi
if [ -z "${AUTOMATION_APP_ID:-}" ] || [ -z "${AUTOMATION_APP_PRIVATE_KEY:-}" ]; then
  say "AUTOMATION_APP_ID / AUTOMATION_APP_PRIVATE_KEY are not set."
  say "Create the 'Brain Automation' GitHub App and add both repository secrets"
  say "(see canonical/governance/REPO_INTEGRITY_POLICY_V1.json, github_side). Nothing was landed."
  exit 1
fi
repo="${GITHUB_REPOSITORY:?GITHUB_REPOSITORY is required}"
if [ -n "$(git status --porcelain --untracked-files=no)" ]; then
  say "working tree has uncommitted tracked changes; commit before landing."
  exit 1
fi
head_sha="$(git rev-parse HEAD)"
base_sha="$(git rev-parse origin/main 2>/dev/null || true)"
if [ -n "${base_sha}" ] && [ "${head_sha}" = "${base_sha}" ]; then
  say "HEAD is already main; nothing to land."
  exit 0
fi

slug="$(printf '%s' "${GITHUB_WORKFLOW:-carrier}" | tr -c 'A-Za-z0-9' '-' | tr -s '-' | sed 's/^-//; s/-$//' | cut -c1-48 | tr 'A-Z' 'a-z')"
branch="carrier/${slug:-carrier}/${GITHUB_RUN_ID:-local}-${GITHUB_RUN_ATTEMPT:-1}"

# ---- mint an installation token for the Brain Automation app (openssl + curl only)
b64url() { openssl base64 -A | tr '+/' '-_' | tr -d '='; }
now="$(date +%s)"
header="$(printf '{"alg":"RS256","typ":"JWT"}' | b64url)"
payload="$(printf '{"iat":%d,"exp":%d,"iss":"%s"}' "$((now - 60))" "$((now + 540))" "${AUTOMATION_APP_ID}" | b64url)"
keyfile="$(mktemp)"; trap 'rm -f "${keyfile}"' EXIT
printf '%s\n' "${AUTOMATION_APP_PRIVATE_KEY}" > "${keyfile}"
signature="$(printf '%s.%s' "${header}" "${payload}" | openssl dgst -sha256 -sign "${keyfile}" | b64url)"
jwt="${header}.${payload}.${signature}"
api="https://api.github.com"
installation_id="$(curl -sSf -H "Authorization: Bearer ${jwt}" -H "Accept: application/vnd.github+json" "${api}/repos/${repo}/installation" | python3 -c 'import json,sys; print(json.load(sys.stdin)["id"])')"
token="$(curl -sSf -X POST -H "Authorization: Bearer ${jwt}" -H "Accept: application/vnd.github+json" "${api}/app/installations/${installation_id}/access_tokens" | python3 -c 'import json,sys; print(json.load(sys.stdin)["token"])')"
echo "::add-mask::${token}"

# ---- 1. push the carrier branch
git push "https://x-access-token:${token}@github.com/${repo}.git" "HEAD:refs/heads/${branch}"
say "pushed ${head_sha} to ${branch}"

# ---- 2. open the pull request as the app
subject="$(git log -1 --pretty=%s)"
run_url="${GITHUB_SERVER_URL:-https://github.com}/${repo}/actions/runs/${GITHUB_RUN_ID:-0}"
body="$(printf 'Carrier result from workflow **%s** (run %s).\n\nProduced on the GitHub-hosted runner for commit %s and submitted through the front door: it merges automatically only when the referee check is green.\n\nFiles:\n%s\n' \
  "${GITHUB_WORKFLOW:-carrier}" "${run_url}" "${base_sha:-unknown}" "$(git diff --name-only "${base_sha:-HEAD~1}" HEAD | sed 's/^/- /')")"
pr_url="$(GH_TOKEN="${token}" gh pr create --repo "${repo}" --base main --head "${branch}" --title "carrier: ${subject}" --body "${body}")"
say "opened ${pr_url}"

# ---- 3. auto-merge: completes only when the required (signed) referee check passes
if GH_TOKEN="${token}" gh pr merge --repo "${repo}" --auto --squash "${pr_url}" 2>/tmp/land_automerge.err; then
  say "auto-merge armed; GitHub merges it when the referee is green."
else
  say "auto-merge could not be armed ($(tr '\n' ' ' </tmp/land_automerge.err | cut -c1-200)); the pull request stays open at ${pr_url}"
fi
exit 0
