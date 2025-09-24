from flask import Flask, request, jsonify, render_template, redirect, url_for, flash
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from flask_bcrypt import Bcrypt
import mysql.connector
from mysql.connector import Error
from functools import wraps

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
            return redirect(url_for('register'))

        hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
        
        cursor.execute("INSERT INTO USERS (Username, PasswordHash, Role) VALUES (%s, %s, 'user')", (username, hashed_password))
        new_user_id = cursor.lastrowid

        cursor.execute("INSERT INTO CLIENT (ClientName, BillingAddress, ContactPerson, UserID) VALUES (%s, %s, %s, %s)", 
                       (client_name, billing_address, contact_person, new_user_id))
        
        conn.commit()
        cursor.close()
        conn.close()

        flash('Your account has been created! You can now log in.', 'success')
        return redirect(url_for('login'))

    return render_template('register.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))

# --- Main Application Routes ---
@app.route('/')
@app.route('/dashboard')
@login_required
def dashboard():
    conn = create_connection()
    cursor = conn.cursor(dictionary=True)
    
    # Get ClientID for the current user
    cursor.execute("SELECT ClientID FROM CLIENT WHERE UserID = %s", (current_user.id,))
    client = cursor.fetchone()
    
    user_bookings = []
    if client:
        cursor.execute("SELECT * FROM TRIP WHERE ClientID = %s ORDER BY StartDate DESC", (client['ClientID'],))
        user_bookings = cursor.fetchall()
    
    cursor.execute("SELECT TruckID, RegistrationNum, Model_Id FROM TRUCK")
    available_trucks = cursor.fetchall()
    cursor.execute("SELECT DriverID, FirstName, LastName FROM DRIVER")
    available_drivers = cursor.fetchall()
    
    cursor.close()
    conn.close()
    
    return render_template('dashboard.html', bookings=user_bookings, trucks=available_trucks, drivers=available_drivers)

@app.route('/book_trip', methods=['POST'])
@login_required
def book_trip():
    origin = request.form.get('origin')
    destination = request.form.get('destination')
    start_date = request.form.get('start_date')
    truck_id = request.form.get('truck_id')
    driver_id = request.form.get('driver_id')
    
    conn = create_connection()
    cursor = conn.cursor(dictionary=True)
    
    cursor.execute("SELECT ClientID FROM CLIENT WHERE UserID = %s", (current_user.id,))
    client = cursor.fetchone()
    
    if client:
        sql = "INSERT INTO TRIP (Origin, Destination, StartDate, Status, TruckID, DriverID, ClientID) VALUES (%s, %s, %s, 'Scheduled', %s, %s, %s)"
        val = (origin, destination, start_date, truck_id, driver_id, client['ClientID'])
        cursor.execute(sql, val)
        conn.commit()
        flash('New trip booked successfully!', 'success')
    else:
        flash('Could not find a client profile for your user.', 'danger')
        
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
    
    # Fetch stats
    cursor.execute("SELECT count(*) as total FROM USERS")
    total_users = cursor.fetchone()['total']
    cursor.execute("SELECT count(*) as total FROM TRIP WHERE Status = 'In Progress'")
    ongoing_trips = cursor.fetchone()['total']
    
    # Fetch all users and trips for tables
    cursor.execute("SELECT UserID, Username, Role FROM USERS")
    all_users = cursor.fetchall()
    cursor.execute("""
        SELECT t.TripID, t.Origin, t.Destination, t.Status, c.ClientName
        FROM TRIP t
        JOIN CLIENT c ON t.ClientID = c.ClientID
        ORDER BY t.StartDate DESC
    """)
    all_trips = cursor.fetchall()
    
    cursor.close()
    conn.close()
    
    return render_template('admin.html', total_users=total_users, ongoing_trips=ongoing_trips, users=all_users, trips=all_trips)


if __name__ == '__main__':
    app.run(debug=True)

