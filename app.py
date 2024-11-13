from flask import Flask, request, jsonify, render_template, g
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity
from werkzeug.security import generate_password_hash, check_password_hash
import mysql.connector
from mysql.connector import pooling
import logging
from datetime import timedelta
import re
import os
from functools import wraps
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    filename='app.log',
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
# Load JWT secret key from environment variable
app.config['JWT_SECRET_KEY'] = os.getenv('JWT_SECRET_KEY', os.urandom(24))
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(hours=int(os.getenv('JWT_EXPIRATION_HOURS', 1)))
jwt = JWTManager(app)

# Database connection configuration
DB_CONFIG = {
    "pool_name": "mypool",
    "pool_size": int(os.getenv('DB_POOL_SIZE', 5)),
    "host": os.getenv('DB_HOST', 'localhost'),
    "user": os.getenv('DB_USER'),
    "password": os.getenv('DB_PASSWORD'),
    "database": os.getenv('DB_NAME')
}

# Initialize connection pool
try:
    connection_pool = mysql.connector.pooling.MySQLConnectionPool(**DB_CONFIG)
    logger.info("Database connection pool created successfully")
except Exception as e:
    logger.error(f"Failed to create database connection pool: {str(e)}")
    raise


def get_db():
    if 'db' not in g:
        try:
            g.db = connection_pool.get_connection()
        except Exception as e:
            logger.error(f"Failed to get database connection: {str(e)}")
            raise
    return g.db


@app.teardown_appcontext
def close_db(e=None):
    db = g.pop('db', None)
    if db is not None:
        db.close()


# Create users table if it doesn't exist
def init_db():
    try:
        db = get_db()
        cursor = db.cursor()

        # Create users table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INT AUTO_INCREMENT PRIMARY KEY,
                email VARCHAR(255) UNIQUE NOT NULL,
                password VARCHAR(255) NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        db.commit()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Database initialization failed: {str(e)}")
        raise


# Initialize database on startup
with app.app_context():
    init_db()


# Main route to render the SPA
@app.route('/')
def index():
    return render_template('index.html')
##########################################################################
# @app.route('/api/test-db')
# def test_db():
#     try:
#         db = get_db()
#         cursor = db.cursor()
#         cursor.execute('SELECT 1')
#         result = cursor.fetchone()
#         return jsonify({
#             "status": "success",
#             "message": "Database connection successful",
#             "result": result[0]
#         }), 200
#     except Exception as e:
#         return jsonify({
#             "status": "error",
#             "message": f"Database connection failed: {str(e)}"
#         }), 500
###########################################################################
@app.route('/api/register', methods=['POST'])
def register():
    try:
        data = request.get_json()
        email = data.get('email')
        password = data.get('password')

        if not email or not password:
            return jsonify({"error": "Email and password are required"}), 400

        if not re.match(r'^[\w\.-]+@[\w\.-]+\.\w+$', email):
            return jsonify({"error": "Formato de correo incorrecto"}), 400

        if len(password) < 8:
            return jsonify({"error": "La contraseña debe ser de minimo 8 caracteres"}), 400

        db = get_db()
        cursor = db.cursor(dictionary=True)

        # Check if user exists
        cursor.execute("SELECT id FROM users WHERE email = %s", (email,))
        if cursor.fetchone():
            return jsonify({"error": "Este correo ha sido registrado anteriormente"}), 409

        # Create new user
        hashed_password = generate_password_hash(password)
        cursor.execute(
            "INSERT INTO users (email, password) VALUES (%s, %s)",
            (email, hashed_password)
        )
        db.commit()

        logger.info(f"New user registered: {email}")
        return jsonify({"message": "Registro exitoso"}), 201

    except Exception as e:
        logger.error(f"Registration error: {str(e)}")
        return jsonify({"error": "Registro fallido, intenta nuevamente"}), 500


@app.route('/api/login', methods=['POST'])
def login():
    try:
        data = request.get_json()
        email = data.get('email')
        password = data.get('password')

        db = get_db()
        cursor = db.cursor(dictionary=True)

        cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
        user = cursor.fetchone()

        if user and check_password_hash(user['password'], password):
            access_token = create_access_token(identity=email)
            logger.info(f"User logged in: {email}")
            return jsonify({
                "access_token": access_token,
                "message": "Login successful"
            }), 200

        return jsonify({"error": "Credenciales invalidas"}), 401

    except Exception as e:
        logger.error(f"Login error: {str(e)}")
        return jsonify({"error": "Inicio de sesión fallido"}), 500


@app.route('/api/employees/search', methods=['GET'])
@jwt_required()
def search_employees():
    try:
        # Get search parameters from query string
        search_term = request.args.get('q', '').strip()
        search_by = request.args.get('by', 'name')  # default search by name
        page = int(request.args.get('page', 1))
        limit = int(request.args.get('limit', 10))
        offset = (page - 1) * limit

        if not search_term:
            return jsonify({"error": "Search term is required"}), 400

        db = get_db()
        cursor = db.cursor(dictionary=True)

        # Base query with common joins
        base_query = """
        FROM employees e
        LEFT JOIN (
            SELECT emp_no, title
            FROM titles
            WHERE to_date = '9999-01-01'
        ) t ON e.emp_no = t.emp_no
        LEFT JOIN (
            SELECT emp_no, salary
            FROM salaries
            WHERE to_date = '9999-01-01'
        ) s ON e.emp_no = s.emp_no
        LEFT JOIN (
            SELECT emp_no, dept_no
            FROM dept_emp
            WHERE to_date = '9999-01-01'
        ) de ON e.emp_no = de.emp_no
        LEFT JOIN departments d ON de.dept_no = d.dept_no
        """

        # Build WHERE clause based on search type
        search_conditions = {
            'name': "WHERE CONCAT(e.first_name, ' ', e.last_name) LIKE %s",
            'id': "WHERE e.emp_no = %s",
            'department': "WHERE d.dept_name LIKE %s",
            'title': "WHERE t.title LIKE %s",
            'salary': "WHERE s.salary >= %s"
        }

        where_clause = search_conditions.get(search_by, search_conditions['name'])

        # Prepare search parameter
        if search_by == 'name':
            search_param = f"%{search_term}%"
        elif search_by == 'id':
            try:
                search_param = int(search_term)
            except ValueError:
                return jsonify({"error": "Invalid employee ID format"}), 400
        elif search_by in ['department', 'title']:
            search_param = f"%{search_term}%"
        elif search_by == 'salary':
            try:
                search_param = float(search_term)
            except ValueError:
                return jsonify({"error": "Invalid salary format"}), 400
        else:
            return jsonify({"error": "Invalid search criteria"}), 400

        # Count total results
        count_query = f"SELECT COUNT(*) as count {base_query} {where_clause}"
        cursor.execute(count_query, (search_param,))
        total_count = cursor.fetchone()['count']

        # Get paginated results with all necessary fields
        select_query = f"""
        SELECT 
            e.emp_no,
            e.first_name,
            e.last_name,
            e.hire_date,
            t.title,
            s.salary,
            d.dept_name
        {base_query}
        {where_clause}
        ORDER BY e.emp_no
        LIMIT %s OFFSET %s
        """

        cursor.execute(select_query, (search_param, limit, offset))
        employees = cursor.fetchall()

        # Format results ensuring all fields are present
        formatted_employees = []
        for emp in employees:
            formatted_employee = {
                'emp_no': emp['emp_no'],
                'first_name': emp['first_name'],
                'last_name': emp['last_name'],
                'hire_date': emp['hire_date'].strftime('%Y-%m-%d') if emp['hire_date'] else None,
                'title': emp['title'] or 'N/A',
                'salary': float(emp['salary']) if emp['salary'] else None,
                'department': emp['dept_name'] or 'N/A'
            }
            formatted_employees.append(formatted_employee)

        return jsonify({
            "employees": formatted_employees,
            "total": total_count,
            "page": page,
            "total_pages": -(-total_count // limit),
            "search_criteria": {
                "term": search_term,
                "type": search_by
            }
        }), 200

    except Exception as e:
        logger.error(f"Search error: {str(e)}")
        return jsonify({"error": "Search operation failed"}), 500

@app.route('/api/employees', methods=['GET'])
@jwt_required()
def get_employees():
    try:
        page = int(request.args.get('page', 1))
        limit = int(request.args.get('limit', 10))
        offset = (page - 1) * limit

        db = get_db()
        cursor = db.cursor(dictionary=True)

        # Get total count
        cursor.execute("SELECT COUNT(*) as count FROM employees")
        total_count = cursor.fetchone()['count']

        # Get paginated employees with efficient JOIN
        query = """
        SELECT 
            e.emp_no,
            e.first_name,
            e.last_name,
            e.hire_date,
            t.title,
            s.salary
        FROM employees e
        LEFT JOIN (
            SELECT emp_no, title
            FROM titles
            WHERE to_date = '9999-01-01'
        ) t ON e.emp_no = t.emp_no
        LEFT JOIN (
            SELECT emp_no, salary
            FROM salaries
            WHERE to_date = '9999-01-01'
        ) s ON e.emp_no = s.emp_no
        ORDER BY e.emp_no
        LIMIT %s OFFSET %s
        """

        cursor.execute(query, (limit, offset))
        employees = cursor.fetchall()

        return jsonify({
            "employees": employees,
            "total": total_count,
            "page": page,
            "total_pages": -(-total_count // limit)  # Ceiling division
        }), 200

    except Exception as e:
        logger.error(f"Error fetching employees: {str(e)}")
        return jsonify({"error": "Failed to fetch employees"}), 500


@app.route('/api/employees/<int:emp_no>', methods=['GET', 'PUT', 'DELETE'])
@jwt_required()
def manage_employee(emp_no):
    try:
        db = get_db()
        cursor = db.cursor(dictionary=True)

        if request.method == 'GET':
            query = """
            SELECT 
                e.*,
                t.title,
                s.salary,
                d.dept_name
            FROM employees e
            LEFT JOIN titles t ON e.emp_no = t.emp_no AND t.to_date = '9999-01-01'
            LEFT JOIN salaries s ON e.emp_no = s.emp_no AND s.to_date = '9999-01-01'
            LEFT JOIN dept_emp de ON e.emp_no = de.emp_no AND de.to_date = '9999-01-01'
            LEFT JOIN departments d ON de.dept_no = d.dept_no
            WHERE e.emp_no = %s
            """
            cursor.execute(query, (emp_no,))
            employee = cursor.fetchone()

            if not employee:
                return jsonify({"error": "Empleado no encontrado"}), 404

            return jsonify(employee), 200

        elif request.method == 'PUT':
            data = request.get_json()

            # Start transaction
            db.start_transaction()
            try:
                # Update employee basic info
                update_query = """
                UPDATE employees 
                SET first_name = %s, last_name = %s
                WHERE emp_no = %s
                """
                cursor.execute(update_query, (
                    data['first_name'],
                    data['last_name'],
                    emp_no
                ))

                # Update salary if provided
                if 'salary' in data:
                    cursor.execute(
                        "UPDATE salaries SET to_date = CURDATE() WHERE emp_no = %s AND to_date = '9999-01-01'",
                        (emp_no,)
                    )
                    cursor.execute(
                        "INSERT INTO salaries (emp_no, salary, from_date, to_date) VALUES (%s, %s, CURDATE(), '9999-01-01')",
                        (emp_no, data['salary'])
                    )

                # Update title if provided
                if 'title' in data:
                    cursor.execute(
                        "UPDATE titles SET to_date = CURDATE() WHERE emp_no = %s AND to_date = '9999-01-01'",
                        (emp_no,)
                    )
                    cursor.execute(
                        "INSERT INTO titles (emp_no, title, from_date, to_date) VALUES (%s, %s, CURDATE(), '9999-01-01')",
                        (emp_no, data['title'])
                    )

                db.commit()
                logger.info(f"Employee updated: {emp_no}")
                return jsonify({"message": "Empleado actualizado exitosamente"}), 200

            except Exception as e:
                db.rollback()
                raise

        elif request.method == 'DELETE':
            # Soft delete by updating end dates
            db.start_transaction()
            try:
                cursor.execute(
                    "UPDATE dept_emp SET to_date = CURDATE() WHERE emp_no = %s AND to_date = '9999-01-01'",
                    (emp_no,)
                )
                cursor.execute(
                    "UPDATE titles SET to_date = CURDATE() WHERE emp_no = %s AND to_date = '9999-01-01'",
                    (emp_no,)
                )
                cursor.execute(
                    "UPDATE salaries SET to_date = CURDATE() WHERE emp_no = %s AND to_date = '9999-01-01'",
                    (emp_no,)
                )

                db.commit()
                logger.info(f"Employee deleted: {emp_no}")
                return jsonify({"message": "Empleado eliminado exitosamente"}), 200

            except Exception as e:
                db.rollback()
                raise

    except Exception as e:
        logger.error(f"Error managing employee {emp_no}: {str(e)}")
        return jsonify({"error": "Operación fallida"}), 500


if __name__ == '__main__':
    app.run()