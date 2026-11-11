"""Crea la base de datos hsg_sgmi, sus tablas y datos de ejemplo.

Uso:  python init_db.py
Atención: borra y vuelve a crear las tablas del prototipo.
"""
import os
from datetime import date, timedelta

import pymysql
from werkzeug.security import generate_password_hash


def hoy_mas(dias):
    return (date.today() + timedelta(days=dias)).isoformat()


def crear_tablas(con):
    with open(os.path.join(os.path.dirname(__file__), "schema.sql"), encoding="utf-8") as archivo:
        texto = archivo.read()
    # Quita comentarios y separa las sentencias por ";"
    lineas = [l for l in texto.splitlines() if not l.strip().startswith("--")]
    with con.cursor() as cur:
        for sentencia in "\n".join(lineas).split(";"):
            if sentencia.strip():
                cur.execute(sentencia)


def cargar_datos(con):
    with con.cursor() as cur:
        usuarios = [
            ("Usuario Bodega", "bodega1", "Bodega123", "bodega", None),
            ("Usuario Urgencias", "urgencias1", "Clinica123", "clinica", "Urgencias"),
            ("Usuario Pabellón", "pabellon1", "Clinica123", "clinica", "Pabellón"),
            ("Usuario Farmacia", "farmacia1", "Farmacia123", "farmacia", None),
            ("Usuario Gerencia", "gerencia1", "Gerencia123", "gerencia", None),
        ]
        for nombre, usuario, clave, rol, unidad in usuarios:
            cur.execute(
                "INSERT INTO usuarios (nombre, usuario, clave_hash, rol, unidad) VALUES (%s, %s, %s, %s, %s)",
                (nombre, usuario, generate_password_hash(clave), rol, unidad),
            )

        for nombre in ("Droguería Andina", "Laboratorios Sur", "Distribuidora MedChile"):
            cur.execute("INSERT INTO proveedores (nombre) VALUES (%s)", (nombre,))

        medicamentos = [
            ("Paracetamol 500 mg", "Paracetamol", "Comprimidos", 100, 40, 200),
            ("Ibuprofeno 400 mg", "Ibuprofeno", "Comprimidos", 80, 30, 160),
            ("Amoxicilina 500 mg", "Amoxicilina", "Cápsulas", 60, 20, 120),
            ("Omeprazol 20 mg", "Omeprazol", "Cápsulas", 50, 20, 100),
            ("Ceftriaxona 1 g", "Ceftriaxona", "Ampolla", 40, 15, 80),
            ("Metamizol 1 g", "Metamizol", "Ampolla", 40, 15, 80),
            ("Suero fisiológico 0,9% 500 ml", "Cloruro de sodio", "Bolsa", 60, 25, 120),
            ("Adrenalina 1 mg/ml", "Adrenalina", "Ampolla", 20, 8, 40),
        ]
        for m in medicamentos:
            cur.execute(
                "INSERT INTO medicamentos (nombre, principio_activo, presentacion, stock_minimo, stock_critico, stock_seguridad) "
                "VALUES (%s, %s, %s, %s, %s, %s)", m)

        # (medicamento, lote, días para vencer, cantidad, proveedor, ubicación, estado, motivo)
        lotes = [
            (1, "PAR-2401", 200, 300, 1, "P1-E2-R1", "Disponible", None),
            (1, "PAR-2312", 25, 120, 1, "P1-E2-R2", "Disponible", None),
            (2, "IBU-2402", 150, 90, 2, "P1-E3-R1", "Disponible", None),
            (3, "AMO-2403", 70, 40, 2, "P2-E1-R1", "Disponible", None),
            (3, "AMO-2311", -5, 30, 2, "P2-E1-R2", "Disponible", None),
            (4, "OME-2404", 300, 160, 3, "P2-E2-R1", "Disponible", None),
            (5, "CEF-2405", 90, 10, 1, "P3-E1-R1", "Disponible", None),
            (5, "CEF-2406", 120, 25, 1, "P3-E1-R2", "En cuarentena", "Embalaje dañado"),
            (6, "MET-2407", 45, 100, 3, "P3-E2-R1", "Disponible", None),
            (7, "SUE-2408", 240, 200, 3, "P4-E1-R1", "Disponible", None),
            (8, "ADR-2409", 110, 12, 2, "P4-E2-R1", "Disponible", None),
        ]
        for med, lote, dias, cant, prov, ubic, estado, motivo in lotes:
            cur.execute(
                "INSERT INTO lotes (medicamento_id, lote, fecha_vencimiento, cantidad, proveedor_id, ubicacion, estado, motivo_cuarentena) "
                "VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
                (med, lote, hoy_mas(dias), cant, prov, ubic, estado, motivo))

        # (solicitante, unidad, ficha, prioridad, estado, motivo, [(medicamento, cantidad)])
        solicitudes = [
            (2, "Urgencias", "FM-10234", "Urgente", "Pendiente", None, [(8, 2), (5, 4)]),
            (3, "Pabellón", None, "Reposición", "Pendiente", None, [(1, 50), (6, 20)]),
            (2, "Urgencias", "FM-10987", "Normal", "Rechazado", "Indicación inconsistente con la dosis solicitada", [(2, 30)]),
        ]
        for i, (sol, unidad, ficha, prioridad, estado, motivo, items) in enumerate(solicitudes, 1):
            cur.execute(
                "INSERT INTO solicitudes (codigo, ficha_paciente, unidad, prioridad, estado, solicitante_id, motivo) "
                "VALUES (%s, %s, %s, %s, %s, %s, %s)",
                ("SOL-%06d" % i, ficha, unidad, prioridad, estado, sol, motivo))
            solicitud_id = cur.lastrowid
            for med, cant in items:
                cur.execute(
                    "INSERT INTO solicitud_items (solicitud_id, medicamento_id, cantidad_pedida) VALUES (%s, %s, %s)",
                    (solicitud_id, med, cant))


def main():
    con = pymysql.connect(
        host=os.environ.get("DB_HOST", "localhost"),
        port=int(os.environ.get("DB_PORT", "3306")),
        user=os.environ.get("DB_USER", "root"),
        password=os.environ.get("DB_PASSWORD", ""),
        charset="utf8mb4",
    )
    try:
        crear_tablas(con)
        cargar_datos(con)
        con.commit()
        print("Base de datos hsg_sgmi lista, con datos de ejemplo.")
    except Exception as error:
        con.rollback()
        print("No se pudo crear la base de datos:", error)
        raise
    finally:
        con.close()


if __name__ == "__main__":
    main()
