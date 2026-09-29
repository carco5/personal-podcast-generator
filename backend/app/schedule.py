from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from app.models import PodcastSettings


def latest_slot(podcast: PodcastSettings, now: datetime) -> datetime | None:
    zone = ZoneInfo(podcast.timezone)
    today = now.astimezone(zone).date()
    for days_back in range(8):
        day = today - timedelta(days=days_back)
        if day.isoweekday() in podcast.schedule_days:
            slot = datetime.combine(day, podcast.schedule_time, tzinfo=zone)
            if slot <= now:
                return slot
    return None


def next_slot(podcast: PodcastSettings, now: datetime) -> datetime | None:
    zone = ZoneInfo(podcast.timezone)
    today = now.astimezone(zone).date()
    for days_ahead in range(8):
        day = today + timedelta(days=days_ahead)
        if day.isoweekday() in podcast.schedule_days:
            slot = datetime.combine(day, podcast.schedule_time, tzinfo=zone)
            if slot > now:
                return slot
    return None
