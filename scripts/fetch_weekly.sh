#!/usr/bin/env bash
set -euo pipefail
REPO="${REPO:-QCT-xyz/qlx-hfp}"
WF="${WF:-.github/workflows/qlx_sts_weekly.yml}"
RID="$(gh run list --repo "$REPO" --workflow "$WF" --limit 1 --json databaseId -q '.[0].databaseId')"
OUT="artifacts_ci/$RID"
rm -rf "$OUT"
mkdir -p "$OUT"
gh run download "$RID" --repo "$REPO" -n sts-weekly -D "$OUT"
python3 - "$OUT" <<'PY'
import sys, json, pathlib
out = pathlib.Path(sys.argv[1])
paths = list(out.glob("**/summary.json"))
print(paths[0].read_text() if paths else "summary.json not found")
PY
