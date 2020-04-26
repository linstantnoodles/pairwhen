from flask import Flask
from flask import render_template
import mysql.connector
from flask import g

app = Flask(__name__)

def connect_to_database():
    return mysql.connector.connect(
        user='root',
        password='',
        host='127.0.0.1',
        database='booker'
    )

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
    return render_template('index.html')

connect_to_database()

if __name__ == '__main__':
    app.run(host='0.0.0.0')
