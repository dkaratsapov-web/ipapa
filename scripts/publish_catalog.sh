#!/usr/bin/env bash
# Публикует выгрузку каталога в ветку webapp-data (одним коммитом, без истории).
# Мини-апп читает её через raw.githubusercontent.com.
set -euo pipefail
SRC="${1:-data/export/catalog.json}"
BRANCH="${DATA_BRANCH:-webapp-data}"
WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT
cd "$WORK"
git init -q
git config user.name "github-actions[bot]"
git config user.email "41898282+github-actions[bot]@users.noreply.github.com"
git checkout -q -b "$BRANCH"
cp "$OLDPWD/$SRC" catalog.json
git add catalog.json
git commit -qm "Каталог $(date -u +%FT%TZ)"
git push -qf "${DATA_REMOTE:?DATA_REMOTE не задан}" "$BRANCH"
