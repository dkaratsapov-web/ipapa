"""Понятные характеристики: значения из реальных инфобоксов Википедии."""
from services.specs_format import humanize, pick_for_model


def h(label, raw, name):
    out = dict(humanize([[label, raw]], name))
    return out.get(label)


def test_pick_for_model():
    raw = "Pro: 206 g; Pro Max: 233 g"
    assert pick_for_model(raw, "iPhone 17 Pro") == "206 g"
    assert pick_for_model(raw, "iPhone 17 Pro Max") == "233 g"
    assert pick_for_model("A3: 2/3/4/6 GB; POCO C61: 4/6 GB; A3x: 3/4 GB", "Redmi A3 Pro") == "2/3/4/6 GB"
    assert pick_for_model("IP64 rating (Note 60); IP54 rating (Note 60x)", "Realme Note 60X") == "IP54 rating"
    assert pick_for_model("Kirin 9020 (Mate 80); Kirin 9030 (Mate 80 Pro, 12GB)", "Huawei Mate 80 Pro") == "Kirin 9030"


def test_display():
    raw = ("Pro: 6.3 in pixel resolution at 460 ppi; Pro Max: 6.9 in pixel resolution at 460 ppi; "
           "ProMotion technology with adaptive refresh rates up to 120 Hz; Always-On display at 1 Hz")
    assert h("Экран", raw, "iPhone 17 Pro Max") == "6,9″, 120 Гц"
    assert h("Экран", "6.7 in; 1080 x 2340 px resolution; Super AMOLED, 90Hz, 800 nits (HBM)", "Galaxy A17") \
        == "6,7″ Super AMOLED, 90 Гц, 2340×1080"
    assert h("Экран", "All models: 720p, 1080p, 4K", "PlayStation 5 Pro") is None   # не экран — убираем


def test_fields():
    assert h("Процессор", "Qualcomm SM8735; Snapdragon 8s Gen 4", "Nothing Phone 3") == "Snapdragon 8s Gen 4"
    assert h("Процессор", "A19 Pro", "iPhone 17 Pro") == "Apple A19 Pro"
    assert h("Оперативная память", "6 / 8 and 12GB RAM", "Galaxy A36") == "6/8/12 ГБ"
    assert h("Основная камера", "Fusion Main: 48 MP, 1.78; Fusion Ultrawide: 48 MP; Telephoto: 48 MP; Video 4K", "iPhone 17 Pro") \
        == "48 + 48 + 48 Мп"
    assert h("Основная камера", "Triple: 50+50+50 MP", "Nothing Phone 3") == "50 + 50 + 50 Мп"
    assert h("Аккумулятор", "3,300 mAh Li-Ion", "OnePlus") == "3300 мА·ч"
    assert h("Зарядка", "Fast charging 30 W; Wireless MagSafe charging 25 W", "iPhone 17e") == "до 30 Вт, беспроводная 25 Вт"
    assert h("Зарядка", "65W wired, 15W wireless, 7.5W reverse charging", "Nothing Phone 3") == "до 65 Вт, беспроводная 15 Вт"
    assert h("Влагозащита", "IP68: dust and water resistant", "x") == "IP68"
    assert h("ОС", "Original: OxygenOS 11 (based on Android 11); Current: OxygenOS 12 (based on Android 12)", "x") \
        == "Android 12 (OxygenOS 12)"
    assert h("Размеры", "162.9 x 78.2 x 7.4 mm (6.41 x 3.08 x 0.29 in)", "x") == "162,9 × 78,2 × 7,4 мм"
    assert h("Вес", "4G: 190 g; 5G: 192 g", "Samsung Galaxy A17") == "190 г"            # «4G» — не 4 грамма
    assert h("Дата выхода", "November 25, 2025", "x") == "25.11.2025"
    assert h("Дата выхода", "11 June 2025", "x") == "11.06.2025"
