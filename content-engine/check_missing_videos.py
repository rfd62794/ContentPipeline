from reschedule_calendar import CalendarRescheduler

r = CalendarRescheduler()
videos = r.get_scheduled_videos()

# Videos that failed in the plan
failed_titles = [
    "My Little Universe — I am okay cheesing this boss",
    "My Little Universe — this is a good passive game", 
    "My Little Universe — it just picks the right tool automatically",
    "My Little Universe — the resources respawn fast enough to never run out",
    "My Little Universe — geez. this opened up.",
    "My Little Universe — purple crystal is the next barrier for everything",
    "Everything is Crab — I got exactly what I needed. the altar took the rest."
]

print("Checking for failed videos:")
for title in failed_titles:
    found = any(v['title'] == title for v in videos)
    print(f"  {title}: {'FOUND' if found else 'NOT FOUND'}")

print("\nAll scheduled MLU videos:")
for v in videos:
    if 'My Little Universe' in v['title']:
        print(f"  - {v['title']}")
