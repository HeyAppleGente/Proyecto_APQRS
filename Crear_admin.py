import bcrypt
import mysql.connector
from dotenv import load_dotenv
import os

load_dotenv()

# ── Datos del administrador ──────────────────────────
DOCUMENTO  = "0000000000"
NOMBRES    = "Admin"
APELLIDOS  = "Sistema"
EMAIL      = "admin@apqrs.com"
PASSWORD   = "Admin1234"   


pw_hash = bcrypt.hashpw(PASSWORD.encode(), bcrypt.gensalt()).decode()

conn = mysql.connector.connect(
    host=os.getenv("DB_HOST"),
    user=os.getenv("DB_USER"),
    password=os.getenv("DB_PASSWORD"),
    database=os.getenv("DB_NAME"),
    charset="utf8mb4"
)
cur = conn.cursor()
cur.execute(
    """INSERT INTO usuario (documento, nombres, apellidos, email, password_hash, id_rol, activo)
       VALUES (%s, %s, %s, %s, %s, 1, 1)
       ON DUPLICATE KEY UPDATE password_hash = VALUES(password_hash)""",
    (DOCUMENTO, NOMBRES, APELLIDOS, EMAIL, pw_hash)
)
conn.commit()
conn.close()

print(f"✅ Admin creado: {EMAIL} / {PASSWORD}")