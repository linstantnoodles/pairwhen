from datetime import datetime, time
from datetime import timedelta
import pytz

def time_list():
    curr_time = datetime.min
    limit = datetime.min + timedelta(days=1)
    while curr_time < limit:
        yield curr_time
        curr_time = curr_time + timedelta(minutes=15)

def date_list(start_dt):
    curr_time = start_dt
    limit = start_dt + timedelta(days=7)
    while curr_time < limit:
        yield curr_time
        curr_time = curr_time + timedelta(days=1)

def datetime_by_dates(dt, days=3):
    date_today = dt.date()
    starting_time = ceil_dt(dt, timedelta(minutes=15))
    datetimes = datetime_til_end_of_day(starting_time)
    return {
        date_today.isoformat(): {
            "options": [(d.isoformat(), d.astimezone(pytz.utc))for d in datetimes]
        }
    }

def ceil_dt(dt, delta):
    datetime_next_hour = datetime(dt.year, dt.month, dt.day, dt.hour, tzinfo=dt.tzinfo)
    diff = datetime_next_hour - dt
    return dt + (diff % delta)

def datetime_til_end_of_day(dt):
    date_today = dt.date()
    date_tomorrow = dt.date() + timedelta(days=1)
    datetime_tomorrow = datetime(date_tomorrow.year, date_tomorrow.month, date_tomorrow.day, tzinfo=dt.tzinfo)
    remaining_seconds = (datetime_tomorrow - dt).seconds
    remaining_minutes = remaining_seconds // 60
    remaining_step_blocks = remaining_minutes // 15
    return datetime_at_or_after(dt, count=remaining_step_blocks)

def convert_to_datetimes(data):
    for d in data:
        date = d["date_available"]
        tstart = d["time_start_available"]
        tend = d["time_end_available"]
        tstart_full = "{} {}".format(date, tstart)
        tend_full = "{} {}".format(date, tend)
        dformat = "%Y-%m-%d %I:%M%p"
        tstart_dt = datetime.strptime(tstart_full, dformat)
        tend_dt = datetime.strptime(tend_full, dformat)
        yield (tstart_dt, tend_dt)

def to_mysql_datetime_str(dt):
    return dt.strftime('%Y-%m-%d %H:%M:%S')

def show_times(data):
    for d in data:
        start_dt = d["start_datetime"]
        end_dt = d["end_datetime"]
        yield {
            "id": d["id"],
            "date": start_dt.strftime("%b %d, %Y"),
            "time_start": start_dt.strftime("%I:%M%p"),
            "time_end": end_dt.strftime("%I:%M%p"),
            "timezone": d["timezone"]
        }

def utc_times_to_recipient(data):
    for d in data:
        start_dt = d["start_datetime"]
        end_dt = d["end_datetime"]
        start_dt_utc = d["start_datetime_utc"]
        end_dt_utc = d["end_datetime_utc"]
        yield {
            "id": d["id"],
            "date": start_dt.strftime("%b %d, %Y"),
            "time_start": start_dt.strftime("%I:%M%p"),
            "time_end": end_dt.strftime("%I:%M%p"),
            "time_start_utc": start_dt_utc.isoformat(),
            "time_end_utc": end_dt_utc.isoformat(),
            "timezone": d["timezone"]
        }

def datetime_at_or_after(dt, count=1):
    for i in range(0, count * 15, 15):
        yield (dt + timedelta(minutes=i))


def generate_options(values, value_f, display_f):
    for v in values:
        print('<option value="{}">{}</option>'.format(v.strftime(value_f), v.strftime(display_f)))

if __name__ == "__main__":
    # .strftime("%Y-%m-%d")
    # .strftime("%I:%M%p")
    dl = date_list(datetime.now())
    tl = time_list()
    generate_options(dl, "%Y-%m-%d", "%b %d, %Y")
    generate_options(tl, "%I:%M%p", "%I:%M%p")
