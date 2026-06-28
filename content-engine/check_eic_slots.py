from reschedule_calendar import CalendarRescheduler

r = CalendarRescheduler()
videos = r.get_scheduled_videos()

# Target dates to check
target_dates = [
    "2026-07-07",
    "2026-07-13",
    "2026-07-18",
    "2026-07-23",
    "2026-07-27",
    "2026-07-31"
]

print("EIC videos on target dates:")
for date in target_dates:
    print(f"\n{date}:")
    for v in videos:
        if 'Everything is Crab' in v['title'] and date in v['current_schedule']:
            print(f"  - {v['title']}")
            print(f"    Video ID: {v['video_id']}")
            print(f"    Current: {v['current_schedule']}")
