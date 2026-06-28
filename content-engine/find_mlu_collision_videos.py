from reschedule_calendar import CalendarRescheduler

r = CalendarRescheduler()
videos = r.get_scheduled_videos()

print("All scheduled videos:")
for v in videos:
    print(f"  - {v['title']}")
