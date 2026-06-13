from __future__ import annotations
import base64
import os
from datetime import datetime
from pathlib import Path

import config

CSS = """\
body { font-family: -apple-system, BlinkMacSystemFont, sans-serif; background: #f5f5f7; margin: 0; padding: 24px; color: #1d1d1f; }
h1 { font-size: 1.6rem; margin-bottom: 4px; }
.subtitle { color: #6e6e73; margin-bottom: 24px; font-size: .9rem; }
h2 { font-size: 1.1rem; margin: 28px 0 6px; padding-left: 12px; border-left: 4px solid #0071e3; }
h3 { font-size: .85rem; font-weight: 600; color: #6e6e73; margin: 14px 0 8px; text-transform: uppercase; letter-spacing: .05em; }
.summary { display: flex; gap: 24px; background: #fff; border-radius: 12px; padding: 20px 28px; box-shadow: 0 1px 4px rgba(0,0,0,.08); margin-bottom: 28px; }
.stat { text-align: center; min-width: 80px; }
.stat-num { font-size: 2rem; font-weight: 700; color: #0071e3; line-height: 1; }
.stat-label { font-size: .78rem; color: #6e6e73; margin-top: 4px; }
.group-section { margin-bottom: 8px; }
.group-tag { display: inline-flex; align-items: center; gap: 6px; background: #fff; border: 1px solid #e5e5ea; border-radius: 20px; padding: 4px 12px; font-size: .78rem; font-weight: 600; color: #3a3a3c; margin-bottom: 10px; }
.group-tag.cross { background: #f0f0ff; border-color: #c7c7ff; color: #3730a3; }
.pair { display: flex; flex-direction: row; align-items: flex-start; gap: 12px; background: #fff; border-radius: 12px; padding: 16px; margin-bottom: 10px; box-shadow: 0 1px 4px rgba(0,0,0,.08); }
.card { display: flex; flex-direction: column; align-items: center; width: 160px; flex-shrink: 0; }
.card img { width: 128px; height: 128px; object-fit: cover; border-radius: 8px; border: 1px solid #e5e5ea; }
.no-img { width: 128px; height: 128px; background: #e5e5ea; border-radius: 8px; display: flex; align-items: center; justify-content: center; font-size: .75rem; color: #6e6e73; }
.meta { text-align: center; font-size: .76rem; margin-top: 8px; line-height: 1.55; color: #3a3a3c; }
.meta-sender { font-size: .82rem; font-weight: 700; color: #1d1d1f; margin-top: 6px; word-break: break-word; }
.meta-dt { font-size: .73rem; color: #6e6e73; margin-top: 2px; }
.badge { display: inline-block; padding: 2px 8px; border-radius: 20px; font-size: .68rem; font-weight: 600; margin-bottom: 4px; }
.badge-exact { background: #ffd60a; color: #1d1d1f; }
.badge-similar { background: #30d158; color: #fff; }
.badge-cross { background: #6366f1; color: #fff; }
.dist { font-size: .75rem; color: #6e6e73; align-self: center; text-align: center; padding: 0 8px; line-height: 1.6; }
.dist b { font-size: 1.1rem; color: #1d1d1f; }
.empty { color: #6e6e73; font-style: italic; padding: 10px 0; }
.card img { cursor: zoom-in; }
.lightbox { display: none; position: fixed; inset: 0; background: rgba(0,0,0,.85); z-index: 1000; align-items: center; justify-content: center; backdrop-filter: blur(6px); }
.lightbox.active { display: flex; }
.lightbox img { max-width: 90vw; max-height: 90vh; border-radius: 10px; box-shadow: 0 24px 80px rgba(0,0,0,.6); object-fit: contain; }
.lightbox-close { position: fixed; top: 20px; right: 24px; font-size: 2rem; color: #fff; cursor: pointer; line-height: 1; opacity: .7; transition: opacity .15s; }
.lightbox-close:hover { opacity: 1; }
"""


def _img_to_base64(path: str) -> str:
    if not path or not os.path.exists(path):
        return ""
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode()


def _fmt_dt(raw: str) -> tuple[str, str]:
    """Returns (date_str, time_str) formatted for display."""
    try:
        dt = datetime.fromisoformat(raw)
        return dt.strftime("%d.%m.%Y"), dt.strftime("%H:%M")
    except Exception:
        return raw[:10], ""


def _photo_card(photo: dict, label: str, badge_class: str) -> str:
    thumb_b64 = _img_to_base64(photo.get("thumb_path", ""))
    full_b64  = _img_to_base64(photo.get("full_path", "")) or thumb_b64
    img_tag = (
        '<img src="data:image/jpeg;base64,' + thumb_b64 + '"'
        + ' data-full="data:image/jpeg;base64,' + full_b64 + '" alt="фото">'
        if thumb_b64 else '<div class="no-img">нет превью</div>'
    )
    date_str, time_str = _fmt_dt(photo.get("date", ""))
    sender = photo.get("sender_name", "") or "Неизвестен"
    dt_label = date_str + (" в " + time_str if time_str else "")
    return (
        '<div class="card">'
        + img_tag
        + '<div class="meta">'
        + '<span class="badge ' + badge_class + '">' + label + '</span>'
        + '<div class="meta-sender">&#128100; ' + sender + '</div>'
        + '<div class="meta-dt">&#128197; ' + dt_label + '</div>'
        + '</div></div>'
    )


def _pair_html_exact(a: dict, b: dict) -> str:
    return (
        '<div class="pair">'
        + _photo_card(a, "Оригинал", "badge-exact")
        + _photo_card(b, "Дубликат", "badge-exact")
        + '</div>\n'
    )


def _pair_html_similar(a: dict, b: dict, dist: int, cross: bool) -> str:
    badge = "badge-cross" if cross else "badge-similar"
    return (
        '<div class="pair">'
        + _photo_card(a, "Фото 1", badge)
        + '<div class="dist">расстояние<br><b>' + str(dist) + '</b></div>'
        + _photo_card(b, "Фото 2", badge)
        + '</div>\n'
    )


def _is_cross(a: dict, b: dict) -> bool:
    return a.get("group_id") != b.get("group_id")


def _section_html(pairs_html: str, group_name: str, cross: bool = False) -> str:
    tag_class = "group-tag cross" if cross else "group-tag"
    icon = "↔️" if cross else "📁"
    return (
        '<div class="group-section">'
        + '<div class="' + tag_class + '">' + icon + ' ' + group_name + '</div>\n'
        + pairs_html
        + '</div>\n'
    )


def generate_report(
    exact_pairs: list[tuple[dict, dict]],
    similar_pairs: list[tuple[dict, dict, int]],
    total_photos: int = 0,
) -> str:
    now = datetime.now()
    report_name = "report_" + now.strftime("%Y-%m-%d_%H-%M") + ".html"
    report_path = str(Path(config.REPORTS_DIR) / report_name)
    Path(config.REPORTS_DIR).mkdir(parents=True, exist_ok=True)

    # ── Точные дубликаты по группам ──────────────────────────────────
    exact_by_group: dict[str, str] = {}
    exact_cross_html = ""
    for a, b in exact_pairs:
        html = _pair_html_exact(a, b)
        if _is_cross(a, b):
            exact_cross_html += html
        else:
            key = a.get("group_name", "Неизвестная группа")
            exact_by_group[key] = exact_by_group.get(key, "") + html

    exact_html = ""
    for gname, pairs_html in exact_by_group.items():
        exact_html += _section_html(pairs_html, gname)
    if exact_cross_html:
        exact_html += _section_html(exact_cross_html, "Между группами", cross=True)
    if not exact_html:
        exact_html = '<p class="empty">Точных дубликатов не найдено.</p>'

    # ── Похожие пары по группам ───────────────────────────────────────
    similar_by_group: dict[str, list] = {}
    similar_cross: list = []
    for a, b, dist in sorted(similar_pairs, key=lambda x: x[2]):
        if _is_cross(a, b):
            similar_cross.append((a, b, dist))
        else:
            key = a.get("group_name", "Неизвестная группа")
            similar_by_group.setdefault(key, []).append((a, b, dist))

    similar_html = ""
    for gname, items in similar_by_group.items():
        pairs_html = "".join(_pair_html_similar(a, b, d, False) for a, b, d in items)
        similar_html += _section_html(pairs_html, gname)
    if similar_cross:
        pairs_html = "".join(_pair_html_similar(a, b, d, True) for a, b, d in similar_cross)
        similar_html += _section_html(pairs_html, "Между группами", cross=True)
    if not similar_html:
        similar_html = '<p class="empty">Похожих фото не найдено.</p>'

    n_exact = len(exact_pairs)
    n_similar = len(similar_pairs)
    n_total = n_exact + n_similar
    date_str = now.strftime("%d.%m.%Y в %H:%M")
    threshold = str(config.PHASH_THRESHOLD)

    html = (
        '<!DOCTYPE html>\n<html lang="ru">\n<head>\n'
        '<meta charset="UTF-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
        '<title>Отчёт дубликатов — ' + now.strftime("%d.%m.%Y %H:%M") + '</title>\n'
        '<style>\n' + CSS + '</style>\n'
        '</head>\n<body>\n'
        '<h1>Отчёт по дубликатам фотографий</h1>\n'
        '<p class="subtitle">Сформирован: ' + date_str + '</p>\n'
        '<div class="summary">'
        '<div class="stat"><div class="stat-num">' + str(total_photos) + '</div><div class="stat-label">Фото проверено</div></div>'
        '<div class="stat" style="border-left:1px solid #e5e5ea;padding-left:24px">'
        '<div class="stat-num">' + str(n_exact) + '</div><div class="stat-label">Точных дубликатов</div></div>'
        '<div class="stat"><div class="stat-num">' + str(n_similar) + '</div><div class="stat-label">Похожих пар</div></div>'
        '<div class="stat"><div class="stat-num">' + str(n_total) + '</div><div class="stat-label">Всего находок</div></div>'
        '</div>\n'
        '<h2>Точные дубликаты (одинаковый файл)</h2>\n' + exact_html + '\n'
        '<h2>Похожие фото (perceptual hash, порог ' + threshold + ')</h2>\n' + similar_html + '\n'
        '<div class="lightbox" id="lb" onclick="closeLb(event)">'
        '<span class="lightbox-close" onclick="document.getElementById(\'lb\').classList.remove(\'active\')">&times;</span>'
        '<img id="lb-img" src="" alt="">'
        '</div>\n'
        '<script>\n'
        'document.querySelectorAll(".card img").forEach(img => {\n'
        '  img.addEventListener("click", () => {\n'
        '    document.getElementById("lb-img").src = img.dataset.full || img.src;\n'
        '    document.getElementById("lb").classList.add("active");\n'
        '  });\n'
        '});\n'
        'function closeLb(e) { if (e.target.id === "lb") document.getElementById("lb").classList.remove("active"); }\n'
        'document.addEventListener("keydown", e => { if (e.key === "Escape") document.getElementById("lb").classList.remove("active"); });\n'
        '</script>\n'
        '</body>\n</html>'
    )

    with open(report_path, "w", encoding="utf-8") as f:
        f.write(html)

    return report_path
