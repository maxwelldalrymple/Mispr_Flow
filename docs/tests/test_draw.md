# `tests/test_draw.py`

47 tests. Source: [`tests/test_draw.py`](../../tests/test_draw.py).


## (module)

- `test_primitive_matches_golden_image`: primitive matches golden image

## TestRect

- `test_centered_places_center`: centered places center
- `test_centered_zero_size`: centered zero size
- `test_derived_edges`: derived edges
- `test_contains_inside_and_edges`: contains inside and edges
- `test_contains_outside`: contains outside
- `test_inset_shrinks_symmetrically`: inset shrinks symmetrically
- `test_negative_inset_grows`: negative inset grows
- `test_inset_keeps_center`: inset keeps center
- `test_union_of_disjoint`: union of disjoint
- `test_union_of_overlapping`: union of overlapping
- `test_union_with_contained_is_outer`: union with contained is outer
- `test_union_with_nonzero_origins`: union with nonzero origins
- `test_union_with_negative_origins`: union with negative origins
- `test_union_is_commutative`: union is commutative
- `test_ns_rect_matches`: ns rect matches
- `test_is_immutable`: is immutable
- `test_hashable_and_equal_by_value`: hashable and equal by value

## TestColors

- `test_white_components`: white components
- `test_white_clamps_alpha`: white clamps alpha
- `test_srgb_components`: srgb components
- `test_srgb_clamps_alpha`: srgb clamps alpha

## TestRich

- `test_concatenates_parts`: concatenates parts
- `test_empty_parts`: empty parts
- `test_bold_part_uses_bold_weight`: bold part uses bold weight
- `test_size_grows_with_text`: size grows with text
- `test_font_size_applied`: font size applied

## TestDrawing

- `test_fill_round_paints_inside_only`: fill round paints inside only
- `test_fill_circle_paints_center_not_corner`: fill circle paints center not corner
- `test_stroke_round_leaves_center_empty`: stroke round leaves center empty
- `test_stroke_circle_leaves_center_empty`: stroke circle leaves center empty
- `test_bars_full_level_draws_tall_bar`: bars full level draws tall bar
- `test_bars_silence_draws_only_a_dot`: bars silence draws only a dot
- `test_bars_are_centered_and_spaced`: bars are centered and spaced
- `test_bars_empty_levels_is_noop`: bars empty levels is noop
- `test_spinner_draws_around_center`: spinner draws around center
- `test_spinner_zero_alpha_draws_nothing`: spinner zero alpha draws nothing
- `test_symbol_draws_known_icon`: symbol draws known icon
- `test_symbol_unknown_name_is_ignored`: symbol unknown name is ignored
- `test_symbol_is_cached`: symbol is cached
- `test_symbol_alpha_zero_draws_nothing`: symbol alpha zero draws nothing
- `test_draw_text_centered_is_centered`: draw text centered is centered
- `test_draw_text_left_starts_at_x`: draw text left starts at x

## TestDrawingDetails

Details too small for the golden-image tolerance, checked with targeted pixels.

- `test_lines_have_round_caps`: lines have round caps
- `test_polylines_have_round_joins`: polylines have round joins
- `test_spinner_fades_from_20_to_90_percent`: spinner fades from 20 to 90 percent
- `test_bars_are_fully_rounded`: bars are fully rounded
