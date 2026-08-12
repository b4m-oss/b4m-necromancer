#!/usr/bin/env bash
# Create a GitHub repository and apply rulesets from this repo.
# Requires: gh (authenticated), jq
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
APPLY_SCRIPT="${ROOT_DIR}/scripts/apply-rulesets.sh"

usage() {
  cat <<'EOF'
Usage:
  create-repo-with-rulesets.sh OWNER/REPO [--public|--private] [extra gh repo create flags...]

Creates the repository with gh, then applies .github/rulesets/*.json.

Default visibility: --public (required for rulesets on GitHub Free).

Examples:
  create-repo-with-rulesets.sh my-org/new-app
  create-repo-with-rulesets.sh my-org/new-app --public --clone
  create-repo-with-rulesets.sh my-org/new-app --public --description "demo"
EOF
}

if [[ $# -lt 1 ]]; then
  usage >&2
  exit 1
fi

case "$1" in
  -h|--help)
    usage
    exit 0
    ;;
esac

REPO="$1"
shift

if [[ "${REPO}" != */* ]] || [[ "${REPO}" == */ ]] || [[ "${REPO}" == /* ]]; then
  echo "error: repo must be OWNER/REPO (got: ${REPO})" >&2
  exit 1
fi

if ! command -v gh >/dev/null 2>&1; then
  echo "error: gh is required" >&2
  exit 1
fi

VISIBILITY_FLAG="--public"
EXTRA_FLAGS=()

while [[ $# -gt 0 ]]; do
  case "$1" in
    --public|--private|--internal)
      VISIBILITY_FLAG="$1"
      shift
      ;;
    *)
      EXTRA_FLAGS+=("$1")
      shift
      ;;
  esac
done

if [[ "${VISIBILITY_FLAG}" != "--public" ]]; then
  cat >&2 <<'EOF'
warning: non-public repositories require GitHub Pro/Team (or higher) for rulesets.
          On GitHub Free, apply will likely fail for private/internal repos.
EOF
fi

echo "Creating repository ${REPO} (${VISIBILITY_FLAG})..."
gh repo create "${REPO}" "${VISIBILITY_FLAG}" "${EXTRA_FLAGS[@]+"${EXTRA_FLAGS[@]}"}"

echo "Applying rulesets..."
"${APPLY_SCRIPT}" --repo "${REPO}"

echo "Verify with:"
echo "  gh ruleset list -R ${REPO}"
echo "  gh ruleset check main -R ${REPO}"
