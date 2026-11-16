"""Generate a watermark-free 3D Isometric Contribution City SVG for GitHub profile README."""

from __future__ import annotations

import datetime as dt
import json
import math
import re
import time
import urllib.error
import urllib.request
from pathlib import Path

USERNAME = "amilasuranjith-dev"
TIMEZONE = "Asia/Colombo"
CONTRIB_API_URL = f"https://github-contributions-api.jogruber.de/v4/{USERNAME}?y=last"
STREAK_SVG_URL = (
    f"https://streak-stats.demolab.com/?user={USERNAME}"
    f"&theme=dark&hide_border=true&timezone=Asia%2FColombo"
)
ASSETS_DIR = Path(__file__).resolve().parent.parent / "assets"
OUTPUT_PATH = ASSETS_DIR / "contribution-city.svg"
STREAK_DARK_PATH = ASSETS_DIR / "streak-dark.svg"
STREAK_LIGHT_PATH = ASSETS_DIR / "streak-light.svg"

STREAK_THEMES = {
    "dark": {
        "stroke": "#FF7F00",
        "ring": "#FF7F00",
        "fire": "#FFA500",
        "curr_num": "#FEFEFE",
        "side_num": "#FEFEFE",
        "curr_label": "#FB8C00",
        "side_label": "#FEFEFE",
        "dates": "#9E9E9E",
    },
    "light": {
        "stroke": "#FF7F00",
        "ring": "#FF7F00",
        "fire": "#FFA500",
        "curr_num": "#FF7F00",
        "side_num": "#FF7F00",
        "curr_label": "#FF5C00",
        "side_label": "#FF5C00",
        "dates": "#555555",
    },
}

# Isometric grid geometry matching the 53x7 3D contribution city layout
ORIGIN_X = 67.8125
ORIGIN_Y = 41.42
STEP_X = 9.6875
STEP_Y = 5.5931
CUBE_SIZE = 8.72
BASE_HEIGHT = 2.6
MAX_HEIGHT = 74.18
MIN_ACTIVE_HEIGHT = 5.24
SCALE_Y = 1.15


def fetch_text(url: str, timeout: int = 15) -> str:
    """Fetch UTF-8 response body from a URL with a standard User-Agent."""
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "amilasuranjith-dev-profile-generator/1.0",
            "Accept": "application/json,image/svg+xml,*/*",
        },
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read().decode("utf-8", errors="replace")


def fetch_contributions() -> tuple[int, list[dict]]:
    """Fetch last-year contribution calendar entries from GitHub Contributions API."""
    payload = json.loads(fetch_text(CONTRIB_API_URL))
    total_obj = payload.get("total", {})
    year_total = int(total_obj.get("lastYear", 0))
    contributions = payload.get("contributions", [])
    if not contributions:
        raise ValueError("Contribution calendar API returned empty contributions list.")
    if year_total == 0:
        year_total = sum(int(day.get("count", 0)) for day in contributions)
    return year_total, contributions


def format_streak_range(start_iso: str, end_iso: str) -> str:
    """Format a streak date range matching M j[, Y] style (omitting year if same as current year)."""
    start_d = dt.date.fromisoformat(start_iso)
    end_d = dt.date.fromisoformat(end_iso)
    cur_year = end_d.year

    def fmt(d: dt.date) -> str:
        base = d.strftime("%b %d").replace(" 0", " ")
        return f"{base}, {d.year}" if d.year != cur_year else base

    return fmt(start_d) if start_d == end_d else f"{fmt(start_d)} - {fmt(end_d)}"


def compute_streaks_from_calendar(contributions: list[dict]) -> tuple[int, str, int, str]:
    """Compute current and longest streak lengths and date ranges from ordered calendar entries."""
    longest = 0
    longest_start = contributions[0]["date"]
    longest_end = contributions[0]["date"]

    running = 0
    run_start = ""
    for day in contributions:
        if int(day.get("count", 0)) > 0:
            if running == 0:
                run_start = day["date"]
            running += 1
            if running >= longest:
                longest = running
                longest_start = run_start
                longest_end = day["date"]
        else:
            running = 0

    current = 0
    idx = len(contributions) - 1
    if idx >= 0 and int(contributions[idx].get("count", 0)) == 0:
        idx -= 1
    cur_end = contributions[idx]["date"] if idx >= 0 else contributions[-1]["date"]
    cur_start = cur_end
    while idx >= 0 and int(contributions[idx].get("count", 0)) > 0:
        cur_start = contributions[idx]["date"]
        current += 1
        idx -= 1

    longest_range = format_streak_range(longest_start, longest_end) if longest > 0 else "N/A"
    current_range = format_streak_range(cur_start, cur_end) if current > 0 else "N/A"
    return current, current_range, longest, longest_range


def fetch_streak_stats(
    contributions: list[dict], year_total: int
) -> tuple[int, str, int, str, int, str]:
    """Fetch all-time total, current streak, and longest streak, cross-checked against calendar."""
    cal_current, cal_cur_range, cal_longest, cal_long_range = compute_streaks_from_calendar(contributions)
    first_d = dt.date.fromisoformat(contributions[0]["date"])
    best_total = year_total
    best_total_range = f"{first_d.strftime('%b %d').replace(' 0', ' ')}, {first_d.year} - Present"
    best_current = cal_current
    best_cur_range = cal_cur_range
    best_longest = cal_longest
    best_long_range = cal_long_range

    num_patterns = {
        "total": r"Total Contributions big number.*?>\s*([0-9,]+)\s*</text>",
        "current": r"Current Streak big number.*?>\s*([0-9,]+)\s*</text>",
        "longest": r"Longest Streak big number.*?>\s*([0-9,]+)\s*</text>",
    }
    range_patterns = {
        "total_range": r"Total Contributions range.*?>\s*([^<]+?)\s*</text>",
        "current_range": r"Current Streak range.*?>\s*([^<]+?)\s*</text>",
        "longest_range": r"Longest Streak range.*?>\s*([^<]+?)\s*</text>",
    }

    for attempt in range(3):
        try:
            url = f"{STREAK_SVG_URL}&_cb={int(time.time())}-{attempt}"
            svg_text = fetch_text(url, timeout=15)
            numbers: dict[str, int] = {}
            ranges: dict[str, str] = {}
            for key, pattern in num_patterns.items():
                match = re.search(pattern, svg_text, re.DOTALL)
                if match:
                    numbers[key] = int(match.group(1).replace(",", ""))
            for key, pattern in range_patterns.items():
                match = re.search(pattern, svg_text, re.DOTALL)
                if match:
                    ranges[key] = match.group(1).strip()

            if len(numbers) == 3:
                if numbers["total"] > best_total:
                    best_total = numbers["total"]
                    if "total_range" in ranges:
                        best_total_range = ranges["total_range"]
                if numbers["current"] > best_current:
                    best_current = numbers["current"]
                    if "current_range" in ranges:
                        best_cur_range = ranges["current_range"]
                if numbers["longest"] > best_longest:
                    best_longest = numbers["longest"]
                    if "longest_range" in ranges:
                        best_long_range = ranges["longest_range"]
                if numbers["current"] >= cal_current and numbers["total"] >= year_total:
                    break
        except (urllib.error.URLError, TimeoutError, ValueError):
            continue

    return (
        best_total,
        best_total_range,
        best_current,
        best_cur_range,
        best_longest,
        best_long_range,
    )


def format_compact_count(value: int) -> str:
    """Format counts cleanly (e.g. 1230 -> '1.2K' or '1,230')."""
    if value >= 1000:
        return f"{value / 1000:.1f}K"
    return str(value)


def format_short_date(iso_date: str) -> str:
    """Convert YYYY-MM-DD into a compact display label like 'Aug 26'."""
    parsed = dt.date.fromisoformat(iso_date)
    return parsed.strftime("%b %d").replace(" 0", " ")


def format_short_year_date(iso_date: str) -> str:
    """Convert YYYY-MM-DD into a compact display label with 2-digit year like \"Nov 16 '26\"."""
    parsed = dt.date.fromisoformat(iso_date)
    return f"{parsed.strftime('%b %d').replace(' 0', ' ')} '{parsed.strftime('%y')}"


def determine_tier(count: int, max_count: int) -> int:
    """Map daily contribution count to a 5-level intensity tier (0..4)."""
    if count <= 0:
        return 0
    if count <= 3:
        return 1
    if count <= 8:
        return 2
    if count <= 19:
        return 3
    if max_count > 0 and count >= 20:
        return 4
    return 3


def compute_bar_height(count: int, max_count: int) -> float:
    """Compute proportional 3D isometric column height using log + linear blend."""
    if count <= 0 or max_count <= 0:
        return BASE_HEIGHT
    log_ratio = math.log1p(count) / math.log1p(max_count)
    lin_ratio = count / max_count
    height = BASE_HEIGHT + log_ratio * 42.0 + lin_ratio * 29.58
    height = max(MIN_ACTIVE_HEIGHT, min(MAX_HEIGHT, height))
    return round(height, 2)


def build_cubes_svg(contributions: list[dict], max_count: int) -> tuple[str, tuple[float, float, float, float]]:
    """Build all 3D isometric column SVG groups sorted back-to-front."""
    # Keep the last 366 days max (GitHub rolling year fits cleanly in 53x7)
    days = contributions[-366:]
    first_date = dt.date.fromisoformat(days[0]["date"])
    # Python weekday(): Mon=0..Sun=6 -> shift to Sun=0..Sat=6
    first_dow = (first_date.weekday() + 1) % 7

    cubes_markup: list[str] = []
    min_col, max_col = 999, -1
    min_row, max_row = 7, -1

    for day in days:
        cur_date = dt.date.fromisoformat(day["date"])
        offset = first_dow + (cur_date - first_date).days
        col = offset // 7
        row = offset % 7
        min_col = min(min_col, col)
        max_col = max(max_col, col)
        min_row = min(min_row, row)
        max_row = max(max_row, row)

        count = int(day.get("count", 0))
        tier = determine_tier(count, max_count)
        height = compute_bar_height(count, max_count)

        x = round(ORIGIN_X + (col - row) * STEP_X, 2)
        y_base = round(ORIGIN_Y + (col + row) * STEP_Y, 2)

        if count <= 0:
            cubes_markup.append(
                f'<g transform="translate({x} {y_base})">'
                f'<rect stroke="none" x="0" y="0" width="{CUBE_SIZE}" height="{CUBE_SIZE}" '
                f'transform="skewY(-30) skewX(40.89) scale(1 {SCALE_Y})" class="c-top-0"/>'
                f'<rect stroke="none" x="0" y="0" width="{CUBE_SIZE}" height="{BASE_HEIGHT}" '
                f'transform="skewY(30) scale(1 {SCALE_Y})" class="c-left-0"/>'
                f'<rect stroke="none" x="0" y="0" width="{CUBE_SIZE}" height="{BASE_HEIGHT}" '
                f'transform="translate(8.72 5.03) skewY(-30) scale(1 {SCALE_Y})" class="c-right-0"/>'
                f"</g>"
            )
        else:
            y_top = round(y_base - (height - BASE_HEIGHT) * SCALE_Y, 2)
            cubes_markup.append(
                f'<g transform="translate({x} {y_top})">'
                f'<animateTransform attributeName="transform" type="translate" '
                f'values="{x} {y_base};{x} {y_top}" dur="2.8s" '
                f'calcMode="spline" keySplines="0.22 1 0.36 1" repeatCount="1"/>'
                f'<rect stroke="none" x="0" y="0" width="{CUBE_SIZE}" height="{CUBE_SIZE}" '
                f'transform="skewY(-30) skewX(40.89) scale(1 {SCALE_Y})" class="c-top-{tier}"/>'
                f'<rect stroke="none" x="0" y="0" width="{CUBE_SIZE}" height="{height}" '
                f'transform="skewY(30) scale(1 {SCALE_Y})" class="c-left-{tier}">'
                f'<animate attributeName="height" values="{BASE_HEIGHT};{height}" dur="2.8s" '
                f'calcMode="spline" keySplines="0.22 1 0.36 1" repeatCount="1"/>'
                f"</rect>"
                f'<rect stroke="none" x="0" y="0" width="{CUBE_SIZE}" height="{height}" '
                f'transform="translate(8.72 5.03) skewY(-30) scale(1 {SCALE_Y})" class="c-right-{tier}">'
                f'<animate attributeName="height" values="{BASE_HEIGHT};{height}" dur="2.8s" '
                f'calcMode="spline" keySplines="0.22 1 0.36 1" repeatCount="1"/>'
                f"</rect>"
                f"</g>"
            )

    # Isometric cyber-deck platform corner coordinates (with slight outer padding)
    pad = 0.55
    c0, c1 = -pad, max_col + pad
    r0, r1 = -pad, 6 + pad

    def corner_point(c: float, r: float, dx: float = 0.0, dy: float = 0.0) -> tuple[float, float]:
        px = ORIGIN_X + (c - r) * STEP_X + dx
        py = ORIGIN_Y + (c + r) * STEP_Y + dy
        return round(px, 2), round(py, 2)

    top_pt = corner_point(c0, r0, 8.72, -5.03)
    right_pt = corner_point(c1, r0, 17.44, 0.0)
    bottom_pt = corner_point(c1, r1, 8.72, 5.03 + BASE_HEIGHT * SCALE_Y)
    left_pt = corner_point(c0, r1, 0.0, BASE_HEIGHT * SCALE_Y)

    return "".join(cubes_markup), (top_pt, right_pt, bottom_pt, left_pt)


def generate_svg(
    year_total: int,
    contributions: list[dict],
    all_time_total: int,
    current_streak: int,
    longest_streak: int,
) -> str:
    """Assemble the complete 3D Isometric Contribution City SVG document."""

    # Metrics over the rolling calendar window
    window = contributions[-365:] if len(contributions) >= 365 else contributions
    active_days = sum(1 for d in window if int(d.get("count", 0)) > 0)
    consistency_pct = round((active_days / max(len(window), 1)) * 100)
    active_avg = round(year_total / max(active_days, 1), 1)

    busiest_day = max(contributions, key=lambda d: int(d.get("count", 0)))
    busiest_count = int(busiest_day.get("count", 0))
    busiest_date = format_short_date(busiest_day["date"])

    # Date window label
    start_label = format_short_year_date(contributions[0]["date"])
    end_label = format_short_year_date(contributions[-1]["date"])
    updated_stamp = dt.datetime.now(dt.timezone(dt.timedelta(hours=5, minutes=30))).strftime("%b %d, %Y")

    cubes_svg, (top_pt, right_pt, bottom_pt, left_pt) = build_cubes_svg(contributions, busiest_count)

    # Cyber-deck platform polygon points + 5px isometric thickness rim
    deck_pts = f"{top_pt[0]},{top_pt[1]} {right_pt[0]},{right_pt[1]} {bottom_pt[0]},{bottom_pt[1]} {left_pt[0]},{left_pt[1]}"
    rim_left_pts = (
        f"{left_pt[0]},{left_pt[1]} {bottom_pt[0]},{bottom_pt[1]} "
        f"{bottom_pt[0]},{round(bottom_pt[1] + 6.0, 2)} {left_pt[0]},{round(left_pt[1] + 6.0, 2)}"
    )
    rim_right_pts = (
        f"{bottom_pt[0]},{bottom_pt[1]} {right_pt[0]},{right_pt[1]} "
        f"{right_pt[0]},{round(right_pt[1] + 6.0, 2)} {bottom_pt[0]},{round(bottom_pt[1] + 6.0, 2)}"
    )

    year_compact = format_compact_count(year_total)
    year_exact = f"{year_total:,}"
    all_time_exact = f"{all_time_total:,}"

    return f'''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="860" height="440" viewBox="0 0 860 440" role="img" aria-label="Amila Suranjith 3D Contribution City">
  <defs>
    <linearGradient id="bg-grad" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0%" stop-color="#07070b"/>
      <stop offset="52%" stop-color="#140d08"/>
      <stop offset="100%" stop-color="#09080f"/>
    </linearGradient>

    <linearGradient id="card-grad" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0%" stop-color="#1b1512" stop-opacity="0.88"/>
      <stop offset="100%" stop-color="#0d0b10" stop-opacity="0.92"/>
    </linearGradient>

    <linearGradient id="hero-grad" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0%" stop-color="#221409" stop-opacity="0.94"/>
      <stop offset="100%" stop-color="#110d0c" stop-opacity="0.96"/>
    </linearGradient>

    <linearGradient id="accent-text" x1="0" y1="0" x2="1" y2="0">
      <stop offset="0%" stop-color="#fef3c7"/>
      <stop offset="45%" stop-color="#ffa500"/>
      <stop offset="100%" stop-color="#ff6b00"/>
    </linearGradient>

    <linearGradient id="accent-bar" x1="0" y1="0" x2="1" y2="0">
      <stop offset="0%" stop-color="#ff6b00"/>
      <stop offset="60%" stop-color="#ffa500"/>
      <stop offset="100%" stop-color="#fbbf24"/>
    </linearGradient>

    <linearGradient id="border-glow" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0%" stop-color="#ff7f00" stop-opacity="0.72"/>
      <stop offset="50%" stop-color="#ffa500" stop-opacity="0.28"/>
      <stop offset="100%" stop-color="#d97706" stop-opacity="0.65"/>
    </linearGradient>

    <linearGradient id="deck-surface" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0%" stop-color="#191417" stop-opacity="0.95"/>
      <stop offset="100%" stop-color="#0e0c12" stop-opacity="0.98"/>
    </linearGradient>

    <radialGradient id="orb-orange" cx="50%" cy="50%" r="50%">
      <stop offset="0%" stop-color="#ff7f00" stop-opacity="0.34"/>
      <stop offset="60%" stop-color="#ff7f00" stop-opacity="0.09"/>
      <stop offset="100%" stop-color="#ff7f00" stop-opacity="0"/>
    </radialGradient>

    <radialGradient id="orb-gold" cx="50%" cy="50%" r="50%">
      <stop offset="0%" stop-color="#fbbf24" stop-opacity="0.24"/>
      <stop offset="60%" stop-color="#f59e0b" stop-opacity="0.06"/>
      <stop offset="100%" stop-color="#f59e0b" stop-opacity="0"/>
    </radialGradient>

    <pattern id="dot-grid" width="24" height="24" patternUnits="userSpaceOnUse">
      <circle cx="2" cy="2" r="0.85" fill="#ff9f43" fill-opacity="0.11"/>
    </pattern>

    <clipPath id="canvas-clip">
      <rect x="0" y="0" width="860" height="440" rx="20"/>
    </clipPath>
  </defs>

  <style>
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@600;800&amp;family=Space+Grotesk:wght@500;700&amp;family=Karla:wght@400;600&amp;display=swap');
    .font-sans {{ font-family: "Outfit", "Space Grotesk", "Karla", -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; }}
    .font-mono {{ font-family: "Space Grotesk", "Karla", ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace; }}

    .pulse-dot {{ animation: pulse 2.4s ease-in-out infinite; transform-origin: center; }}
    .orb-float {{ animation: floatOrb 11s ease-in-out infinite; }}
    .orb-float-slow {{ animation: floatOrb 15s ease-in-out infinite reverse; }}
    .panel-in {{ animation: fadeSlide 0.65s ease-out both; }}
    @keyframes pulse {{
      0%, 100% {{ opacity: 1; }}
      50% {{ opacity: 0.4; }}
    }}
    @keyframes floatOrb {{
      0%, 100% {{ transform: translate(0px, 0px); }}
      50% {{ transform: translate(18px, -12px); }}
    }}
    @keyframes fadeSlide {{
      from {{ opacity: 0; }}
      to {{ opacity: 1; }}
    }}

    /* 5-tier Cyber-Orange and Gold isometric shading */
    .c-top-0   {{ fill: #2b262d; }}
    .c-left-0  {{ fill: #201c22; }}
    .c-right-0 {{ fill: #171419; }}

    .c-top-1   {{ fill: #9a3412; }}
    .c-left-1  {{ fill: #7c2d12; }}
    .c-right-1 {{ fill: #5c1f0c; }}

    .c-top-2   {{ fill: #ea580c; }}
    .c-left-2  {{ fill: #c2410c; }}
    .c-right-2 {{ fill: #9a3412; }}

    .c-top-3   {{ fill: #ff7f00; }}
    .c-left-3  {{ fill: #d96b00; }}
    .c-right-3 {{ fill: #b35600; }}

    .c-top-4   {{ fill: #fbbf24; }}
    .c-left-4  {{ fill: #f59e0b; }}
    .c-right-4 {{ fill: #d97706; }}
  </style>

  <g clip-path="url(#canvas-clip)">
    <!-- Canvas Background & Ambient Glow -->
    <rect width="860" height="440" fill="url(#bg-grad)"/>
    <rect width="860" height="440" fill="url(#dot-grid)"/>
    <circle cx="620" cy="240" r="280" fill="url(#orb-orange)" class="orb-float"/>
    <circle cx="150" cy="95" r="210" fill="url(#orb-gold)" class="orb-float-slow"/>
    <circle cx="770" cy="90" r="160" fill="url(#orb-orange)" class="orb-float-slow"/>

    <!-- Top-Right Telemetry & Intensity Scale HUD -->
    <g class="panel-in" transform="translate(590 22)">
      <rect x="0" y="0" width="246" height="66" rx="12" fill="url(#card-grad)" stroke="#ff7f00" stroke-opacity="0.28" stroke-width="1"/>
      <circle cx="15" cy="20" r="3.5" fill="#ff7f00" class="pulse-dot"/>
      <text x="25" y="23.5" class="font-mono" font-size="9.5" font-weight="700" letter-spacing="1.2" fill="#fcd34d">LIVE TELEMETRY</text>
      <text x="233" y="23.5" text-anchor="end" class="font-mono" font-size="8.5" fill="#9ca3af">{start_label} - {end_label}</text>

      <text x="14" y="48" class="font-mono" font-size="8.5" font-weight="600" letter-spacing="0.6" fill="#9ca3af">LESS</text>
      <rect x="44" y="39.5" width="12" height="10" rx="2.5" fill="#2b262d" stroke="#ffffff" stroke-opacity="0.1"/>
      <rect x="59" y="39.5" width="12" height="10" rx="2.5" fill="#9a3412"/>
      <rect x="74" y="39.5" width="12" height="10" rx="2.5" fill="#ea580c"/>
      <rect x="89" y="39.5" width="12" height="10" rx="2.5" fill="#ff7f00"/>
      <rect x="104" y="39.5" width="12" height="10" rx="2.5" fill="#fbbf24"/>
      <text x="122" y="48" class="font-mono" font-size="8.5" font-weight="600" letter-spacing="0.6" fill="#fcd34d">MORE</text>
      <text x="233" y="48" text-anchor="end" class="font-mono" font-size="9" fill="#fb923c">{all_time_exact} total</text>
    </g>

    <!-- 3D Isometric Contribution City Visualization (Same 53x7 Data Grid) -->
    <g transform="translate(252 42)">
      <!-- Isometric Cyber-Deck Platform -->
      <polygon points="{rim_left_pts}" fill="#1a120d" stroke="#ff7f00" stroke-opacity="0.25" stroke-width="0.7"/>
      <polygon points="{rim_right_pts}" fill="#120c09" stroke="#ff7f00" stroke-opacity="0.2" stroke-width="0.7"/>
      <polygon points="{deck_pts}" fill="url(#deck-surface)" stroke="#ff7f00" stroke-opacity="0.38" stroke-width="1"/>
      <!-- 3D Contribution Cubes -->
      <g>{cubes_svg}</g>
    </g>

    <!-- Left Bento Dashboard Panel -->
    <g class="panel-in" transform="translate(24 22)">
      <!-- Header Pill -->
      <rect x="0" y="0" width="220" height="44" rx="12" fill="url(#card-grad)" stroke="#ff7f00" stroke-opacity="0.32" stroke-width="1"/>
      <circle cx="17" cy="22" r="4" fill="#ff7f00" class="pulse-dot"/>
      <text x="29" y="19" class="font-mono" font-size="10.5" font-weight="700" letter-spacing="1.6" fill="#ffa500">CONTRIBUTION CITY</text>
      <text x="29" y="34" class="font-mono" font-size="10" fill="#9ca3af">@{USERNAME}</text>

      <!-- Hero Metric Card -->
      <g transform="translate(0 54)">
        <rect x="0" y="0" width="220" height="104" rx="14" fill="url(#hero-grad)" stroke="#ff7f00" stroke-opacity="0.42" stroke-width="1"/>
        <rect x="14" y="14" width="4" height="76" rx="2" fill="url(#accent-bar)"/>
        <text x="28" y="30" class="font-mono" font-size="9.5" font-weight="700" letter-spacing="1.3" fill="#fb923c">LAST 365 DAYS</text>
        <text x="28" y="67" class="font-sans" font-size="34" font-weight="800" fill="url(#accent-text)">{year_compact}</text>
        <rect x="138" y="44" width="68" height="22" rx="6" fill="#ff7f00" fill-opacity="0.14" stroke="#ff7f00" stroke-opacity="0.35"/>
        <text x="172" y="58.5" text-anchor="middle" class="font-mono" font-size="10.5" font-weight="700" fill="#fed7aa">{year_exact}</text>
        <text x="28" y="88" class="font-sans" font-size="11.5" font-weight="500" fill="#d1d5db">verified contributions</text>
      </g>

      <!-- 2x2 Bento Stat Grid -->
      <!-- Card 1: Active Days -->
      <g transform="translate(0 168)">
        <rect x="0" y="0" width="105" height="84" rx="12" fill="url(#card-grad)" stroke="#ffffff" stroke-opacity="0.09" stroke-width="1"/>
        <text x="12" y="21" class="font-mono" font-size="9" font-weight="700" letter-spacing="0.9" fill="#9ca3af">ACTIVE DAYS</text>
        <text x="12" y="51" class="font-sans" font-size="24" font-weight="800" fill="#fef3c7">{active_days}</text>
        <text x="12" y="70" class="font-mono" font-size="9.5" fill="#fb923c">{consistency_pct}% of year</text>
      </g>

      <!-- Card 2: Busiest Day -->
      <g transform="translate(115 168)">
        <rect x="0" y="0" width="105" height="84" rx="12" fill="url(#card-grad)" stroke="#ffffff" stroke-opacity="0.09" stroke-width="1"/>
        <text x="12" y="21" class="font-mono" font-size="9" font-weight="700" letter-spacing="0.9" fill="#9ca3af">BUSIEST DAY</text>
        <text x="12" y="51" class="font-sans" font-size="24" font-weight="800" fill="#fbbf24">{busiest_count}</text>
        <text x="12" y="70" class="font-mono" font-size="9.5" fill="#fcd34d">{busiest_date} peak</text>
      </g>

      <!-- Card 3: Current Streak -->
      <g transform="translate(0 262)">
        <rect x="0" y="0" width="105" height="84" rx="12" fill="url(#card-grad)" stroke="#ff7f00" stroke-opacity="0.32" stroke-width="1"/>
        <text x="12" y="21" class="font-mono" font-size="9" font-weight="700" letter-spacing="0.9" fill="#fb923c">STREAK</text>
        <text x="12" y="51" class="font-sans" font-size="24" font-weight="800" fill="#ff9f43">{current_streak}d</text>
        <text x="12" y="70" class="font-mono" font-size="9.5" fill="#9ca3af">Best: {longest_streak}d</text>
      </g>

      <!-- Card 4: Daily Intensity -->
      <g transform="translate(115 262)">
        <rect x="0" y="0" width="105" height="84" rx="12" fill="url(#card-grad)" stroke="#ffffff" stroke-opacity="0.09" stroke-width="1"/>
        <text x="12" y="21" class="font-mono" font-size="9" font-weight="700" letter-spacing="0.9" fill="#9ca3af">INTENSITY</text>
        <text x="12" y="51" class="font-sans" font-size="24" font-weight="800" fill="#fed7aa">{active_avg}</text>
        <text x="12" y="70" class="font-mono" font-size="9.5" fill="#9ca3af">Avg / active day</text>
      </g>

      <!-- Footer Metadata -->
      <g transform="translate(0 360)">
        <line x1="0" y1="0" x2="220" y2="0" stroke="#ff7f00" stroke-opacity="0.2" stroke-width="1"/>
        <text x="2" y="18" class="font-sans" font-size="10" font-weight="600" fill="#d1d5db">3D Isometric Skyline</text>
        <text x="2" y="33" class="font-mono" font-size="9" fill="#9ca3af">Synced {updated_stamp} • {TIMEZONE}</text>
      </g>
    </g>

    <!-- Bottom-Right Micro Credit -->
    <text x="838" y="424" text-anchor="end" class="font-mono" font-size="9" fill="#9ca3af" fill-opacity="0.55">github.com/{USERNAME} • self-hosted svg</text>

    <!-- Outer Frame Border -->
    <rect x="0.75" y="0.75" width="858.5" height="438.5" rx="19.5" fill="none" stroke="url(#border-glow)" stroke-width="1.5"/>
  </g>
</svg>
'''


def generate_streak_svg(
    all_time_total: int,
    total_range: str,
    current_streak: int,
    current_range: str,
    longest_streak: int,
    longest_range: str,
    theme: str = "dark",
) -> str:
    """Render a transparent GitHub Streak card SVG matching the chosen theme palette."""
    palette = STREAK_THEMES[theme]
    total_str = f"{all_time_total:,}"
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" style="isolation: isolate" viewBox="0 0 495 195" width="495px" height="195px" direction="ltr" role="img" aria-label="GitHub Streak ({theme})">
  <style>
    @keyframes currstreak {{
      0% {{ font-size: 3px; opacity: 0.2; }}
      80% {{ font-size: 34px; opacity: 1; }}
      100% {{ font-size: 28px; opacity: 1; }}
    }}
    @keyframes fadein {{
      0% {{ opacity: 0; }}
      100% {{ opacity: 1; }}
    }}
  </style>
  <defs>
    <clipPath id="outer_rectangle">
      <rect width="495" height="195" rx="4.5"/>
    </clipPath>
    <mask id="mask_out_ring_behind_fire">
      <rect width="495" height="195" fill="white"/>
      <ellipse id="mask-ellipse" cx="247.5" cy="32" rx="13" ry="18" fill="black"/>
    </mask>
  </defs>
  <g clip-path="url(#outer_rectangle)">
    <g style="isolation: isolate">
      <rect stroke="#000000" stroke-opacity="0" fill="#000000" fill-opacity="0" rx="4.5" x="0.5" y="0.5" width="494" height="194"/>
    </g>
    <g style="isolation: isolate">
      <line x1="165" y1="28" x2="165" y2="170" vector-effect="non-scaling-stroke" stroke-width="1" stroke="{palette['stroke']}" stroke-linejoin="miter" stroke-linecap="square" stroke-miterlimit="3"/>
      <line x1="330" y1="28" x2="330" y2="170" vector-effect="non-scaling-stroke" stroke-width="1" stroke="{palette['stroke']}" stroke-linejoin="miter" stroke-linecap="square" stroke-miterlimit="3"/>
    </g>
    <g style="isolation: isolate">
      <g transform="translate(82.5, 48)">
        <text x="0" y="32" stroke-width="0" text-anchor="middle" fill="{palette['side_num']}" stroke="none" font-family='"Segoe UI", Ubuntu, sans-serif' font-weight="700" font-size="28px" font-style="normal" style="opacity: 0; animation: fadein 0.5s linear forwards 0.6s">
          {total_str}
        </text>
      </g>
      <g transform="translate(82.5, 84)">
        <text x="0" y="32" stroke-width="0" text-anchor="middle" fill="{palette['side_label']}" stroke="none" font-family='"Segoe UI", Ubuntu, sans-serif' font-weight="400" font-size="14px" font-style="normal" style="opacity: 0; animation: fadein 0.5s linear forwards 0.7s">
          Total Contributions
        </text>
      </g>
      <g transform="translate(82.5, 114)">
        <text x="0" y="32" stroke-width="0" text-anchor="middle" fill="{palette['dates']}" stroke="none" font-family='"Segoe UI", Ubuntu, sans-serif' font-weight="400" font-size="12px" font-style="normal" style="opacity: 0; animation: fadein 0.5s linear forwards 0.8s">
          {total_range}
        </text>
      </g>
    </g>
    <g style="isolation: isolate">
      <g transform="translate(247.5, 108)">
        <text x="0" y="32" stroke-width="0" text-anchor="middle" fill="{palette['curr_label']}" stroke="none" font-family='"Segoe UI", Ubuntu, sans-serif' font-weight="700" font-size="14px" font-style="normal" style="opacity: 0; animation: fadein 0.5s linear forwards 0.9s">
          Current Streak
        </text>
      </g>
      <g transform="translate(247.5, 145)">
        <text x="0" y="21" stroke-width="0" text-anchor="middle" fill="{palette['dates']}" stroke="none" font-family='"Segoe UI", Ubuntu, sans-serif' font-weight="400" font-size="12px" font-style="normal" style="opacity: 0; animation: fadein 0.5s linear forwards 0.9s">
          {current_range}
        </text>
      </g>
      <g mask="url(#mask_out_ring_behind_fire)">
        <circle cx="247.5" cy="71" r="40" fill="none" stroke="{palette['ring']}" stroke-width="5" style="opacity: 0; animation: fadein 0.5s linear forwards 0.4s"/>
      </g>
      <g transform="translate(247.5, 19.5)" stroke-opacity="0" style="opacity: 0; animation: fadein 0.5s linear forwards 0.6s">
        <path d="M -12 -0.5 L 15 -0.5 L 15 23.5 L -12 23.5 L -12 -0.5 Z" fill="none"/>
        <path d="M 1.5 0.67 C 1.5 0.67 2.24 3.32 2.24 5.47 C 2.24 7.53 0.89 9.2 -1.17 9.2 C -3.23 9.2 -4.79 7.53 -4.79 5.47 L -4.76 5.11 C -6.78 7.51 -8 10.62 -8 13.99 C -8 18.41 -4.42 22 0 22 C 4.42 22 8 18.41 8 13.99 C 8 8.6 5.41 3.79 1.5 0.67 Z M -0.29 19 C -2.07 19 -3.51 17.6 -3.51 15.86 C -3.51 14.24 -2.46 13.1 -0.7 12.74 C 1.07 12.38 2.9 11.53 3.92 10.16 C 4.31 11.45 4.51 12.81 4.51 14.2 C 4.51 16.85 2.36 19 -0.29 19 Z" fill="{palette['fire']}" stroke-opacity="0"/>
      </g>
      <g transform="translate(247.5, 48)">
        <text x="0" y="32" stroke-width="0" text-anchor="middle" fill="{palette['curr_num']}" stroke="none" font-family='"Segoe UI", Ubuntu, sans-serif' font-weight="700" font-size="28px" font-style="normal" style="animation: currstreak 0.6s linear forwards">
          {current_streak}
        </text>
      </g>
    </g>
    <g style="isolation: isolate">
      <g transform="translate(412.5, 48)">
        <text x="0" y="32" stroke-width="0" text-anchor="middle" fill="{palette['side_num']}" stroke="none" font-family='"Segoe UI", Ubuntu, sans-serif' font-weight="700" font-size="28px" font-style="normal" style="opacity: 0; animation: fadein 0.5s linear forwards 1.2s">
          {longest_streak}
        </text>
      </g>
      <g transform="translate(412.5, 84)">
        <text x="0" y="32" stroke-width="0" text-anchor="middle" fill="{palette['side_label']}" stroke="none" font-family='"Segoe UI", Ubuntu, sans-serif' font-weight="400" font-size="14px" font-style="normal" style="opacity: 0; animation: fadein 0.5s linear forwards 1.3s">
          Longest Streak
        </text>
      </g>
      <g transform="translate(412.5, 114)">
        <text x="0" y="32" stroke-width="0" text-anchor="middle" fill="{palette['dates']}" stroke="none" font-family='"Segoe UI", Ubuntu, sans-serif' font-weight="400" font-size="12px" font-style="normal" style="opacity: 0; animation: fadein 0.5s linear forwards 1.4s">
          {longest_range}
        </text>
      </g>
    </g>
  </g>
</svg>
"""


def main() -> None:
    ASSETS_DIR.mkdir(parents=True, exist_ok=True)
    year_total, contributions = fetch_contributions()
    (
        all_time_total,
        total_range,
        current_streak,
        current_range,
        longest_streak,
        longest_range,
    ) = fetch_streak_stats(contributions, year_total)

    city_svg = generate_svg(
        year_total=year_total,
        contributions=contributions,
        all_time_total=all_time_total,
        current_streak=current_streak,
        longest_streak=longest_streak,
    )
    OUTPUT_PATH.write_text(city_svg, encoding="utf-8")
    print(f"Generated {OUTPUT_PATH} ({len(city_svg)} bytes)")

    for theme, out_path in (("dark", STREAK_DARK_PATH), ("light", STREAK_LIGHT_PATH)):
        streak_svg = generate_streak_svg(
            all_time_total=all_time_total,
            total_range=total_range,
            current_streak=current_streak,
            current_range=current_range,
            longest_streak=longest_streak,
            longest_range=longest_range,
            theme=theme,
        )
        out_path.write_text(streak_svg, encoding="utf-8")
        print(f"Generated {out_path} ({len(streak_svg)} bytes)")


if __name__ == "__main__":
    main()
