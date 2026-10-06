#!/usr/bin/env bash
# Установка и проверка окружения AI Montage Kit.
#   ./setup.sh          поставить всё недостающее (macOS — через Homebrew; Linux/WSL — подскажет apt-команды)
#   ./setup.sh --check  только проверить
set -u
cd "$(dirname "$0")"
CHECK=0; [ "${1:-}" = "--check" ] && CHECK=1
OS="$(uname -s)"
ok=0; miss=()
say()  { printf "  %-34s %s\n" "$1" "$2"; }
has()  { command -v "$1" >/dev/null 2>&1; }

echo "AI Montage Kit — проверка окружения"
for b in python3 node npm ffmpeg ffprobe; do
  if has "$b"; then say "$b" "✓"; else say "$b" "✗ нет"; miss+=("$b"); fi
done
if has whisper-cli || has whisper-cpp; then say "whisper.cpp (распознавание речи)" "✓"; else say "whisper.cpp (распознавание речи)" "✗ нет"; miss+=("whisper"); fi
MODEL=""
for p in "${WHISPER_MODEL:-}" models/ggml-small.bin "$HOME/.cache/hyperframes/whisper/models/ggml-small.bin"; do
  [ -n "$p" ] && [ -f "$p" ] && MODEL="$p" && break
done
if [ -n "$MODEL" ]; then say "модель речи" "✓ $MODEL"; else say "модель речи (ggml-small, 470 МБ)" "✗ нет"; miss+=("model"); fi
CHROME=""
for p in "${CHROME_PATH:-}" "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" /usr/bin/google-chrome /usr/bin/chromium /usr/bin/chromium-browser; do
  [ -n "$p" ] && [ -x "$p" ] && CHROME="$p" && break
done
if [ -n "$CHROME" ]; then say "Chrome (скриншоты сайтов)" "✓"; else say "Chrome (скриншоты сайтов)" "✗ нет (не обязателен для монтажа)"; fi
if [ -d tools/node_modules/puppeteer-core ]; then say "node-зависимости tools/" "✓"; else say "node-зависимости tools/" "✗ нет"; miss+=("npm"); fi
SK=0
for d in .claude/skills "$HOME/.claude/skills" "$HOME/.agents/skills" "$HOME/.codex/skills"; do
  [ -f "$d/hyperframes-audio/scripts/carve.mjs" ] && SK=1
done
if [ $SK = 1 ]; then say "скиллы HyperFrames (музыка под голос)" "✓"; else say "скиллы HyperFrames (музыка под голос)" "✗ нет (желательно)"; miss+=("skills"); fi
if [ -f studio/studio.json ] && [ -f studio/profile.md ]; then say "студия" "✓ настроена"; else say "студия" "— не настроена → в агенте: /setup-studio"; fi

if [ ${#miss[@]} -eq 0 ]; then echo; echo "Всё готово. Открой папку в Claude Code и напиши /setup-studio (или /make-reel)."; exit 0; fi
if [ $CHECK = 1 ]; then echo; echo "Не хватает: ${miss[*]} → запусти ./setup.sh"; exit 1; fi

echo; echo "Ставлю недостающее…"
need() { for m in "${miss[@]}"; do [ "$m" = "$1" ] && return 0; done; return 1; }
if [ "$OS" = "Darwin" ]; then
  if ! has brew; then
    echo "Нужен Homebrew: https://brew.sh — установи его командой с сайта и запусти ./setup.sh снова"; exit 1
  fi
  pk=()
  need python3 && pk+=(python)
  { need node || need npm; } && pk+=(node)
  { need ffmpeg || need ffprobe; } && pk+=(ffmpeg)
  need whisper && pk+=(whisper-cpp)
  [ ${#pk[@]} -gt 0 ] && brew install "${pk[@]}"
else
  if need python3 || need node || need ffmpeg || need whisper; then
    echo "Linux/WSL: поставь пакеты сам и запусти ./setup.sh снова:"
    echo "  sudo apt install -y python3 nodejs npm ffmpeg"
    echo "  whisper.cpp: https://github.com/ggml-org/whisper.cpp (собрать и положить whisper-cli в PATH)"
  fi
fi
if need npm; then (cd tools && npm install --no-fund --no-audit); fi
if need model; then
  mkdir -p models
  echo "Скачиваю модель распознавания речи (≈470 МБ)…"
  curl -L --fail -o models/ggml-small.bin "https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-small.bin" \
    || { rm -f models/ggml-small.bin; echo "не скачалось — повтори ./setup.sh"; }
fi
if need skills; then
  echo "Ставлю скиллы HyperFrames (официальные, нужны для музыки под голос)…"
  npx -y hyperframes skills || echo "не вышло — можно позже: npx hyperframes skills"
fi
echo; ./setup.sh --check
