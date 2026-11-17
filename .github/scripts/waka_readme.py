#!/usr/bin/env python3
"""Render the WakaTime README block as lifetime totals = baseline + tracked time."""

import base64
import json
import os
import re
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
README = ROOT / "README.md"
BASELINE = json.loads((Path(__file__).resolve().parents[1] / "wakatime-baseline.json").read_text())
API = os.environ.get("WAKATIME_API_URL", "https://wakatime.com/api/v1").rstrip("/")
TOKEN = os.environ["WAKATIME_API_KEY"]
START = "<!--START_SECTION:waka-->"
END = "<!--END_SECTION:waka-->"
LANG_COUNT = 8
BAR_WIDTH = 25
BAR_STYLE = "⣀⣄⣤⣦⣶⣷⣿"


def fetch_languages():
    req = urllib.request.Request(
        f"{API}/users/current/stats/all_time",
        headers={
            "Authorization": "Basic " + base64.b64encode(TOKEN.encode()).decode(),
            "Accept": "application/json",
            "User-Agent": "waka-readme-baseline",
        },
    )
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = json.load(resp).get("data") or {}
        except urllib.error.HTTPError as err:
            if err.code in (202, 429) or err.code >= 500:
                if attempt < 2:
                    time.sleep(10)
                    continue
            raise
        if data.get("is_up_to_date", True) or attempt == 2:
            return data.get("languages") or []
        time.sleep(10)
    return []


def fmt_time(seconds):
    hours, minutes = int(seconds // 3600), int(seconds % 3600 // 60)
    if hours and minutes:
        return f"{hours} hr{'s' if hours != 1 else ''} {minutes} min{'s' if minutes != 1 else ''}"
    if hours:
        return f"{hours} hr{'s' if hours != 1 else ''}"
    return f"{minutes} min{'s' if minutes != 1 else ''}"


def make_graph(percent):
    markers = len(BAR_STYLE) - 1
    proportion = percent / 100 * BAR_WIDTH
    bar = BAR_STYLE[-1] * int(proportion + 0.5 / markers)
    remainder = int((proportion - len(bar)) * markers + 0.5)
    bar += BAR_STYLE[remainder] if remainder > 0 else ""
    return bar + BAR_STYLE[0] * (BAR_WIDTH - len(bar))


def render(languages):
    totals = {name: int(hours) * 3600 for name, hours in BASELINE.items()}
    for lang in languages:
        name = lang.get("name")
        if name:
            totals[name] = totals.get(name, 0) + int(lang.get("total_seconds", 0))

    ranked = sorted(totals.items(), key=lambda item: item[1], reverse=True)[:LANG_COUNT]
    total_seconds = sum(totals.values())
    lines = []
    for name, seconds in ranked:
        percent = seconds / total_seconds * 100 if total_seconds else 0
        pct = f"{percent:.2f}".zfill(5)
        lines.append(f"{name:<22}{fmt_time(seconds):<22}{make_graph(percent)}   {pct} %")
    return "\n".join(lines)


def main():
    block = render(fetch_languages())
    text = README.read_text()
    section = f"{START}\n\n```txt\n{block}\n```\n\n{END}"
    updated = re.sub(re.escape(START) + r".*?" + re.escape(END), section, text, flags=re.S)
    if updated != text:
        README.write_text(updated)


if __name__ == "__main__":
    main()
