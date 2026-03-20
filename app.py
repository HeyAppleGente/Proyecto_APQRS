"""
APQRS - Sistema de Gestión Residencial

"""

import os
import bcrypt
import secrets
from dotenv import load_dotenv
from datetime import datetime
from functools import wraps

from flask import Flask, request, jsonify, render_template, session, redirect, url_for
import mysql.connector
from mysql.connector import Error

load_dotenv()

app = Flask(__name__, template_folder="templates", static_folder="static")


app.secret_key = os.getenv("SECRET_KEY") or secrets.token_hex(32)

# ── Configuración DB ──
DB_CONFIG = {
    "host":     os.getenv("DB_HOST"),
    "user":     os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD"),
    "database": os.getenv("DB_NAME"),
    "charset":  "utf8mb4"
}


def get_db():
    return mysql.connector.connect(**DB_CONFIG, autocommit=False)


def query(sql, params=None, fetchone=False, commit=False):
    conn = get_db()
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute(sql, params or ())
        if commit:
            conn.commit()
            return cur.lastrowid
        return cur.fetchone() if fetchone else cur.fetchall()
    except Error as e:
        conn.rollback()
        raise e
    finally:
        conn.close()


# Verificación hash 
def hash_pw(password: str) -> str:
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode(), salt)
    return hashed.decode()

def check_pw(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode(), hashed.encode())


# ── Decoradores ──
def login_required(f):
    @wraps(f)
    def dec(*a, **kw):
        if "user_id" not in session:
            if request.is_json:
                return jsonify({"error": "No autenticado"}), 401
            return redirect(url_for("login_page"))
        return f(*a, **kw)
    return dec


def admin_required(f):
    @wraps(f)
    def dec(*a, **kw):
        if "user_id" not in session:
            return jsonify({"error": "No autenticado"}), 401
        if session.get("rol") != "Administrador":
            return jsonify({"error": "Acceso denegado"}), 403
        return f(*a, **kw)
    return dec



# PÁGINAS HTML

@app.route("/")
def index():
    if "user_id" in session:
        if session.get("rol") == "Administrador":
            return redirect(url_for("admin_page"))
        return redirect(url_for("dashboard_page"))
    return redirect(url_for("login_page"))


@app.route("/login")
def login_page():
    if "user_id" in session:
        return redirect(url_for("index"))
    return render_template("Login.html")


@app.route("/register")
def register_page():
    return render_template("register.html")


@app.route("/dashboard")
@login_required
def dashboard_page():
    return render_template("dashboard_residente.html")


@app.route("/admin")
@login_required
def admin_page():
    if session.get("rol") != "Administrador":
        return redirect(url_for("dashboard_page"))
    return render_template("Vista_administrador.html")


@app.route("/calendario")
@login_required
def calendario_page():
    return render_template("Calendario.html")


# AUTH API

@app.route("/api/auth/login", methods=["POST"])
def api_login():
    data = request.json or {}
    usuario_input = data.get("usuario", "")
    password_input = data.get("password", "")

    # ✅ FIX 3: Buscar usuario por email/documento SIN comparar hash en SQL
    user = query(
        """SELECT u.*, r.nombre AS rol_nombre,
                  a.numero AS apto_num, b.nombre AS bloque_nom
           FROM usuario u
           JOIN rol r ON u.id_rol = r.id_rol
           LEFT JOIN apartamento a ON u.id_apartamento = a.id_apartamento
           LEFT JOIN bloque b ON a.id_bloque = b.id_bloque
           WHERE (u.email = %s OR u.documento = %s)
             AND u.activo = 1""",
        (usuario_input, usuario_input),
        fetchone=True,
    )

    # ✅ Verificar la contraseña en Python con check_pw()
    if not user or not check_pw(password_input, user["password_hash"]):
        return jsonify({"error": "Usuario o contraseña incorrectos"}), 401

    session.permanent = True
    session.update({
        "user_id":     user["id_usuario"],
        "nombres":     user["nombres"],
        "apellidos":   user["apellidos"],
        "email":       user["email"],
        "rol":         user["rol_nombre"],
        "apartamento": f"Bloque {user['bloque_nom']} - {user['apto_num']}" if user.get("apto_num") else "",
    })
    return jsonify({"rol": user["rol_nombre"], "nombres": user["nombres"]})


@app.route("/api/auth/register", methods=["POST"])
def api_register():
    d = request.json or {}
    reqs = ["documento", "nombres", "apellidos", "email", "password", "id_apartamento"]
    for f in reqs:
        if not d.get(f):
            return jsonify({"error": f"Campo requerido: {f}"}), 400

    if query("SELECT id_usuario FROM usuario WHERE email=%s OR documento=%s",
             (d["email"], d["documento"]), fetchone=True):
        return jsonify({"error": "Email o documento ya registrado"}), 409

    uid = query(
        """INSERT INTO usuario (documento,nombres,apellidos,email,telefono,
           password_hash,id_rol,id_apartamento)
           VALUES (%s,%s,%s,%s,%s,%s,2,%s)""",
        (d["documento"], d["nombres"], d["apellidos"], d["email"],
         d.get("telefono", ""), hash_pw(d["password"]), d["id_apartamento"]),
        commit=True,
    )
    return jsonify({"message": "Cuenta creada", "id": uid}), 201


@app.route("/api/auth/logout", methods=["POST"])
def api_logout():
    session.clear()
    return jsonify({"ok": True})


@app.route("/api/auth/me")
@login_required
def api_me():
    return jsonify({
        "id":          session["user_id"],
        "nombres":     session["nombres"],
        "apellidos":   session["apellidos"],
        "email":       session["email"],
        "rol":         session["rol"],
        "apartamento": session.get("apartamento", ""),
    })


# ══════════════════════════════════════
# APARTAMENTOS
# ══════════════════════════════════════

@app.route("/api/apartamentos")
def api_apartamentos():
    return jsonify(query(
        """SELECT a.id_apartamento, a.numero, a.piso, a.estado, b.nombre AS bloque
           FROM apartamento a JOIN bloque b ON a.id_bloque = b.id_bloque
           ORDER BY b.nombre, a.piso, a.numero"""
    ))


# ══════════════════════════════════════
# PQRS
# ══════════════════════════════════════

@app.route("/api/pqrs", methods=["GET"])
@login_required
def api_pqrs_list():
    if session.get("rol") == "Administrador":
        rows = query(
            """SELECT p.*, tp.nombre AS tipo_nombre,
                      u.nombres, u.apellidos,
                      a.numero AS apto_num, b.nombre AS bloque_nom
               FROM pqrs p
               JOIN tipopqrs tp ON p.id_tipopqrs = tp.id_tipopqrs
               JOIN usuario u  ON p.id_usuario  = u.id_usuario
               LEFT JOIN apartamento a ON u.id_apartamento = a.id_apartamento
               LEFT JOIN bloque b ON a.id_bloque = b.id_bloque
               ORDER BY p.fecha_creacion DESC"""
        )
    else:
        rows = query(
            """SELECT p.*, tp.nombre AS tipo_nombre
               FROM pqrs p
               JOIN tipopqrs tp ON p.id_tipopqrs = tp.id_tipopqrs
               WHERE p.id_usuario = %s
               ORDER BY p.fecha_creacion DESC""",
            (session["user_id"],),
        )
    for r in rows:
        for k, v in r.items():
            if isinstance(v, datetime):
                r[k] = v.strftime("%Y-%m-%d %H:%M")
    return jsonify(rows)


@app.route("/api/pqrs", methods=["POST"])
@login_required
def api_pqrs_create():
    d = request.json or {}
    if not d.get("asunto") or not d.get("descripcion") or not d.get("id_tipopqrs"):
        return jsonify({"error": "Faltan campos"}), 400
    pid = query(
        "INSERT INTO pqrs (asunto,descripcion,id_usuario,id_tipopqrs) VALUES (%s,%s,%s,%s)",
        (d["asunto"], d["descripcion"], session["user_id"], d["id_tipopqrs"]),
        commit=True,
    )
    query(
        "INSERT INTO seguimiento (descripcion,tipo_registro,id_usuario,id_pqrs) VALUES (%s,'pqrs',%s,%s)",
        (f"PQRS radicada: {d['asunto']}", session["user_id"], pid),
        commit=True,
    )
    return jsonify({"message": "PQRS radicada", "id_pqrs": pid}), 201


@app.route("/api/pqrs/<int:pid>/responder", methods=["PUT"])
@admin_required
def api_pqrs_responder(pid):
    d = request.json or {}
    if not d.get("respuesta"):
        return jsonify({"error": "Respuesta requerida"}), 400
    query(
        "UPDATE pqrs SET respuesta=%s, estado='respondida', fecha_respuesta=NOW() WHERE id_pqrs=%s",
        (d["respuesta"], pid),
        commit=True,
    )
    return jsonify({"message": "PQRS respondida"})


@app.route("/api/tipopqrs")
@login_required
def api_tipopqrs():
    return jsonify(query("SELECT * FROM tipopqrs"))


# ══════════════════════════════════════
# CITAS
# ══════════════════════════════════════

@app.route("/api/citas", methods=["GET"])
@login_required
def api_citas_list():
    if session.get("rol") == "Administrador":
        rows = query(
            """SELECT c.*, tc.nombre AS tipo_nombre,
                      u.nombres, u.apellidos,
                      a.numero AS apto_num, b.nombre AS bloque_nom
               FROM citas c
               JOIN tipocita tc ON c.id_tipocita = tc.id_tipocita
               JOIN usuario u   ON c.id_usuario  = u.id_usuario
               LEFT JOIN apartamento a ON u.id_apartamento = a.id_apartamento
               LEFT JOIN bloque b ON a.id_bloque = b.id_bloque
               ORDER BY c.fecha_cita DESC"""
        )
    else:
        rows = query(
            """SELECT c.*, tc.nombre AS tipo_nombre
               FROM citas c JOIN tipocita tc ON c.id_tipocita = tc.id_tipocita
               WHERE c.id_usuario = %s ORDER BY c.fecha_cita DESC""",
            (session["user_id"],),
        )
    for r in rows:
        for k, v in r.items():
            if isinstance(v, datetime):
                r[k] = v.strftime("%Y-%m-%d %H:%M")
    return jsonify(rows)


@app.route("/api/citas", methods=["POST"])
@login_required
def api_citas_create():
    d = request.json or {}
    if not d.get("fecha_cita") or not d.get("id_tipocita"):
        return jsonify({"error": "Faltan campos"}), 400
    cid = query(
        "INSERT INTO citas (fecha_cita,descripcion,id_usuario,id_tipocita) VALUES (%s,%s,%s,%s)",
        (d["fecha_cita"], d.get("descripcion", ""), session["user_id"], d["id_tipocita"]),
        commit=True,
    )
    query(
        "INSERT INTO seguimiento (descripcion,tipo_registro,id_usuario,id_cita) VALUES (%s,'cita',%s,%s)",
        (f"Cita agendada: {d['fecha_cita']}", session["user_id"], cid),
        commit=True,
    )
    return jsonify({"message": "Cita agendada", "id_cita": cid}), 201


@app.route("/api/citas/<int:cid>/responder", methods=["PUT"])
@admin_required
def api_citas_responder(cid):
    d = request.json or {}
    query(
        "UPDATE citas SET respuesta=%s, estado=%s, fecha_respuesta=NOW() WHERE id_cita=%s",
        (d.get("respuesta", ""), d.get("estado", "confirmada"), cid),
        commit=True,
    )
    return jsonify({"message": "Cita actualizada"})


@app.route("/api/tipocita")
@login_required
def api_tipocita():
    return jsonify(query("SELECT * FROM tipocita"))


# ══════════════════════════════════════
# NOTIFICACIONES
# ══════════════════════════════════════

@app.route("/api/notificaciones")
@login_required
def api_notificaciones():
    solo = request.args.get("no_leidas") == "1"
    sql = """SELECT n.*, tn.nombre AS tipo_nombre, tn.icono
             FROM notificaciones n
             JOIN tiponotificacion tn ON n.id_tiponotificacion = tn.id_tiponotificacion
             WHERE n.id_usuario = %s"""
    if solo:
        sql += " AND n.leido = 0"
    sql += " ORDER BY n.fecha_creacion DESC LIMIT 50"
    rows = query(sql, (session["user_id"],))
    for r in rows:
        for k, v in r.items():
            if isinstance(v, datetime):
                r[k] = v.strftime("%Y-%m-%d %H:%M")
    return jsonify(rows)


@app.route("/api/notificaciones/<int:nid>/leer", methods=["PUT"])
@login_required
def api_notif_leer(nid):
    query(
        "UPDATE notificaciones SET leido=1,fecha_lectura=NOW() WHERE id_notificacion=%s AND id_usuario=%s",
        (nid, session["user_id"]),
        commit=True,
    )
    return jsonify({"ok": True})


@app.route("/api/notificaciones/leer-todas", methods=["PUT"])
@login_required
def api_notif_todas():
    query(
        "UPDATE notificaciones SET leido=1,fecha_lectura=NOW() WHERE id_usuario=%s AND leido=0",
        (session["user_id"],),
        commit=True,
    )
    return jsonify({"ok": True})


# ══════════════════════════════════════
# DASHBOARD STATS
# ══════════════════════════════════════

@app.route("/api/stats")
@login_required
def api_stats():
    uid = session["user_id"]
    is_admin = session.get("rol") == "Administrador"

    if is_admin:
        return jsonify({
            "pqrs_total":     query("SELECT COUNT(*) n FROM pqrs", fetchone=True)["n"],
            "citas_total":    query("SELECT COUNT(*) n FROM citas", fetchone=True)["n"],
            "usuarios":       query("SELECT COUNT(*) n FROM usuario WHERE id_rol=2", fetchone=True)["n"],
            "pqrs_pendiente": query("SELECT COUNT(*) n FROM pqrs WHERE estado='radicada'", fetchone=True)["n"],
        })
    return jsonify({
        "pqrs_total":     query("SELECT COUNT(*) n FROM pqrs  WHERE id_usuario=%s", (uid,), fetchone=True)["n"],
        "citas_total":    query("SELECT COUNT(*) n FROM citas WHERE id_usuario=%s", (uid,), fetchone=True)["n"],
        "notif_noread":   query("SELECT COUNT(*) n FROM notificaciones WHERE id_usuario=%s AND leido=0", (uid,), fetchone=True)["n"],
        "pqrs_pendiente": query("SELECT COUNT(*) n FROM pqrs WHERE id_usuario=%s AND estado='radicada'", (uid,), fetchone=True)["n"],
    })


# ══════════════════════════════════════
# SEGUIMIENTO
# ══════════════════════════════════════

@app.route("/api/seguimiento")
@login_required
def api_seguimiento():
    rows = query(
        "SELECT * FROM seguimiento WHERE id_usuario=%s ORDER BY fecha DESC LIMIT 30",
        (session["user_id"],),
    )
    for r in rows:
        for k, v in r.items():
            if isinstance(v, datetime):
                r[k] = v.strftime("%Y-%m-%d %H:%M")
    return jsonify(rows)


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)