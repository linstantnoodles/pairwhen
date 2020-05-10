from main import time
from datetime import datetime, timedelta
from pytz import timezone

def test_time_list():
    result = list(time.time_list())
    result = [x.strftime("%I:%M%p") for x in result]
    first_five = result[0:5]
    last_five = result[-5:]

    assert first_five == [
        "12:00AM",
        "12:15AM",
        "12:30AM",
        "12:45AM",
        "01:00AM"
    ]

    assert last_five == [
        "10:45PM",
        "11:00PM",
        "11:15PM",
        "11:30PM",
        "11:45PM"
    ]

def test_date_list():
    # given a timezone aware date ... give me the next 7 days including today
    tz = timezone('America/New_York')
    current_datetime = datetime(2020, 5, 1, tzinfo=tz)
    result = list(time.date_list(current_datetime))
    result = [x.strftime("%Y-%m-%d") for x in result]

    assert result == [
        "2020-05-01",
        "2020-05-02",
        "2020-05-03",
        "2020-05-04",
        "2020-05-05",
        "2020-05-06",
        "2020-05-07"
    ]

def test_datetime_at_or_after_default():
    tz = timezone('America/New_York')
    current_datetime = datetime(2020, 4, 22, 8, 0, tzinfo=tz)
    expected_datetimes = [
        datetime(2020, 4, 22, 8, 0, tzinfo=tz)
    ]

    assert list(time.datetime_at_or_after(current_datetime)) == expected_datetimes

def test_datetime_at_or_after_with_count():
    tz = timezone('America/New_York')
    current_datetime = datetime(2020, 4, 22, 8, 0, tzinfo=tz)

    assert list(time.datetime_at_or_after(current_datetime, count=1)) == [
        datetime(2020, 4, 22, 8, 0, tzinfo=tz)
    ]
    assert list(time.datetime_at_or_after(current_datetime, count=2)) == [
        datetime(2020, 4, 22, 8, 0, tzinfo=tz),
        datetime(2020, 4, 22, 8, 15, tzinfo=tz)
    ]
    assert list(time.datetime_at_or_after(current_datetime, count=3)) == [
        datetime(2020, 4, 22, 8, 0, tzinfo=tz),
        datetime(2020, 4, 22, 8, 15, tzinfo=tz),
        datetime(2020, 4, 22, 8, 30, tzinfo=tz)
    ]

def test_datetime_now_til_end_of_day():
    tz = timezone('America/New_York')
    current_datetime = datetime(2020, 4, 22, 23, 0, tzinfo=tz)

    expected_datetimes = [
        datetime(2020, 4, 22, 23, 0, tzinfo=tz),
        datetime(2020, 4, 22, 23, 15, tzinfo=tz),
        datetime(2020, 4, 22, 23, 30, tzinfo=tz),
        datetime(2020, 4, 22, 23, 45, tzinfo=tz) ]
    assert list(time.datetime_til_end_of_day(current_datetime)) == expected_datetimes

def test_ceil():
    tz = timezone('America/New_York')
    current_datetime = datetime(2020, 4, 22, 23, 12, tzinfo=tz)

    assert time.ceil_dt(current_datetime, timedelta(minutes=30)) == datetime(2020, 4, 22, 23, 30, tzinfo=tz)
    assert time.ceil_dt(current_datetime, timedelta(minutes=15)) == datetime(2020, 4, 22, 23, 15, tzinfo=tz)

def test_show_times():
    time_data = [
        {
            'id': 1,
            'meeting_id': 4,
            'start_datetime': datetime(2020, 5, 1, 0, 0),
            'end_datetime': datetime(2020, 5, 1, 0, 0),
            'timezone': 'America/New_York'
        }
    ]
    assert list(time.show_times(time_data)) == [
        {
            "id": 1,
            "date": "May 01, 2020",
            "time_start": "12:00AM",
            "time_end": "12:00AM",
            "timezone": "America/New_York"
        }
    ]

def test_parse_input_into_datetimes():
    data = [
        {
            "date_available": "2020-05-01",
            "date_available_text": "May 01, 2020",
            "time_start_available": "12:00AM",
            "time_end_available": "12:15AM"
        }
    ]
    assert list(time.convert_to_datetimes(data)) == [
       (datetime(2020, 5, 1, 0, 0), datetime(2020, 5, 1, 0, 15))
    ]

def test_to_mysql_datetime_str():
    dt = datetime(2020, 5, 1, 12, 15)
    assert time.to_mysql_datetime_str(dt) == "2020-05-01 12:15:00"
