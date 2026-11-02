#!/bin/bash
# Run only the tests for files changed vs HEAD; the full suite if unmappable.

set -euo pipefail

cd "$(git rev-parse --show-toplevel)"
readonly PY=".venv/bin/python"
CHANGED=()
while IFS= read -r f; do
    [[ -n "$f" && -e "$f" ]] && CHANGED+=("$f")
done < <({ git diff --name-only HEAD 2>/dev/null || true; git ls-files --others --exclude-standard; } | sort -u)

full=0 touched=0
tests=()
for f in "${CHANGED[@]}"; do
    base="$(basename "$f" .py)"
    case "$f" in
        pyproject.toml | */conftest.py) full=1; touched=1 ;;
        focus_guard/tests/test_*.py) touched=1; tests+=("$f") ;;
        focus_guard/tests/*.py) full=1; touched=1 ;;
        focus_guard/*.py)
            touched=1
            cand="focus_guard/tests/test_${base#_}.py"
            if [[ -f "$cand" ]]; then tests+=("$cand"); else full=1; fi
            ;;
    esac
done

if [[ $touched -eq 0 ]]; then
    echo "no python changes vs HEAD: nothing to test"; exit 0
fi
rc=0
if [[ $full -eq 1 ]]; then
    echo "python: running full suite"
    xvfb-run -a "$PY" -m pytest -q --tb=short || rc=1
else
    mapfile -t uniq < <(printf '%s\n' "${tests[@]}" | sort -u)
    echo "python: ${#uniq[@]} test file(s)"
    xvfb-run -a "$PY" -m pytest -q --tb=short --no-cov "${uniq[@]}" || rc=1
fi
[[ $rc -eq 0 ]] && echo "test-changed: pass" || echo "test-changed: FAIL"
exit $rc
