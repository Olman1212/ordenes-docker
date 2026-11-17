# Órdenes Docker: arquitectura de 3 contenedores

**Asignatura:** Arquitectura de Computadoras, Universidad Tecnológica de Honduras (UTH)
**Trabajo:** Parte práctica del examen del segundo parcial: arquitectura de 3 contenedores (Django + API Flask + SQL Server)
**Grupo:** 2

Es una aplicación para gestionar **órdenes** y sus **líneas de detalle**, distribuida en tres contenedores que se levantan con un solo comando de Docker Compose:

| Contenedor | Tecnología | Responsabilidad |
|---|---|---|
| `db` | Imagen oficial `mcr.microsoft.com/mssql/server:2022-latest` | Guarda la base **OrdenesDB** con las tablas `ordenes` y `orden_detalle`. Los datos viven en el volumen con nombre `ordenes-datos`. |
| `api` | Python + Flask + pymssql (imagen propia) | Expone la API REST en JSON con el CRUD de órdenes y detalles. Es el **único** servicio que se conecta a SQL Server. |
| `web` | Python + Django + requests (imagen propia) | Frontend con las pantallas CRUD. Consume la API en `http://api:5000` y **no** se conecta a la base de datos. |

Flujo: **Navegador → web (Django) → api (Flask) → db (SQL Server)**

---

## Integrantes

| N.º | Nombre completo | Número de cuenta |
|---|---|---|
| 1 | Jeancarlo Murillo Ortiz | 202210060019 |
| 2 | Olman Darío Peña Espinal | 202510010127 |
| 3 | Brayan Adonay Cedillo Mayorga | 202310010645 |
| 4 | Edwin Daniel Díaz Orellana | 202130030079 |
| 5 | Carlos Josué López | 202430060683 |
| 6 | David Alonso Padilla Brizuela | 202430010027 |
| 7 | Alexis Joel Márquez Vásquez | 202230060291 |

---

## Diagrama de la arquitectura

```mermaid
flowchart LR
    N["Navegador<br/>localhost:8000"]
    C["curl / Postman<br/>localhost:5000"]

    subgraph RED["Red bridge propia: red-ordenes"]
        W["web<br/>Django + gunicorn<br/>puerto 8000<br/>0.5 CPU, 256 MB"]
        A["api<br/>Flask + gunicorn<br/>puerto 5000<br/>0.5 CPU, 256 MB"]
        D[("db<br/>SQL Server 2022<br/>puerto 1433 (solo interno)<br/>2 CPU, 2 GB")]
        I["db-init<br/>sqlcmd -i init.sql<br/>se ejecuta una vez y termina"]
    end

    V[("Volumen con nombre<br/>ordenes-datos<br/>/var/opt/mssql")]

    N -- "HTTP 8000:8000" --> W
    C -- "HTTP 5000:5000" --> A
    W -- "HTTP http://api:5000 (requests)" --> A
    A -- "TDS db:1433 (pymssql)" --> D
    I -- "db:1433" --> D
    D --- V
```

| Servicio | Imagen | Puerto host → contenedor | Depende de | Healthcheck |
|---|---|---|---|---|
| `db` | `mcr.microsoft.com/mssql/server:2022-latest` | no se publica (solo `1433` dentro de la red) | — | `sqlcmd ... -Q "SELECT 1"` |
| `db-init` | la misma de `db` (trae `sqlcmd`) | — | `db` sano | — (termina con código 0) |
| `api` | `olman1212/ordenes-api:v1.0` | `5000 → 5000` | `db` sano y `db-init` terminado | `GET /health` |
| `web` | `olman1212/ordenes-web:v1.0` | `8000 → 8000` | `api` sana | `GET /salud/` |

---

## Estructura del repositorio

```
ordenes-docker/
├── compose.yaml          # db, db-init, api y web; red, volumen, límites y healthchecks
├── .env.example          # plantilla de variables (sin contraseñas reales)
├── README.md
├── db/
│   └── init.sql          # crea OrdenesDB, tablas (PK, IDENTITY, FK) y 5 órdenes de prueba
├── api/
│   ├── Dockerfile
│   ├── .dockerignore
│   ├── requirements.txt  # Flask, pymssql, gunicorn
│   └── app.py            # API REST
├── web/
│   ├── Dockerfile
│   ├── .dockerignore
│   ├── requirements.txt  # Django, requests, gunicorn
│   ├── manage.py
│   ├── ordenes_web/      # configuración del proyecto Django
│   └── ordenes/          # vistas, formularios, cliente de la API y plantillas
└── evidencias/           # capturas y script de pruebas de la API
```

---

## Pasos para ejecutar el proyecto desde cero

**Requisitos:** Docker Desktop (o Docker Engine con el plugin Compose v2) y Git. SQL Server necesita que Docker tenga al menos 2 GB de RAM disponibles.

1. Clonar el repositorio y entrar a la carpeta:

   ```bash
   git clone https://github.com/Olman1212/ordenes-docker.git
   cd ordenes-docker
   ```

2. Crear el archivo `.env` a partir de la plantilla y, si se desea, cambiar la contraseña:

   ```bash
   cp .env.example .env
   ```

   En PowerShell: `Copy-Item .env.example .env`

   La contraseña de `MSSQL_SA_PASSWORD` debe tener 8 caracteres o más y combinar mayúsculas, minúsculas, números y símbolos. El `compose.yaml` no tiene ninguna contraseña escrita: la toma del `.env`.

3. Construir y levantar todo con un solo comando:

   ```bash
   docker compose up -d --build
   ```

   La primera vez tarda unos minutos porque descarga la imagen de SQL Server. Compose respeta el orden por los healthchecks: primero `db` queda sano, después `db-init` ejecuta `init.sql`, luego arranca `api` y, cuando la API está sana, arranca `web`.

4. Verificar que los tres servicios estén sanos (`healthy`):

   ```bash
   docker compose ps
   ```

5. Abrir el frontend en el navegador: **http://localhost:8000**
   La API también se puede probar directamente en **http://localhost:5000/api/ordenes**.

Para detener todo sin borrar datos: `docker compose down`. Para borrar también la base de datos (volumen): `docker compose down -v`.

### Cómo se ejecuta `init.sql`

El script lo ejecuta el servicio **`db-init`** del `compose.yaml`. Usa la misma imagen oficial de SQL Server, que ya incluye `sqlcmd`, y monta `./db/init.sql` en modo de solo lectura:

```bash
/opt/mssql-tools18/bin/sqlcmd -S db -U sa -P "$MSSQL_SA_PASSWORD" -C -b -i /init/init.sql
```

- Solo corre cuando `db` está **sano** (`depends_on` con `condition: service_healthy`).
- La API espera a que `db-init` termine bien (`condition: service_completed_successfully`).
- El script es **idempotente**: si la base, las tablas o los datos ya existen, no los vuelve a crear ni los duplica. Por eso se puede hacer `down` y `up` las veces que se quiera.

Para ver lo que hizo: `docker compose logs db-init`

### Base de datos

- `ordenes`: `id` (PK, IDENTITY), `cliente`, `fecha`, `estado` (`Pendiente`, `Pagada` o `Anulada`) y `total`.
- `orden_detalle`: `id` (PK, IDENTITY), `orden_id` (FK hacia `ordenes`), `producto`, `cantidad`, `precio_unitario` y `subtotal`.
- Datos de prueba: 5 órdenes con 2 o 3 líneas de detalle cada una (11 detalles en total).

---

## API REST (Flask)

Todas las respuestas son JSON. La conexión usa `pymssql` con el servidor `db` (nombre del servicio) y las variables de entorno `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER` y `DB_PASSWORD`.

| Método | Ruta | Acción | Códigos |
|---|---|---|---|
| GET | `/api/ordenes` | Listar órdenes | 200 |
| GET | `/api/ordenes/<id>` | Ver una orden con sus detalles | 200, 404 |
| POST | `/api/ordenes` | Crear una orden (puede incluir `detalles`) | 201, 400 |
| PUT | `/api/ordenes/<id>` | Actualizar cliente, fecha o estado | 200, 400, 404 |
| DELETE | `/api/ordenes/<id>` | Eliminar una orden y sus detalles | 200, 404 |
| GET | `/api/ordenes/<id>/detalles` | Listar las líneas de detalle de una orden | 200, 404 |
| POST | `/api/ordenes/<id>/detalles` | Agregar una línea de detalle | 201, 400, 404 |
| GET | `/api/detalles/<id>` | Ver una línea de detalle (la usa la pantalla de edición) | 200, 404 |
| PUT | `/api/detalles/<id>` | Actualizar una línea de detalle | 200, 400, 404 |
| DELETE | `/api/detalles/<id>` | Eliminar una línea de detalle | 200, 404 |
| GET | `/health` | Estado de la API y de la conexión a la base (healthcheck) | 200, 503 |

El **subtotal** de cada línea es `cantidad × precio_unitario`, y el **total** de la orden se recalcula como la suma de los subtotales cada vez que se agrega, modifica o elimina un detalle.

Ejemplos con curl (en PowerShell use `curl.exe`):

```bash
curl http://localhost:5000/health
curl http://localhost:5000/api/ordenes/1
curl -X POST http://localhost:5000/api/ordenes -H "Content-Type: application/json" -d '{"cliente":"Pedro Gomez","estado":"Pendiente"}'
curl -X POST http://localhost:5000/api/ordenes/1/detalles -H "Content-Type: application/json" -d '{"producto":"Mouse","cantidad":3,"precio_unitario":100}'
curl -X PUT http://localhost:5000/api/detalles/1 -H "Content-Type: application/json" -d '{"cantidad":5}'
curl -X DELETE http://localhost:5000/api/detalles/1
```

El script [`evidencias/pruebas-api.sh`](evidencias/pruebas-api.sh) prueba todos los endpoints, incluidos los casos de error (400 y 404). Se ejecuta con `bash evidencias/pruebas-api.sh` (en Windows, desde Git Bash). Su salida está en [`evidencias/pruebas-api.txt`](evidencias/pruebas-api.txt).

---

## Frontend (Django)

- Pantallas para **listar, crear, editar y eliminar órdenes**, y para **agregar, editar y eliminar detalles** dentro de cada orden.
- Todas las operaciones llaman a la API con la librería `requests`. La URL de la API se define con la variable de entorno `API_URL` (`http://api:5000`).
- El proyecto Django no tiene base de datos propia (`DATABASES = {}`); los mensajes se guardan en una cookie.
- Cuando la API devuelve un error, la pantalla muestra un mensaje claro con el código y el texto que envió la API (por ejemplo, `La API respondió 404: La orden 999 no existe.`). Si la API no responde, muestra `No se pudo conectar con la API`.

---

## Docker Compose y buenas prácticas

| Requisito | Cómo se cumple |
|---|---|
| Un solo `compose.yaml` | Servicios `db`, `db-init`, `api` y `web`; todo levanta con `docker compose up -d --build`. |
| `depends_on` con `service_healthy` | `api` depende de `db` (sano); `web` depende de `api` (sana). |
| Healthchecks | `db` con `sqlcmd SELECT 1`, `api` con `GET /health`, `web` con `GET /salud/`. |
| Red bridge propia | `red-ordenes` (`driver: bridge`). Los servicios se encuentran por su nombre (`db`, `api`). |
| Volumen con nombre | `ordenes-datos` montado en `/var/opt/mssql`: los datos sobreviven a `docker compose down`. |
| Variables desde `.env` | `MSSQL_SA_PASSWORD` y `DJANGO_SECRET_KEY` salen del `.env` (que no se sube a Git). Se incluye `.env.example`. |
| Límites de CPU y memoria | `db`: 2 CPU y 2 GB; `api` y `web`: 0.5 CPU y 256 MB; `db-init`: 0.5 CPU y 256 MB. |
| Usuario sin privilegios | `api` y `web` corren como `appuser` (`USER appuser` en el Dockerfile). |
| Dockerfile optimizado | `FROM`, `WORKDIR`, `COPY requirements.txt` y `RUN pip install` antes de copiar el código, para aprovechar la caché de capas; `EXPOSE` y `CMD` con gunicorn. |
| `.dockerignore` | En `api/` y `web/`. |
| Imágenes en Docker Hub | `olman1212/ordenes-api:v1.0` y `olman1212/ordenes-web:v1.0` (enlaces abajo). |

### Imágenes en Docker Hub

- API: https://hub.docker.com/r/olman1212/ordenes-api (etiqueta `v1.0`)
- Web: https://hub.docker.com/r/olman1212/ordenes-web (etiqueta `v1.0`)

Se publicaron con:

```bash
docker login
docker compose build
docker compose push api web
```

---

## Evidencias

Todas las capturas son de la ejecución real del proyecto (17/11/2026).

### 1. `docker compose ps` con los tres servicios sanos

`db-init` aparece como `Exited (0)` porque solo ejecuta `init.sql` y termina.

![docker compose ps](evidencias/01-docker-compose-ps.png)

### 2. Pruebas de la API con curl (códigos 200, 201, 400 y 404, y recálculo del total)

![Pruebas de la API, parte 1](evidencias/02-pruebas-api-1.png)
![Pruebas de la API, parte 2](evidencias/02-pruebas-api-2.png)

### 3. CRUD funcionando en el navegador

Listado de órdenes (datos de prueba de `init.sql`):

![Listado](evidencias/03-web-listado.png)

Crear una orden:

![Formulario nueva orden](evidencias/04-web-crear-orden.png)
![Orden creada](evidencias/05-web-orden-creada.png)

Agregar detalles (el total se recalcula):

![Detalles agregados](evidencias/06-web-detalles-agregados.png)

Editar un detalle:

![Editar detalle](evidencias/07-web-editar-detalle.png)
![Detalle editado](evidencias/08-web-detalle-editado.png)

Eliminar un detalle:

![Confirmar eliminación de detalle](evidencias/09-web-confirmar-eliminar-detalle.png)
![Detalle eliminado](evidencias/10-web-detalle-eliminado.png)

Editar la orden (cambio de estado):

![Editar orden](evidencias/11-web-editar-orden.png)
![Orden editada](evidencias/12-web-orden-editada.png)

Eliminar una orden:

![Confirmar eliminación de orden](evidencias/13-web-confirmar-eliminar-orden.png)
![Orden eliminada](evidencias/14-web-orden-eliminada.png)

Mensajes claros cuando la API devuelve un error (404) o no responde:

![Error 404 de la API](evidencias/15-web-error-404-de-la-api.png)
![API detenida](evidencias/16-web-error-api-caida.png)

### 4. Los datos persisten después de `docker compose down` y `up`

La orden 8 (creada desde la web) sigue ahí después de bajar y volver a levantar los contenedores, y `init.sql` no duplica los datos de prueba.

![Persistencia down / up](evidencias/17-persistencia-down-up.png)
![Datos en la web después de down / up](evidencias/18-web-datos-despues-de-down-up.png)

### 5. `docker stats` con los límites de recursos

También se muestra que `api` y `web` corren como `appuser` y la red bridge `red-ordenes`.

![docker stats](evidencias/19-docker-stats-limites.png)

---

## Comandos útiles

```bash
docker compose logs -f api     # ver los registros de la API
docker compose logs db-init    # ver la salida de init.sql
docker compose restart web     # reiniciar un servicio
docker compose down            # detener y borrar contenedores y red (los datos quedan)
docker compose down -v         # además borra el volumen: la base vuelve a los datos de prueba
```
