# Coach Ejecutivo - Sistema de Análisis de Ventas con IA

Sistema automatizado de análisis de ventas que utiliza AWS Bedrock (IA) para generar recomendaciones personalizadas para ejecutivos de ventas, con notificaciones por email vía SendGrid.

## 📋 Descripción

Este sistema analiza datos de ventas, clientes, reclamos y retiros desde MongoDB, genera análisis inteligentes usando AWS Bedrock, y envía reportes personalizados por email a cada ejecutivo con:

- **Métricas de ventas**: Avance vs meta, ritmo diario, proyecciones
- **Análisis de cartera**: Clientes activos, en riesgo, con reclamos
- **Sugerencias específicas**: Acciones concretas con clientes prioritarios (máximo 3 por ejecutivo)
- **Alertas operacionales**: Reclamos activos, problemas de retiros, clientes en riesgo crítico

## 🏗️ Arquitectura

```
┌─────────────┐      ┌──────────────┐      ┌─────────────┐
│   MongoDB   │─────▶│  FastAPI     │─────▶│ AWS Bedrock │
│  (Datos)    │      │  (Orquesta)  │      │    (IA)     │
└─────────────┘      └──────────────┘      └─────────────┘
                            │
                            ▼
                     ┌──────────────┐
                     │   SendGrid   │
                     │   (Email)    │
                     └──────────────┘
```

### Componentes Principales

1. **FastAPI**: API REST que orquesta el flujo completo
2. **MongoDB**: Base de datos con información de ventas, clientes, reclamos, retiros
3. **AWS Bedrock**: Servicio de IA para análisis y generación de recomendaciones
4. **SendGrid**: Servicio de envío de emails con reportes HTML

## 🚀 Instalación

### Requisitos Previos

- Python 3.11+
- MongoDB (acceso a base de datos)
- Cuenta AWS con acceso a Bedrock
- Cuenta SendGrid con API Key
- Docker (opcional)

### Instalación Local

```bash
# Clonar repositorio
git clone <repository-url>
cd <repository-name>

# Crear entorno virtual
python -m venv venv
source venv/bin/activate  # En Windows: venv\Scripts\activate

# Instalar dependencias
pip install -r requirements.txt

# Configurar variables de entorno
cp .env.example .env
# Editar .env con tus credenciales
```

### Instalación con Docker

```bash
# Construir y levantar contenedor
docker-compose up -d

# Ver logs
docker-compose logs -f
```

## ⚙️ Configuración

### Variables de Entorno (.env)

```env
# MongoDB
MONGODB_URI=mongodb://usuario:password@host:27017/
MONGODB_DATABASE=nombre_base_datos

# AWS Bedrock
AWS_REGION=us-east-1
AWS_BEDROCK_MODEL_ID=arn:aws:bedrock:us-east-1::inference-profile/amazon-nova-lite-v1
AWS_ACCESS_KEY_ID=tu_access_key
AWS_SECRET_ACCESS_KEY=tu_secret_key

# SendGrid
SENDGRID_API_KEY=SG.xxxxxxxxxxxxxxxxxxxxx
SENDGRID_FROM_EMAIL=noreply@tudominio.com
SENDGRID_TEST_EMAIL=test@tudominio.com

# API
API_HOST=0.0.0.0
API_PORT=8000
```

### Colecciones MongoDB Requeridas

El sistema consulta las siguientes colecciones:

1. **clientes_por_ejecutivo**: Asignación de clientes a ejecutivos
2. **sales_last_month**: Ventas del mes actual
3. **clients_data**: Métricas de riesgo y comportamiento de clientes
4. **claims_last_month**: Reclamos del mes actual
5. **pickup_last_month**: Retiros/entregas del mes actual
6. **clients_recomendations**: Recomendaciones previas de Bedrock
7. **sales_goal**: Metas de ventas por ejecutivo

## 📡 Uso de la API

### Iniciar Servidor

```bash
# Desarrollo
uvicorn app.main:app --reload

# Producción
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### Endpoints Disponibles

| Método | Endpoint | Descripción | Tag |
|--------|----------|-------------|-----|
| GET | `/api/health` | Health check general | health |
| GET | `/api/health/mongodb` | Verificar conexión MongoDB | health |
| GET | `/api/health/bedrock` | Verificar conexión AWS Bedrock | health |
| GET | `/api/health/sendgrid` | Verificar configuración SendGrid | health |
| POST | `/api/analyze` | Ejecutar análisis y enviar emails | analysis |

### Endpoint Principal: Análisis y Notificaciones

```bash
POST /api/analyze
Content-Type: application/json

{
  "current_date": "2026-02-12",
  "is_testing": false
}
```

**Parámetros:**
- `current_date` (string, requerido): Fecha de análisis en formato YYYY-MM-DD
- `is_testing` (boolean, opcional): Si es `true`, todos los emails se envían a `SENDGRID_TEST_EMAIL`

**Respuesta:**

```json
{
  "data": {
    "fecha_analisis": "2026-02-12",
    "ejecutivos": [
      {
        "id_ejecutivo": 123,
        "nombre": "Juan Pérez",
        "correo": "juan.perez@empresa.com",
        "estado": "Necesita acelerar",
        "metricas": {
          "ventas_acumuladas": 1631551,
          "meta_mes": 5000000,
          "avance_porcentual": 0.326,
          "faltante": 3368449,
          "dias_restantes": 16,
          "venta_diaria_actual": 135963,
          "venta_diaria_requerida": 210528
        },
        "cartera": {
          "total_clientes": 3,
          "clientes_activos": 2,
          "clientes_riesgo_alto": 1,
          "clientes_riesgo_medio": 2,
          "total_reclamos_cartera": 0,
          "tasa_cumplimiento_retiros": 0.964
        },
        "diagnostico": "El ejecutivo tiene clientes en riesgo crítico...",
        "sugerencias_clientes": [
          {
            "prioridad": "CRÍTICA",
            "cliente_rut": "13964232",
            "cliente_nombre": "MAGALY",
            "accion": "Contactar urgentemente",
            "razon": "Cliente en riesgo crítico (red) con drop_flag activo...",
            "origen": "analisis_riesgo"
          }
        ],
        "alertas": [
          "1 cliente en riesgo crítico (red)",
          "2 clientes en riesgo medio (yellow)"
        ]
      }
    ]
  },
  "metadata": {
    "data_count": 1,
    "model": "amazon-nova-lite-v1",
    "tokens": {
      "prompt": 1234,
      "completion": 567,
      "total": 1801
    },
    "cost": {
      "input": 0.000987,
      "output": 0.001814,
      "total": 0.002801
    }
  },
  "email_notifications": {
    "total_sent": 1,
    "total_failed": 0,
    "notifications": [
      {
        "ejecutivo": "Juan Pérez",
        "recipient": "juan.perez@empresa.com",
        "subject": "Reporte diario Coach Ejecutivo (Juan Pérez)",
        "status": "success",
        "status_code": 202
      }
    ]
  }
}
```

### Health Check Endpoints

#### General Health Check
```bash
GET /api/health
```

Respuesta:
```json
{
  "status": "healthy",
  "service": "AWS Bedrock API Service"
}
```

#### MongoDB Connection Check
```bash
GET /api/health/mongodb
```

Respuesta exitosa:
```json
{
  "status": "connected",
  "message": "MongoDB connection is healthy",
  "database": "nombre_base_datos"
}
```

Respuesta con error (503):
```json
{
  "detail": "MongoDB connection failed: [error message]"
}
```

#### AWS Bedrock Connection Check
```bash
GET /api/health/bedrock
```

Respuesta exitosa:
```json
{
  "status": "connected",
  "message": "AWS Bedrock connection is healthy",
  "model": "amazon-nova-lite-v1",
  "region": "us-east-1",
  "test_response": "OK"
}
```

Respuesta con error (503):
```json
{
  "detail": "AWS Bedrock connection failed: [error message]"
}
```

#### SendGrid Configuration Check
```bash
GET /api/health/sendgrid
```

Respuesta exitosa:
```json
{
  "status": "configured",
  "message": "SendGrid is properly configured",
  "from_email": "noreply@tudominio.com",
  "test_email": "test@tudominio.com",
  "note": "Use /api/analyze with is_testing=true to test actual email sending"
}
```

Respuesta con error (503):
```json
{
  "detail": "SendGrid API key not configured"
}
```

### Documentación Interactiva

Una vez iniciado el servidor, accede a:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## 📧 Formato de Emails

Los emails enviados incluyen:

### Header
- Título del reporte
- Nombre del ejecutivo
- Fecha del análisis
- Badge de estado (🟢 Excelente / 🔵 Buen ritmo / 🟡 Ritmo justo / 🔴 Necesita acelerar)

### Métricas de Ventas
- Ventas acumuladas vs Meta
- Barra de progreso visual
- Días restantes
- Venta diaria actual vs requerida

### Análisis de Cartera
- Total de clientes y clientes activos
- Indicadores de riesgo (ALTO/MEDIO)
- Total de reclamos
- Tasa de cumplimiento de retiros

### Sugerencias Prioritarias
Máximo 3 sugerencias por ejecutivo, cada una con:
- Badge de prioridad (🔴 CRÍTICA / 🟠 ALTA / 🟡 MEDIA)
- Nombre y RUT del cliente
- Acción específica a realizar
- Razón detallada con datos

### Alertas
- Clientes en riesgo crítico
- Reclamos activos sin resolver
- Problemas operacionales

## 🧪 Testing

### Ejecutar Tests

```bash
# Todos los tests
pytest

# Tests específicos
pytest tests/test_api_routes.py
pytest tests/test_analysis_service.py
pytest tests/test_health_endpoints.py

# Con cobertura
pytest --cov=app tests/

# Tests de health checks solamente
pytest tests/test_health_endpoints.py -v
```

### Tests Disponibles

- `test_main.py` - Tests del punto de entrada de la aplicación
- `test_api_routes.py` - Tests de endpoints de análisis
- `test_health_endpoints.py` - Tests de endpoints de health check (MongoDB, Bedrock, SendGrid)
- `test_analysis_service.py` - Tests del servicio de análisis
- `test_mongodb_client.py` - Tests del cliente MongoDB
- `test_aws_bedrock_client.py` - Tests del cliente AWS Bedrock
- `test_settings.py` - Tests de configuración

### Modo Testing de Emails

Para probar sin enviar emails a destinatarios reales:

```bash
POST /api/analyze
{
  "current_date": "2026-02-12",
  "is_testing": true
}
```

Todos los emails se redirigirán a `SENDGRID_TEST_EMAIL` con un banner indicando el destinatario original.

## 📊 Lógica de Análisis

### Priorización de Clientes

El sistema prioriza clientes en este orden:

1. **CRÍTICA**: 
   - `risk_level = "red"`
   - `drop_flag = 1` AND `needs_attention = true`
   - Cliente inactivo con historial de ventas alto

2. **ALTA**:
   - `risk_level = "yellow"` AND `drop_flag = 1`
   - 2+ meses consecutivos bajo percentil 25
   - Caída significativa en ventas (>30%)

3. **MEDIA**:
   - Reclamos activos
   - Tasa de retiros < 80%
   - Problemas operacionales recurrentes

### Clasificación de Estado del Ejecutivo

- **Excelente ritmo**: Venta diaria actual ≥ 120% de la requerida
- **Buen ritmo**: Venta diaria actual ≥ 90% de la requerida
- **Ritmo justo**: Venta diaria actual ≥ 70% de la requerida
- **Necesita acelerar**: Venta diaria actual < 70% de la requerida

### Generación de Sugerencias

Cada sugerencia incluye:
- Cliente específico (nombre + RUT)
- Acción concreta (Llamar, Reunión, Visitar, Resolver)
- Razón con datos (risk_level, ventas, reclamos, retiros)
- Origen (recomendación previa, análisis de riesgo, análisis operacional, oportunidad)

## 🔧 Estructura del Proyecto

```
.
├── app/
│   ├── api/
│   │   ├── routes.py          # Endpoints de la API
│   │   └── schemas.py         # Modelos Pydantic
│   ├── clients/
│   │   ├── interfaces.py      # Interfaces abstractas
│   │   ├── mongodb_client.py  # Cliente MongoDB
│   │   ├── aws_bedrock_client.py  # Cliente AWS Bedrock
│   │   └── email_client.py    # Cliente SendGrid
│   ├── config/
│   │   ├── settings.py        # Configuración
│   │   └── queries.py         # Queries MongoDB y prompts
│   ├── services/
│   │   ├── analysis_service.py  # Orquestación del análisis
│   │   └── email_notification_service.py  # Envío de emails
│   └── main.py                # Punto de entrada
├── tests/                     # Tests unitarios
├── .env                       # Variables de entorno
├── requirements.txt           # Dependencias Python
├── Dockerfile                 # Imagen Docker
├── docker-compose.yml         # Orquestación Docker
└── README.md                  # Este archivo
```

## 🐛 Troubleshooting

### Verificar Conexiones

Usa los endpoints de health check para diagnosticar problemas:

```bash
# Verificar todas las conexiones manualmente
curl http://localhost:8000/api/health
curl http://localhost:8000/api/health/mongodb
curl http://localhost:8000/api/health/bedrock
curl http://localhost:8000/api/health/sendgrid

# O usa el script de prueba (Linux/Mac)
chmod +x test_health_checks.sh
./test_health_checks.sh

# O usa el script de prueba (Windows PowerShell)
.\test_health_checks.ps1
```

O visita la documentación interactiva en `http://localhost:8000/docs` y prueba los endpoints desde ahí.

### Error: "Service not initialized"
- Verifica que todas las variables de entorno estén configuradas
- Ejecuta `Settings().validate()` para ver qué falta
- Usa `GET /api/health/mongodb` para verificar conexión a MongoDB
- Usa `GET /api/health/bedrock` para verificar conexión a AWS Bedrock
- Usa `GET /api/health/sendgrid` para verificar configuración de SendGrid

### Error de conexión a MongoDB
- Verifica que `MONGODB_URI` sea correcta
- Comprueba conectividad de red
- Revisa permisos del usuario MongoDB
- **Usa `GET /api/health/mongodb` para diagnosticar**

### Error de AWS Bedrock
- Verifica credenciales AWS (`AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`)
- Comprueba que el modelo esté disponible en tu región
- Revisa permisos IAM para Bedrock
- **Usa `GET /api/health/bedrock` para diagnosticar**

### Emails no se envían
- Verifica `SENDGRID_API_KEY` válida
- Comprueba que `SENDGRID_FROM_EMAIL` esté verificado en SendGrid
- Revisa logs para errores específicos
- **Usa `GET /api/health/sendgrid` para verificar configuración**
- Prueba con `POST /api/analyze` usando `is_testing: true`

### Análisis vacío o incorrecto
- Verifica que las colecciones MongoDB tengan datos
- Comprueba que `current_date` esté en formato correcto (YYYY-MM-DD)
- Revisa que los datos del mes/año solicitado existan

## 🎯 Gestión de Prompts desde MongoDB

El sistema permite gestionar el prompt del agente de AWS Bedrock desde MongoDB sin necesidad de redesplegar la aplicación. Esto facilita:

- Modificar el comportamiento del agente sin downtime
- Mantener un historial de versiones del prompt
- Probar diferentes estrategias de análisis fácilmente

### Subir el Prompt Inicial

```bash
python upload_prompt_to_mongo.py
```

Este script crea el documento del prompt en la colección `prompts` de MongoDB.

### Ver el Prompt Actual

```bash
python update_prompt.py --view
```

### Actualizar el Prompt

```bash
# Desde un archivo
python update_prompt.py --file mi_nuevo_prompt.txt

# Con versión específica
python update_prompt.py --file mi_nuevo_prompt.txt --version 2.1
```

### Ver Historial de Versiones

```bash
python update_prompt.py --history
```

### Desactivar/Activar Prompt

```bash
# Desactivar (usa prompt por defecto como fallback)
python update_prompt.py --deactivate

# Activar
python update_prompt.py --activate
```

### Variables Dinámicas en el Prompt

El template del prompt usa estas variables que se reemplazan automáticamente:

- `{current_date}`: Fecha de análisis (YYYY-MM-DD)
- `{year}`: Año objetivo
- `{month}`: Mes objetivo
- `{day}`: Día actual del mes
- `{dias_mes}`: Total de días del mes
- `{dias_restantes}`: Días restantes
- `{avance_esperado}`: Avance esperado (decimal)
- `{avance_esperado_pct}`: Avance esperado (porcentaje)

Para más detalles, consulta [PROMPT_MANAGEMENT.md](PROMPT_MANAGEMENT.md).

