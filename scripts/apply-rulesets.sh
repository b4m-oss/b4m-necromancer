#!/usr/bin/env bash
# Apply repository rulesets from .github/rulesets/*.json to a GitHub repo.
# Requires: gh (authenticated as a repo admin), jq
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RULESETS_DIR="${ROOT_DIR}/.github/rulesets"
API_VERSION="2022-11-28"

usage() {
  cat <<'EOF'
Usage:
  apply-rulesets.sh --repo OWNER/REPO

Applies all JSON files in .github/rulesets/ to the target repository.
Existing rulesets with the same name are updated (PUT); otherwise created (POST).

Notes:
  - GitHub Free (org): repository rulesets work on public repos only.
  - Caller must be a repository admin (gh auth login).
EOF
}

REPO=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --repo)
      REPO="${2:-}"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "error: unknown argument: $1" >&2
      usage >&2
      exit 1
      ;;
  esac
done

if [[ -z "${REPO}" ]]; then
  echo "error: --repo OWNER/REPO is required" >&2
  usage >&2
  exit 1
fi

if ! command -v gh >/dev/null 2>&1; then
  echo "error: gh is required" >&2
  exit 1
fi

if ! command -v jq >/dev/null 2>&1; then
  echo "error: jq is required" >&2
  exit 1
fi

if [[ ! -d "${RULESETS_DIR}" ]]; then
  echo "error: rulesets directory not found: ${RULESETS_DIR}" >&2
  exit 1
fi

shopt -s nullglob
FILES=("${RULESETS_DIR}"/*.json)
if [[ ${#FILES[@]} -eq 0 ]]; then
  echo "error: no ruleset JSON files in ${RULESETS_DIR}" >&2
  exit 1
fi

echo "Listing existing rulesets for ${REPO}..."
EXISTING_JSON="$(
  gh api \
    -H "Accept: application/vnd.github+json" \
    -H "X-GitHub-Api-Version: ${API_VERSION}" \
    "/repos/${REPO}/rulesets" \
    --paginate
)"

for file in "${FILES[@]}"; do
  name="$(jq -r '.name // empty' "${file}")"
  if [[ -z "${name}" ]]; then
    echo "error: missing .name in ${file}" >&2
    exit 1
  fi

  ruleset_id="$(
    jq -r --arg name "${name}" '
      if type == "array" then
        map(select(.name == $name)) | .[0].id // empty
      else
        empty
      end
    ' <<<"${EXISTING_JSON}"
  )"

  if [[ -n "${ruleset_id}" ]]; then
    echo "Updating ruleset '${name}' (id=${ruleset_id}) from $(basename "${file}")..."
    gh api \
      --method PUT \
      -H "Accept: application/vnd.github+json" \
      -H "X-GitHub-Api-Version: ${API_VERSION}" \
      "/repos/${REPO}/rulesets/${ruleset_id}" \
      --input "${file}" \
      >/dev/null
  else
    echo "Creating ruleset '${name}' from $(basename "${file}")..."
    gh api \
      --method POST \
      -H "Accept: application/vnd.github+json" \
      -H "X-GitHub-Api-Version: ${API_VERSION}" \
      "/repos/${REPO}/rulesets" \
      --input "${file}" \
      >/dev/null
  fi
done

echo "Done. Applied ${#FILES[@]} ruleset(s) to ${REPO}."
