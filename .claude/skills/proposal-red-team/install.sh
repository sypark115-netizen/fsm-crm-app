#!/usr/bin/env bash
# Install proposal-red-team for Claude Code and/or Codex (user-level, local copy).
#   ./install.sh            -> both
#   ./install.sh claude     -> ~/.claude/skills/proposal-red-team
#   ./install.sh codex      -> ${CODEX_HOME:-~/.codex}/skills/proposal-red-team
set -eu
SRC="$(cd "$(dirname "$0")" && pwd)"
targets="${1:-both}"
copy() {
  mkdir -p "$1"
  rsync -a --delete --exclude evals --exclude tests --exclude '__pycache__' --exclude '.pytest_cache' "$SRC/" "$1/proposal-red-team/"
  echo "installed -> $1/proposal-red-team"
}
case "$targets" in
  claude) copy "$HOME/.claude/skills" ;;
  codex)  copy "${CODEX_HOME:-$HOME/.codex}/skills" ;;
  both)   copy "$HOME/.claude/skills"; copy "${CODEX_HOME:-$HOME/.codex}/skills" ;;
  *) echo "usage: $0 [claude|codex|both]"; exit 1 ;;
esac
python3 -m pip install -q -r "$SRC/scripts/requirements.txt" || echo "pip install failed — install scripts/requirements.txt manually"
command -v soffice >/dev/null || echo "note: LibreOffice not found — supply decks as PDF (or install LibreOffice) for rendering"
fc-list 2>/dev/null | grep -qiE "nanum|noto sans cjk|malgun|pretendard" || echo "note: no Korean font found — install fonts-nanum / Noto CJK for correct renders"
