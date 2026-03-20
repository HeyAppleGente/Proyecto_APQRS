-- ============================================================
-- APQRS - Sistema de Gestión Residencial
-- ============================================================

CREATE DATABASE IF NOT EXISTS bd_apqrs
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

USE bd_apqrs;

-- ──────────────────────────────────────
-- ROLES
-- ──────────────────────────────────────
CREATE TABLE IF NOT EXISTS rol (
  id_rol  INT          NOT NULL AUTO_INCREMENT,
  nombre  VARCHAR(50)  NOT NULL,
  PRIMARY KEY (id_rol)
);

INSERT INTO rol (id_rol, nombre) VALUES
  (1, 'Administrador'),
  (2, 'Residente');


-- ──────────────────────────────────────
-- BLOQUES Y APARTAMENTOS
-- ──────────────────────────────────────
CREATE TABLE IF NOT EXISTS bloque (
  id_bloque INT         NOT NULL AUTO_INCREMENT,
  nombre    VARCHAR(50) NOT NULL,
  PRIMARY KEY (id_bloque)
);

CREATE TABLE IF NOT EXISTS apartamento (
  id_apartamento INT         NOT NULL AUTO_INCREMENT,
  numero         VARCHAR(10) NOT NULL,
  piso           INT         NOT NULL DEFAULT 1,
  estado         ENUM('disponible','ocupado','mantenimiento') NOT NULL DEFAULT 'disponible',
  id_bloque      INT         NOT NULL,
  PRIMARY KEY (id_apartamento),
  FOREIGN KEY (id_bloque) REFERENCES bloque(id_bloque)
);

-- Datos de ejemplo
INSERT INTO bloque (nombre) VALUES ('1'), ('2'), ('3'), ('4'), ('5'), ('6'), ('7'), ('8'), ('9'), ('10'), ('11'), ('12'), ('13'), ('14'), ('15');

INSERT INTO apartamento (numero, piso, estado, id_bloque) VALUES
  ('101', 1, 'disponible', 1),
  ('102', 1, 'disponible', 1),
  ('201', 2, 'disponible', 1),
  ('101', 1, 'disponible', 2),
  ('201', 2, 'disponible', 2),
  ('101', 1, 'disponible', 3);


-- ──────────────────────────────────────
-- USUARIOS
-- ──────────────────────────────────────
CREATE TABLE IF NOT EXISTS usuario (
  id_usuario     INT          NOT NULL AUTO_INCREMENT,
  documento      VARCHAR(20)  NOT NULL UNIQUE,
  nombres        VARCHAR(100) NOT NULL,
  apellidos      VARCHAR(100) NOT NULL,
  email          VARCHAR(150) NOT NULL UNIQUE,
  telefono       VARCHAR(20)  DEFAULT NULL,
  password_hash  VARCHAR(255) NOT NULL,
  activo         TINYINT(1)   NOT NULL DEFAULT 1,
  id_rol         INT          NOT NULL DEFAULT 2,
  id_apartamento INT          DEFAULT NULL,
  fecha_registro DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id_usuario),
  FOREIGN KEY (id_rol)         REFERENCES rol(id_rol),
  FOREIGN KEY (id_apartamento) REFERENCES apartamento(id_apartamento)
);

-- ──────────────────────────────────────
-- TIPOS DE PQRS
-- ──────────────────────────────────────
CREATE TABLE IF NOT EXISTS tipopqrs (
  id_tipopqrs INT         NOT NULL AUTO_INCREMENT,
  nombre      VARCHAR(50) NOT NULL,
  PRIMARY KEY (id_tipopqrs)
);

INSERT INTO tipopqrs (nombre) VALUES
  ('Petición'),
  ('Queja'),
  ('Reclamo'),
  ('Sugerencia');


-- ──────────────────────────────────────
-- PQRS
-- ──────────────────────────────────────
CREATE TABLE IF NOT EXISTS pqrs (
  id_pqrs        INT          NOT NULL AUTO_INCREMENT,
  asunto         VARCHAR(200) NOT NULL,
  descripcion    TEXT         NOT NULL,
  respuesta      TEXT         DEFAULT NULL,
  estado         ENUM('radicada','en_proceso','respondida','cerrada') NOT NULL DEFAULT 'radicada',
  fecha_creacion DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
  fecha_respuesta DATETIME    DEFAULT NULL,
  id_usuario     INT          NOT NULL,
  id_tipopqrs    INT          NOT NULL,
  PRIMARY KEY (id_pqrs),
  FOREIGN KEY (id_usuario)  REFERENCES usuario(id_usuario),
  FOREIGN KEY (id_tipopqrs) REFERENCES tipopqrs(id_tipopqrs)
);


-- ──────────────────────────────────────
-- TIPOS DE CITA
-- ──────────────────────────────────────
CREATE TABLE IF NOT EXISTS tipocita (
  id_tipocita INT         NOT NULL AUTO_INCREMENT,
  nombre      VARCHAR(80) NOT NULL,
  PRIMARY KEY (id_tipocita)
);

INSERT INTO tipocita (nombre) VALUES
  ('Mantenimiento'),
  ('Administración'),
  ('Seguridad'),
  ('Otro');


-- ──────────────────────────────────────
-- CITAS
-- ──────────────────────────────────────
CREATE TABLE IF NOT EXISTS citas (
  id_cita         INT          NOT NULL AUTO_INCREMENT,
  fecha_cita      DATETIME     NOT NULL,
  descripcion     TEXT         DEFAULT NULL,
  respuesta       TEXT         DEFAULT NULL,
  estado          ENUM('pendiente','confirmada','cancelada','completada') NOT NULL DEFAULT 'pendiente',
  fecha_creacion  DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
  fecha_respuesta DATETIME     DEFAULT NULL,
  id_usuario      INT          NOT NULL,
  id_tipocita     INT          NOT NULL,
  PRIMARY KEY (id_cita),
  FOREIGN KEY (id_usuario)  REFERENCES usuario(id_usuario),
  FOREIGN KEY (id_tipocita) REFERENCES tipocita(id_tipocita)
);


-- ──────────────────────────────────────
-- TIPOS DE NOTIFICACIÓN
-- ──────────────────────────────────────
CREATE TABLE IF NOT EXISTS tiponotificacion (
  id_tiponotificacion INT         NOT NULL AUTO_INCREMENT,
  nombre              VARCHAR(80) NOT NULL,
  icono               VARCHAR(50) DEFAULT 'bell',
  PRIMARY KEY (id_tiponotificacion)
);

INSERT INTO tiponotificacion (nombre, icono) VALUES
  ('PQRS',   'file-text'),
  ('Cita',   'calendar'),
  ('General','bell');


-- ──────────────────────────────────────
-- NOTIFICACIONES
-- ──────────────────────────────────────
CREATE TABLE IF NOT EXISTS notificaciones (
  id_notificacion     INT      NOT NULL AUTO_INCREMENT,
  titulo              VARCHAR(200) NOT NULL,
  mensaje             TEXT     NOT NULL,
  leido               TINYINT(1) NOT NULL DEFAULT 0,
  fecha_creacion      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  fecha_lectura       DATETIME DEFAULT NULL,
  id_usuario          INT      NOT NULL,
  id_tiponotificacion INT      NOT NULL,
  PRIMARY KEY (id_notificacion),
  FOREIGN KEY (id_usuario)          REFERENCES usuario(id_usuario),
  FOREIGN KEY (id_tiponotificacion) REFERENCES tiponotificacion(id_tiponotificacion)
);


-- ──────────────────────────────────────
-- SEGUIMIENTO (bitácora)
-- ──────────────────────────────────────
CREATE TABLE IF NOT EXISTS seguimiento (
  id_seguimiento INT      NOT NULL AUTO_INCREMENT,
  descripcion    TEXT     NOT NULL,
  tipo_registro  ENUM('pqrs','cita','general') NOT NULL DEFAULT 'general',
  fecha          DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  id_usuario     INT      NOT NULL,
  id_pqrs        INT      DEFAULT NULL,
  id_cita        INT      DEFAULT NULL,
  PRIMARY KEY (id_seguimiento),
  FOREIGN KEY (id_usuario) REFERENCES usuario(id_usuario),
  FOREIGN KEY (id_pqrs)    REFERENCES pqrs(id_pqrs),
  FOREIGN KEY (id_cita)    REFERENCES citas(id_cita)
);