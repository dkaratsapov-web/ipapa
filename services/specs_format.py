"""Характеристики из Википедии -> коротко и по-русски для карточки товара.

В инфобоксах статей часто перечислены сразу несколько моделей серии
(«Pro: 6.3 in …; Pro Max: 6.9 in …») и много технических подробностей.
Здесь выбираем значение для своей модели и оставляем главное:
«6,9″ Super Retina XDR OLED, 120 Гц», «48 + 48 + 48 Мп», «5000 мА·ч».
"""
from __future__ import annotations

import re
from typing import Callable

_TOKEN = re.compile(r"[a-zа-я]+|\d+", re.I)
_MONTHS = {m: i for i, m in enumerate(
    ["january", "february", "march", "april", "may", "june", "july", "august", "september",
     "october", "november", "december"], 1)}
_MONTHS.update({m[:3]: i for m, i in list(_MONTHS.items())})


def _tokens(text: str) -> set[str]:
    text = re.sub(r"\d+\s*(gb|гб|tb|тб)\b", " ", text.lower())  # «12GB» — не часть названия модели
    return set(_TOKEN.findall(text))


def _num(value: str) -> str:
    """Число по-русски: 6.9 -> 6,9; 5,000 -> 5000."""
    value = value.replace(",", "") if re.fullmatch(r"\d{1,3}(,\d{3})+", value) else value
    return value.replace(".", ",")


def pick_for_model(raw: str, model_name: str, keep_common: bool = False) -> str:
    """Из «Pro: X; Pro Max: Y; общее» — значение для своей модели.

    keep_common — добавить общие для серии части (нужно экрану: частота часто указана отдельно).
    """
    name = _tokens(model_name)
    segments = [s.strip() for s in re.split(r"[;；]", raw) if s.strip()]
    best: tuple[int, str] | None = None
    common: list[str] = []
    for seg in segments:
        label, text = None, seg
        m = re.match(r"^([^:：]{1,40})[:：]\s*(.+)$", seg)
        if m:
            label, text = m[1], m[2]
        else:
            m = re.match(r"^(.+?)\s*\(([^()]{1,40})\)\s*$", seg)  # «Kirin 9030 (Mate 80 Pro, 12GB)»
            if m:
                text, label = m[1], m[2]
        if label is None:
            common.append(seg)
            continue
        lt = _tokens(label)
        if lt and lt <= name:  # подпись целиком из слов нашей модели
            if best is None or len(lt) > best[0]:
                best = (len(lt), text)
        elif lt & name:
            continue  # другая модель серии
        else:
            common.append(seg)  # подпись поля («Type: OLED»), не модели
    if best:
        return "; ".join([best[1], *common]) if keep_common else best[1]
    return "; ".join(common) if common else raw


# ---------- поля ----------

_PANELS = ["Super Retina XDR OLED", "Super Retina XDR", "Liquid Retina XDR", "Liquid Retina", "Retina",
           "Dynamic LTPO AMOLED 2X", "Dynamic AMOLED 2X", "Dynamic AMOLED", "Super AMOLED", "Optic AMOLED",
           "LTPO OLED", "AMOLED", "P-OLED", "pOLED", "OLED", "Mini-LED", "LTPS IPS LCD", "IPS LCD", "PLS LCD",
           "LCD", "E-ink"]


def fmt_display(v: str) -> str | None:
    size = re.search(r"(\d{1,2}(?:[.,]\d{1,2})?)\s*(?:-?\s*inch(?:es)?|in\b|″|\"|”)", v, re.I)
    panel = next((p for p in _PANELS if re.search(re.escape(p), v, re.I)), None)
    hz = [int(x) for x in re.findall(r"(\d{2,3})\s*Hz", v, re.I) if 50 <= int(x) <= 240]
    res = re.search(r"(\d{3,4})\s*[×xX]\s*(\d{3,4})", v)
    if not size and not panel:
        return None
    parts = []
    if size:
        parts.append(f"{_num(size[1])}″")
    if panel:
        parts.append(panel)
    head = " ".join(parts)
    tail = []
    if hz and max(hz) > 60:
        tail.append(f"{max(hz)} Гц")
    if res:
        a, b = sorted((int(res[1]), int(res[2])), reverse=True)
        tail.append(f"{a}×{b}")
    return ", ".join([head, *tail])


_CHIP = re.compile(
    r"(?:Apple\s+)?(?:A\d{2}(?:\s+(?:Pro|Bionic))?|M\d(?:\s+(?:Pro|Max|Ultra))?)\b"
    r"|(?:Qualcomm\s+)?Snapdragon\s+[\w+ ]+?(?=\s*(?:\(|,|;|$))"
    r"|(?:MediaTek\s+)?(?:Dimensity|Helio)\s+[\w+ ]+?(?=\s*(?:\(|,|;|$))"
    r"|(?:Samsung\s+)?Exynos\s+\w+|(?:Google\s+)?Tensor\s*G?\d*|(?:HiSilicon\s+)?Kirin\s+\w+"
    r"|Unisoc\s+[\w ]+?(?=\s*(?:\(|,|;|$))|Tiger\s+T\d+",
    re.I,
)


def fmt_chip(v: str) -> str | None:
    m = _CHIP.search(v)
    if m:
        chip = re.sub(r"\s+", " ", m[0]).strip()
        return chip if not re.fullmatch(r"A\d{2}.*", chip) else f"Apple {chip}"
    first = re.sub(r"\([^)]*\)", "", v.split(";")[0]).strip(" ,")
    return first[:40] or None


def fmt_ram(v: str) -> str | None:
    v = re.sub(r"LPDDR\w*", " ", v, flags=re.I)
    nums = sorted({int(x) for x in re.findall(r"\d+", v) if 1 <= int(x) <= 32})
    if not nums:
        return None
    return "/".join(map(str, nums)) + " ГБ"


def fmt_camera(v: str) -> str | None:
    v = re.split(r"\bvideo\b", v, flags=re.I)[0]
    mp = re.findall(r"(\d{1,3}(?:\.\d)?)\s*(?=MP|Мп|\+\s*\d)", v, re.I)
    mp = [x for x in mp if 1 <= float(x) <= 300][:4]
    if not mp:
        return None
    return " + ".join(_num(x) for x in mp) + " Мп"


def fmt_front(v: str) -> str | None:
    m = re.search(r"(\d{1,3}(?:\.\d)?)\s*MP", v, re.I)
    return f"{_num(m[1])} Мп" if m else None


def fmt_battery(v: str) -> str | None:
    m = re.search(r"(\d{1,2}[,\s]?\d{3})\s*mAh", v, re.I)
    if m:
        mah = re.sub(r"[,\s]", "", m[1])
        return f"{mah} мА·ч"
    m = re.search(r"(\d+(?:\.\d+)?)\s*W\s?h\b", v, re.I)
    if m:
        return f"{_num(m[1])} Вт·ч"
    m = re.search(r"(?:up to\s+)?(\d{1,3})\s*hours?", v, re.I)
    return f"до {m[1]} ч работы" if m else None


def fmt_charging(v: str) -> str | None:
    wired, wireless = [], []
    for part in re.split(r"[;,/]", v):
        low = part.lower()
        if "reverse" in low:
            continue
        is_wireless = bool(re.search(r"wireless|magsafe|qi\b", low)) and "wired" not in low.replace("wireless", "")
        for m in re.finditer(r"(\d+(?:\.\d+)?)\s*W\b", part):
            if 5 <= float(m[1]) <= 240:
                (wireless if is_wireless else wired).append(float(m[1]))
    parts = []
    if wired:
        parts.append(f"до {_num(f'{max(wired):g}')} Вт")
    if wireless:
        parts.append(f"беспроводная {_num(f'{max(wireless):g}')} Вт")
    if parts:
        return ", ".join(parts)
    return "MagSafe" if "magsafe" in v.lower() else None


def fmt_water(v: str) -> str | None:
    m = re.search(r"\bIP[X\d]\d\b", v, re.I)
    return m[0].upper() if m else None


_OS = r"(iOS|iPadOS|watchOS|macOS|tvOS|visionOS|Android|HarmonyOS|Harmony OS|Wear OS)"
_SHELL = r"(One UI|HyperOS|MIUI|OxygenOS|ColorOS|Realme UI|Nothing OS|EMUI|MagicOS|Funtouch OS|OriginOS|HiOS|XOS)"


def fmt_os(v: str) -> str | None:
    cur = re.search(r"current[^:]*:\s*([^;]+)", v, re.I)
    text = cur[1] if cur else v
    os_ = re.search(_OS + r"\s*([\d.]+)?", text, re.I)
    shell = re.search(_SHELL + r"\s*([\d.]+)?", text, re.I)
    if os_:
        out = f"{os_[1]} {os_[2] or ''}".strip()
        if shell:
            out += f" ({shell[1]} {shell[2] or ''})".replace(" )", ")")
        return out.replace("Harmony OS", "HarmonyOS")
    if shell:
        return f"{shell[1]} {shell[2] or ''}".strip()
    return None


def fmt_size(v: str) -> str | None:
    if "mm" not in v.lower():
        return None
    v = re.split(r"\(", v)[0] if re.search(r"\d\s*mm", v.split("(")[0], re.I) else v
    nums = re.findall(r"\d+(?:\.\d+)?", v)
    if len(nums) < 3:
        return None
    return " × ".join(_num(n) for n in nums[:3]) + " мм"


def fmt_weight(v: str) -> str | None:
    m = re.search(r"(?<![\w.])(\d{2,4}(?:\.\d)?)\s*(?:g|grams)\b", v, re.I)
    if m:
        return f"{_num(m[1])} г"
    m = re.search(r"(\d+(?:\.\d+)?)\s*kg\b", v, re.I)
    return f"{_num(m[1])} кг" if m else None


def fmt_date(v: str) -> str | None:
    m = re.search(r"\b(\d{2})\.(\d{2})\.(\d{4})\b", v)
    if m:
        return m[0]
    m = re.search(r"\b([A-Za-z]{3,9})\s+(\d{1,2}),?\s+(\d{4})", v) or None
    if m and m[1].lower() in _MONTHS:
        return f"{int(m[2]):02d}.{_MONTHS[m[1].lower()]:02d}.{m[3]}"
    m = re.search(r"\b(\d{1,2})\s+([A-Za-z]{3,9})\s+(\d{4})", v)
    if m and m[2].lower() in _MONTHS:
        return f"{int(m[1]):02d}.{_MONTHS[m[2].lower()]:02d}.{m[3]}"
    m = re.search(r"\b([A-Za-z]{3,9})\s+(\d{4})", v)
    if m and m[1].lower() in _MONTHS:
        return f"{_MONTHS[m[1].lower()]:02d}.{m[2]}"
    m = re.search(r"\b(20\d{2}|19\d{2})\b", v)
    return m[1] if m else None


FORMATTERS: dict[str, Callable[[str], str | None]] = {
    "Экран": fmt_display,
    "Процессор": fmt_chip,
    "Оперативная память": fmt_ram,
    "Основная камера": fmt_camera,
    "Фронтальная камера": fmt_front,
    "Аккумулятор": fmt_battery,
    "Зарядка": fmt_charging,
    "Влагозащита": fmt_water,
    "ОС": fmt_os,
    "Размеры": fmt_size,
    "Вес": fmt_weight,
    "Дата выхода": fmt_date,
}


def humanize(specs: list[list[str]], model_name: str) -> list[list[str]]:
    """Понятные характеристики для своей модели; непонятные значения отбрасываем."""
    out = []
    for label, raw in specs:
        fmt = FORMATTERS.get(label)
        if not fmt:
            continue
        value = fmt(pick_for_model(raw, model_name, keep_common=label == "Экран"))
        if value:
            out.append([label, value])
    return out
