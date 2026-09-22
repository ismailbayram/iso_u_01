#!/usr/bin/env bash
# Yer istasyonunu nereden cagrilirsa cagrilsin dogru dizinden baslatir.
# navstation bir Python paketi ve yalniz tools/ icinden import edilebiliyor;
# repo kokunden "python -m navstation" demek "No module named navstation" verir.
set -euo pipefail

cd "$(dirname "$0")"

PY="../.env/bin/python"
if [ ! -x "$PY" ]; then
    echo "Sanal ortam bulunamadi: $(cd .. && pwd)/.env" >&2
    echo "Kurulum adimlari: tools/navstation/README.md" >&2
    exit 1
fi

exec "$PY" -m navstation "$@"
