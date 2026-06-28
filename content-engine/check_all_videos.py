from reschedule_calendar import CalendarRescheduler

r = CalendarRescheduler()

# Try to get all videos, not just scheduled
# The API might be filtering by status
print("Checking API to see if we can get all videos...")

# Let's modify the get_scheduled_videos method to not filter by status
service = r.service

# Get all videos from the channel
request = service.search().list(
    part='snippet',
    channelId='UCrfd62794',  # This might need the actual channel ID
    maxResults=50,
    order='date'
)

print("Note: Need actual channel ID to search all videos")
