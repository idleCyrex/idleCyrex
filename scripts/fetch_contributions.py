#!/usr/bin/env python3
"""
Pull the last year of daily contribution counts and write
data/contributions.json with the raw days plus derived stats (streaks, best
day). No token needed.

Source 1: GitHub's own public contributions fragment (what the profile page
          renders), scraped with BeautifulSoup.
Source 2: github-contributions-api.jogruber.de, if GitHub's markup changes or
          the request is blocked.

Run daily by .github/workflows/update-profile-art.yml.
"""
import datetime
import json
import os
import re
import sys

import requests

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
DATA_PATH = os.path.join(ROOT, "data", "contributions.json")
USERNAME = os.environ.get("GH_PROFILE_USER", "idleCyrex")

UA = {"User-Agent": "idlecyrex-profile-readme/1.0"}


def from_github():
    from bs4 import BeautifulSoup

    resp = requests.get(f"https://github.com/users/{USERNAME}/contributions", headers=UA, timeout=30)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")
    tips = {t.get("for"): t.get_text(strip=True) for t in soup.find_all("tool-tip")}

    days = []
    for td in soup.select("td.ContributionCalendar-day"):
        date = td.get("data-date")
        if not date:
            continue
        m = re.match(r"(\d+)", tips.get(td.get("id"), ""))
        days.append({"date": date, "count": int(m.group(1)) if m else 0,
                     "level": int(td.get("data-level") or 0)})
    if not days:
        raise RuntimeError("no calendar cells found -- github markup may have changed")
    return days


def from_api():
    # this API resets connections that send a custom User-Agent; use requests' default
    resp = requests.get(f"https://github-contributions-api.jogruber.de/v4/{USERNAME}?y=last", timeout=30)
    resp.raise_for_status()
    return [{"date": d["date"], "count": d["count"], "level": d["level"]}
            for d in resp.json()["contributions"]]


def fetch_days():
    for source in (from_github, from_api):
        try:
            days = source()
            print(f"fetched {len(days)} days via {source.__name__}")
            break
        except Exception as e:  # try the next source
            print(f"{source.__name__} failed: {e}", file=sys.stderr)
    else:
        sys.exit("every contribution source failed")

    # the API returns the whole calendar year incl. future days; drop those
    today = datetime.date.today().isoformat()
    days = sorted((d for d in days if d["date"] <= today), key=lambda d: d["date"])
    return days


def current_streak(days):
    i = len(days) - 1
    if days[i]["count"] == 0:
        i -= 1  # today isn't over yet -- don't break the streak on it
    end = i
    while i >= 0 and days[i]["count"] > 0:
        i -= 1
    length = end - i
    return {"length": length,
            "start": days[i + 1]["date"] if length else None,
            "end": days[end]["date"] if length else None}


def longest_streak(days):
    best = {"length": 0, "start": None, "end": None}
    run_start = None
    for i, d in enumerate(days):
        if d["count"] == 0:
            run_start = None
            continue
        if run_start is None:
            run_start = i
        if i - run_start + 1 > best["length"]:
            best = {"length": i - run_start + 1, "start": days[run_start]["date"], "end": d["date"]}
    return best


def build(days):
    total = sum(d["count"] for d in days)
    active = sum(1 for d in days if d["count"])
    best = max(days, key=lambda d: d["count"])

    return {
        "username": USERNAME,
        "generated_at": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "range": {"start": days[0]["date"], "end": days[-1]["date"]},
        "total_contributions": total,
        "active_days": active,
        "avg_per_active_day": round(total / active, 1) if active else 0,
        "current_streak": current_streak(days),
        "longest_streak": longest_streak(days),
        "best_day": {"date": best["date"], "count": best["count"]},
        "days": days,
    }


if __name__ == "__main__":
    data = build(fetch_days())
    os.makedirs(os.path.dirname(DATA_PATH), exist_ok=True)
    with open(DATA_PATH, "w") as f:
        json.dump(data, f, indent=2)
    print(f"wrote data/contributions.json: {data['total_contributions']} contributions, "
          f"current streak {data['current_streak']['length']}, "
          f"longest {data['longest_streak']['length']}")
