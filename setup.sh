#!/usr/bin/env bash
# Установка и проверка окружения (macOS/Linux). На любой системе то же самое: python3 setup.py …
# (Windows: setup.cmd или python setup.py …)
#   ./setup.sh          поставить недостающее (всё кладётся в папку проекта)
#   ./setup.sh --check  только проверить
#   ./setup.sh --heygen подключить HeyGen (по желанию: музыка из каталога HeyGen)
cd "$(dirname "$0")"
if ! command -v python3 >/dev/null 2>&1; then
  echo "Нужен Python 3: Mac — xcode-select --install · Linux — sudo apt install python3"; exit 1
fi
exec python3 setup.py "$@"
