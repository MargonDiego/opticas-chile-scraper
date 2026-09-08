# 🚀 Despliegue en Homelab con Coolify (Ubuntu - 192.168.1.85)

Esta guía detalla cómo desplegar el servicio **Chilean Optics Scraper & API** en tu servidor Ubuntu con **Coolify**.

---

## 📋 Requisitos Previos

- Servidor Ubuntu en `192.168.1.85` con Coolify instalado y corriendo.
- Acceso a la interfaz web de Coolify (generalmente en `http://192.168.1.85:8000` o el puerto configurado).
- Repositorio de GitHub con este código.

---

## 🛠️ Opción 1: Despliegue desde la UI de Coolify (Recomendado)

1. **Crear Nuevo Recurso**:
   - Entrá a tu panel de Coolify en `http://192.168.1.85:8000`.
   - Seleccioná tu **Project** / **Environment**.
   - Hacé clic en **+ New Resource** -> **Application** -> **Public Repository** (o Private con tu GitHub App/Deploy Key).

2. **Configurar el Repositorio**:
   - URL del repositorio: `https://github.com/tu-usuario/opticas-chile-scraper`
   - Branch: `main`
   - Build Pack: **Dockerfile** (o **Docker Compose**).

3. **Configurar Variables de Entorno (Environment Variables)**:
   Agregá en Coolify:
   ```env
   ENVIRONMENT=production
   PORT=8000
   DATABASE_URL=sqlite+aiosqlite:///data/opticas.db
   AUTO_SCRAPE_INTERVAL_HOURS=12
   SCRAPER_MAX_CONCURRENCY=5
   ```

4. **Configurar Almacenamiento Persistente (Volumes)**:
   Para que la base de datos con el historial de precios no se borre entre reinicios:
   - Volume / Mount: `opticas_data:/app/data`

5. **Exposición de Puerto**:
   - Port Mapping: `8000:8000` (o asignale un dominio interno/local con el proxy Caddy/Traefik de Coolify, ej: `http://opticas.local`).

6. **Desplegar**:
   - Hacé clic en **Deploy**.
   - `uv` compilará la imagen en segundos.

---

## 🖥️ Opción 2: Despliegue directo por SSH y Docker Compose

Si preferís levantarlo directamente por terminal en el servidor:

```bash
# 1. Conectarse al servidor Ubuntu
ssh chalaox@192.168.1.85

# 2. Clonar el repositorio
git clone https://github.com/tu-usuario/opticas-chile-scraper.git /home/chalaox/opticas-chile-scraper
cd /home/chalaox/opticas-chile-scraper

# 3. Levantar con Docker Compose
docker compose up -d --build

# 4. Verificar logs
docker compose logs -f
```

---

## 🔍 Verificación Post-Despliegue

1. **Healthcheck**:
   ```bash
   curl http://192.168.1.85:8000/api/health
   ```
2. **Swagger UI**:
   Abrí en tu navegador: `http://192.168.1.85:8000/docs`

3. **Disparar un Scrape Manual de Prueba**:
   ```bash
   curl -X POST http://192.168.1.85:8000/api/scrape/trigger \
     -H "Content-Type: application/json" \
     -d '{"store": "gmo", "max_pages": 2}'
   ```