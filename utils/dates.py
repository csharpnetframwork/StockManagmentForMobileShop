import datetime
import pytz
IST = pytz.timezone("Asia/Kolkata")
def today_range_ist():
    now = datetime.datetime.now(IST)
    start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    end = start + datetime.timedelta(days=1)
    return start, end
