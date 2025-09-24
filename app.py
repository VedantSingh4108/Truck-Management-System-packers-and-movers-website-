from flask import Flask, request, jsonify, render_template, redirect, url_for, flash
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from flask_bcrypt import Bcrypt
import mysql.connector
from mysql.connector import Error
from functools import wraps
from datetime import date, timedelta, datetime

# --- App and Extension Initialization ---
app = Flask(__name__)
app.config['SECRET_KEY'] = 'a-very-secret-key-that-you-should-change'
bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# --- Database Configuration ---
db_config = {
    'host': 'localhost',
    'user': 'root',
    'password': '',
    'database': 'truck_management_system'
}

def create_connection():
    return mysql.connector.connect(**db_config)

# --- User Model and Loader ---
class User(UserMixin):
    def __init__(self, id, username, role):
        self.id = id
        self.username = username
        self.role = role

@login_manager.user_loader
def load_user(user_id):
    conn = create_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT UserID, Username, Role FROM USERS WHERE UserID = %s", (user_id,))
    user_data = cursor.fetchone()
    cursor.close()
    conn.close()
    if user_data:
        return User(id=user_data['UserID'], username=user_data['Username'], role=user_data['Role'])
    return None

# --- Custom Decorator for Role Checking ---
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'admin':
            flash("You do not have permission to access this page.", "danger")
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated_function

# --- Authentication Routes ---
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        conn = create_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM USERS WHERE Username = %s", (username,))
        user_data = cursor.fetchone()
        cursor.close()
        conn.close()

        if user_data and bcrypt.check_password_hash(user_data['PasswordHash'], password):
            user = User(id=user_data['UserID'], username=user_data['Username'], role=user_data['Role'])
            login_user(user)
            flash('Logged in successfully!', 'success')
            if user.role == 'admin':
                return redirect(url_for('admin_dashboard'))
            else:
                return redirect(url_for('dashboard'))
        else:
            flash('Login Unsuccessful. Please check username and password', 'danger')
    
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        client_name = request.form.get('client_name')
        billing_address = request.form.get('billing_address')
        contact_person = request.form.get('contact_person')

        conn = create_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("SELECT * FROM USERS WHERE Username = %s", (username,))
        existing_user = cursor.fetchone()
        if existing_user:
            flash('Username already exists. Please choose a different one.', 'danger')
            return render_template('register.html')
        
        password_hash = bcrypt.generate_password_hash(password).decode('utf-8')
        
        cursor.execute("INSERT INTO USERS (Username, PasswordHash, Role) VALUES (%s, %s, 'user')", (username, password_hash))
        new_user_id = cursor.lastrowid
        
        cursor.execute("INSERT INTO CLIENT (ClientName, BillingAddress, ContactPerson, UserID) VALUES (%s, %s, %s, %s)",
                       (client_name, billing_address, contact_person, new_user_id))
        
        conn.commit()
        cursor.close()
        conn.close()
        
        flash('Account created successfully! You can now log in.', 'success')
        return redirect(url_for('login'))

    return render_template('register.html')


@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))

# --- User Routes ---
@app.route('/')
@app.route('/dashboard')
@login_required
def dashboard():
    if current_user.role == 'admin':
        return redirect(url_for('admin_dashboard'))

    conn = create_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("SELECT ClientID FROM CLIENT WHERE UserID = %s", (current_user.id,))
    client = cursor.fetchone()
    client_id = client['ClientID'] if client else None

    bookings = []
    if client_id:
        cursor.execute("SELECT * FROM TRIP WHERE ClientID = %s ORDER BY StartDate DESC", (client_id,))
        bookings = cursor.fetchall()

    cursor.execute("SELECT TruckID, RegistrationNum, Model_Id FROM TRUCK")
    trucks = cursor.fetchall()
    cursor.execute("SELECT DriverID, FirstName, LastName FROM DRIVER")
    drivers = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template('dashboard.html', bookings=bookings, trucks=trucks, drivers=drivers)

@app.route('/book_trip', methods=['POST'])
@login_required
def book_trip():
    origin = request.form.get('origin')
    destination = request.form.get('destination')
    start_date_str = request.form.get('start_date')
    end_date_str = request.form.get('end_date')
    truck_id = request.form.get('truck_id')
    driver_id = request.form.get('driver_id')

    try:
        start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
        end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
    except (ValueError, TypeError):
        flash('Invalid date format. Please use YYYY-MM-DD.', 'danger')
        return redirect(url_for('dashboard'))

    # --- New, Updated Validation Logic ---
    today = date.today()
    min_start_date = today + timedelta(days=1)

    # Rule 1: Start date must be tomorrow or later.
    if start_date < min_start_date:
        flash(f'Booking failed. Start date must be tomorrow or later (on or after {min_start_date.strftime("%Y-%m-%d")}).', 'danger')
        return redirect(url_for('dashboard'))

    # Rule 2: The trip duration must be at least 7 days.
    min_duration = timedelta(days=7)
    if (end_date - start_date) < min_duration:
        required_end_date = start_date + min_duration
        flash(f'Booking failed. Trip duration must be at least 7 days. End date must be on or after {required_end_date.strftime("%Y-%m-%d")}.', 'danger')
        return redirect(url_for('dashboard'))
    # --- End of New Validation ---

    conn = create_connection()
    cursor = conn.cursor(dictionary=True)
    
    # --- Conflict Detection Logic ---
    # Check if the selected TRUCK is already booked during the requested dates
    cursor.execute("""
        SELECT TripID FROM TRIP 
        WHERE TruckID = %s AND Status != 'Completed' AND (%s < EndDate AND %s > StartDate)
    """, (truck_id, start_date, end_date))
    truck_conflict = cursor.fetchone()

    if truck_conflict:
        flash(f'Booking failed. The selected truck is already booked during this period (Trip ID: {truck_conflict["TripID"]}).', 'danger')
        cursor.close()
        conn.close()
        return redirect(url_for('dashboard'))

    # Check if the selected DRIVER is already booked during the requested dates
    cursor.execute("""
        SELECT TripID FROM TRIP 
        WHERE DriverID = %s AND Status != 'Completed' AND (%s < EndDate AND %s > StartDate)
    """, (driver_id, start_date, end_date))
    driver_conflict = cursor.fetchone()

    if driver_conflict:
        flash(f'Booking failed. The selected driver is already assigned to a trip during this period (Trip ID: {driver_conflict["TripID"]}).', 'danger')
        cursor.close()
        conn.close()
        return redirect(url_for('dashboard'))
    # --- End of Conflict Detection ---

    cursor.execute("SELECT ClientID FROM CLIENT WHERE UserID = %s", (current_user.id,))
    client = cursor.fetchone()
    
    if client:
        sql = "INSERT INTO TRIP (Origin, Destination, StartDate, EndDate, Status, TruckID, DriverID, ClientID) VALUES (%s, %s, %s, %s, 'Scheduled', %s, %s, %s)"
        val = (origin, destination, start_date, end_date, truck_id, driver_id, client['ClientID'])
        cursor.execute(sql, val)
        conn.commit()
        flash('New trip booked successfully!', 'success')
    else:
        flash('Could not find a client profile for your account.', 'danger')

    cursor.close()
    conn.close()
    return redirect(url_for('dashboard'))

@app.route('/cancel_trip/<int:trip_id>', methods=['POST'])
@login_required
def cancel_trip(trip_id):
    conn = create_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("SELECT c.UserID FROM TRIP t JOIN CLIENT c ON t.ClientID = c.ClientID WHERE t.TripID = %s", (trip_id,))
    trip_owner = cursor.fetchone()

    if trip_owner and trip_owner['UserID'] == current_user.id:
        cursor.execute("DELETE FROM SHIPMENT WHERE TripID = %s", (trip_id,))
        cursor.execute("DELETE FROM TRIP WHERE TripID = %s", (trip_id,))
        conn.commit()
        flash('Booking has been successfully cancelled.', 'success')
    else:
        flash('You do not have permission to cancel this booking.', 'danger')

    cursor.close()
    conn.close()
    return redirect(url_for('dashboard'))

# --- Admin Routes ---
@app.route('/admin')
@login_required
@admin_required
def admin_dashboard():
    conn = create_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("SELECT COUNT(*) as total_users FROM USERS")
    total_users = cursor.fetchone()['total_users']
    
    cursor.execute("SELECT COUNT(*) as ongoing_trips FROM TRIP WHERE Status IN ('Scheduled', 'In Progress')")
    ongoing_trips = cursor.fetchone()['ongoing_trips']

    cursor.execute("""
        SELECT t.*, c.ClientName, d.FirstName, d.LastName 
        FROM TRIP t 
        JOIN CLIENT c ON t.ClientID = c.ClientID 
        JOIN DRIVER d ON t.DriverID = d.DriverID
        ORDER BY t.StartDate DESC
    """)
    all_trips = cursor.fetchall()

    cursor.execute("SELECT * FROM USERS ORDER BY UserID")
    all_users_list = cursor.fetchall()
    
    cursor.close()
    conn.close()
    
    return render_template('admin.html', 
                           total_users=total_users, 
                           ongoing_trips=ongoing_trips, 
                           all_trips=all_trips, 
                           all_users_list=all_users_list)

# --- Add this new route for updating trip status ---
@app.route('/admin/update_trip_status/<int:trip_id>', methods=['POST'])
@login_required
@admin_required
def update_trip_status(trip_id):
    new_status = request.form.get('status')
    valid_statuses = ['Scheduled', 'In Progress', 'Completed', 'Cancelled']

    if new_status in valid_statuses:
        conn = create_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE TRIP SET Status = %s WHERE TripID = %s", (new_status, trip_id))
        conn.commit()
        cursor.close()
        conn.close()
        flash(f'Trip #{trip_id} status has been updated to "{new_status}".', 'success')
    else:
        flash('Invalid status selected.', 'danger')

    return redirect(url_for('admin_dashboard'))


if __name__ == '__main__':
    app.run(debug=True)

