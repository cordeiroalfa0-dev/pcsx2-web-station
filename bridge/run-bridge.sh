#!/usr/bin/env sh
set -eu
cd "$(dirname "$0")"
if ! command -v node >/dev/null 2>&1; then
  echo "Node.js 18 ou superior não foi encontrado. Instale-o e execute novamente." >&2
  exit 1
fi
exec node bridge.mjs
