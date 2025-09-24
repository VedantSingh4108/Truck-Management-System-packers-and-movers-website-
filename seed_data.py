import mysql.connector
from mysql.connector import Error
from flask_bcrypt import Bcrypt

# Create a dummy Flask app context to use Bcrypt
from flask import Flask
app = Flask(__name__)
bcrypt = Bcrypt(app)

# --- Database Configuration ---
db_config = {
    'host': 'localhost',
    'user': 'root',
    'password': '',
    'database': 'truck_management_system'
}

def run_seed():
    """
    Connects to the database and inserts initial data for owners, users, 
    clients, drivers, trucks, and a sample trip.
    """
    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor()

        # --- Clear existing data to prevent duplicates ---
        print("Clearing old data...")
        cursor.execute("SET FOREIGN_KEY_CHECKS = 0;")
        tables_to_clear = ['TRIP', 'CLIENT', 'USERS', 'OWNER', 'DRIVER', 'TRUCK']
        for table in tables_to_clear:
            cursor.execute(f"TRUNCATE TABLE {table};")
        cursor.execute("SET FOREIGN_KEY_CHECKS = 1;")
        print("Old data cleared.")

        # --- Hash Passwords ---
        admin_password_hash = bcrypt.generate_password_hash('admin123').decode('utf-8')
        user_password_hash = bcrypt.generate_password_hash('user123').decode('utf-8')

        # --- SQL INSERT Statements ---
        sql_statements = {
            "owner": "INSERT INTO OWNER (OwnerName, ContactInfo, Address) VALUES ('Speedy Logistics', 'contact@speedy.com', '123 Logistics Lane');",
            "admin_user": f"INSERT INTO USERS (Username, PasswordHash, Role) VALUES ('admin', '{admin_password_hash}', 'admin');",
            "test_user": f"INSERT INTO USERS (Username, PasswordHash, Role) VALUES ('testuser', '{user_password_hash}', 'user');",
            # We need the UserID of 'testuser' to link it to a client. We assume it will be 2.
            "client": "INSERT INTO CLIENT (ClientName, BillingAddress, ContactPerson, UserID) VALUES ('Global Electronics', '789 Tech Park', 'Priya Sharma', 2);",
            "driver": "INSERT INTO DRIVER (FirstName, LastName, LicenseNumber) VALUES ('Rajesh', 'Kumar', 'DL123XYZ');",
            # We need the OwnerID, we assume it will be 1.
            "truck": "INSERT INTO TRUCK (RegistrationNum, Model_Id, Capacity_in_Tons, OwnerID) VALUES ('TN-01-AB-1234', 'Tata Ultra', 10, 1);",
            # We need TruckID, DriverID, ClientID. Assume they are all 1.
            "trip": "INSERT INTO TRIP (Origin, Destination, StartDate, Status, TruckID, DriverID, ClientID) VALUES ('Chennai', 'Bangalore', '2025-10-10', 'Scheduled', 1, 1, 1);"
        }
        
        print("Inserting new dummy data...")
        for key, query in sql_statements.items():
            cursor.execute(query)
            print(f"  - Inserted {key} data.")

        conn.commit()
        print("\nDummy data inserted successfully!")

    except Error as err:
        print(f"\nError: {err}")
    finally:
        if 'conn' in locals() and conn.is_connected():
            cursor.close()
            conn.close()
            print("MySQL connection is closed.")

# --- Main execution point ---
if __name__ == '__main__':
    # Before running, make sure you've installed the necessary library
    print("This script will populate your database with initial data.")
    print("Have you installed flask-bcrypt? If not, run: pip install Flask-Bcrypt")
    input("Press Enter to continue...")
    run_seed()

