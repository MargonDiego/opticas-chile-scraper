# 🚀 Despliegue en Homelab con Coolify (Ubuntu - 192.168.1.85)

Esta guía detalla cómo desplegar el stack completo: **Astro + shadcn/ui Frontend (Puerto 3001)**, **FastAPI Scraper (Puerto 8008)**, **PostgreSQL + pgvector** y **Ollama AI**.

---

## 🏗️ Servicios en Docker Compose

1. **`opticas-frontend`**: Interfaz web en **Astro 5 + React + Tailwind + shadcn/ui** servida en el puerto **`3001`**.
2. **`opticas-api`**: Backend FastAPI servido en el puerto **`8008`** (con Swagger en `/docs`).
3. **`postgres`**: Base de datos PostgreSQL con extensión `pgvector` en red aislada.
4. **`ollama`**: Servidor LLM (`qwen2.5:1.5b`) y Embeddings (`nomic-embed-text`) corriendo en tu homelab.

---

## 🛠️ Despliegue en Coolify

1. **En tu panel de Coolify**:
   - Ingresá a tu recurso Docker Compose.
   - Verificá las **Environment Variables**:
     ```env
     ENVIRONMENT=production
     API_KEY=<genera-una-key-con-secrets.token_urlsafe(48)>
     ADMIN_API_KEY=<otra-key-distinta-nunca-expuesta-al-frontend>
     PUBLIC_API_URL=http://192.168.1.85:8008
     PUBLIC_API_KEY=<mismo-valor-que-API_KEY>
     APP_PORT=8008
     FRONTEND_PORT=3001
     ```

2. **Hacé clic en Redeploy**:
   - Coolify compilará el backend con `uv` y el frontend con `Astro` en segundos.

---

## 🌐 URLs de Acceso

- 🖥️ **Frontend Web (Astro + shadcn/ui)**: 👉 `http://192.168.1.85:3001`
- 📑 **Swagger API Backend**: 👉 `http://192.168.1.85:8008/docs`