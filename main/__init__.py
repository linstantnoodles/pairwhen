from flask import Flask
from flask import render_template
from flask import session, redirect, url_for
from flask import flash
from main import auth
from main.auth import login_required
import requests
import pytz
import uuid
import json
from datetime import datetime, timedelta
import pymysql.cursors
from flask import request
from flask import g
from main.time import datetime_by_dates, convert_to_datetimes, to_mysql_datetime_str, date_list, ceil_dt, utc_times_to_recipient
import os

from dotenv import load_dotenv
load_dotenv(verbose=True)

app = Flask(__name__)
app.secret_key = os.getenv("APP_SECRET")

def current_user():
    if g.user:
        return g.user
    return None

def notify_admin(text=None, html=None, subject="Alert!"):
    sandbox_url = "https://api.mailgun.net/v3/sandboxc28e2296a38d4429bca1442750ee645b.mailgun.org"
    return requests.post(
        "{}/messages".format(sandbox_url),
     auth=("api", os.getenv("MAILGUN_KEY")),
     data={
       "from": "Admin <catwind7@gmail.com>",
       "to": ["catwind7@gmail.com"],
       "subject": subject,
       "text": text,
       "html": html
    })

def send_simple_message(text=None, html=None, to=None, subject="Meeting confirmed!"):
    sandbox_url = "https://api.mailgun.net/v3/sandboxc28e2296a38d4429bca1442750ee645b.mailgun.org"
    prod_url = "https://api.mailgun.net/v3/mg.pairwhen.com"
    url = prod_url
    if os.getenv("FLASK_ENV") == "development":
        url = sandbox_url
    return requests.post(
        "{}/messages".format(url),
     auth=("api", os.getenv("MAILGUN_KEY")),
     data={
       "from": "support <support@pairwhen.com>",
       "to": [to],
       "subject": subject,
       "text": text,
       "html": html
    })

def connect_to_database():
    connection = pymysql.connect(
        host=os.getenv("DB_HOST"),
        user=os.getenv("DB_USERNAME"),
        password=os.getenv("DB_PASSWORD"),
        db=os.getenv("DATABASE"),
        charset='utf8mb4',
        cursorclass=pymysql.cursors.DictCursor
    )
    return connection

def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = connect_to_database()
    return db

@app.teardown_appcontext
def teardown_db(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

@app.route('/')
def index():
    return render_template('index.html', current_user=current_user())

@app.route('/dashboard')
@login_required
def dashboard():
    user_id = session["user_id"]
    with get_db().cursor() as cursor:
        cursor.execute("SELECT * FROM meetings WHERE user_id = %s ORDER BY created_at DESC", user_id)
        meetings = cursor.fetchall()
        meetings = [{
            "name": meeting["name"] or "Anonymous pairing",
            "created_at_date": meeting["created_at"].strftime("%b %d, %Y"),
            "created_at_time": meeting["created_at"].strftime("%I:%M%p"),
            "url": url_for("show_meeting", meeting_id=meeting["id"])
        } for meeting in meetings]
        return render_template('dashboard.html', current_user=current_user(), meetings=meetings)

@app.route('/invitation/<token>', methods=("GET", "POST"))
def meeting_invitation(token):
    if request.method == "POST":
        guest_email = request.form.get("email")
        guest_name = request.form.get("name")
        guest_message = request.form.get("message")
        guest_timezone = request.form.get("timezone")
        time_ids = request.form.getlist("available_time")

        if not time_ids:
            return redirect(url_for("meeting_invitation", token=token))

        if time_ids[0] == "none_of_the_above":
            host_info = {}
            with get_db().cursor() as cursor:
                query = "SELECT u.email FROM meetings m INNER JOIN users u ON m.user_id = u.id WHERE m.token=%s";
                cursor.execute(query, (token,))
                host_info = cursor.fetchone()
            host_email = host_info["email"]
            email_template = render_template(
                "email/message.html",
                guest_email=guest_email,
                guest_name=guest_name,
                guest_message=guest_message
            )
            email_template_txt = render_template(
                "email/message.txt",
                guest_email=guest_email,
                guest_name=guest_name,
                guest_message=guest_message
            )
            response = send_simple_message(
                subject="{} was unable to find a time! [pairwhen]".format(guest_email),
                to=host_email,
                text=email_template_txt,
                html=email_template
            )
            return render_template(
                "message-sent.html",
                guest_message=guest_message
            )

        db = get_db()
        with db.cursor() as cursor:
            records = [
                (
                    tid,
                    guest_email,
                    guest_timezone
                )
                for tid in time_ids
            ]
            cursor.executemany(
                "INSERT INTO confirmations (time_id, guest_email, timezone) VALUES (%s, %s, %s)",
                records
            )
        db.commit()
        with get_db().cursor() as cursor:
            query = "SELECT u.email FROM meetings m INNER JOIN users u ON m.user_id = u.id WHERE m.token=%s";
            cursor.execute(query, (token,))
            host_info = cursor.fetchone()
            cursor.execute("SELECT * FROM available_times WHERE id = %s", (time_ids[0],))
            time_info = cursor.fetchone()
            host_email = host_info["email"]
            timezone = time_info["timezone"]
            start_dt = time_info["start_datetime"]
            end_dt = time_info["end_datetime"]
            email_template = render_template(
                "email/confirmed.html",
                guest_email=guest_email,
                guest_name=guest_name,
                date = start_dt.strftime("%b %d, %Y"),
                start_time = start_dt.strftime("%I:%M%p"),
                end_time = end_dt.strftime("%I:%M%p"),
                timezone = timezone,
                time_info=time_info
            )
            email_template_txt = render_template(
                "email/confirmed.txt",
                guest_email=guest_email,
                guest_name=guest_name,
                date = start_dt.strftime("%b %d, %Y"),
                start_time = start_dt.strftime("%I:%M%p"),
                end_time = end_dt.strftime("%I:%M%p"),
                timezone = timezone,
                time_info=time_info
            )
            response = send_simple_message(
                subject="{} just confirmed a meeting! [pairwhen]".format(guest_email),
                to=host_email,
                text=email_template_txt,
                html=email_template
            )
            if not response.ok:
                notify_admin(
                    subject="Email delivery failure for {} with status code {}".format(host_email, response.status_code),
                    text=email_template_txt,
                    html=email_template
                )
                return "Sorry! We were unable to notify the host at {}, we're looking into the issue right away.".format(host_email)

            guest_tz = pytz.timezone(guest_timezone)
            start_dt_utc = time_info["start_datetime_utc"]
            end_dt_utc = time_info["end_datetime_utc"]
            local_start_dt = pytz.utc.localize(start_dt_utc).astimezone(guest_tz)
            local_end_dt = pytz.utc.localize(end_dt_utc).astimezone(guest_tz)
            return render_template(
                "meeting-confirmed.html",
                date = local_start_dt.strftime("%b %d, %Y"),
                start_time = local_start_dt.strftime("%I:%M%p"),
                end_time = local_end_dt.strftime("%I:%M%p"),
                timezone = guest_timezone
            )
    with get_db().cursor() as cursor:
        query = "SELECT m.name as meeting_name, u.name as host_name, m.id as meeting_id FROM meetings m INNER JOIN users u ON m.user_id = u.id WHERE m.token = %s";
        cursor.execute(query, (token,))
        meeting_info = cursor.fetchone()
        if not meeting_info:
            return render_template("404.html")
        host_name = meeting_info["host_name"]
        query = "SELECT a.*, COUNT(c.id) as confcount FROM available_times a LEFT JOIN confirmations c ON a.id = c.time_id WHERE meeting_id = %s GROUP BY a.id HAVING COUNT(c.id) = 0 ORDER BY a.start_datetime_utc"
        cursor.execute(query, (meeting_info["meeting_id"],))
        time_range_info = cursor.fetchall()
        time_range_info = list(utc_times_to_recipient(time_range_info))
    return render_template('invite-meeting.html', token=token, host_name=host_name, num_times=len(time_range_info), time_info=json.dumps(time_range_info))

@app.route('/meeting/<int:meeting_id>', methods=("GET", "POST"))
@login_required
def show_meeting(meeting_id):
    if request.method == "POST":
        confirmations = request.form.getlist("confirmation")
        db = get_db()
        with db.cursor() as cursor:
            query = "UPDATE confirmations SET host_accepted = %s WHERE id = %s"
            records = [
                (True, c)
                for c in confirmations
            ]
            cursor.executemany(query, records)
        db.commit()
        return redirect(url_for("show_meeting", meeting_id=meeting_id))

    time_range_info = []
    with get_db().cursor() as cursor:
        cursor.execute("SELECT * FROM meetings WHERE id = %s", (meeting_id,))
        meeting_info = cursor.fetchone()
        if not meeting_info:
            return render_template("404.html")
        query = "SELECT a.id, a.start_datetime, a.end_datetime, c.guest_email, a.timezone host_timezone, c.id cid, c.timezone guest_timezone, c.host_accepted FROM available_times a LEFT JOIN confirmations c on a.id = c.time_id WHERE a.meeting_id = %s ORDER BY a.start_datetime";
        cursor.execute(query, (meeting_id,))
        time_range_info = cursor.fetchall()
        confirmations = {}
        for d in time_range_info:
            did = d["id"]
            start_dt = d["start_datetime"]
            end_dt = d["end_datetime"]
            if did in confirmations:
                confirmations[did]["confirmations"].append({
                    "id": d["cid"],
                    "guest_email": d["guest_email"],
                    "guest_timezone": d["guest_timezone"],
                    "host_accepted": d["host_accepted"]
                })
            else:
                confirmations[did] = {
                    "date": start_dt.strftime("%b %d, %Y"),
                    "time_start": start_dt.strftime("%I:%M%p"),
                    "time_end": end_dt.strftime("%I:%M%p"),
                    "host_timezone": d["host_timezone"],
                    "confirmations": []
                }
                if d["cid"]:
                    confirmations[did]["confirmations"].append({
                        "id": d["cid"],
                        "guest_email": d["guest_email"],
                        "guest_timezone": d["guest_timezone"],
                        "host_accepted": d["host_accepted"]
                    })
    invite_url = url_for("meeting_invitation", token=meeting_info["token"], _external=True)
    return render_template('show-meeting.html', current_user=current_user(), meeting_id=meeting_id, invite_url=invite_url, meeting_info=meeting_info, time_info=confirmations)

@app.route('/meeting/new', methods=("GET", "POST"))
@login_required
def new_meeting():
    curr_user_timezone = current_user().get("timezone", None)
    if request.method == "POST":
        start = datetime.now()
        meeting_name = request.form.get("meeting_name", "Pair Programming")
        time_range_data = json.loads(request.form["time_input_data"])
        user_id = session["user_id"]
        tz = pytz.timezone(curr_user_timezone)
        db = get_db()
        token = uuid.uuid4().hex
        error = None
        if not time_range_data:
            error = "You must add at least one available time!"
            flash(error)
        if time_range_data:
            try:
                with db.cursor() as cursor:
                    cursor.execute(
                        "INSERT INTO meetings (name, user_id, token) VALUES (%s, %s, %s)",
                                (meeting_name, user_id, token)
                        )
                    meeting_id = cursor.lastrowid
                    records = convert_to_datetimes(time_range_data)
                    records = [
                        (
                            to_mysql_datetime_str(tz.localize(time_record[0])),
                            to_mysql_datetime_str(tz.localize(time_record[1])),
                            to_mysql_datetime_str(tz.localize(time_record[0]).astimezone(pytz.utc)),
                            to_mysql_datetime_str(tz.localize(time_record[1]).astimezone(pytz.utc)),
                            curr_user_timezone,
                            meeting_id
                        )
                        for time_record in records
                    ]
                    cursor.executemany(
                        "INSERT INTO available_times (start_datetime, end_datetime, start_datetime_utc, end_datetime_utc, timezone, meeting_id) VALUES (%s, %s, %s, %s, %s, %s)",
                        records
                    )
            except:
                db.rollback()
                raise
            else:
                db.commit()
            return redirect(url_for('show_meeting', meeting_id=meeting_id))
    tz = pytz.timezone(curr_user_timezone)
    local_datetime = datetime.now(tz)
    curr_date_list = date_list(local_datetime)
    preselected_time = ceil_dt(local_datetime, timedelta(minutes=15))
    return render_template('new-meeting.html', timezone=curr_user_timezone, current_user=current_user(), preselected_time=preselected_time, curr_date_list=curr_date_list)

@app.route('/settings')
@login_required
def settings():
    return render_template('settings.html', current_user=current_user())

@app.route('/settings/edit')
@login_required
def settings_edit():
    return render_template('edit-settings.html', current_user=current_user())


@app.route('/about')
def about():
    return render_template('about.html', current_user=current_user())

@app.route('/tour')
def tour():
    return render_template('tour.html', current_user=current_user())

@app.route('/blog')
def blog():
    return render_template('blog.html', current_user=current_user())

@app.route('/calendar/<token>', methods=("GET", "POST"))
def calendar(token):
    if token != "linalan":
        return "Sorry, that calendar does not exist. Please reach out to <support@pairwhen.com>"
    if request.method == "POST":
        host_email = 'catwind7@gmail.com'
        guest_email = request.form.get("email")
        guest_name = request.form.get("name")
        guest_message = request.form.get("message")
        guest_timezone = request.form.get("timezone")
        guest_date = request.form.get("date")
        guest_time = request.form.get("time")
        email_template = render_template(
            "email/calendar-confirmed.html",
            guest_email=guest_email,
            guest_name=guest_name,
            date = guest_date,
            time = guest_time,
            timezone = guest_timezone
        )
        response = send_simple_message(
            subject="{} just schedled a meeting with you! [pairwhen]".format(guest_email),
            to=host_email,
            html=email_template
        )
        if not response.ok:
            notify_admin(
                subject="Email delivery failure for {} with status code {}".format(host_email, response.status_code),
                html=email_template
            )
            return "Sorry! We were unable to notify the host at {}, we're looking into the issue right away.".format(host_email)
        return render_template(
            "calendar-meeting-confirmed.html",
            date = guest_date,
            time = guest_time,
            timezone = guest_timezone
        )
    repeat_availability = {
      "sunday": [
        "09:00AM",
        "10:00AM",
        "10:15AM",
        "10:30AM",
        "11:00AM",
        "11:15AM",
        "11:30AM",
        "01:00PM",
        "01:30PM",
        "02:00PM",
        "02:30PM",
        "03:00PM",
        "03:30PM",
        "04:00PM",
        "04:30PM",
        "05:00PM",
        "05:30PM",
        "07:00PM"
      ],
      "monday": [
        "09:00AM",
        "10:00AM",
        "10:15AM",
        "10:30AM",
        "11:00AM",
        "11:15AM",
        "11:30AM",
        "01:00PM",
        "01:30PM",
        "02:00PM",
        "02:30PM",
        "03:00PM",
        "03:30PM",
        "04:00PM",
        "04:30PM",
        "05:00PM",
        "05:30PM",
        "07:00PM"
      ],
      "tuesday": [
        "09:00AM",
        "10:00AM",
        "10:15AM",
        "10:30AM",
        "11:00AM",
        "11:15AM",
        "11:30AM",
        "01:00PM",
        "01:30PM",
        "02:00PM",
        "02:30PM",
        "03:00PM",
        "03:30PM",
        "04:00PM",
        "04:30PM",
        "05:00PM",
        "05:30PM",
        "07:00PM"
      ],
      "wednesday": [
        "09:00AM",
        "10:00AM",
        "03:30PM",
        "04:00PM",
        "04:30PM",
        "05:00PM",
        "05:30PM",
        "07:00PM"
      ],
      "thursday": [
        "09:00AM",
        "10:00AM",
        "10:15AM",
        "10:30AM",
        "11:00AM",
        "11:15AM",
        "11:30AM",
        "01:00PM",
        "01:30PM",
        "02:00PM",
        "02:30PM",
        "03:00PM",
        "03:30PM",
        "04:00PM",
        "04:30PM",
        "05:00PM",
        "05:30PM",
        "07:00PM"
     ],
      "friday": [
        "09:00AM",
        "10:00AM",
        "10:15AM",
        "10:30AM",
        "11:00AM",
        "11:15AM",
        "11:30AM",
        "01:00PM",
        "01:30PM",
        "02:00PM",
        "02:30PM",
        "03:00PM",
        "03:30PM",
        "04:00PM",
        "04:30PM",
        "05:00PM",
        "05:30PM",
        "07:00PM"
     ],
      "saturday": [
        "09:00AM",
        "10:00AM",
        "10:15AM",
        "10:30AM",
        "11:00AM",
        "11:15AM",
        "11:30AM",
        "01:00PM",
        "01:30PM",
        "02:00PM",
        "02:30PM",
        "03:00PM",
        "03:30PM",
        "04:00PM",
        "04:30PM",
        "05:00PM",
        "05:30PM",
        "07:00PM"
      ]
    }
    return render_template('calendar.html', current_user=current_user(), availability=repeat_availability)

connect_to_database()
app.register_blueprint(auth.bp)

if __name__ == '__main__':
    app.run(host='0.0.0.0')
