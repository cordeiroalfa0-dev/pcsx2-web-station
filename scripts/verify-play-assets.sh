#!/usr/bin/env sh
set -eu
cd "$(dirname "$0")/.."
expected_file=$(mktemp)
actual_file=$(mktemp)
trap 'rm -f "$expected_file" "$actual_file"' EXIT
cat > "$expected_file" <<'EOF'
5599ff16ae5e3534f9b779736aedfa20661821d57be7f03e587e31ef8d090317  Play.js
5c6ace637a23f3416a8105d1a07786631994e8dfe34d603a9f62c3b47c47f1a2  Play.wasm
a1e02dc43527f92cfc8bc99831027647053ddfe64f903b5a9b746cefaac04180  vendor/playjs/main.js
105036c0e8a13b39a811506e499363c0bea1aa2325a0104b237bd9a9d8cafeb8  vendor/playjs/main.css
EOF
sha256sum Play.js Play.wasm vendor/playjs/main.js vendor/playjs/main.css > "$actual_file"
if ! cmp -s "$expected_file" "$actual_file"; then
  echo "Falha: os assets Play! não correspondem aos hashes esperados." >&2
  diff -u "$expected_file" "$actual_file" || true
  exit 1
fi
echo "OK: assets Play! íntegros e correspondentes ao manifesto."
