#!/usr/bin/env bash
# Установка и проверка окружения AI Montage Kit.
#   ./setup.sh          поставить недостающее (без Homebrew и прав администратора — всё кладётся в папку проекта)
#   ./setup.sh --check  только проверить
#   ./setup.sh --heygen подключить HeyGen (по желанию: музыка из каталога HeyGen; вход через браузер)
# Нужно заранее только Node.js 22+ (nodejs.org, LTS) и Python 3 (на Mac предложит установиться сам).
set -u
cd "$(dirname "$0")"
ROOT="$PWD"
export PATH="$ROOT/bin:$PATH"
CHECK=0; [ "${1:-}" = "--check" ] && CHECK=1
if [ "${1:-}" = "--heygen" ]; then
  export PATH="$HOME/.local/bin:$PATH"
  if ! command -v heygen >/dev/null 2>&1; then
    echo "Ставлю HeyGen CLI…"
    curl -fsSL https://static.heygen.ai/cli/install.sh | bash || { echo "не вышло — https://developers.heygen.com/cli"; exit 1; }
    export PATH="$HOME/.local/bin:$PATH"
  fi
  echo "Вход в HeyGen: откроется браузер — войди в свой аккаунт HeyGen (можно бесплатный) и подтверди доступ."
  heygen auth login --oauth && echo "✓ HeyGen подключён: музыка из каталога доступна"
  exit $?
fi
OS="$(uname -s)"; ARCH="$(uname -m)"
miss=()
say() { printf "  %-30s %s\n" "$1" "$2"; }
has() { command -v "$1" >/dev/null 2>&1; }

echo "AI Montage Kit — проверка окружения"
if has node && has npx && [ "$(node -p "process.versions.node.split('.')[0]")" -ge 22 ] 2>/dev/null; then say "Node.js" "✓ $(node -v)"
else say "Node.js 22+" "✗ нет или старая версия — скачай LTS с https://nodejs.org"; miss+=(node); fi
if has python3 && python3 -c "import sys; sys.exit(sys.version_info < (3, 9))" 2>/dev/null; then say "Python 3" "✓"; else
  say "Python 3" "✗ нет — Mac: xcode-select --install · Windows/Linux: python.org"; miss+=(python); fi
if has ffmpeg && has ffprobe; then say "ffmpeg (видео и звук)" "✓"; else say "ffmpeg (видео и звук)" "✗ нет"; miss+=(ffmpeg); fi
if has yt-dlp; then say "yt-dlp (видео по ссылкам)" "✓"; else say "yt-dlp (видео по ссылкам)" "✗ нет"; miss+=(ytdlp); fi
if [ -x tools/node_modules/.bin/hyperframes ] && [ -d tools/node_modules/puppeteer-core ]; then
  say "HyperFrames (анимация и рендер)" "✓ $(tools/node_modules/.bin/hyperframes --version 2>/dev/null | tail -1)"
  if ./hf browser path >/dev/null 2>&1; then say "браузер для рендера" "✓"; else say "браузер для рендера" "✗ нет"; miss+=(browser); fi
else say "HyperFrames (анимация и рендер)" "✗ нет"; miss+=(npm browser); fi
if ls "$HOME"/.cache/hyperframes/whisper/models/ggml-small*.bin >/dev/null 2>&1; then say "распознавание речи" "✓"
else say "распознавание речи" "— скачается при первом запуске (~470 МБ)"; miss+=(asr); fi
SK=0
for d in .agents/skills .claude/skills "$HOME/.claude/skills" "$HOME/.agents/skills" "$HOME/.codex/skills"; do
  [ -f "$d/hyperframes-audio/scripts/carve.mjs" ] && SK=1
done
if [ $SK = 1 ]; then say "скиллы HyperFrames (музыка)" "✓"; else say "скиллы HyperFrames (музыка)" "— нет (желательно)"; miss+=(skills); fi
HG="$HOME/.local/bin/heygen"; command -v heygen >/dev/null 2>&1 && HG="$(command -v heygen)"
if [ -x "$HG" ] && "$HG" auth status >/dev/null 2>&1; then say "HeyGen (музыка из каталога)" "✓ подключён"
else say "HeyGen (музыка из каталога)" "— не подключён (по желанию: ./setup.sh --heygen)"; fi
if [ -f studio/studio.json ] && [ -f studio/profile.md ]; then say "монтаж" "✓ настроен"; else say "монтаж" "— не настроен: открой агента и напиши «привет»"; fi

need() { for m in "${miss[@]:-}"; do [ "$m" = "$1" ] && return 0; done; return 1; }
hard=0; for m in "${miss[@]:-}"; do case "$m" in node|python|ffmpeg|npm|browser|ytdlp) hard=1;; esac; done
if [ ${#miss[@]} -eq 0 ] || { [ $CHECK = 1 ] && [ $hard = 0 ]; }; then
  echo; echo "Готово. Открой папку в Claude Code или Codex и напиши «привет»."; exit 0; fi
if [ $CHECK = 1 ]; then echo; echo "Не хватает: ${miss[*]} → запусти ./setup.sh"; exit 1; fi
if need node || need python; then echo; echo "Сначала поставь Node.js и Python (ссылки выше), потом снова ./setup.sh"; exit 1; fi

echo; echo "Ставлю недостающее в папку проекта…"
mkdir -p bin
echo "• HyperFrames и зависимости"
(cd tools && npm install --no-fund --no-audit --loglevel=error)
if need ffmpeg; then
  echo "• ffmpeg"
  (cd tools && npm install --no-save --no-fund --no-audit --loglevel=error ffmpeg-static ffprobe-static)
  F="$(cd tools && node -e "process.stdout.write(require('ffmpeg-static'))")"
  P="$(cd tools && node -e "process.stdout.write(require('ffprobe-static').path)")"
  ln -sf "$F" bin/ffmpeg && ln -sf "$P" bin/ffprobe && chmod +x "$F" "$P"
fi
if need ytdlp; then
  echo "• yt-dlp"
  case "$OS-$ARCH" in
    Darwin-*) Y=yt-dlp_macos ;;
    Linux-aarch64|Linux-arm64) Y=yt-dlp_linux_aarch64 ;;
    *) Y=yt-dlp_linux ;;
  esac
  curl -fsSL -o bin/yt-dlp "https://github.com/yt-dlp/yt-dlp/releases/latest/download/$Y" && chmod +x bin/yt-dlp \
    || echo "  не скачался — видео по ссылкам не будут работать, файлами можно"
fi
if need browser || need npm; then
  echo "• браузер для рендера"
  ./hf browser ensure >/dev/null 2>&1 || echo "  не скачался — повтори ./setup.sh"
fi
if need asr; then
  echo "• распознавание речи (модель ~470 МБ, один раз)"
  ffmpeg -v error -y -f lavfi -i "sine=f=440:d=2" -ar 16000 -ac 1 bin/.probe.wav \
    && ./hf transcribe bin/.probe.wav -d bin/.probe -m small -l ru --json >/dev/null 2>&1
  rm -rf bin/.probe bin/.probe.wav
fi
if need skills; then
  echo "• скиллы HyperFrames"
  ./hf skills >/dev/null 2>&1 || echo "  не вышло — можно позже: ./hf skills"
fi
echo; exec ./setup.sh --check
