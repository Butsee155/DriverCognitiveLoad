import pyodbc

def get_connection():
    conn = pyodbc.connect(
        'DRIVER={ODBC Driver 17 for SQL Server};'
        'SERVER=Butsee\SQLEXPRESS;'
        'DATABASE=DriverCognitiveLoad;'
        'Trusted_Connection=yes;'
    )
    return conn