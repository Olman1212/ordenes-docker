-- =====================================================================
-- init.sql  -  Base de datos OrdenesDB (SQL Server 2022)
-- Lo ejecuta el servicio "db-init" del compose.yaml con sqlcmd, una vez
-- que el contenedor "db" está sano. Es idempotente: si la base, las
-- tablas o los datos ya existen, no los vuelve a crear ni los duplica.
-- =====================================================================

IF DB_ID(N'OrdenesDB') IS NULL
BEGIN
    CREATE DATABASE OrdenesDB;
    PRINT 'Base de datos OrdenesDB creada.';
END
ELSE
    PRINT 'La base de datos OrdenesDB ya existe.';
GO

USE OrdenesDB;
GO

-- ---------------------------------------------------------------------
-- Tabla ordenes
-- ---------------------------------------------------------------------
IF OBJECT_ID(N'dbo.ordenes', N'U') IS NULL
BEGIN
    CREATE TABLE dbo.ordenes (
        id       INT IDENTITY(1,1) NOT NULL CONSTRAINT PK_ordenes PRIMARY KEY,
        cliente  NVARCHAR(100)     NOT NULL,
        fecha    DATE              NOT NULL CONSTRAINT DF_ordenes_fecha  DEFAULT (CAST(GETDATE() AS DATE)),
        estado   NVARCHAR(20)      NOT NULL CONSTRAINT DF_ordenes_estado DEFAULT (N'Pendiente'),
        total    DECIMAL(12,2)     NOT NULL CONSTRAINT DF_ordenes_total  DEFAULT (0),
        CONSTRAINT CK_ordenes_estado CHECK (estado IN (N'Pendiente', N'Pagada', N'Anulada'))
    );
    PRINT 'Tabla ordenes creada.';
END
GO

-- ---------------------------------------------------------------------
-- Tabla orden_detalle (FK hacia ordenes)
-- ---------------------------------------------------------------------
IF OBJECT_ID(N'dbo.orden_detalle', N'U') IS NULL
BEGIN
    CREATE TABLE dbo.orden_detalle (
        id              INT IDENTITY(1,1) NOT NULL CONSTRAINT PK_orden_detalle PRIMARY KEY,
        orden_id        INT               NOT NULL,
        producto        NVARCHAR(100)     NOT NULL,
        cantidad        INT               NOT NULL,
        precio_unitario DECIMAL(10,2)     NOT NULL,
        subtotal        DECIMAL(12,2)     NOT NULL,
        CONSTRAINT FK_orden_detalle_ordenes FOREIGN KEY (orden_id)
            REFERENCES dbo.ordenes (id) ON DELETE CASCADE,
        CONSTRAINT CK_detalle_cantidad CHECK (cantidad > 0),
        CONSTRAINT CK_detalle_precio   CHECK (precio_unitario >= 0)
    );
    PRINT 'Tabla orden_detalle creada.';
END
GO

-- ---------------------------------------------------------------------
-- Datos de prueba: 5 órdenes con 2 o más líneas de detalle cada una.
-- Solo se insertan si la tabla ordenes está vacía (primera ejecución).
-- ---------------------------------------------------------------------
IF NOT EXISTS (SELECT 1 FROM dbo.ordenes)
BEGIN
    DECLARE @o1 INT, @o2 INT, @o3 INT, @o4 INT, @o5 INT;

    INSERT INTO dbo.ordenes (cliente, fecha, estado) VALUES (N'Ana Martínez',   '2026-11-02', N'Pagada');
    SET @o1 = SCOPE_IDENTITY();
    INSERT INTO dbo.ordenes (cliente, fecha, estado) VALUES (N'Luis Hernández', '2026-11-05', N'Pendiente');
    SET @o2 = SCOPE_IDENTITY();
    INSERT INTO dbo.ordenes (cliente, fecha, estado) VALUES (N'María López',    '2026-11-08', N'Pagada');
    SET @o3 = SCOPE_IDENTITY();
    INSERT INTO dbo.ordenes (cliente, fecha, estado) VALUES (N'Carlos Rivera',  '2026-11-10', N'Anulada');
    SET @o4 = SCOPE_IDENTITY();
    INSERT INTO dbo.ordenes (cliente, fecha, estado) VALUES (N'Sofía Castro',   '2026-11-12', N'Pendiente');
    SET @o5 = SCOPE_IDENTITY();

    INSERT INTO dbo.orden_detalle (orden_id, producto, cantidad, precio_unitario, subtotal) VALUES
        (@o1, N'Memoria RAM DDR4 8 GB',      2,  850.00,  1700.00),
        (@o1, N'Disco SSD 480 GB',           1, 1200.00,  1200.00),
        (@o2, N'Teclado mecánico',           1,  950.00,   950.00),
        (@o2, N'Mouse inalámbrico',          2,  320.00,   640.00),
        (@o2, N'Pad para mouse',             1,  150.00,   150.00),
        (@o3, N'Monitor 24 pulgadas',        1, 3500.00,  3500.00),
        (@o3, N'Cable HDMI 2 m',             2,  180.00,   360.00),
        (@o4, N'Fuente de poder 600 W',      1, 1800.00,  1800.00),
        (@o4, N'Pasta térmica',              3,   95.00,   285.00),
        (@o5, N'Memoria RAM DDR5 16 GB',     2, 1650.00,  3300.00),
        (@o5, N'Gabinete ATX',               1, 1400.00,  1400.00);

    -- El total de cada orden es la suma de los subtotales de sus detalles.
    UPDATE o
       SET total = ISNULL((SELECT SUM(d.subtotal) FROM dbo.orden_detalle d WHERE d.orden_id = o.id), 0)
      FROM dbo.ordenes o;

    PRINT 'Datos de prueba insertados: 5 ordenes y 11 detalles.';
END
ELSE
    PRINT 'Ya hay ordenes guardadas: no se insertan datos de prueba.';
GO
