import mysql.connector
from mysql.connector import Error
from flask_bcrypt import Bcrypt
from flask import Flask

# --- Flask + Bcrypt setup ---
app = Flask(__name__)
bcrypt = Bcrypt(app)

# --- DB Config ---
db_config = {
    'host': 'localhost',
    'user': 'root',
    'password': '',
    'database': 'truck_management_system'
}

def recreate_schema(cursor):
    # Disable FK checks
    cursor.execute("SET FOREIGN_KEY_CHECKS = 0")

    # Drop tables regardless of FK dependencies
    drop_order = [
        "SHIPMENT", "MAINTENANCE", "TRIP",
        "TRUCK", "DRIVER", "CLIENT",
        "USERS", "GOODS", "OWNER"
    ]
    for table in drop_order:
        cursor.execute(f"DROP TABLE IF EXISTS {table}")

    # Re-enable FK checks
    cursor.execute("SET FOREIGN_KEY_CHECKS = 1")

    # Now create tables fresh with AUTO_INCREMENT
    cursor.execute("""
        CREATE TABLE OWNER (
            OwnerID INT AUTO_INCREMENT PRIMARY KEY,
            OwnerName VARCHAR(100),
            ContactInfo VARCHAR(100),
            Address VARCHAR(255)
        )
    """)

    cursor.execute("""
        CREATE TABLE USERS (
            UserID INT AUTO_INCREMENT PRIMARY KEY,
            Username VARCHAR(50) UNIQUE,
            PasswordHash VARCHAR(255),
            Role ENUM('admin','user')
        )
    """)

    cursor.execute("""
        CREATE TABLE CLIENT (
            ClientID INT AUTO_INCREMENT PRIMARY KEY,
            ClientName VARCHAR(100),
            BillingAddress VARCHAR(255),
            ContactPerson VARCHAR(100),
            UserID INT,
            FOREIGN KEY (UserID) REFERENCES USERS(UserID)
        )
    """)

    cursor.execute("""
        CREATE TABLE DRIVER (
            DriverID INT AUTO_INCREMENT PRIMARY KEY,
            FirstName VARCHAR(50),
            LastName VARCHAR(50),
            LicenseNumber VARCHAR(50)
        )
    """)

    cursor.execute("""
        CREATE TABLE TRUCK (
            TruckID INT AUTO_INCREMENT PRIMARY KEY,
            RegistrationNum VARCHAR(50),
            Model_Id VARCHAR(100),
            Capacity_in_Tons INT,
            OwnerID INT,
            FOREIGN KEY (OwnerID) REFERENCES OWNER(OwnerID)
        )
    """)

    cursor.execute("""
        CREATE TABLE GOODS (
            GoodsID INT AUTO_INCREMENT PRIMARY KEY,
            GoodsName VARCHAR(100),
            GoodsType VARCHAR(100)
        )
    """)

    cursor.execute("""
        CREATE TABLE TRIP (
            TripID INT AUTO_INCREMENT PRIMARY KEY,
            Origin VARCHAR(100),
            Destination VARCHAR(100),
            StartDate DATE,
            Status VARCHAR(50),
            TruckID INT,
            DriverID INT,
            ClientID INT,
            FOREIGN KEY (TruckID) REFERENCES TRUCK(TruckID),
            FOREIGN KEY (DriverID) REFERENCES DRIVER(DriverID),
            FOREIGN KEY (ClientID) REFERENCES CLIENT(ClientID)
        )
    """)

    cursor.execute("""
        CREATE TABLE MAINTENANCE (
            MaintenanceID INT AUTO_INCREMENT PRIMARY KEY,
            TruckID INT,
            MaintenanceDate DATE,
            Description VARCHAR(255),
            FOREIGN KEY (TruckID) REFERENCES TRUCK(TruckID)
        )
    """)

    cursor.execute("""
        CREATE TABLE SHIPMENT (
            ShipmentID INT AUTO_INCREMENT PRIMARY KEY,
            TripID INT,
            GoodsID INT,
            Quantity INT,
            FOREIGN KEY (TripID) REFERENCES TRIP(TripID),
            FOREIGN KEY (GoodsID) REFERENCES GOODS(GoodsID)
        )
    """)

def seed_data(cursor):
    # Hash passwords
    admin_pass = bcrypt.generate_password_hash('admin123').decode('utf-8')
    user_pass = bcrypt.generate_password_hash('user123').decode('utf-8')

    # Owners
    cursor.execute("INSERT INTO OWNER (OwnerName, ContactInfo, Address) VALUES ('Speedy Logistics', 'contact@speedy.com', '123 Logistics Lane, Chennai')")
    cursor.execute("INSERT INTO OWNER (OwnerName, ContactInfo, Address) VALUES ('Bharat Transport', 'bharat@bt.com', '45 MG Road, Mumbai')")

    # Users
    cursor.execute("INSERT INTO USERS (Username, PasswordHash, Role) VALUES ('admin', %s, 'admin')", (admin_pass,))
    cursor.execute("INSERT INTO USERS (Username, PasswordHash, Role) VALUES ('rajesh_k', %s, 'user')", (user_pass,))

    # Clients
    cursor.execute("INSERT INTO CLIENT (ClientName, BillingAddress, ContactPerson, UserID) VALUES ('Global Electronics', '789 Tech Park, Pune', 'Priya Sharma', 2)")

    # Drivers
    cursor.execute("INSERT INTO DRIVER (FirstName, LastName, LicenseNumber) VALUES ('Rajesh', 'Kumar', 'DL123XYZ')")
    cursor.execute("INSERT INTO DRIVER (FirstName, LastName, LicenseNumber) VALUES ('Anil', 'Mehta', 'MH56ABC')")

    # Trucks
    cursor.execute("INSERT INTO TRUCK (RegistrationNum, Model_Id, Capacity_in_Tons, OwnerID) VALUES ('TN-01-AB-1234', 'Tata Ultra', 10, 1)")
    cursor.execute("INSERT INTO TRUCK (RegistrationNum, Model_Id, Capacity_in_Tons, OwnerID) VALUES ('MH-12-XY-9876', 'Ashok Leyland Dost', 8, 2)")

    # Goods
    cursor.execute("INSERT INTO GOODS (GoodsName, GoodsType) VALUES ('Electronic Components', 'Fragile')")
    cursor.execute("INSERT INTO GOODS (GoodsName, GoodsType) VALUES ('Cement Bags', 'Construction')")

    # Trips
    cursor.execute("INSERT INTO TRIP (Origin, Destination, StartDate, Status, TruckID, DriverID, ClientID) VALUES ('Chennai', 'Bangalore', '2025-10-10', 'Scheduled', 1, 1, 1)")
    cursor.execute("INSERT INTO TRIP (Origin, Destination, StartDate, Status, TruckID, DriverID, ClientID) VALUES ('Mumbai', 'Pune', '2025-10-15', 'Scheduled', 2, 2, 1)")

    # Maintenance
    cursor.execute("INSERT INTO MAINTENANCE (TruckID, MaintenanceDate, Description) VALUES (1, '2025-09-01', 'Oil Change')")
    cursor.execute("INSERT INTO MAINTENANCE (TruckID, MaintenanceDate, Description) VALUES (2, '2025-09-10', 'Brake Inspection')")

    # Shipments
    cursor.execute("INSERT INTO SHIPMENT (TripID, GoodsID, Quantity) VALUES (1, 1, 100)")
    cursor.execute("INSERT INTO SHIPMENT (TripID, GoodsID, Quantity) VALUES (2, 2, 200)")

    # Add more shipments
    cursor.execute("INSERT INTO SHIPMENT (TripID, GoodsID, Quantity) VALUES (1, 2, 50)")
    cursor.execute("INSERT INTO SHIPMENT (TripID, GoodsID, Quantity) VALUES (2, 1, 75)")
    cursor.execute("INSERT INTO SHIPMENT (TripID, GoodsID, Quantity) VALUES (2, 2, 150)")

def run_seed():
    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor()

        print("Dropping & recreating schema...")
        recreate_schema(cursor)

        print("Inserting independent + dependent data...")
        seed_data(cursor)

        conn.commit()
        print("Dummy data inserted successfully!")

    except Error as err:
        print(f"Error: {err}")
    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()
            print("MySQL connection is closed.")

if __name__ == '__main__':
    run_seed()
