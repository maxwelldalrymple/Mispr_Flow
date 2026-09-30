import dataclasses

import pytest
from AppKit import NSFontAttributeName, NSFontWeightSemibold

from whispr import draw
from whispr.draw import Rect, srgb, white


# --- Rect ---------------------------------------------------------------------

class TestRect:
    def test_centered_places_center(self):
        r = Rect.centered(100, 50, 40, 20)
        assert (r.x, r.y, r.w, r.h) == (80, 40, 40, 20)
        assert (r.cx, r.cy) == (100, 50)

    def test_centered_zero_size(self):
        r = Rect.centered(10, 10, 0, 0)
        assert (r.x, r.y, r.w, r.h) == (10, 10, 0, 0)

    def test_derived_edges(self):
        r = Rect(10, 20, 30, 40)
        assert r.right == 40
        assert r.top == 60
        assert r.cx == 25
        assert r.cy == 40

    @pytest.mark.parametrize("px,py", [(10, 20), (40, 60), (25, 40), (10, 60), (40, 20)])
    def test_contains_inside_and_edges(self, px, py):
        assert Rect(10, 20, 30, 40).contains(px, py)

    @pytest.mark.parametrize("px,py", [(9.9, 30), (40.1, 30), (25, 19.9), (25, 60.1), (-5, -5)])
    def test_contains_outside(self, px, py):
        assert not Rect(10, 20, 30, 40).contains(px, py)

    def test_inset_shrinks_symmetrically(self):
        assert Rect(0, 0, 100, 50).inset(10) == Rect(10, 10, 80, 30)

    def test_negative_inset_grows(self):
        assert Rect(10, 10, 20, 20).inset(-5) == Rect(5, 5, 30, 30)

    def test_inset_keeps_center(self):
        r = Rect.centered(50, 60, 40, 30)
        assert (r.inset(7).cx, r.inset(7).cy) == (50, 60)

    def test_union_of_disjoint(self):
        assert Rect(0, 0, 10, 10).union(Rect(20, 30, 5, 5)) == Rect(0, 0, 25, 35)

    def test_union_of_overlapping(self):
        assert Rect(0, 0, 10, 10).union(Rect(5, 5, 10, 10)) == Rect(0, 0, 15, 15)

    def test_union_with_contained_is_outer(self):
        outer, inner = Rect(0, 0, 100, 100), Rect(10, 10, 5, 5)
        assert outer.union(inner) == outer
        assert inner.union(outer) == outer

    def test_union_is_commutative(self):
        a, b = Rect(-5, 3, 10, 2), Rect(7, -8, 4, 20)
        assert a.union(b) == b.union(a)

    def test_ns_rect_matches(self):
        ns = Rect(1.5, 2.5, 3.5, 4.5).ns()
        assert (ns.origin.x, ns.origin.y, ns.size.width, ns.size.height) == (1.5, 2.5, 3.5, 4.5)

    def test_is_immutable(self):
        with pytest.raises(dataclasses.FrozenInstanceError):
            Rect(0, 0, 1, 1).x = 5

    def test_hashable_and_equal_by_value(self):
        assert Rect(1, 2, 3, 4) == Rect(1, 2, 3, 4)
        assert len({Rect(1, 2, 3, 4), Rect(1, 2, 3, 4)}) == 1


# --- Colours --------------------------------------------------------------------

class TestColors:
    def test_white_components(self):
        c = white(0.25, 0.5)
        assert c.whiteComponent() == pytest.approx(0.25)
        assert c.alphaComponent() == pytest.approx(0.5)

    @pytest.mark.parametrize("alpha,expected", [(-1.0, 0.0), (0.0, 0.0), (0.4, 0.4), (1.0, 1.0), (3.0, 1.0)])
    def test_white_clamps_alpha(self, alpha, expected):
        assert white(1.0, alpha).alphaComponent() == pytest.approx(expected)

    def test_srgb_components(self):
        c = srgb(0.1, 0.2, 0.3, 0.9)
        assert (c.redComponent(), c.greenComponent(), c.blueComponent()) == pytest.approx((0.1, 0.2, 0.3), abs=1e-6)
        assert c.alphaComponent() == pytest.approx(0.9)

    @pytest.mark.parametrize("alpha,expected", [(-0.5, 0.0), (1.5, 1.0)])
    def test_srgb_clamps_alpha(self, alpha, expected):
        assert srgb(1, 1, 1, alpha).alphaComponent() == pytest.approx(expected)


# --- Text -------------------------------------------------------------------------

class TestRich:
    def test_concatenates_parts(self):
        s = draw.rich([("Press ", False), ("fn", True), (" to paste", False)], 13, white(1, 1))
        assert s.string() == "Press fn to paste"

    def test_empty_parts(self):
        assert draw.rich([], 13, white(1, 1)).string() == ""

    def test_bold_part_uses_bold_weight(self):
        s = draw.rich([("a", False), ("b", True)], 13, white(1, 1))
        regular = s.attribute_atIndex_effectiveRange_(NSFontAttributeName, 0, None)[0]
        bold = s.attribute_atIndex_effectiveRange_(NSFontAttributeName, 1, None)[0]
        assert regular.pointSize() == bold.pointSize() == 13
        assert regular.fontName() != bold.fontName()
        # Same text with an explicit semibold font must match the bold part.
        explicit = draw.rich([("b", True)], 13, white(1, 1), bold_weight=NSFontWeightSemibold)
        assert explicit.attribute_atIndex_effectiveRange_(NSFontAttributeName, 0, None)[0].fontName() == bold.fontName()

    def test_size_grows_with_text(self):
        short = draw.rich([("a", False)], 13, white(1, 1)).size()
        long = draw.rich([("aaaaaaaaaa", False)], 13, white(1, 1)).size()
        assert long.width > short.width > 0

    def test_font_size_applied(self):
        s = draw.rich([("x", False)], 21, white(1, 1))
        assert s.attribute_atIndex_effectiveRange_(NSFontAttributeName, 0, None)[0].pointSize() == 21


# --- Drawing into a real bitmap ---------------------------------------------------------

class TestDrawing:
    def test_fill_round_paints_inside_only(self, bitmap_context):
        draw.fill_round(Rect(20, 20, 60, 40), 8, white(1.0, 1.0))
        assert bitmap_context(50, 40)[3] == pytest.approx(1.0)
        assert bitmap_context(150, 40)[3] == pytest.approx(0.0)

    def test_fill_circle_paints_center_not_corner(self, bitmap_context):
        draw.fill_circle(50, 50, 20, white(1.0, 1.0))
        assert bitmap_context(50, 50)[3] == pytest.approx(1.0)
        assert bitmap_context(32, 32)[3] == pytest.approx(0.0)  # inside bounding box, outside circle

    def test_stroke_round_leaves_center_empty(self, bitmap_context):
        draw.stroke_round(Rect(20, 20, 60, 40), 8, white(1.0, 1.0), 2.0)
        assert bitmap_context(50, 40)[3] == pytest.approx(0.0)
        assert bitmap_context(21, 40)[3] > 0.5  # on the stroke

    def test_stroke_circle_leaves_center_empty(self, bitmap_context):
        draw.stroke_circle(50, 50, 20, white(1.0, 1.0), 2.0)
        assert bitmap_context(50, 50)[3] == pytest.approx(0.0)
        assert bitmap_context(50, 70)[3] > 0.3

    def test_bars_full_level_draws_tall_bar(self, bitmap_context):
        draw.bars(100, 50, [1.0], 4, 2, 30, white(1.0, 1.0))
        assert bitmap_context(100, 50 + 12)[3] > 0.5

    def test_bars_silence_draws_only_a_dot(self, bitmap_context):
        draw.bars(100, 50, [0.0], 4, 2, 30, white(1.0, 1.0))
        assert bitmap_context(100, 50)[3] > 0.0
        assert bitmap_context(100, 50 + 12)[3] == pytest.approx(0.0)

    def test_bars_are_centered_and_spaced(self, bitmap_context):
        draw.bars(100, 50, [1.0, 1.0, 1.0], 10, 2, 30, white(1.0, 1.0))
        for x in (90, 100, 110):
            assert bitmap_context(x, 50)[3] > 0.5
        assert bitmap_context(95, 50)[3] == pytest.approx(0.0)

    def test_bars_empty_levels_is_noop(self, bitmap_context):
        draw.bars(100, 50, [], 4, 2, 30, white(1.0, 1.0))
        assert bitmap_context(100, 50)[3] == pytest.approx(0.0)

    def test_spinner_draws_around_center(self, bitmap_context):
        draw.spinner(100, 50, 10, 0.3, 1.0)
        assert bitmap_context(100, 50)[3] == pytest.approx(0.0)  # hollow middle
        assert any(bitmap_context(100 + dx, 50 + dy)[3] > 0.1 for dx, dy in ((9, 0), (0, 9), (-9, 0), (0, -9)))

    def test_spinner_zero_alpha_draws_nothing(self, bitmap_context):
        draw.spinner(100, 50, 10, 0.0, 0.0)
        assert bitmap_context(109, 50)[3] == pytest.approx(0.0)

    def test_symbol_draws_known_icon(self, bitmap_context):
        draw.symbol("stop.fill", 100, 50, 20)
        assert bitmap_context(100, 50)[3] > 0.5

    def test_symbol_unknown_name_is_ignored(self, bitmap_context):
        draw.symbol("definitely.not.a.real.symbol", 100, 50, 20)
        assert bitmap_context(100, 50)[3] == pytest.approx(0.0)

    def test_symbol_is_cached(self, bitmap_context):
        draw._symbol_cache.clear()
        draw.symbol("mic.fill", 100, 50, 15)
        draw.symbol("mic.fill", 100, 50, 15)
        assert len([k for k in draw._symbol_cache if k[0] == "mic.fill"]) == 1

    def test_symbol_alpha_zero_draws_nothing(self, bitmap_context):
        draw.symbol("stop.fill", 100, 50, 20, alpha=0.0)
        assert bitmap_context(100, 50)[3] == pytest.approx(0.0)

    def test_draw_text_centered_is_centered(self, bitmap_context):
        label = draw.rich([("MMMM", True)], 20, white(1.0, 1.0))
        draw.draw_text_centered(label, 100, 50)
        painted = [x for x in range(0, 200, 2) if bitmap_context(x, 50)[3] > 0.3]
        assert painted and abs((min(painted) + max(painted)) / 2 - 100) < 8

    def test_draw_text_left_starts_at_x(self, bitmap_context):
        label = draw.rich([("MMMM", True)], 20, white(1.0, 1.0))
        draw.draw_text_left(label, 30, 50)
        painted = [x for x in range(0, 200) if bitmap_context(x, 50)[3] > 0.3]
        assert painted and 28 <= min(painted) <= 40
