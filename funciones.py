"""Funciones del sistema HSG SGMI (reglas de negocio del Sprint 1)."""
from datetime import date, datetime

from db import consultar, una_fila, transaccion

PRIORIDADES = ["Urgente", "Normal", "Reposición"]
ORDEN_PRIORIDAD = {"Urgente": 0, "Normal": 1, "Reposición": 2}
ESTADOS_ACTIVOS = ("Pendiente", "En Preparación")


def ahora():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def a_entero(valor, nombre):
    try:
        return int(valor)
    except (TypeError, ValueError):
        raise ValueError(nombre + " debe ser un número entero.")


def bitacora(cur, usuario_id, accion, detalle):
    cur.execute(
        "INSERT INTO bitacora (usuario_id, accion, detalle) VALUES (%s, %s, %s)",
        (usuario_id, accion, detalle),
    )


# ---------------------------------------------------------------- Catálogos
def listar_medicamentos():
    return consultar("SELECT id, nombre, presentacion FROM medicamentos ORDER BY nombre")


def listar_proveedores():
    return consultar("SELECT id, nombre FROM proveedores ORDER BY nombre")


# ------------------------------------------------- HU-1 Registro de entradas
def registrar_entrada(usuario_id, medicamento_id, lote, fecha_venc, cantidad, proveedor_id, ubicacion):
    lote = (lote or "").strip()
    if not lote:
        raise ValueError("Debes indicar el número de lote.")
    cantidad = a_entero(cantidad, "La cantidad")
    if cantidad <= 0:
        raise ValueError("La cantidad debe ser mayor que cero.")
    medicamento_id = a_entero(medicamento_id, "El medicamento")
    proveedor_id = a_entero(proveedor_id, "El proveedor")
    try:
        vence = date.fromisoformat(fecha_venc)
    except (TypeError, ValueError):
        raise ValueError("La fecha de vencimiento no es válida.")
    if vence <= date.today():
        raise ValueError("La fecha de vencimiento debe ser posterior a la fecha actual.")
    ubicacion = (ubicacion or "").strip() or None

    def trabajo(cur):
        cur.execute(
            "SELECT id, cantidad, estado, fecha_vencimiento FROM lotes "
            "WHERE medicamento_id = %s AND lote = %s FOR UPDATE",
            (medicamento_id, lote),
        )
        actual = cur.fetchone()
        if actual:
            if str(actual["fecha_vencimiento"]) != vence.isoformat():
                raise ValueError("Ese lote ya existe con otra fecha de vencimiento.")
            nueva_cantidad = actual["cantidad"] + cantidad
            estado = "Disponible" if actual["estado"] == "Agotado" else actual["estado"]
            cur.execute("UPDATE lotes SET cantidad = %s, estado = %s WHERE id = %s",
                        (nueva_cantidad, estado, actual["id"]))
            lote_id = actual["id"]
        else:
            cur.execute(
                "INSERT INTO lotes (medicamento_id, lote, fecha_vencimiento, cantidad, proveedor_id, ubicacion) "
                "VALUES (%s, %s, %s, %s, %s, %s)",
                (medicamento_id, lote, vence.isoformat(), cantidad, proveedor_id, ubicacion),
            )
            lote_id = cur.lastrowid
        cur.execute(
            "INSERT INTO entradas (lote_id, cantidad, proveedor_id, usuario_id) VALUES (%s, %s, %s, %s)",
            (lote_id, cantidad, proveedor_id, usuario_id),
        )
        entrada_id = cur.lastrowid
        codigo = "ENT-%06d" % entrada_id
        cur.execute("UPDATE entradas SET codigo = %s WHERE id = %s", (codigo, entrada_id))
        bitacora(cur, usuario_id, "ENTRADA", codigo + ": lote " + lote + ", " + str(cantidad) + " unidades")
        return entrada_id

    return transaccion(trabajo)


def obtener_entrada(entrada_id):
    return una_fila(
        "SELECT e.id, e.codigo, e.cantidad, e.fecha, l.lote, l.fecha_vencimiento, l.ubicacion, "
        "m.nombre AS medicamento, p.nombre AS proveedor, u.nombre AS usuario "
        "FROM entradas e "
        "JOIN lotes l ON l.id = e.lote_id "
        "JOIN medicamentos m ON m.id = l.medicamento_id "
        "JOIN proveedores p ON p.id = e.proveedor_id "
        "JOIN usuarios u ON u.id = e.usuario_id "
        "WHERE e.id = %s", (entrada_id,))


def ultimas_entradas(limite=10):
    return consultar(
        "SELECT e.id, e.codigo, e.cantidad, e.fecha, l.lote, m.nombre AS medicamento, u.nombre AS usuario "
        "FROM entradas e "
        "JOIN lotes l ON l.id = e.lote_id "
        "JOIN medicamentos m ON m.id = l.medicamento_id "
        "JOIN usuarios u ON u.id = e.usuario_id "
        "ORDER BY e.id DESC LIMIT " + str(int(limite)))


# --------------------------------------- HU-7 Semáforo (se usa en varias vistas)
def semaforo(dias):
    """Rojo: 30 días o menos. Amarillo: 31 a 60. Verde: más de 60."""
    if dias < 0:
        return "Vencido"
    if dias <= 30:
        return "Rojo"
    if dias <= 60:
        return "Amarillo"
    return "Verde"


def semaforo_lotes():
    filas = consultar(
        "SELECT l.id, m.nombre, l.lote, l.fecha_vencimiento, l.cantidad, l.ubicacion, l.estado, "
        "DATEDIFF(l.fecha_vencimiento, CURDATE()) AS dias "
        "FROM lotes l JOIN medicamentos m ON m.id = l.medicamento_id "
        "WHERE l.cantidad > 0 ORDER BY l.fecha_vencimiento, m.nombre")
    for fila in filas:
        fila["semaforo"] = semaforo(fila["dias"])
    return filas


# ------------------------------------------- Consulta de stock y HU-2 Cuarentena
def buscar_stock(texto="", estado=""):
    sql = (
        "SELECT l.id, m.nombre, m.principio_activo, l.lote, l.fecha_vencimiento, l.cantidad, l.ubicacion, "
        "l.estado, l.motivo_cuarentena, DATEDIFF(l.fecha_vencimiento, CURDATE()) AS dias "
        "FROM lotes l JOIN medicamentos m ON m.id = l.medicamento_id WHERE 1 = 1 "
    )
    params = []
    if texto:
        sql += "AND (m.nombre LIKE %s OR m.principio_activo LIKE %s OR l.lote LIKE %s OR l.ubicacion LIKE %s) "
        params += ["%" + texto + "%"] * 4
    if estado:
        sql += "AND l.estado = %s "
        params.append(estado)
    sql += "ORDER BY m.nombre, l.fecha_vencimiento"
    filas = consultar(sql, params)
    for fila in filas:
        fila["semaforo"] = semaforo(fila["dias"])
    return filas


def poner_en_cuarentena(usuario_id, lote_id, motivo):
    motivo = (motivo or "").strip()
    if not motivo:
        raise ValueError("El motivo de la cuarentena es obligatorio.")

    def trabajo(cur):
        cur.execute("SELECT lote, estado FROM lotes WHERE id = %s FOR UPDATE", (lote_id,))
        lote = cur.fetchone()
        if not lote:
            raise ValueError("No se encontró el lote.")
        if lote["estado"] == "En cuarentena":
            raise ValueError("El lote ya está en cuarentena.")
        cur.execute("UPDATE lotes SET estado = 'En cuarentena', motivo_cuarentena = %s WHERE id = %s",
                    (motivo, lote_id))
        bitacora(cur, usuario_id, "CUARENTENA", "Lote " + lote["lote"] + ": " + motivo)

    transaccion(trabajo)


def liberar_lote(usuario_id, lote_id):
    def trabajo(cur):
        cur.execute("SELECT lote, estado, cantidad FROM lotes WHERE id = %s FOR UPDATE", (lote_id,))
        lote = cur.fetchone()
        if not lote:
            raise ValueError("No se encontró el lote.")
        if lote["estado"] != "En cuarentena":
            raise ValueError("El lote no está en cuarentena.")
        estado = "Disponible" if lote["cantidad"] > 0 else "Agotado"
        cur.execute("UPDATE lotes SET estado = %s, motivo_cuarentena = NULL WHERE id = %s", (estado, lote_id))
        bitacora(cur, usuario_id, "LIBERACION", "Lote " + lote["lote"] + " liberado a " + estado)

    transaccion(trabajo)


# ------------------------------------------ HU-3 Solicitud digital por paciente
def crear_solicitud(usuario_id, unidad, ficha, prioridad, items):
    """items: lista de pares (medicamento_id, cantidad) tal como llegan del formulario."""
    ficha = (ficha or "").strip()
    if prioridad not in PRIORIDADES:
        raise ValueError("La prioridad no es válida.")
    if prioridad != "Reposición" and not ficha:
        raise ValueError("Indica la ficha médica o el RUT del paciente.")
    pedidos = {}
    for medicamento_id, cantidad in items:
        medicamento_id = a_entero(medicamento_id, "El medicamento")
        cantidad = a_entero(cantidad, "La cantidad")
        if cantidad <= 0:
            raise ValueError("Las cantidades deben ser mayores que cero.")
        pedidos[medicamento_id] = pedidos.get(medicamento_id, 0) + cantidad
    if not pedidos:
        raise ValueError("Agrega al menos un medicamento a la solicitud.")

    def trabajo(cur):
        cur.execute(
            "INSERT INTO solicitudes (ficha_paciente, unidad, prioridad, solicitante_id) VALUES (%s, %s, %s, %s)",
            (ficha or None, unidad, prioridad, usuario_id),
        )
        solicitud_id = cur.lastrowid
        codigo = "SOL-%06d" % solicitud_id
        cur.execute("UPDATE solicitudes SET codigo = %s WHERE id = %s", (codigo, solicitud_id))
        for medicamento_id, cantidad in pedidos.items():
            cur.execute(
                "INSERT INTO solicitud_items (solicitud_id, medicamento_id, cantidad_pedida) VALUES (%s, %s, %s)",
                (solicitud_id, medicamento_id, cantidad),
            )
        bitacora(cur, usuario_id, "SOLICITUD", codigo + " (" + prioridad + ") de " + unidad)
        return codigo

    return transaccion(trabajo)


# --------------------------------- HU-4 Estado de solicitudes (y cola de Farmacia)
def listar_solicitudes(rol, unidad=None, estado="", texto=""):
    sql = (
        "SELECT s.id, s.codigo, s.ficha_paciente, s.unidad, s.prioridad, s.estado, s.creada, s.actualizada, "
        "s.motivo, u.nombre AS solicitante "
        "FROM solicitudes s JOIN usuarios u ON u.id = s.solicitante_id WHERE 1 = 1 "
    )
    params = []
    if rol == "clinica":
        sql += "AND s.unidad = %s "
        params.append(unidad)
    if estado:
        sql += "AND s.estado = %s "
        params.append(estado)
    if texto:
        sql += "AND (s.ficha_paciente LIKE %s OR s.codigo LIKE %s) "
        params += ["%" + texto + "%"] * 2
    sql += "ORDER BY s.creada DESC, s.id DESC"
    solicitudes = consultar(sql, params)

    if solicitudes:
        ids = [s["id"] for s in solicitudes]
        marcas = ", ".join(["%s"] * len(ids))
        items = consultar(
            "SELECT i.solicitud_id, m.nombre, i.cantidad_pedida, i.cantidad_despachada "
            "FROM solicitud_items i JOIN medicamentos m ON m.id = i.medicamento_id "
            "WHERE i.solicitud_id IN (" + marcas + ") ORDER BY i.id", ids)
        for s in solicitudes:
            s["items"] = [i for i in items if i["solicitud_id"] == s["id"]]

    if rol == "farmacia":
        # Cola priorizada: primero las activas, por prioridad y antigüedad
        solicitudes.sort(key=lambda s: (
            s["estado"] not in ESTADOS_ACTIVOS,
            ORDEN_PRIORIDAD[s["prioridad"]] if s["estado"] in ESTADOS_ACTIVOS else 0,
            str(s["creada"]) if s["estado"] in ESTADOS_ACTIVOS else "",
        ))
    return solicitudes


def cancelar_solicitud(usuario_id, unidad, solicitud_id, motivo):
    motivo = (motivo or "").strip()
    if not motivo:
        raise ValueError("Indica el motivo de la cancelación.")

    def trabajo(cur):
        cur.execute("SELECT codigo, estado, unidad FROM solicitudes WHERE id = %s FOR UPDATE", (solicitud_id,))
        s = cur.fetchone()
        if not s or s["unidad"] != unidad:
            raise ValueError("No se encontró la solicitud en tu unidad.")
        if s["estado"] != "Pendiente":
            raise ValueError("Solo se pueden cancelar solicitudes en estado Pendiente.")
        cur.execute("UPDATE solicitudes SET estado = 'Cancelada', motivo = %s, actualizada = %s WHERE id = %s",
                    (motivo, ahora(), solicitud_id))
        bitacora(cur, usuario_id, "CANCELACION", s["codigo"] + ": " + motivo)

    transaccion(trabajo)


# ------------------------------------------------- HU-5 Despacho con FEFO
def preparar_solicitud(usuario_id, solicitud_id):
    def trabajo(cur):
        cur.execute("SELECT codigo, estado FROM solicitudes WHERE id = %s FOR UPDATE", (solicitud_id,))
        s = cur.fetchone()
        if not s or s["estado"] != "Pendiente":
            raise ValueError("Solo se puede preparar una solicitud Pendiente.")
        cur.execute("UPDATE solicitudes SET estado = 'En Preparación', actualizada = %s WHERE id = %s",
                    (ahora(), solicitud_id))
        bitacora(cur, usuario_id, "PREPARACION", s["codigo"])

    transaccion(trabajo)


def despachar_solicitud(usuario_id, solicitud_id):
    """Despacha usando FEFO: primero salen los lotes que vencen antes.
    No usa lotes vencidos ni en cuarentena. Devuelve cuántos ítems quedaron incompletos."""

    def trabajo(cur):
        cur.execute("SELECT codigo, estado FROM solicitudes WHERE id = %s FOR UPDATE", (solicitud_id,))
        s = cur.fetchone()
        if not s:
            raise ValueError("No se encontró la solicitud.")
        if s["estado"] not in ESTADOS_ACTIVOS:
            raise ValueError("Esta solicitud ya no se puede despachar (estado: " + s["estado"] + ").")
        cur.execute("SELECT id, medicamento_id, cantidad_pedida FROM solicitud_items WHERE solicitud_id = %s",
                    (solicitud_id,))
        items = cur.fetchall()
        total = 0
        incompletos = 0
        for item in items:
            falta = item["cantidad_pedida"]
            entregado = 0
            cur.execute(
                "SELECT id, cantidad FROM lotes "
                "WHERE medicamento_id = %s AND estado = 'Disponible' AND cantidad > 0 "
                "AND fecha_vencimiento >= CURDATE() ORDER BY fecha_vencimiento, id FOR UPDATE",
                (item["medicamento_id"],))
            for lote in cur.fetchall():
                if falta == 0:
                    break
                tomar = min(falta, lote["cantidad"])
                restante = lote["cantidad"] - tomar
                estado = "Agotado" if restante == 0 else "Disponible"
                cur.execute("UPDATE lotes SET cantidad = %s, estado = %s WHERE id = %s",
                            (restante, estado, lote["id"]))
                cur.execute("INSERT INTO despacho_lotes (item_id, lote_id, cantidad) VALUES (%s, %s, %s)",
                            (item["id"], lote["id"], tomar))
                falta -= tomar
                entregado += tomar
            cur.execute("UPDATE solicitud_items SET cantidad_despachada = %s WHERE id = %s",
                        (entregado, item["id"]))
            total += entregado
            if falta > 0:
                incompletos += 1
        if total == 0:
            raise ValueError("No hay stock vigente para despachar. Puedes rechazar la solicitud indicando el motivo.")
        nota = "Despacho parcial por falta de stock" if incompletos else None
        cur.execute("UPDATE solicitudes SET estado = 'Despachado', actualizada = %s, motivo = %s WHERE id = %s",
                    (ahora(), nota, solicitud_id))
        bitacora(cur, usuario_id, "DESPACHO", s["codigo"] + " (FEFO)")
        return incompletos

    return transaccion(trabajo)


def rechazar_solicitud(usuario_id, solicitud_id, motivo):
    motivo = (motivo or "").strip()
    if not motivo:
        raise ValueError("El motivo del rechazo es obligatorio.")

    def trabajo(cur):
        cur.execute("SELECT codigo, estado FROM solicitudes WHERE id = %s FOR UPDATE", (solicitud_id,))
        s = cur.fetchone()
        if not s or s["estado"] not in ESTADOS_ACTIVOS:
            raise ValueError("Solo se pueden rechazar solicitudes activas.")
        cur.execute("UPDATE solicitudes SET estado = 'Rechazado', motivo = %s, actualizada = %s WHERE id = %s",
                    (motivo, ahora(), solicitud_id))
        bitacora(cur, usuario_id, "RECHAZO", s["codigo"] + ": " + motivo)

    transaccion(trabajo)


# ------------------------------------------- HU-6 Alertas de stock mínimo
def nivel_stock(stock, minimo, critico, seguridad):
    if stock <= critico:
        return "Crítico"
    if stock <= minimo:
        return "Mínimo"
    if stock <= seguridad:
        return "Seguridad"
    return "Normal"


def alertas_stock():
    """Stock vigente = lotes Disponibles que no están vencidos."""
    filas = consultar(
        "SELECT m.id, m.nombre, m.stock_minimo, m.stock_critico, m.stock_seguridad, "
        "COALESCE(SUM(l.cantidad), 0) AS stock "
        "FROM medicamentos m LEFT JOIN lotes l ON l.medicamento_id = m.id "
        "AND l.estado = 'Disponible' AND l.fecha_vencimiento >= CURDATE() "
        "GROUP BY m.id, m.nombre, m.stock_minimo, m.stock_critico, m.stock_seguridad "
        "ORDER BY m.nombre")
    for fila in filas:
        fila["stock"] = int(fila["stock"])
        fila["nivel"] = nivel_stock(fila["stock"], fila["stock_minimo"], fila["stock_critico"], fila["stock_seguridad"])
    return filas


def guardar_umbrales(usuario_id, medicamento_id, minimo, critico, seguridad):
    minimo = a_entero(minimo, "El stock mínimo")
    critico = a_entero(critico, "El stock crítico")
    seguridad = a_entero(seguridad, "El stock de seguridad")
    if critico < 0 or minimo < 0 or seguridad < 0:
        raise ValueError("Los niveles no pueden ser negativos.")
    if not (critico <= minimo <= seguridad):
        raise ValueError("Se debe cumplir: crítico ≤ mínimo ≤ seguridad.")

    def trabajo(cur):
        cur.execute(
            "UPDATE medicamentos SET stock_minimo = %s, stock_critico = %s, stock_seguridad = %s WHERE id = %s",
            (minimo, critico, seguridad, medicamento_id))
        bitacora(cur, usuario_id, "UMBRALES", "Medicamento " + str(medicamento_id) + ": " +
                 str(critico) + "/" + str(minimo) + "/" + str(seguridad))

    transaccion(trabajo)


# ------------------------------------------------------------ Panel de inicio
def resumen_inicio(rol, unidad):
    alertas = alertas_stock()
    lotes = semaforo_lotes()
    if rol == "clinica":
        activas = una_fila(
            "SELECT COUNT(*) AS n FROM solicitudes WHERE estado IN ('Pendiente', 'En Preparación') AND unidad = %s",
            (unidad,))
    else:
        activas = una_fila("SELECT COUNT(*) AS n FROM solicitudes WHERE estado IN ('Pendiente', 'En Preparación')")
    cuarentena = una_fila("SELECT COUNT(*) AS n FROM lotes WHERE estado = 'En cuarentena'")
    return {
        "criticos": len([a for a in alertas if a["nivel"] == "Crítico"]),
        "minimos": len([a for a in alertas if a["nivel"] == "Mínimo"]),
        "rojos": len([l for l in lotes if l["semaforo"] == "Rojo"]),
        "vencidos": len([l for l in lotes if l["semaforo"] == "Vencido"]),
        "activas": activas["n"],
        "cuarentena": cuarentena["n"],
    }
