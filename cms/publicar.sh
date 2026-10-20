#!/usr/bin/env bash
# Publica site/ + cms/ no GitHub Pages da revista.
# Não usa rsync --delete em conteudo/: a mesa dos alunos vive no repo Pages.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SITE="$ROOT/site"
PAGES="${PAGES_DIR:-/tmp/revista-experimental-canones}"
REPO="${PAGES_REPO:-git@github.com:LAB-IA-BR/revista-experimental-canones.git}"

python3 "$ROOT/cms/build.py"

if [[ -d "$PAGES/.git" ]]; then
  git -C "$PAGES" fetch origin
  git -C "$PAGES" checkout main
  git -C "$PAGES" pull --ff-only origin main
else
  rm -rf "$PAGES"
  git clone "$REPO" "$PAGES"
fi

rsync -a \
  --exclude '.git/' \
  --exclude '.github/' \
  --exclude 'cms/' \
  --exclude 'img/brasao-ufes.png' \
  --exclude 'img/brasao-ufes.svg' \
  --exclude 'img/logo-ufes.png' \
  --exclude 'img/marca-ufes.svg' \
  --exclude 'conteudo/' \
  "$SITE/" "$PAGES/"

# conteudo: copia sem apagar peças que só existem no Pages
rsync -a "$SITE/conteudo/" "$PAGES/conteudo/"
rsync -a --exclude '__pycache__/' --exclude '*.pyc' --exclude '.gitignore' "$ROOT/cms/" "$PAGES/cms/"
printf '%s\n' '__pycache__/' '*.pyc' > "$PAGES/cms/.gitignore"
mkdir -p "$PAGES/.github/workflows"
cp "$ROOT/cms/github/montar-revista.yml" "$PAGES/.github/workflows/montar-revista.yml"
touch "$PAGES/.nojekyll"

git -C "$PAGES" add -A
if git -C "$PAGES" diff --cached --quiet; then
  echo "nada a publicar"
  exit 0
fi

MSG="${REVISTA_COMMIT_MSG:-feat(revista): atualiza o site publicado}"
git -C "$PAGES" -c user.email="orlandolopes.es@gmail.com" -c user.name="Orlando Lopes" \
  commit -m "$MSG"
git -C "$PAGES" push origin main
echo "publicado: https://lab-ia-br.github.io/revista-experimental-canones/"
