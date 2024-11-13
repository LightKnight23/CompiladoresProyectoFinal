# Instrucciones para Ejecutar el Código en Python - API con Flask y MySQL

Este archivo describe los pasos para configurar y ejecutar una aplicación web desarrollada en Python que utiliza Flask, una base de datos MySQL y autenticación JWT. La aplicación permite el registro de usuarios, autenticación, y manejo de información de empleados.

## Requisitos Previos

- Python 3.8 o superior
- MySQL
- Variables de entorno configuradas (.env)
- Librerías requeridas en `requirements.txt` (ejecutar `pip install -r requirements.txt`)

## Pasos de Configuración y Ejecución

### 1. Configuración de la Base de Datos

La aplicación requiere una base de datos MySQL con las siguientes configuraciones mínimas:

1. Crear una base de datos y un usuario con permisos de acceso.
2. En el archivo `.env` (detallado más adelante), configurar las credenciales de acceso para esta base de datos.
3. La aplicación crea automáticamente la tabla de usuarios (`users`) si no existe, durante la inicialización.

### 2. Configuración de Variables de Entorno

El archivo `.env` debe contener las siguientes variables de entorno:

```plaintext
JWT_SECRET_KEY="tu_clave_secreta_para_JWT"
JWT_EXPIRATION_HOURS=1                  # Tiempo de expiración del token en horas
DB_HOST="localhost"                      # Dirección del servidor MySQL
DB_USER="usuario_mysql"
DB_PASSWORD="contraseña_mysql"
DB_NAME="nombre_base_datos"
DB_POOL_SIZE=5                           # Tamaño del pool de conexiones
```
Nota: La clave JWT es importante para la autenticación segura de la API. Puede generarse utilizando cualquier generador de claves seguras.

### 3. Instalación de Dependencias

Ejecutar el siguiente comando en la terminal para instalar todas las librerías necesarias:

```bash
   pip install -r requirements.txt
```

### 4. Inicialización y Ejecución de la Aplicación

1.	En la raíz del proyecto, ejecute el archivo principal de la aplicación:
```bash
   python app.py
```

2.	Esto lanzará el servidor en el puerto 5000 por defecto. Acceda a http://127.0.0.1:5000/ para verificar el estado de la aplicación.

## Funcionalidades de la API

### Endpoints Principales

	•	Registro de Usuarios: POST /api/register
	•	Parámetros de entrada: email, password
	•	Retorna: Mensaje de éxito o error.
	•	Inicio de Sesión: POST /api/login
	•	Parámetros de entrada: email, password
	•	Retorna: Token JWT para autenticación.
	•	Buscar Empleados: GET /api/employees/search
	•	Autenticación JWT requerida.
	•	Parámetros de búsqueda: q (término de búsqueda), by (criterio), page, limit.
	•	Retorna: Información de empleados filtrada.
	•	Gestión de Empleados: GET/PUT/DELETE /api/employees/<emp_no>
	•	Autenticación JWT requerida.
	•	Permite obtener, actualizar o eliminar (soft delete) un empleado específico por emp_no.

## Ejemplos de Uso

###	1.	Registro de Usuario
```bash
  curl -X POST http://127.0.0.1:5000/api/register -H "Content-Type: application/json" -d '{"email": "user@example.com", "password": "password123"}'
```

###	2.	Inicio de Sesión
```bash
  curl -X POST http://127.0.0.1:5000/api/login -H "Content-Type: application/json" -d '{"email": "user@example.com", "password": "password123"}'
```

###	3.	Búsqueda de Empleados
```bash
  curl -X GET http://127.0.0.1:5000/api/employees/search?q=John&by=name&page=1&limit=10 -H "Authorization: Bearer <TOKEN>"
```

### 4.	Obtener Detalles de un Empleado Específico
```bash
  curl -X GET http://127.0.0.1:5000/api/employees/123 -H "Authorization: Bearer <TOKEN>"
```

Nota: Reemplace <TOKEN> con el JWT obtenido durante el inicio de sesión.

### Manejo de Errores y Registros (Logging)

La aplicación genera registros en el archivo app.log para monitorear eventos, errores y el flujo de uso de la API. Estos registros incluyen detalles sobre las conexiones a la base de datos, creación de usuarios y autenticación.

#### Advertencia: Mantenga la clave secreta JWT y las credenciales de base de datos seguras y nunca las comparta públicamente.