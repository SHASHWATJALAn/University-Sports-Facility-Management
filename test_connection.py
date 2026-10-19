
import mysql.connector

try:
    connection = mysql.connector.connect(
        host="localhost",
        port=3306,
        user="root",
        password="Shashwat1!",
        database="SportsFacilityDB"
    )

    if connection.is_connected():
        print("Successfully connected to MySQL!")
        print("Database:", connection.database)

        cursor = connection.cursor()
        cursor.execute("SELECT DATABASE()")
        result = cursor.fetchone()

        print("Active database:", result[0])

        cursor.close()
        connection.close()
        print("Connection closed successfully.")

except mysql.connector.Error as error:
    print("Database connection failed:", error)

