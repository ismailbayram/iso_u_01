#!/usr/bin/env bash
# Ana makinede derlenen donanimsiz testler. PlatformIO'nun test runner'i
# kullanilmiyor; test/ klasorunde PlatformIO testi olmayan eski taslaklar var.
set -euo pipefail

cd "$(dirname "$0")/.."
OUT="$(mktemp -d)"
trap 'rm -rf "$OUT"' EXIT

FAILED=0
for src in test/native/test_*.cpp; do
    name="$(basename "$src" .cpp)"
    if ! g++ -std=c++17 -Wall -Wextra -Iinclude "$src" -o "$OUT/$name"; then
        echo "DERLEME HATASI: $src"
        FAILED=1
        continue
    fi
    if ! "$OUT/$name"; then
        echo "TEST BASARISIZ: $src"
        FAILED=1
    fi
done

exit "$FAILED"
