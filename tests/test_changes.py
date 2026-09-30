from services.sync import Change, State, SyncError, check_counts, detect_change

import pytest


def test_new_item_is_not_a_change():
    assert detect_change(1, None, State(100, True)) is None


def test_no_change():
    assert detect_change(1, State(100, True), State(100, True)) is None


def test_price_change():
    ch = detect_change(1, State(11990000, True), State(11490000, True))
    assert ch == Change(1, 11990000, 11490000, True, True)
    assert ch.price_changed and not ch.stock_changed


def test_stock_change():
    ch = detect_change(1, State(100, False), State(100, True))
    assert ch and ch.stock_changed and not ch.price_changed


@pytest.mark.parametrize("old, new", [(0, 100), (100, 0), (0, 0)])
def test_price_on_request_ignored(old, new):
    assert detect_change(1, State(old, True), State(new, True)) is None


def test_price_on_request_with_stock_change_is_stock_only():
    ch = detect_change(1, State(0, False), State(100, True))
    assert ch and ch.stock_changed and not ch.price_changed


def test_check_counts():
    check_counts(100, 200, None, None)          # первая синхронизация
    check_counts(60, 120, 100, 200)             # ровно выше порога
    with pytest.raises(SyncError):
        check_counts(0, 0, None, None)          # пустой ответ
    with pytest.raises(SyncError):
        check_counts(49, 200, 100, 200)         # товаров < 50%
    with pytest.raises(SyncError):
        check_counts(100, 99, 100, 200)         # вариантов < 50%
