import mysql.connector

db_config = {
    'host': 'localhost',
    'user': 'root',
    'password': '',
    'database': 'truck_management_system'
}

create_table_queries = [
    """
    CREATE TABLE IF NOT EXISTS OWNER (
        OwnerID INT PRIMARY KEY,
        OwnerName VARCHAR(255),
        ContactInfo VARCHAR(255),
        Address VARCHAR(255)
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS TRUCK (
        TruckID INT PRIMARY KEY,
        RegistrationNum VARCHAR(255),
        Model_Id VARCHAR(255),
        Capacity_in_Tons INT,
        OwnerID INT,
        FOREIGN KEY (OwnerID) REFERENCES OWNER(OwnerID)
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS DRIVER (
        DriverID INT PRIMARY KEY,
        FirstName VARCHAR(255),
        LastName VARCHAR(255),
        LicenseNumber VARCHAR(255),
        ContactNumber VARCHAR(255)
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS CLIENT (
        ClientID INT PRIMARY KEY,
        ClientName VARCHAR(255),
        BillingAddress VARCHAR(255),
        ContactPerson VARCHAR(255)
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS TRIP (
        TripID INT PRIMARY KEY,
        Origin VARCHAR(255),
        Destination VARCHAR(255),
        StartDate DATE,
        EndDate DATE,
        Status VARCHAR(255),
        TruckID INT,
        DriverID INT,
        ClientID INT,
        FOREIGN KEY (TruckID) REFERENCES TRUCK(TruckID),
        FOREIGN KEY (DriverID) REFERENCES DRIVER(DriverID),
        FOREIGN KEY (ClientID) REFERENCES CLIENT(ClientID)
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS GOODS (
        GoodsID INT PRIMARY KEY,
        Description TEXT,
        Category VARCHAR(255),
        RequiresRefrigeration BOOLEAN
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS SHIPMENT (
        ShipmentID INT PRIMARY KEY,
        Weight DECIMAL(10, 2),
        Quantity INT
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS MAINTENANCE (
        MaintenanceDate DATE,
        GarageName VARCHAR(255),
        Cost DECIMAL(10, 2),
        Description TEXT,
        TruckID INT,
        PRIMARY KEY (TruckID, MaintenanceDate),
        FOREIGN KEY (TruckID) REFERENCES TRUCK(TruckID)
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS INCLUDES (
        TripID INT,
        GoodsID INT,
        ShipmentID INT,
        PRIMARY KEY (TripID, GoodsID),
        FOREIGN KEY (TripID) REFERENCES TRIP(TripID),
        FOREIGN KEY (GoodsID) REFERENCES GOODS(GoodsID),
        FOREIGN KEY (ShipmentID) REFERENCES SHIPMENT(ShipmentID)
    );
    """
]

try:
    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor()

    for query in create_table_queries:
        cursor.execute(query)
        print("Successfully created a table.")

    print("\nAll tables have been created successfully!")
    
except mysql.connector.Error as err:
    print(f"Error: {err}")
    
finally:
    if 'cursor' in locals() and cursor is not None:
        cursor.close()
    if 'conn' in locals() and conn.is_connected():
        conn.close()
        print("MySQL connection is closed.")