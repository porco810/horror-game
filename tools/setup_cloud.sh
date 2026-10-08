#!/usr/bin/env bash
set -euo pipefail
cd /workspace/horror-game
command -v blender >/dev/null
command -v python3 >/dev/null
command -v npm >/dev/null
mkdir -p /workspace/scratch/npm-cache
npm ci --include=dev --ignore-scripts --no-audit --no-fund --cache /workspace/scratch/npm-cache
if [ ! -s export/kuchikagura_game.blend ] || [ ! -s web/assets/models/kuchikagura.glb ]; then
  if npm run build > build_log.txt 2>&1; then
    tail -n 8 build_log.txt
  else
    tail -n 60 build_log.txt
    exit 1
  fi
fi
npm run validate
npm run test:logic
npm run build:web
