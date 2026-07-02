from __future__ import annotations

from mecateca.contexts.duels.elo import K, expected, update


def test_equal_ratings_win_is_half_k():
    na, nb = update(1000, 1000, 1.0)
    assert na == 1016 and nb == 984


def test_equal_ratings_draw_changes_nothing():
    na, nb = update(1000, 1000, 0.5)
    assert na == 1000 and nb == 1000


def test_underdog_win_gains_more_than_favourite_win():
    underdog_gain = update(1000, 1400, 1.0)[0] - 1000
    favourite_gain = update(1400, 1000, 1.0)[0] - 1400
    assert underdog_gain > favourite_gain
    assert underdog_gain <= K


def test_rating_total_is_conserved():
    for ra, rb, s in [(1000, 1200, 1.0), (900, 1500, 0.0), (1100, 1100, 0.5)]:
        na, nb = update(ra, rb, s)
        assert na + nb == ra + rb


def test_expected_is_symmetric():
    assert abs(expected(1200, 1000) + expected(1000, 1200) - 1.0) < 1e-9
