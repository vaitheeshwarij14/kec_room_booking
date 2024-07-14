from flask import Flask, render_template, request, g, redirect, url_for, session,send_file
import sqlite3
from email.message import EmailMessage
import smtplib
import pandas as pd
from io import BytesIO

application = Flask(__name__)
application.config['DATABASE'] = 'site.db'
application.secret_key = "hello"

EMAIL_ADDRESS = "vishnus.22aim@kongu.edu" 
EMAIL_PASSWORD = "password"  #neet to give password here 
RECIPIENT_EMAIL = "pranavsivakumar328@gmail.com"

def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(application.config['DATABASE'])
        db.row_factory = sqlite3.Row  # Access rows as dictionaries
    return db

def close_db(e=None):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

@application.teardown_appcontext
def teardown_db(e=None):
    close_db()

house_info = {
    1: {
        'rooms': 3,
        'adults': 2,
        'children': 1,
        'description': "NATURAL VIEW",
        'url': "https://saliniyan.github.io/images/room_1.jpg"
    },

    2: {
        'rooms': 4,
        'adults': 3,
        'children': 2,
        'description': "HOTEL NEAR",
        'url': "https://saliniyan.github.io/images/room_2.jpg"
    },
    3: {
        'rooms': 2,
        'adults': 1,
        'children': 0,
        'description': "PARKING LOT",
        'url': "https://saliniyan.github.io/images/room_3.jpg"
    }
}

def create_tables():
    with application.app_context():
        db = get_db()
        cursor = db.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS reservations (
                id INTEGER PRIMARY KEY,
                check_in DATE,
                check_out DATE,
                House_NO INTEGER NOT NULL,
                status varchar(50),
                name TEXT,
                designation TEXT,
                phone_no TEXT,
                purpose_of_visit TEXT,
                originator_name TEXT,
                department_contact_no TEXT,
                no_of_breakfast INTEGER,
                no_of_lunch INTEGER,
                no_of_dinner INTEGER,
                FOREIGN KEY (House_NO) REFERENCES houses(id)
            );
        ''')
        db.commit()

@application.route('/')
def index():
    return render_template('login.html')

@application.route('/authenticate', methods=['POST'])
def authenticate():
    username = request.form['username']
    password = request.form['password']

    if username == 's.ac.in' and password == '123':
        session['username'] = username
        return redirect(url_for('index1'))  # Redirect to index1 route
    elif username == 'b' and password == '456':
        session['username'] = username
        return redirect(url_for('admin_panel'))  # Redirect to admin_panel route
    else:
        return "Invalid credentials"

@application.route('/index1')
def index1():
    if 'username' in session and session['username'] == 's.ac.in':
        return render_template('index1.html')
    else:
        return redirect(url_for('index'))

@application.route('/submit', methods=['POST'])
def submit():
    check_in = request.form['check_in']
    check_out = request.form['check_out']
    rooms_needed = int(request.form['rooms'])

    if not check_in or not check_out or rooms_needed <= 0:
        return "Invalid input. Please fill in all fields correctly."

    db = get_db()
    cursor = db.cursor()

    available_houses = []
    for house_id, info in house_info.items():
        if info['rooms'] >= rooms_needed:
            available_houses.append(house_id)

    available_results = []
    for house_id in available_houses:
        cursor.execute('''
            SELECT COUNT(*) FROM reservations
            WHERE House_NO = ? AND
            (check_in BETWEEN ? AND ? OR check_out BETWEEN ? AND ?) AND
            status != 'rejected';  -- Exclude bookings with status 'rejected'
        ''', (house_id, check_in, check_out, check_in, check_out))
        booking_count = cursor.fetchone()[0]
        if booking_count == 0:
            house_description = house_info[house_id]['description']
            house_url = house_info[house_id]['url']
            available_results.append({
                'house_id': house_id,
                'rooms': house_info[house_id]['rooms'],
                'description': house_description,
                'url': house_url
            })


    if available_results:
        return render_template('available_houses.html', available_results=available_results)
    else:
        return "Sorry, no houses are available for your requested dates or rooms."

@application.route('/book', methods=['POST'])
def book():
    house_id = request.form['house_id']
    check_in = request.form['check_in']
    check_out = request.form['check_out']

    if not house_id or not check_in or not check_out:
        return "Invalid input. Please fill in all fields correctly."

    # Render the guest details form, passing house booking details as parameters
    return render_template('guest_details_form.html', house_id=house_id, check_in=check_in, check_out=check_out)

@application.route('/submit_form', methods=['POST'])
def submit_form():
    # Extract guest details from the form
    name = request.form['name']
    designation = request.form['designation']
    phone_no = request.form['phone_no']
    purpose_of_visit = request.form['purpose_of_visit']
    originator_name = request.form['originator_name']
    department_contact_no = request.form['department_contact_no']
    no_of_breakfast = request.form['no_of_breakfast']
    no_of_lunch = request.form['no_of_lunch']
    no_of_dinner = request.form['no_of_dinner']
    house_id = request.form['house_id']
    check_in = request.form['check_in']
    check_out = request.form['check_out']

    # Insert both guest details and house booking details into the database
    db = get_db()
    cursor = db.cursor()
    status = "pending"

    cursor.execute('''
        INSERT INTO reservations (check_in, check_out, House_NO, status,  name, designation, phone_no, purpose_of_visit, originator_name, department_contact_no, no_of_breakfast, no_of_lunch, no_of_dinner)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
    ''', (check_in, check_out, house_id, status, name, designation, phone_no, purpose_of_visit, originator_name, department_contact_no, no_of_breakfast, no_of_lunch, no_of_dinner))

    db.commit()
    success_message = "Your request is successfully sent to admin"
    return render_template('success.html', success_message=success_message)

@application.route('/admin', methods=['GET', 'POST'])
def admin_panel():
    if 'username' not in session or session['username'] != 'b':
        return redirect(url_for('index')) 

    if request.method == 'GET':
        db = get_db()
        cursor = db.cursor()
        cursor.execute('''
            SELECT * FROM reservations WHERE status = 'pending';
        ''')
        pending_bookings = cursor.fetchall()
        
        return render_template('admin_panel.html', pending_bookings=pending_bookings)
    elif request.method == 'POST':
        booking_id = request.form['booking_id']
        action = request.form['action']
        reason = request.form['reason']

        if action == 'accept':
            db = get_db()
            cursor = db.cursor()
            cursor.execute('''
                UPDATE reservations SET status = 'accepted' WHERE id = ?;
            ''', (booking_id,))
            db.commit()
            # Notify user via email that booking is accepted
            #send_email('accepted', booking_id, reason)
        elif action == 'reject':
            db = get_db()
            cursor = db.cursor()
            cursor.execute('''
                UPDATE reservations SET status = 'rejected' WHERE id = ?;
            ''', (booking_id,))
            db.commit()
            # Notify user via email that booking is rejected
            #send_email('rejected', booking_id, reason)

        return redirect(url_for('admin_panel'))

# def send_email(status, booking_id, reason):
#     msg = EmailMessage()
#     msg['Subject'] = 'Booking Status Notification'
#     msg['From'] = EMAIL_ADDRESS
#     msg['To'] = RECIPIENT_EMAIL

#     if status == 'accepted':
#         msg.set_content(f"""\
#             Booking Accepted!
#             Your booking for the room with ID {booking_id} has been accepted.

#         """)
#     elif status == 'rejected':
#         msg.set_content(f"""\
#             Booking Rejected!
#             We regret to inform you that your booking for the room with ID {booking_id} has been rejected.

#             Reason: {reason}
#         """)

#     with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
#         smtp.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
#         smtp.send_message(msg)

@application.route('/accepted_bookings', methods=['GET'])
def database_view():
    # Connect to the SQLite database
    conn = sqlite3.connect(application.config['DATABASE'])

    query = "SELECT * FROM reservations WHERE status = 'accepted';"

    # Fetch data into a pandas DataFrame
    df = pd.read_sql_query(query, conn)

    conn.close()

    # Convert the DataFrame to an Excel file in memory
    excel_file = BytesIO()
    df.to_excel(excel_file, index=False)
    excel_file.seek(0)

    # Send the Excel file as a response to the client
    return send_file(
        excel_file,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment=True,
        download_name='accepted_bookings.xlsx'
    )

if __name__ == '__main__':
    create_tables()
    application.run(debug=True)
