# 🚀 Despliegue en Homelab con Coolify (Ubuntu - 192.168.1.85)

Esta guía detalla cómo desplegar el servicio **Chilean Optics Scraper & AI API** con **PostgreSQL + pgvector** y **Ollama** en tu servidor con Coolify.

---

## 🏗️ Arquitectura de Servicios en Coolify

- **`opticas-api`**: FastAPI app con los scrapers, cron de scraping y endpoints de IA.
- **`postgres` (`pgvector/pgvector:pg16`)**: Base de datos relacional y vectorial para búsqueda semántica.
- **`ollama`**: Servidor de modelos LLM (`llama3`, `qwen2.5`) y Embeddings (`nomic-embed-text`) ya instalado en tu servidor.

---

## 🛠️ Opción 1: Despliegue con Docker Compose en Coolify (Recomendado)

1. **Crear Nuevo Recurso en Coolify**:
   - Entrá a tu panel de Coolify en `http://192.168.1.85:8000`.
   - Clic en **+ New Resource** -> **Application** -> **Public Repository**.
   - URL del repo: `https://github.com/MargonDiego/opticas-chile-scraper`
   - Branch: `main`
   - Build Pack: **Docker Compose**.

2. **Variables de Entorno en Coolify**:
   Agregá en la sección de Environment Variables:
   ```env
   ENVIRONMENT=production
   PORT=8000
   POSTGRES_USER=opticas_user
   POSTGRES_PASSWORD=opticas_pass_segura_123
   POSTGRES_DB=opticas_db
   OLLAMA_BASE_URL=http://host.docker.internal:11434
   OLLAMA_EMBED_MODEL=nomic-embed-text
   OLLAMA_LLM_MODEL=llama3
   ```
   *(Nota: si Ollama está en la misma red de Docker de Coolify, podés usar su hostname directo ej: `http://ollama:11434`)*.

3. **Descargar Modelos en Ollama (si aún no los tenés)**:
   En la consola de tu servidor Ubuntu:
   ```bash
   ollama pull nomic-embed-text
   ollama pull llama3
   ```

4. **Desplegar**:
   - Hacé clic en **Deploy**. Coolify levantará Postgres con pgvector y compilará la API con `uv` al instante.

---

## 🖥️ Opción 2: Despliegue directo por Terminal (SSH)

```bash
# 1. Conectarse al servidor Ubuntu
ssh chalaox@192.168.1.85

# 2. Clonar o actualizar repo
git clone https://github.com/MargonDiego/opticas-chile-scraper.git /home/chalaox/opticas-chile-scraper
cd /home/chalaox/opticas-chile-scraper

# 3. Levantar con Docker Compose
docker compose up -d --build

# 4. Ver estado de contenedores
docker compose ps
docker compose logs -f opticas-api
```

---

## 🔍 Endpoints y Pruebas

1. **Swagger UI**:
   Abrí `http://192.168.1.85:8000/docs`

2. **Búsqueda Semántica con IA (`pgvector`)**:
   ```bash
   curl -X POST http://192.168.1.85:8000/api/products/search/semantic \
     -H "Content-Type: application/json" \
     -d '{"query": "armazón dorado vintage para sol", "limit": 5}'
   ```

3. **Asesor Inteligente con Ollama (`/api/advisor/chat`)**:
   ```bash
   curl -X POST http://192.168.1.85:8000/api/advisor/chat \
     -H "Content-Type: application/json" \
     -d '{"message": "Recomiéndame lentes de sol polarizados para manejar por menos de 70.000 CLP"}'
   ```