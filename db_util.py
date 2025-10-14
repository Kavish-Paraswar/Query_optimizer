# db_util.py
import mysql.connector
import os

DB_CONF = {
    "host": "127.0.0.1",
    "user": "root",
    "password": "Kavish@76",
    "database": "query_optimizatio2",   # <- keep the DB name you created
    "allow_local_infile": True
}

def get_conn():
    """Return a mysql.connector connection using DB_CONF."""
    return mysql.connector.connect(**DB_CONF)

def create_table_if_not_exists():
    q = """
    CREATE TABLE IF NOT EXISTS employees (
      emp_id INT UNSIGNED NOT NULL PRIMARY KEY,
      name VARCHAR(100) NOT NULL,
      age INT UNSIGNED,
      department VARCHAR(50),
      salary DECIMAL(10,2),
      INDEX idx_name (name),
      INDEX idx_age (age)
    ) ENGINE=InnoDB;
    """
    cnx = get_conn()
    cur = cnx.cursor()
    cur.execute(q)
    cnx.commit()
    cur.close()
    cnx.close()
    print("✅ Table 'employees' is ready in database:", DB_CONF["database"])

def load_csv_into_db(csv_path):
    """
    Use LOAD DATA LOCAL INFILE to import CSV quickly.
    If your server disallows LOCAL INFILE, this will raise an error.
    """
    cnx = get_conn()
    cur = cnx.cursor()
    query = """
    LOAD DATA LOCAL INFILE %s
    INTO TABLE employees
    FIELDS TERMINATED BY ','
    OPTIONALLY ENCLOSED BY '"'
    LINES TERMINATED BY '\\n'
    IGNORE 1 LINES
    (emp_id, name, age, department, salary)
    """
    cur.execute(query, (csv_path,))
    cnx.commit()
    cur.close()
    cnx.close()
    print(f"✅ CSV '{csv_path}' loaded into employees table.")

def run_query(q, params=None, fetch=False):
    cnx = get_conn()
    cur = cnx.cursor(dictionary=True)
    cur.execute(q, params or ())
    res = cur.fetchall() if fetch else None
    cnx.commit()
    cur.close()
    cnx.close()
    return res

def check_row_count():
    rows = run_query("SELECT COUNT(*) AS cnt FROM employees", fetch=True)
    if rows:
        print(f"ℹ️ Employees table contains {rows[0]['cnt']} rows")
    else:
        print("⚠️ Employees table is empty or not found")

if __name__ == "__main__":
    create_table_if_not_exists()
    check_row_count()
