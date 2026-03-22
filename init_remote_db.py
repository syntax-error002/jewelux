import os
import MySQLdb
from dotenv import load_dotenv

load_dotenv()

def init_db():
    host = os.environ.get('MYSQL_HOST', 'localhost')
    user = os.environ.get('MYSQL_USER', 'root')
    password = os.environ.get('MYSQL_PASSWORD', 'Rishi@2207')
    db = os.environ.get('MYSQL_DB', 'jewelux')
    
    print(f"Connecting to {host} as {user}...")
    try:
        # Connect directly mapping to the target DB
        conn = MySQLdb.connect(host=host, user=user, passwd=password, db=db)
        cursor = conn.cursor()
        
        with open('schema.sql', 'r', encoding='utf-8') as f:
            sql = f.read()
            
        print("Executing schema.sql...")
        # Execute multi-line statement
        for stmt in sql.split(';'):
            if stmt.strip():
                cursor.execute(stmt)
                
        conn.commit()
        print("Database initialized successfully.")
    except Exception as e:
        print(f"Error initializing database: {e}")
        raise
    finally:
        if 'conn' in locals() and getattr(conn, 'open', False):
            conn.close()

if __name__ == '__main__':
    init_db()
