# Carpeta API

Esta carpeta contiene la capa de presentación de la aplicación, manejando las rutas HTTP y la validación de datos de entrada/salida.

## Archivos

### `routes.py`
**Función:** Define los endpoints de la API REST usando FastAPI.

**Responsabilidades:**
- Expone el endpoint principal `/analyze` para ejecutar análisis de datos
- Gestiona endpoints de health check para verificar conectividad con servicios externos (MongoDB, AWS Bedrock, SendGrid, Embeddings)
- Inyecta dependencias de servicios (AnalysisService, EmailNotificationService)
- Maneja errores y retorna respuestas HTTP apropiadas

**Endpoints principales:**
- `POST /api/analyze` - Ejecuta análisis de datos y envía notificaciones
  - Parámetros: `current_date` (string), `is_testing` (boolean)
  - Modo testing: Solo envía correos a ejecutivos con campo `test_correo`
  - Enriquecimiento automático: Agrega `test_correo` desde datos originales
- `GET /api/health` - Verifica estado general de la API
- `GET /api/health/mongodb` - Verifica conexión con MongoDB
- `GET /api/health/bedrock` - Verifica conexión con AWS Bedrock
- `GET /api/health/sendgrid` - Verifica configuración de SendGrid
- `GET /api/health/sendgrid/test` - Prueba envío real de email
- `GET /api/health/embedding` - Verifica servicio de embeddings

### `schemas.py`
**Función:** Define los modelos de datos (schemas) usando Pydantic para validación de requests y responses.

**Responsabilidades:**
- Valida estructura de datos de entrada en requests HTTP
- Define el contrato de la API (qué datos se esperan y qué se retorna)
- Proporciona validación automática de tipos y valores

**Schemas principales:**
- `AnalysisRequest` - Estructura de datos para solicitudes de análisis
  - `current_date` (string, required): Fecha de análisis en formato YYYY-MM-DD
  - `is_testing` (boolean, optional): Modo testing para correos (default: false)
- `EmailNotification` - Resultado de envío de email individual
  - Incluye: ejecutivo, recipient, test_correo, status, error
- `Config` - Configuración anidada dentro de AnalysisRequest

### `__init__.py`
**Función:** Marca el directorio como un paquete Python (archivo vacío o con imports).

## Diagrama de Flujo

```
┌─────────────────────────────────────────────────────────────┐
│                         Cliente HTTP                         │
└────────────────────────────┬────────────────────────────────┘
                             │
                             ▼
                    ┌────────────────┐
                    │  routes.py     │
                    │  (FastAPI)     │
                    └────────┬───────┘
                             │
                ┌────────────┴────────────┐
                │                         │
                ▼                         ▼
        ┌───────────────┐         ┌──────────────┐
        │  schemas.py   │         │   Services   │
        │  (Validación) │         │  (Lógica de  │
        └───────────────┘         │   Negocio)   │
                                  └──────────────┘
                                          │
                                          ▼
                                  ┌──────────────┐
                                  │   Clients    │
                                  │ (MongoDB, AI)│
                                  └──────────────┘

Flujo de una petición POST /analyze:
1. Cliente envía JSON → routes.py
2. schemas.py valida el request (AnalysisRequest)
3. routes.py llama a AnalysisService
4. AnalysisService ejecuta la lógica de negocio
5. routes.py retorna respuesta JSON al cliente
```

## Relaciones con otros módulos

- **Depende de:** `app.services` (AnalysisService, EmailNotificationService), `app.config` (Settings)
- **Usado por:** Cliente HTTP externo (aplicaciones frontend, scripts, etc.)
