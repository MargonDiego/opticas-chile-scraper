# 🚀 Despliegue Seguro en Homelab con Coolify (Ubuntu - 192.168.1.85)

Esta guía detalla cómo desplegar el servicio **Chilean Optics Scraper, AI & Security API** en tu servidor con Coolify.

---

## 🔒 Configuración de Ciberseguridad

Para proteger tu servidor de accesos no autorizados y abusos de CPU/scraping:

1. **Definir tu API Key en Coolify**:
   Agregá en la sección de **Environment Variables** de Coolify:
   ```env
   ENVIRONMENT=production
   PORT=8000
   API_KEY=tu_clave_secreta_super_segura_aqui
   CORS_ORIGINS=*
   ENABLE_SECURITY_HEADERS=true
   POSTGRES_USER=opticas_user
   POSTGRES_PASSWORD=opticas_pass_segura_123
   POSTGRES_DB=opticas_db
   OLLAMA_BASE_URL=http://host.docker.internal:11434
   OLLAMA_EMBED_MODEL=nomic-embed-text
   OLLAMA_LLM_MODEL=qwen2.5:1.5b
   ```

2. **Cómo autenticarse desde Swagger UI**:
   - Abrí `http://192.168.1.85:8008/docs`.
   - Hacé clic en el botón verde **Authorize** arriba a la derecha.
   - Ingresá tu `API_KEY` en el campo `X-API-Key`.

3. **Cómo llamar a la API por Curl / Scripts**:
   ```bash
   curl -H "X-API-Key: tu_clave_secreta_super_segura_aqui" \
     http://192.168.1.85:8008/api/products
   ```
   *(Cualquier petición sin la cabecera `X-API-Key` será rechazada con `401 Unauthorized`)*.