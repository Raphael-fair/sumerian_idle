# --- Responsive Layout ---
def viewport_layout(width_dp, height_dp, gui):
    rules = gui["responsive"]
    narrow = width_dp < rules["single_column_below_dp"]
    compact = width_dp < rules["compact_navigation_below_dp"]
    short = height_dp < rules["small_screen_below_dp"]
    return {
        "columns": 1 if narrow else 2,
        "navigation": rules["compact_page_names"] if compact else rules["wide_page_names"],
        "header_dp": rules["small_screen_header_dp"] if short else gui["header_height_dp"],
        "footer_dp": rules["small_screen_footer_dp"] if short else gui["footer_height_dp"],
        "scene_dp": rules["small_screen_scene_dp"] if short else None,
        "title_size_dp": rules["small_screen_title_size_dp"] if short else gui["font_size"]["title"],
    }
