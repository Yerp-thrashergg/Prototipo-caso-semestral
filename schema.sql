-- HSG SGMI - Prototipo Sprint 1 (MVP)
-- Base de datos MySQL 8. Este script se ejecuta con: python init_db.py

CREATE DATABASE IF NOT EXISTS hsg_sgmi CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE hsg_sgmi;

DROP TABLE IF EXISTS despacho_lotes;
DROP TABLE IF EXISTS solicitud_items;
DROP TABLE IF EXISTS solicitudes;
DROP TABLE IF EXISTS entradas;
DROP TABLE IF EXISTS lotes;
DROP TABLE IF EXISTS medicamentos;
DROP TABLE IF EXISTS proveedores;
DROP TABLE IF EXISTS bitacora;
DROP TABLE IF EXISTS usuarios;

CREATE TABLE usuarios (
    id INT AUTO_INCREMENT PRIMARY KEY,
    nombre VARCHAR(100) NOT NULL,
    usuario VARCHAR(40) NOT NULL UNIQUE,
    clave_hash VARCHAR(255) NOT NULL,
    rol ENUM('bodega','clinica','farmacia','gerencia') NOT NULL,
    unidad VARCHAR(60) NULL,
    activo TINYINT NOT NULL DEFAULT 1
);

CREATE TABLE proveedores (
    id INT AUTO_INCREMENT PRIMARY KEY,
    nombre VARCHAR(100) NOT NULL UNIQUE
);

CREATE TABLE medicamentos (
    id INT AUTO_INCREMENT PRIMARY KEY,
    nombre VARCHAR(100) NOT NULL,
    principio_activo VARCHAR(100) NOT NULL,
    presentacion VARCHAR(60) NOT NULL,
    stock_minimo INT NOT NULL DEFAULT 0,
    stock_critico INT NOT NULL DEFAULT 0,
    stock_seguridad INT NOT NULL DEFAULT 0
);

CREATE TABLE lotes (
    id INT AUTO_INCREMENT PRIMARY KEY,
    medicamento_id INT NOT NULL,
    lote VARCHAR(40) NOT NULL,
    fecha_vencimiento DATE NOT NULL,
    cantidad INT NOT NULL DEFAULT 0,
    proveedor_id INT NOT NULL,
    ubicacion VARCHAR(60) NULL,
    estado ENUM('Disponible','En cuarentena','Agotado') NOT NULL DEFAULT 'Disponible',
    motivo_cuarentena VARCHAR(200) NULL,
    UNIQUE (medicamento_id, lote),
    FOREIGN KEY (medicamento_id) REFERENCES medicamentos(id),
    FOREIGN KEY (proveedor_id) REFERENCES proveedores(id)
);

CREATE TABLE entradas (
    id INT AUTO_INCREMENT PRIMARY KEY,
    codigo VARCHAR(20) NULL UNIQUE,
    lote_id INT NOT NULL,
    cantidad INT NOT NULL,
    proveedor_id INT NOT NULL,
    usuario_id INT NOT NULL,
    fecha DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (lote_id) REFERENCES lotes(id),
    FOREIGN KEY (proveedor_id) REFERENCES proveedores(id),
    FOREIGN KEY (usuario_id) REFERENCES usuarios(id)
);

CREATE TABLE solicitudes (
    id INT AUTO_INCREMENT PRIMARY KEY,
    codigo VARCHAR(20) NULL UNIQUE,
    ficha_paciente VARCHAR(30) NULL,
    unidad VARCHAR(60) NOT NULL,
    prioridad ENUM('Urgente','Normal','Reposición') NOT NULL DEFAULT 'Normal',
    estado ENUM('Pendiente','En Preparación','Despachado','Rechazado','Cancelada') NOT NULL DEFAULT 'Pendiente',
    solicitante_id INT NOT NULL,
    creada DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    actualizada DATETIME NULL,
    motivo VARCHAR(250) NULL,
    FOREIGN KEY (solicitante_id) REFERENCES usuarios(id)
);

CREATE TABLE solicitud_items (
    id INT AUTO_INCREMENT PRIMARY KEY,
    solicitud_id INT NOT NULL,
    medicamento_id INT NOT NULL,
    cantidad_pedida INT NOT NULL,
    cantidad_despachada INT NOT NULL DEFAULT 0,
    FOREIGN KEY (solicitud_id) REFERENCES solicitudes(id),
    FOREIGN KEY (medicamento_id) REFERENCES medicamentos(id)
);

CREATE TABLE despacho_lotes (
    id INT AUTO_INCREMENT PRIMARY KEY,
    item_id INT NOT NULL,
    lote_id INT NOT NULL,
    cantidad INT NOT NULL,
    FOREIGN KEY (item_id) REFERENCES solicitud_items(id),
    FOREIGN KEY (lote_id) REFERENCES lotes(id)
);

CREATE TABLE bitacora (
    id INT AUTO_INCREMENT PRIMARY KEY,
    usuario_id INT NULL,
    accion VARCHAR(60) NOT NULL,
    detalle VARCHAR(255) NULL,
    fecha DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (usuario_id) REFERENCES usuarios(id)
);
