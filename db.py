"""Conexión a MySQL y funciones simples para consultar y ejecutar."""
import os
import pymysql


def conectar():
    return pymysql.connect(
        host=os.environ.get("DB_HOST", "localhost"),
        port=int(os.environ.get("DB_PORT", "3306")),
        user=os.environ.get("DB_USER", "root"),
        password=os.environ.get("DB_PASSWORD", ""),
        database="hsg_sgmi",
        charset="utf8mb4",
        cursorclass=pymysql.cursors.DictCursor,
    )


def consultar(sql, params=()):
    """Devuelve una lista de filas (diccionarios)."""
    con = conectar()
    try:
        with con.cursor() as cur:
            cur.execute(sql, params)
            return list(cur.fetchall())
    finally:
        con.close()


def una_fila(sql, params=()):
    filas = consultar(sql, params)
    return filas[0] if filas else None


def ejecutar(sql, params=()):
    """Ejecuta un INSERT/UPDATE y devuelve el id generado."""
    con = conectar()
    try:
        with con.cursor() as cur:
            cur.execute(sql, params)
            nuevo_id = cur.lastrowid
        con.commit()
        return nuevo_id
    except Exception:
        con.rollback()
        raise
    finally:
        con.close()


def transaccion(trabajo):
    """Ejecuta varias sentencias juntas: si algo falla, se deshace todo."""
    con = conectar()
    try:
        with con.cursor() as cur:
            resultado = trabajo(cur)
        con.commit()
        return resultado
    except Exception:
        con.rollback()
        raise
    finally:
        con.close()
