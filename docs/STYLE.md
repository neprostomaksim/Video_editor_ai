# studio.json — справочник стиля

`studio/studio.json` хранит **только отличия** от `engine/defaults.json`. Править удобнее командой:

```bash
python3 tools/studio.py set colors.accent=#FF2E88 captions.style=highlight
python3 tools/style_preview.py      # посмотреть результат: studio/preview.jpg
```

Цвет можно задать hex (`#RRGGBB`), а в субтитрах и CTA — ещё и именем из палитры: `"accent"`, `"ink"`, `"dark"`.

## colors — палитра
| ключ | что красит |
|---|---|
| `accent` | главный цвет бренда: активное слово субтитров, маркер `*слово*`, плашки, кодовое слово CTA, галочки |
| `accent_ink` | текст поверх акцентной плашки (обычно чёрный или белый — по контрасту) |
| `bg` / `card` / `ink` / `muted` / `line` | светлые сцены графики: фон, карточки, текст, второстепенный текст, линии |
| `dark` / `dark_ink` | тёмные сцены (`"bg": "dark"`) и плашки `pill` |

## fonts — шрифты
| ключ | |
|---|---|
| `head` | заголовки: хук, титулы, крупный текст, числа |
| `body` | всё остальное, включая субтитры |
| `mono` | код, терминал, кодовое слово CTA (если `cta.word_font = "mono"`) |
| `head_weight` | жирность заголовков (400–900) |
| `title_case` | `"uppercase"` — заголовки капсом, `"none"` — как написано |

Любой шрифт Google Fonts ставится одной командой: `python3 tools/fonts.py add "Unbounded"` (нужна кириллица).
Свой файл: `python3 tools/fonts.py file "Brand Sans" font.woff2 --weight 700`. Встроены Montserrat и JetBrains Mono.

## shape
`radius` — скругление плашек и карточек (px); `plate` — цвет плашек `pill` (по умолч. `dark`).

## captions — субтитры
| ключ | значения |
|---|---|
| `enabled` | `true` / `false` |
| `style` | `box` — плашка под фразой, активное слово цветом · `highlight` — активное слово на цветной плашке, текст с обводкой · `outline` — без плашки, обводка, активное слово цветом · `word` — по одному крупному слову |
| `max_words`, `max_chars` | сколько слов/символов в одной фразе на экране |
| `size`, `weight`, `uppercase` | кегль (px), жирность, капс |
| `text`, `active`, `active_ink` | цвет текста, активного слова, текста на плашке активного слова (highlight) |
| `box`, `radius` | цвет и скругление плашки (`box`; можно `rgba(…)` для прозрачности) |
| `stroke` | цвет обводки (highlight/outline/word) |
| `y_full` | высота (px от верха, кадр 1080×1920) на полном кадре и полноэкранной графике; низ ~350 px закрыт интерфейсом |
| `y_split` | `"seam"` — на стыке графики и спикера, или число px |

## cta — финальная плашка
`enabled`, `line1` («напиши»), `line3` («в комментарии»), `box`, `text`, `word_color`, `word_font` (`mono` | `head`).
Само кодовое слово задаётся в каждом ролике: `"cta": {"from_w": 118, "word": "ГАЙД"}`.

## layout
`split_h` — высота зоны графики в split (по умолч. 1010 из 1920); `split_radius` — скругление окна спикера.

## source — спикер
| ключ | |
|---|---|
| `type` | `talking_head` (живая запись) / `avatar` (ИИ-аватар) |
| `full_pos` / `split_pos` | `object-position` видео в полном кадре и в нижней половине split (`"50% 40%"` — голова выше) |
| `face_top` | где начинается голова в полном кадре (px) — по нему хук опускает спикера, чтобы текст не лёг на лицо |
| `crop_x` | центр кадрирования горизонтального видео в 9:16 (0…1) |
| `jumpcuts`, `jump_scale` | наезды 1.0↔1.1 на фразах и склейках |

## sound
`sfx` (вкл/выкл), `sfx_volume` (множитель), `music` (вкл/выкл), `music_style` (`funk` | `epic` | `electronic`), `music_mood` (свои слова для поиска трека).

## montage — правила режиссёра
`pace` (`minimal` | `standard` | `dynamic`), `hook_style` (`split` | `face` | `comment` | `result`), `split`, `full_graphics`, `punches` — см. `docs/DIRECTOR.md §0`.
