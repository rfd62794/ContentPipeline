from reschedule_calendar import CalendarRescheduler

r = CalendarRescheduler()
videos = r.get_scheduled_videos()

# MLU videos we need to find
search_terms = [
    "cheesing this boss",
    "it just picks the right tool automatically", 
    "the resources respawn fast enough to never run out",
    "geez. this opened up",
    "purple crystal is the next barrier for everything"
]

print("Searching for MLU videos with collision issues:")
for term in search_terms:
    found = []
    for v in videos:
        if term.lower() in v['title'].lower() and 'My Little Universe' in v['title']:
            found.append(v['title'])
    if found:
        print(f"  '{term}' found:")
        for title in found:
            print(f"    - {title}")
    else:
        print(f"  '{term}' NOT FOUND")
