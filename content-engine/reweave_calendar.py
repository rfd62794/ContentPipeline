#!/usr/bin/env python3
"""ContentEngine — Calendar Reweave (round-robin, one per day)."""
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple

sys.path.insert(0, str(Path(__file__).parent))
from core.youtube_auth import build_service

SCOPES = ["https://www.googleapis.com/auth/youtube", "https://www.googleapis.com/auth/yt-analytics.readonly"]

GAME_SLOTS = [
    ("EIC",         "Everything is Crab"),
    ("MLU",         "My Little Universe"),
    ("AF",          "Abiotic Factor"),
    ("Duckov",      "Escape From Duckov"),
    ("Raccoin",     "Raccoin"),
    ("Dragonwilds", "RuneScape: Dragonwilds"),
    ("FishingInc",  "Fishing Inc"),
    ("Dune",        "Dune: Awakening"),
    ("TurboShells", "TurboShells"),
]

EDT = timezone(timedelta(hours=-4))
START_DATE = datetime(2026, 6, 29, 22, 0, 0, tzinfo=EDT)
SKIP_PREFIX = "2026-06-28"


def is_short(duration: str) -> bool:
    """Return True if ISO 8601 duration is <= 60 seconds."""
    if "H" in duration:
        return False
    m = re.match(r"PT(?:(\d+)M)?(?:(\d+)S)?", duration)
    if not m:
        return False
    minutes = int(m.group(1) or 0)
    seconds = int(m.group(2) or 0)
    return minutes * 60 + seconds <= 60


def match_game(title: str) -> Optional[str]:
    for key, prefix in GAME_SLOTS:
        if title.startswith(prefix):
            return key
    return None


def fetch_videos(service) -> List[Dict]:
    ch = service.channels().list(part="contentDetails", mine=True).execute()
    pl_id = ch["items"][0]["contentDetails"]["relatedPlaylists"]["uploads"]
    all_ids = []
    token = None
    while True:
        r = service.playlistItems().list(part="contentDetails", playlistId=pl_id, maxResults=50, pageToken=token).execute()
        all_ids.extend(i["contentDetails"]["videoId"] for i in r.get("items", []))
        token = r.get("nextPageToken")
        if not token:
            break
    videos = []
    for i in range(0, len(all_ids), 50):
        r = service.videos().list(part="snippet,status,contentDetails", id=",".join(all_ids[i:i+50])).execute()
        for item in r.get("items", []):
            st = item.get("status", {})
            if st.get("privacyStatus") != "private":
                continue
            duration = item.get("contentDetails", {}).get("duration", "")
            if not is_short(duration):
                continue
            sn = item.get("snippet", {})
            pa = st.get("publishAt")
            videos.append({"id": item["id"], "title": sn.get("title", ""), "publish_at": pa, "published_at": sn.get("publishedAt", "")})
    return videos


def build_queues(videos: List[Dict]) -> Dict[str, List[Dict]]:
    groups = {k: [] for k, _ in GAME_SLOTS}
    bad = []
    for v in videos:
        if v["publish_at"]:
            pa_edt = datetime.fromisoformat(v["publish_at"].replace("Z", "+00:00")).astimezone(EDT)
            if pa_edt.strftime("%Y-%m-%d") == SKIP_PREFIX:
                print(f"  SKIP Jun28 (EDT): {v['title']}")
                continue
        g = match_game(v["title"])
        if g is None:
            bad.append(v["title"])
        else:
            groups[g].append(v)
    if bad:
        print("STOP — unrecognized:")
        for t in bad:
            print(f"  {t!r}")
        sys.exit(1)
    for k in groups:
        sched = sorted([v for v in groups[k] if v["publish_at"]], key=lambda v: v["publish_at"])
        priv  = sorted([v for v in groups[k] if not v["publish_at"]], key=lambda v: v["published_at"])
        groups[k] = sched + priv
    return groups


def round_robin(queues: Dict[str, List[Dict]]) -> List[Tuple[Dict, datetime]]:
    keys = [k for k, _ in GAME_SLOTS]
    rem = {k: list(v) for k, v in queues.items()}
    total = sum(len(q) for q in rem.values())
    plan, date, pos = [], START_DATE, 0
    while total > 0:
        slot = keys[pos % len(keys)]
        pos += 1
        if rem[slot]:
            plan.append((rem[slot].pop(0), date))
            date += timedelta(days=1)
            total -= 1
    return plan


def print_manifest(plan, total_in):
    print(f"\n{'='*110}")
    print(f"REWEAVE MANIFEST  {len(plan)} videos  {plan[0][1].strftime('%b %d')} → {plan[-1][1].strftime('%b %d, %Y')}")
    print(f"{'='*110}")
    print(f"{'#':>4}  {'Game':<12}  {'ID':<14}  {'Old':^12}  {'New':^12}  Title")
    print("-"*110)
    seen_ids, seen_dates = set(), set()
    for i, (v, nd) in enumerate(plan, 1):
        old = datetime.fromisoformat(v["publish_at"].replace("Z","+00:00")).astimezone(EDT).strftime("%Y-%m-%d") if v["publish_at"] else "private"
        new = nd.strftime("%Y-%m-%d")
        if v["id"] in seen_ids:
            print(f"STOP duplicate id {v['id']}"); sys.exit(1)
        if nd in seen_dates:
            print(f"STOP duplicate date {new}"); sys.exit(1)
        seen_ids.add(v["id"]); seen_dates.add(nd)
        print(f"{i:>4}  {match_game(v['title']):<12}  {v['id']:<14}  {old:^12}  {new:^12}  {v['title'][:55]}")
    print("-"*110)
    if len(plan) != total_in:
        print(f"STOP count mismatch manifest={len(plan)} expected={total_in}"); sys.exit(1)
    print(f"Total {len(plan)} | no duplicates | no date conflicts | count matches ✓")


def execute(service, plan):
    print(f"\nExecuting {len(plan)} updates...\n")
    for i, (v, nd) in enumerate(plan, 1):
        pa = nd.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")
        try:
            service.videos().update(part="status", body={"id": v["id"], "status": {"privacyStatus": "private", "publishAt": pa}}).execute()
            old = v["publish_at"][:10] if v["publish_at"] else "private"
            print(f"[{i:>2}/{len(plan)}] {v['id']}  {old} → {nd.strftime('%Y-%m-%d')}  {v['title'][:60]}")
        except Exception as e:
            print(f"STOP API error {v['id']}: {e}"); sys.exit(1)
    print(f"\nDone. {len(plan)} rescheduled.")


def main():
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--yes", action="store_true")
    args = p.parse_args()

    service = build_service("youtube", "v3", SCOPES)

    print("Fetching private/scheduled videos...")
    videos = fetch_videos(service)
    print(f"Found {len(videos)} private/scheduled\n")

    queues = build_queues(videos)
    total_in = sum(len(q) for q in queues.values())
    print("\nGame inventory:")
    for k, prefix in GAME_SLOTS:
        print(f"  {k:<12} {len(queues[k]):>3}  ({prefix})")

    plan = round_robin(queues)
    print_manifest(plan, total_in)

    if not args.yes:
        print("\nRun with --yes to execute.")
        return
    execute(service, plan)


if __name__ == "__main__":
    main()
