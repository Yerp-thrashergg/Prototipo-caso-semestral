"""HSG SGMI - Prototipo Sprint 1 (Flask + MySQL).

Ejecutar:  python app.py   y abrir  http://localhost:5000
"""
import os
from datetime import date, datetime
from functools import wraps
from secrets import token_hex

import pymysql
from flask import Flask, abort, flash, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash

import funciones as f
from db import una_fila

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "clave-solo-para-pruebas-locales")

ROLES = {
    "bodega": "Personal de Bodega",
    "clinica": "Personal de Área Clínica",
    "farmacia": "Personal de Farmacia",
    "gerencia": "Personal de Gerencia",
}
TODOS = ("bodega", "clinica", "farmacia", "gerencia")

# (función de la vista, texto del menú, roles que la ven)
MENU = [
    ("inicio", "Inicio", TODOS),
    ("entradas", "Registrar entradas", ("bodega",)),
    ("inventario", "Inventario y cuarentena", TODOS),
    ("solicitud_nueva", "Nueva solicitud", ("clinica",)),
    ("solicitudes", "Solicitudes", ("clinica", "farmacia", "gerencia")),
    ("alertas", "Alertas de stock", ("farmacia", "gerencia")),
    ("vencimientos", "Vencimientos", ("bodega", "farmacia", "gerencia")),
]


# ------------------------------------------------------------ Utilidades
def csrf_token():
    if "csrf" not in session:
        session["csrf"] = token_hex(16)
    return session["csrf"]


app.jinja_env.globals["csrf_token"] = csrf_token


@app.before_request
def revisar_csrf():
    if request.method == "POST" and request.form.get("csrf") != session.get("csrf"):
        abort(400)


@app.context_processor
def datos_comunes():
    usuario = session.get("usuario")
    menu = []
    if usuario:
        menu = [{"endpoint": e, "texto": t} for e, t, roles in MENU if usuario["rol"] in roles]
    return {
        "usuario": usuario,
        "menu": menu,
        "rol_nombre": ROLES.get(usuario["rol"], "") if usuario else "",
    }


@app.template_filter("fecha")
def filtro_fecha(valor):
    if valor is None or valor == "":
        return ""
    if isinstance(valor, str):
        valor = datetime.fromisoformat(valor) if len(valor) > 10 else date.fromisoformat(valor)
    if isinstance(valor, datetime):
        return valor.strftime("%d-%m-%Y %H:%M")
    return valor.strftime("%d-%m-%Y")


def login_requerido(vista):
    @wraps(vista)
    def envoltura(*args, **kwargs):
        if "usuario" not in session:
            return redirect(url_for("login"))
        return vista(*args, **kwargs)
    return envoltura


def solo_roles(*roles):
    def decorador(vista):
        @wraps(vista)
        @login_requerido
        def envoltura(*args, **kwargs):
            if session["usuario"]["rol"] not in roles:
                abort(403)
            return vista(*args, **kwargs)
        return envoltura
    return decorador


@app.errorhandler(400)
def error_400(e):
    return render_template("error.html", titulo="Solicitud no válida",
                           mensaje="El formulario expiró. Vuelve atrás y envíalo de nuevo."), 400


@app.errorhandler(403)
def error_403(e):
    return render_template("error.html", titulo="Acceso restringido",
                           mensaje="Tu perfil no tiene permiso para ver esta página."), 403


@app.errorhandler(pymysql.err.OperationalError)
def error_bd(e):
    return render_template("error.html", titulo="Sin conexión con la base de datos",
                           mensaje="Revisa que MySQL esté encendido y que la clave en DB_PASSWORD sea correcta."), 500


#Sesión
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        nombre = request.form.get("usuario", "").strip()
        clave = request.form.get("clave", "")
        fila = una_fila("SELECT id, nombre, clave_hash, rol, unidad FROM usuarios WHERE usuario = %s AND activo = 1",
                        (nombre,))
        if fila and check_password_hash(fila["clave_hash"], clave):
            session.clear()
            session["usuario"] = {"id": fila["id"], "nombre": fila["nombre"], "rol": fila["rol"], "unidad": fila["unidad"]}
            return redirect(url_for("inicio"))
        flash("Usuario o clave incorrectos.", "error")
    return render_template("login.html")


@app.route("/salir")
def salir():
    session.clear()
    return redirect(url_for("login"))


@app.route("/")
@login_requerido
def inicio():
    u = session["usuario"]
    return render_template("inicio.html", resumen=f.resumen_inicio(u["rol"], u["unidad"]))


# HU-1 Entradas
@app.route("/entradas", methods=["GET", "POST"])
@solo_roles("bodega")
def entradas():
    if request.method == "POST":
        try:
            entrada_id = f.registrar_entrada(
                session["usuario"]["id"],
                request.form.get("medicamento"),
                request.form.get("lote"),
                request.form.get("vencimiento"),
                request.form.get("cantidad"),
                request.form.get("proveedor"),
                request.form.get("ubicacion"),
            )
            flash("Entrada registrada correctamente.", "ok")
            return redirect(url_for("comprobante", entrada_id=entrada_id))
        except ValueError as error:
            flash(str(error), "error")
    return render_template("entradas.html", medicamentos=f.listar_medicamentos(),
                           proveedores=f.listar_proveedores(), recientes=f.ultimas_entradas(),
                           hoy=date.today().isoformat(), form=request.form)


@app.route("/entradas/<int:entrada_id>")
@solo_roles("bodega", "farmacia", "gerencia")
def comprobante(entrada_id):
    entrada = f.obtener_entrada(entrada_id)
    if not entrada:
        abort(404)
    return render_template("comprobante.html", e=entrada)


# Inventario y HU-2 Cuarentena
@app.route("/inventario")
@login_requerido
def inventario():
    texto = request.args.get("q", "").strip()
    estado = request.args.get("estado", "")
    return render_template("inventario.html", lotes=f.buscar_stock(texto, estado), q=texto, estado=estado)


@app.route("/inventario/<int:lote_id>/cuarentena", methods=["POST"])
@solo_roles("bodega")
def cuarentena(lote_id):
    try:
        f.poner_en_cuarentena(session["usuario"]["id"], lote_id, request.form.get("motivo"))
        flash("El lote quedó en cuarentena y no se puede despachar.", "ok")
    except ValueError as error:
        flash(str(error), "error")
    return redirect(url_for("inventario"))


@app.route("/inventario/<int:lote_id>/liberar", methods=["POST"])
@solo_roles("bodega")
def liberar(lote_id):
    try:
        f.liberar_lote(session["usuario"]["id"], lote_id)
        flash("El lote fue liberado.", "ok")
    except ValueError as error:
        flash(str(error), "error")
    return redirect(url_for("inventario"))


#HU-3 y HU-4 Solicitudes
@app.route("/solicitudes/nueva", methods=["GET", "POST"])
@solo_roles("clinica")
def solicitud_nueva():
    u = session["usuario"]
    if request.method == "POST":
        pares = zip(request.form.getlist("medicamento"), request.form.getlist("cantidad"))
        items = [(m, c) for m, c in pares if m]
        try:
            codigo = f.crear_solicitud(u["id"], u["unidad"], request.form.get("ficha"),
                                       request.form.get("prioridad"), items)
            flash("Solicitud " + codigo + " enviada a Farmacia Central.", "ok")
            return redirect(url_for("solicitudes"))
        except ValueError as error:
            flash(str(error), "error")
    return render_template("solicitud_nueva.html", medicamentos=f.listar_medicamentos(),
                           prioridades=f.PRIORIDADES, form=request.form)


def datos_solicitudes():
    u = session["usuario"]
    return f.listar_solicitudes(u["rol"], u["unidad"], request.args.get("estado", ""),
                                request.args.get("q", "").strip())


@app.route("/solicitudes")
@solo_roles("clinica", "farmacia", "gerencia")
def solicitudes():
    return render_template("solicitudes.html", solicitudes=datos_solicitudes(),
                           estado=request.args.get("estado", ""), q=request.args.get("q", ""))


@app.route("/solicitudes/tabla")
@solo_roles("clinica", "farmacia", "gerencia")
def solicitudes_tabla():
    """Solo la tabla: la página la pide cada 15 segundos para actualizarse sin recargar."""
    return render_template("_tabla_solicitudes.html", solicitudes=datos_solicitudes())


def accion_solicitud(funcion, mensaje_ok):
    try:
        resultado = funcion()
        flash(mensaje_ok, "ok")
        return resultado
    except ValueError as error:
        flash(str(error), "error")


@app.route("/solicitudes/<int:solicitud_id>/preparar", methods=["POST"])
@solo_roles("farmacia")
def preparar(solicitud_id):
    accion_solicitud(lambda: f.preparar_solicitud(session["usuario"]["id"], solicitud_id),
                     "La solicitud quedó En Preparación.")
    return redirect(url_for("solicitudes"))


@app.route("/solicitudes/<int:solicitud_id>/despachar", methods=["POST"])
@solo_roles("farmacia")
def despachar(solicitud_id):
    try:
        incompletos = f.despachar_solicitud(session["usuario"]["id"], solicitud_id)
        if incompletos:
            flash("Despachada con FEFO, pero faltó stock en " + str(incompletos) + " ítem(s).", "ok")
        else:
            flash("Solicitud despachada con FEFO y stock descontado.", "ok")
    except ValueError as error:
        flash(str(error), "error")
    return redirect(url_for("solicitudes"))


@app.route("/solicitudes/<int:solicitud_id>/rechazar", methods=["POST"])
@solo_roles("farmacia")
def rechazar(solicitud_id):
    accion_solicitud(lambda: f.rechazar_solicitud(session["usuario"]["id"], solicitud_id,
                                                  request.form.get("motivo")),
                     "La solicitud fue rechazada.")
    return redirect(url_for("solicitudes"))


@app.route("/solicitudes/<int:solicitud_id>/cancelar", methods=["POST"])
@solo_roles("clinica")
def cancelar(solicitud_id):
    u = session["usuario"]
    accion_solicitud(lambda: f.cancelar_solicitud(u["id"], u["unidad"], solicitud_id, request.form.get("motivo")),
                     "La solicitud fue cancelada.")
    return redirect(url_for("solicitudes"))


#HU-6 Alertas
@app.route("/alertas")
@solo_roles("farmacia", "gerencia")
def alertas():
    return render_template("alertas.html", alertas=f.alertas_stock())


@app.route("/alertas/<int:medicamento_id>", methods=["POST"])
@solo_roles("farmacia")
def guardar_umbrales(medicamento_id):
    accion_solicitud(
        lambda: f.guardar_umbrales(session["usuario"]["id"], medicamento_id, request.form.get("minimo"),
                                   request.form.get("critico"), request.form.get("seguridad")),
        "Niveles de stock actualizados.")
    return redirect(url_for("alertas"))


#HU-7 Vencimientos
@app.route("/vencimientos")
@solo_roles("bodega", "farmacia", "gerencia")
def vencimientos():
    lotes = f.semaforo_lotes()
    conteo = {nombre: len([l for l in lotes if l["semaforo"] == nombre])
              for nombre in ("Vencido", "Rojo", "Amarillo", "Verde")}
    return render_template("vencimientos.html", lotes=lotes, conteo=conteo)


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
