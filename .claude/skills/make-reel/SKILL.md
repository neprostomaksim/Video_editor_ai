---
name: make-reel
description: >
  Монтаж вертикального ролика (9:16) в стиле студии клиента: видео спикера (ИИ-аватар или живая запись) →
  чистка пауз/дублей → субтитры, хук с первого кадра, сцены из библиотеки (список, число, сравнение, титулы,
  скрины, b-roll, логотипы, чат, GitHub…), наезды, звуковые акценты, музыка, CTA → MP4. По желанию — по
  ролику-референсу (скелет и b-roll из донора). Используй, когда пользователь пишет /make-reel, «смонтируй»,
  «сделай ролик», присылает видео спикера (или кладёт его в inbox/). Если студия не настроена — сначала /setup-studio.
---

# /make-reel — монтаж ролика

## Перед стартом
1. Нет `studio/studio.json` или `studio/profile.md` → скажи, что сначала настроим студию (10–15 минут), и запусти
   /setup-studio. Без профиля монтаж будет в чужом стиле.
2. **Прочитай `studio/profile.md`** (аудитория, тон, CTA, запреты, что сработало) и **`docs/DIRECTOR.md`**
   (хук §1а, ритм §1б, выбор сцен §2, правила §3). Стиль — `python3 tools/studio.py show` (`montage`, `source`, `sound`).
3. Входные данные: видео спикера (путь или файл в `inbox/`), по желанию сценарий, ссылки, референс, кодовое слово.
   Придумай `slug` (латиница, коротко: `3-oshibki-reels`). Папка ролика — `videos/<slug>/`.

## Конвейер
1. **Речь.**
   - Живая запись (`source.type = talking_head`): `python3 tools/cleanup.py <raw.mp4> videos/<slug>` →
     прочитай `videos/<slug>/source/plan.md`: дубли (`retake`, `marker`) и помеченные паразиты (`filler?`) проверь
     по тексту — вырезаем неудачный дубль, а не удачный; спорное покажи клиенту. Правь `plan.json`, затем
     `python3 tools/cleanup.py <raw.mp4> videos/<slug> --apply` → `transcribe.py videos/<slug>/source/clean.mp4 videos/<slug>`.
   - ИИ-аватар: сразу `python3 tools/transcribe.py <video.mp4> videos/<slug>`.
   - Проверь `videos/<slug>/frame.jpg`: спикер в кадре, голова не обрезана (горизонтальное видео → `--x`).
   - Прочитай `transcript.txt`, исправь названия в `words.json`; повторяющиеся ошибки → `studio/glossary.json`.
2. **Референс ролика** (если дали): по `docs/REFERENCE_MODE.md` — `tools/ref_analyze.py`, решения по шотам, b-roll `clip.py`.
3. **Материалы** — только для того, что звучит в озвучке, факты проверяй:
   - сайт/пост/новость: `node tools/web_capture.mjs <url> videos/<slug>/captures/x.png [--mobile] [--scroll N]`;
   - GitHub: `node tools/github_capture.mjs owner/name videos/<slug>`;
   - логотипы: `python3 tools/logos.py find "имя"` → `fetch <slug>` → `add <slug> <файл|url> "Имя" "синонимы"`;
   - видео/GIF продукта, свои записи экрана → `python3 tools/clip.py` (в т.ч. `--fit blur` для полного экрана);
   - движение для хука без видео → HTML-макет → `node tools/html_record.mjs mock.html media/hook.mp4 1080 1010 --dur 4`.
4. **Раскадровка** `videos/<slug>/shotlist.json` по DIRECTOR и темпу студии (`montage.pace`). Кодовое слово CTA —
   из последней фразы. Хук сомнительный → 2–3 варианта (`build.py --shot shot_hookA.json --pub public_hookA --duration 6.5`).
5. **Музыка** (если `sound.music`): `python3 tools/music.py videos/<slug>`. Нет треков/доступа — собираем без музыки
   и говорим клиенту, как добавить (`studio/music/`).
6. **Сборка:** `python3 engine/build.py videos/<slug>` — исправь все ⚠.
7. **Проверка:** `cd videos/<slug> && npx hyperframes check public` (0 errors) →
   `npx hyperframes snapshot public --at 0,<середины сцен> --describe false` → **посмотри
   `public/snapshots/contact-sheet.jpg` сам**: кадр 0 = обложка, текст не на лице, субтитры не перекрывают графику,
   логотипы настоящие. Нашёл проблему — правь раскадровку и пересобирай.
8. **Рендер:** `cd videos/<slug> && npx hyperframes render public -o output.mp4 --fps 25`
   (60 с+ → `--low-memory-mode`; ошибка «detached Frame» → повторить; на Mac быстрее с `PRODUCER_BROWSER_GPU_MODE=hardware`) →
   `python3 tools/finalize.py videos/<slug>` — громкость к −16 LUFS + лёгкая копия `output_web.mp4`.
9. **Клиенту:** путь к ролику + таблица «время — сцена — что на экране» + что проверить (названия, цифры,
   кодовое слово). Попроси после публикации прислать статистику (охват, досмотры, пропуск в первые 3 с) —
   выводы допиши в `studio/profile.md` → «Что сработало / провалилось».

## Когда сцены не хватает
Сначала `html` (свободная сцена в токенах стиля: `var(--accent)`, `var(--ink)`, шрифты `'Head'`, `'Body'`).
Приём понадобится снова → модуль `engine/scenes/<kind>.py` (KIND, CSS, render, animate + docstring — по образцу
соседних) и строка в таблице `docs/DIRECTOR.md §2`. Так библиотека растёт с каждым роликом.

## Правки после показа
- «Поменяй стиль/цвет/субтитры» для всех роликов → /style-lab; только для этого ролика → блоки `theme`,
  `captions`, `cta_style` в shotlist.json.
- «Убери/добавь кусок речи» → правь `source/plan.json` → `cleanup.py --apply` → `transcribe.py` → **индексы слов
  сдвинутся**, раскадровку сверяй заново.
