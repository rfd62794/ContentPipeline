from reschedule_calendar import CalendarRescheduler

r = CalendarRescheduler()
videos = r.get_scheduled_videos()
print("MLU videos found:")
for v in videos:
    if 'My Little Universe' in v['title']:
        print(f"  - {v['title']}")
