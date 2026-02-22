# AWS Bedrock API Service - Coach Ejecutivo de Ventas

## 📋 Tabla de Contenidos
- [Problemática y Contexto](#problemática-y-contexto)
- [Objetivos](#objetivos)
- [Alcance del Proyecto](#alcance-del-proyecto)
- [Arquitectura de la Solución](#arquitectura-de-la-solución)
- [Historial de Versiones](#historial-de-versiones)
- [Instalación y Configuración](#instalación-y-configuración)
- [Uso de la API](#uso-de-la-api)
- [Testing](#testing)
- [Extensibilidad](#extensibilidad)

## 🎯 Problemática y Contexto

Los ejecutivos de ventas de gestionan carteras de clientes con diferentes niveles de riesgo, 
comportamientos de compra y problemas operacionales. La toma de decisiones sobre qué clientes contactar 
y qué acciones tomar requiere analizar múltiples fuentes de datos:

- Ventas históricas y metas mensuales
- Métricas de riesgo de abandono (drop_flag, risk_level)
- Reclamos activos y su estado
- Problemas de retiros/pickups
- Recomendaciones previas

Sin un sistema automatizado, los ejecutivos pueden:
- Perder oportunidades con clientes de alto valor
- No detectar clientes en riesgo crítico a tiempo
- Recibir recomendaciones repetitivas sin valor agregado
- Carecer de priorización clara de acciones

## 🎯 Objetivos

1. **Automatizar el análisis de cartera**: Procesar datos de múltiples fuentes (ventas, reclamos, retiros, métricas de riesgo)
2. **Generar recomendaciones accionables**: Sugerencias específicas con cliente, acción y razón basada en datos
3. **Priorizar acciones**: Clasificar clientes por nivel de riesgo y urgencia
4. **Evitar repetición**: Sistema de memoria con embeddings para no repetir recomendaciones similares
5. **Notificación automática**: Envío de reportes diarios por email a cada ejecutivo


## 📦 Alcance del Proyecto

### Funcionalidades Incluidas

✅ **Análisis de Datos**
- Integración con MongoDB para consultas complejas (aggregation pipelines)
- Análisis de ventas, metas y avance mensual
- Evaluación de métricas de riesgo de clientes
- Análisis de reclamos y problemas operacionales

✅ **Inteligencia Artificial**
- Integración con AWS Bedrock (Amazon Nova Lite)
- Generación de recomendaciones personalizadas por ejecutivo
- Análisis de contexto y priorización automática

✅ **Sistema de Memoria con Embeddings**
- Generación de embeddings semánticos (text-embedding-3-large)
- Detección de similitud entre recomendaciones
- Cooldown period configurable (7-14 días)
- Reset inteligente cuando no hay clientes disponibles

✅ **Notificaciones por Email**
- Integración con SendGrid
- Emails HTML personalizados por ejecutivo
- Modo testing para desarrollo
- Métricas visuales y alertas prioritarias

✅ **API REST**
- Endpoint principal `/api/analyze`
- Health checks para todos los servicios
- Documentación automática (Swagger/OpenAPI)

### Fuera del Alcance

❌ **Ejecución Periódica**: La API no incluye scheduling. Se espera que sea invocada por Azure Functions u otro orquestador externo.

❌ **Interfaz de Usuario**: No incluye frontend. Es una API REST pura.

❌ **Gestión de Usuarios**: No incluye autenticación ni autorización.


## 🏗️ Arquitectura de la Solución

### Diagrama General del Flujo

```
┌─────────────────┐
│  Azure Function │  (Trigger diario)
│   o Scheduler   │
└────────┬────────┘
         │
         │ POST /api/analyze
         │ {current_date, is_testing}
         ▼
┌─────────────────────────────────────────────────────────────┐
│                     FastAPI Application                      │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │              Analysis Service                         │  │
│  │  - Orchestrates workflow                             │  │
│  │  - Applies business rules                            │  │
│  │  - Manages memory system                             │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                              │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐  │
│  │ MongoDB  │  │   AWS    │  │Embedding │  │ SendGrid │  │
│  │  Client  │  │ Bedrock  │  │  Client  │  │  Client  │  │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘  │
└─────────────────────────────────────────────────────────────┘
         │              │              │              │
         ▼              ▼              ▼              ▼
    ┌────────┐    ┌────────┐    ┌────────┐    ┌────────┐
    │MongoDB │    │  AWS   │    │Embedding│   │SendGrid│
    │  Atlas │    │Bedrock │    │ Service │   │  API   │
    └────────┘    └────────┘    └────────┘    └────────┘
```

### Flujo Detallado de Ejecución

1. **Recepción de Request**
   - POST `/api/analyze` con `current_date` e `is_testing`
   - Validación de parámetros (Pydantic schemas)

2. **Generación de Queries Dinámicas**
   - `get_queries(current_date)` genera pipeline de agregación
   - `get_analysis_prompt(current_date)` genera prompt con variables

3. **Verificación de Memoria (Pre-filtrado)**
   - Para cada ejecutivo, cuenta clientes disponibles
   - Si 0 clientes → Reset completo (borra todos los embeddings)
   - Si 1-2 clientes → Reset parcial (borra los más antiguos)
   - Si 3+ clientes → Continúa normal

4. **Consulta a MongoDB**
   - Ejecuta aggregation pipeline complejo
   - Enriquece datos con: sales, client_metrics, claims, pickups, memory_recs
   - Retorna estructura completa por ejecutivo

5. **Pre-filtrado de Clientes**
   - Filtra clientes con `memory_recs` recientes (últimos N días)
   - Solo envía al AI clientes disponibles para recomendar

6. **Análisis con AWS Bedrock**
   - Optimiza datos (limita a top 30 clientes por ejecutivo)
   - Envía prompt + datos al modelo
   - Recibe JSON con recomendaciones estructuradas

7. **Validación de Recomendaciones**
   - Detecta clientes ficticios (nombres/RUTs de ejemplo)
   - Valida que clientes pertenezcan a la cartera del ejecutivo
   - Verifica que sean exactamente 3 recomendaciones

8. **Filtrado por Similitud**
   - Genera embeddings para cada recomendación
   - Compara con historial usando cosine similarity
   - Filtra si similitud > threshold Y dentro de cooldown

9. **Almacenamiento en Memoria**
   - Guarda recomendaciones en `memory_embeddings`
   - Incluye: executive_id, client_id, recommendation, embedding, timestamp

10. **Envío de Emails**
    - Genera HTML personalizado por ejecutivo
    - Incluye métricas, diagnóstico, sugerencias, alertas
    - Envía vía SendGrid (modo testing o producción)

11. **Respuesta**
    - Retorna JSON con análisis, métricas, notificaciones enviadas


### Diagrama del Sistema de MongoDB

```
┌─────────────────────────────────────────────────────────────┐
│                    MongoDB Collections                       │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  clientes_por_ejecutivo                                     │
│  ├─ id_ejecutivo, nombre_ejecutivo, correo                  │
│  └─ rut_clientes[]                                          │
│                                                              │
│  sales_last_month                                           │
│  ├─ rut_cliente, agno, mes                                  │
│  └─ ventas[] → MONTO_VENTAS_NETAS                          │
│                                                              │
│  clients_data                                               │
│  ├─ rut_key, nombre                                         │
│  ├─ drop_flag, risk_level, risk_score                       │
│  ├─ monto_neto_mes_mean, avg_last3, avg_prev3              │
│  └─ p25, p50, consec_below_p25                             │
│                                                              │
│  claims_last_month                                          │
│  ├─ rut_cliente, agno, mes                                  │
│  └─ reclamos[] → numero_caso, motivo, estado, valor        │
│                                                              │
│  pickup_last_month                                          │
│  ├─ rut_cliente, agno, mes                                  │
│  └─ cant_retiros_programados, cant_retiros_efectuados      │
│                                                              │
│  memory_embeddings (Sistema de Memoria)                     │
│  ├─ executive_id, client_id                                 │
│  ├─ recommendation, embedding[]                             │
│  └─ timestamp, metadata                                     │
│                                                              │
│  prompts (Configuración)                                    │
│  ├─ prompt_id, template                                     │
│  └─ version, variables[], active                            │
└─────────────────────────────────────────────────────────────┘

Aggregation Pipeline:
1. $unwind rut_clientes
2. $lookup sales_last_month (ventas por cliente)
3. $lookup clients_data (métricas de riesgo)
4. $lookup claims_last_month (reclamos)
5. $lookup pickup_last_month (retiros)
6. $lookup memory_embeddings (últimas 3 recomendaciones)
7. $group por ejecutivo con cartera_detallada[]
8. $lookup sales_goal (metas)
9. $addFields (cálculos de avance, faltante)
10. $sort por avance_pct
```

### Diagrama del Sistema de Embeddings y Memoria

```
┌─────────────────────────────────────────────────────────────┐
│              Embedding & Memory System                       │
└─────────────────────────────────────────────────────────────┘

1. Nueva Recomendación Generada
   │
   ▼
┌──────────────────────────────┐
│  "Llamar al cliente para     │
│   revisar riesgo crítico"    │
└──────────────────────────────┘
   │
   │ generate_embedding()
   ▼
┌──────────────────────────────┐
│  [0.123, -0.456, 0.789, ...] │  (vector de 3072 dimensiones)
└──────────────────────────────┘
   │
   │ get_historical_recommendations()
   ▼
┌──────────────────────────────────────────────────────────────┐
│  Recomendaciones Históricas (últimas 5)                      │
│  ┌────────────────────────────────────────────────────────┐ │
│  │ Rec 1: "Contactar cliente riesgo" [emb1] 2026-02-10   │ │
│  │ Rec 2: "Reunión oportunidades"    [emb2] 2026-02-08   │ │
│  │ Rec 3: "Revisar reclamos activos" [emb3] 2026-02-05   │ │
│  └────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────┘
   │
   │ cosine_similarity(new_emb, historical_emb)
   ▼
┌──────────────────────────────────────────────────────────────┐
│  Similarity Scores                                            │
│  ├─ Rec 1: 0.92 (MUY SIMILAR) ⚠️                            │
│  ├─ Rec 2: 0.45 (DIFERENTE) ✅                              │
│  └─ Rec 3: 0.38 (DIFERENTE) ✅                              │
└──────────────────────────────────────────────────────────────┘
   │
   │ check_recommendation_similarity()
   ▼
┌──────────────────────────────────────────────────────────────┐
│  Decisión de Filtrado                                         │
│                                                               │
│  IF similarity > 0.85 AND days_since < cooldown_days:        │
│     → FILTRAR (no almacenar, no enviar)                      │
│  ELSE IF similarity > 0.85 AND days_since >= cooldown_days:  │
│     → PERMITIR (marcar como "repeated_no_change")            │
│  ELSE:                                                        │
│     → PERMITIR (marcar como "new")                           │
└──────────────────────────────────────────────────────────────┘
   │
   │ store_recommendation()
   ▼
┌──────────────────────────────────────────────────────────────┐
│  MongoDB: memory_embeddings                                   │
│  {                                                            │
│    executive_id: "123",                                       │
│    client_id: "12345678",                                     │
│    recommendation: "Llamar al cliente...",                    │
│    embedding: [0.123, -0.456, ...],                          │
│    timestamp: "2026-02-18T10:30:00",                         │
│    metadata: {status: "new", prioridad: "CRÍTICA"}           │
│  }                                                            │
└──────────────────────────────────────────────────────────────┘

Reglas de Cooldown:
- cooldown_days = 7 (configurable)
- Si recomendación similar fue hecha hace < 7 días → FILTRAR
- Si recomendación similar fue hecha hace >= 7 días → PERMITIR (sin cambios)
- Si no hay similitud → PERMITIR (nueva)
```


### Diagrama de Casos Bordes y Reset de Memoria

```
┌─────────────────────────────────────────────────────────────┐
│           Memory Reset Service - Border Cases                │
└─────────────────────────────────────────────────────────────┘

Ejecutivo tiene 9 clientes en cartera
Pre-filtrado: Clientes con memory_recs recientes son excluidos

┌──────────────────────────────────────────────────────────────┐
│  CASO 1: 0 Clientes Disponibles                              │
│  ────────────────────────────────────────────────────────    │
│  Todos los clientes fueron recomendados recientemente         │
│                                                               │
│  Acción: RESET COMPLETO                                      │
│  ├─ Borrar TODOS los embeddings del ejecutivo                │
│  ├─ Liberar todos los clientes                               │
│  └─ AI puede recomendar cualquier cliente                    │
│                                                               │
│  Resultado: 9 clientes disponibles                           │
└──────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────┐
│  CASO 2: 1-2 Clientes Disponibles                            │
│  ────────────────────────────────────────────────────────    │
│  Solo 1-2 clientes sin recomendaciones recientes             │
│  Necesitamos 3 recomendaciones                               │
│                                                               │
│  Acción: RESET PARCIAL                                       │
│  ├─ Usar los 1-2 clientes disponibles                        │
│  ├─ Borrar embeddings MÁS ANTIGUOS para liberar 1-2 más      │
│  └─ AI recomienda: disponibles + recién liberados            │
│                                                               │
│  Resultado: 3 clientes disponibles (1-2 + 1-2 liberados)     │
└──────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────┐
│  CASO 3: 3+ Clientes Disponibles                             │
│  ────────────────────────────────────────────────────────    │
│  Suficientes clientes sin recomendaciones recientes          │
│                                                               │
│  Acción: NINGUNA                                             │
│  └─ AI recomienda de los clientes disponibles                │
│                                                               │
│  Resultado: Flujo normal                                     │
└──────────────────────────────────────────────────────────────┘

Ejemplo Timeline:
Día 1: Recomienda clientes A, B, C
Día 2: Recomienda clientes D, E, F (A,B,C en cooldown)
Día 3: Recomienda clientes G, H, I (A-F en cooldown)
Día 4: Solo quedan 0 clientes → RESET COMPLETO
Día 5: Recomienda clientes A, B, C (todos liberados)
```

### Diagrama de AWS Bedrock y SendGrid

```
┌─────────────────────────────────────────────────────────────┐
│                    AWS Bedrock Flow                          │
└─────────────────────────────────────────────────────────────┘

1. Optimización de Datos
   ├─ Limitar a top 30 clientes por ejecutivo (prioridad)
   ├─ Truncar campos largos (recomendaciones previas)
   └─ Formato JSON compacto (sin espacios)

2. Construcción del Prompt
   ├─ Contexto: fecha, días del mes, días restantes
   ├─ Instrucciones: priorización, formato JSON
   ├─ Reglas: NO repetir memory_recs, variar acciones
   └─ Ejemplos: sugerencias correctas e incorrectas

3. Invocación del Modelo
   ├─ Modelo: Amazon Nova Lite (o configurado)
   ├─ Parámetros: maxTokens=4096, temperature=0.2
   └─ API: converse() con system prompt

4. Parsing de Respuesta
   ├─ Limpiar markdown (```json)
   ├─ Parsear JSON
   ├─ Extraer metadata (tokens, cost)
   └─ Validar estructura

┌─────────────────────────────────────────────────────────────┐
│                    SendGrid Flow                             │
└─────────────────────────────────────────────────────────────┘

1. Generación de HTML
   ├─ Template con estilos inline (email-safe)
   ├─ Métricas visuales (progress bars, badges)
   ├─ Sugerencias con prioridad (colores)
   └─ Alertas destacadas

2. Modo Testing
   ├─ Redirigir todos los emails a test_email
   ├─ Agregar banner "[TEST]" en subject
   ├─ Mostrar destinatario original en body
   └─ Útil para desarrollo/QA

3. Envío
   ├─ API: SendGrid v3
   ├─ From: configurado en .env
   ├─ To: correo del ejecutivo (o test_email)
   └─ HTML: contenido personalizado

4. Tracking
   ├─ Status code de SendGrid
   ├─ Contador de enviados/fallidos
   └─ Log de errores
```


## 📚 Historial de Versiones

### v1.0.0 - Commit Inicial (Enero 2026)
**Funcionalidades Base**
- Integración con MongoDB para consultas de datos
- Integración con AWS Bedrock para análisis con IA
- Endpoint `/api/analyze` para análisis de ventas
- Generación de recomendaciones básicas por ejecutivo
- Estructura de proyecto modular (clients, services, config)

**Componentes**
- `MongoDBClient`: Consultas simples y aggregation pipelines
- `AWSBedrockClient`: Invocación del modelo con converse API
- `AnalysisService`: Orquestación del flujo de análisis
- Configuración dinámica de queries y prompts

### v2.0.0 - Sistema de Notificaciones (Enero 2026)
**Nuevas Funcionalidades**
- Integración con SendGrid para envío de emails
- Generación de emails HTML personalizados por ejecutivo
- Modo testing para desarrollo (redirección de emails)
- Métricas visuales en emails (progress bars, badges, alertas)

**Componentes Agregados**
- `SendGridEmailClient`: Cliente para envío de emails
- `EmailNotificationService`: Servicio de notificaciones
- Templates HTML con estilos inline
- Health check para SendGrid

**Mejoras**
- Validación de configuración de SendGrid
- Manejo de errores en envío de emails
- Tracking de emails enviados/fallidos

### v3.0.0 - Sistema de Memoria con Embeddings (Febrero 2026)
**Funcionalidades Principales**
- Sistema de memoria semántica con embeddings
- Detección de similitud entre recomendaciones
- Cooldown period configurable (7-14 días)
- Pre-filtrado de clientes por memoria
- Reset inteligente de memoria (casos bordes)

**Componentes Agregados**
- `EmbeddingClient`: Generación de embeddings (text-embedding-3-large)
- `RecommendationMemoryStore`: Almacenamiento y recuperación de recomendaciones
- `SimilarityService`: Cálculo de similitud coseno y filtrado
- `MemoryResetService`: Gestión de casos bordes (0, 1-2, 3+ clientes)

**Colecciones MongoDB**
- `memory_embeddings`: Almacenamiento de recomendaciones con embeddings
- Índices: executive_id + client_id, timestamp

**Reglas de Negocio**
- Pre-filtrado: Excluir clientes con memory_recs recientes (últimos N días)
- Similitud: Threshold 0.85 (configurable)
- Cooldown: 7-14 días (configurable)
- Reset completo: Si 0 clientes disponibles
- Reset parcial: Si 1-2 clientes disponibles (libera los más antiguos)

**Validaciones**
- Detección de clientes ficticios (nombres/RUTs de ejemplo)
- Validación de pertenencia a cartera
- Verificación de exactamente 3 recomendaciones

**Mejoras**
- Optimización de tokens (limitar a top 30 clientes)
- Truncado de campos largos
- Prompt mejorado con instrucciones de variación
- Health check para embedding service
- Logging detallado de memoria y filtrado

**Casos Bordes Manejados**
1. 0 clientes disponibles → Reset completo
2. 1-2 clientes disponibles → Reset parcial
3. Recomendaciones muy similares → Filtrado
4. Cooldown expirado → Permitir con marca "repeated_no_change"
5. Clientes ficticios → Rechazo automático


## 🚀 Instalación y Configuración

### Requisitos Previos
- Python 3.9+
- MongoDB Atlas (o instancia local)
- AWS Account con acceso a Bedrock
- SendGrid API Key
- Embedding Service API Key

### Instalación

1. **Clonar el repositorio**
```bash
git clone <repository-url>
cd aws-bedrock-api-service
```

2. **Crear entorno virtual**
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows
```

3. **Instalar dependencias**
```bash
pip install -r requirements.txt
```

4. **Configurar variables de entorno**

Copiar `.env.example` a `.env` y configurar:

```env
# MongoDB
MONGODB_URI=mongodb+srv://user:password@cluster.mongodb.net/
MONGODB_DATABASE=your_database

# AWS Bedrock
AWS_REGION=us-east-1
AWS_BEDROCK_MODEL_ID=arn:aws:bedrock:us-east-1::inference-profile/amazon-nova-lite-v1
AWS_BEARER_TOKEN_BEDROCK=your_aws_token

# SendGrid
SENDGRID_API_KEY=your_sendgrid_api_key
SENDGRID_FROM_EMAIL=noreply@yourcompany.com
SENDGRID_TEST_EMAIL=test@yourcompany.com

# Embedding Service
EMBEDDING_API_KEY=your_embedding_api_key
EMBEDDING_ENDPOINT=https://api.openai.com/v1/embeddings
EMBEDDING_MODEL_NAME=text-embedding-3-large

# Memory System
MEMORY_ENABLED=true
SIMILARITY_THRESHOLD=0.85
COOLDOWN_DAYS=7
PREFILTER_ENABLED=true
PREFILTER_DAYS_THRESHOLD=7

# API
API_HOST=0.0.0.0
API_PORT=8000
```

### Ejecución Local

**Modo Desarrollo**
```bash
python app/main.py
```

**Modo Producción (con Uvicorn)**
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

**Con Docker**
```bash
docker-compose up --build
```

### Verificación

1. **Health Check General**
```bash
curl http://localhost:8000/api/health
```

2. **Health Checks Específicos**
```bash
curl http://localhost:8000/api/health/mongodb
curl http://localhost:8000/api/health/bedrock
curl http://localhost:8000/api/health/sendgrid
curl http://localhost:8000/api/health/embedding
```

3. **Documentación Swagger**
```
http://localhost:8000/docs
```


## 📖 Uso de la API

### Endpoint Principal: `/api/analyze`

**Request**
```http
POST /api/analyze
Content-Type: application/json

{
  "current_date": "2026-02-18",
  "is_testing": false
}
```

**Parámetros**
- `current_date` (string, required): Fecha de análisis en formato YYYY-MM-DD
- `is_testing` (boolean, optional): Si true, envía emails a test_email. Default: false

**Response (200 OK)**
```json
{
  "data": {
    "fecha_analisis": "2026-02-18",
    "ejecutivos": [
      {
        "id_ejecutivo": 123,
        "nombre": "Juan Pérez",
        "correo": "juan.perez@company.com",
        "estado": "Buen ritmo",
        "metricas": {
          "ventas_acumuladas": 1500000,
          "meta_mes": 2000000,
          "avance_porcentual": 0.75,
          "faltante": 500000,
          "dias_restantes": 10
        },
        "cartera": {
          "total_clientes": 50,
          "clientes_activos": 35,
          "clientes_riesgo_alto": 3,
          "clientes_riesgo_medio": 5
        },
        "diagnostico": "El ejecutivo mantiene buen ritmo...",
        "sugerencias_clientes": [
          {
            "prioridad": "CRÍTICA",
            "cliente_rut": "12345678-9",
            "cliente_nombre": "Empresa ABC",
            "accion": "Llamar urgentemente",
            "razon": "Cliente en riesgo crítico con drop_flag activo...",
            "origen": "analisis_riesgo"
          }
        ],
        "alertas": [
          "3 clientes en riesgo crítico",
          "5 reclamos activos sin resolver"
        ]
      }
    ],
    "resumen_general": {
      "total_ejecutivos": 10,
      "ejecutivos_buen_ritmo": 6,
      "ejecutivos_necesitan_apoyo": 4
    }
  },
  "metadata": {
    "data_count": 10,
    "model": "amazon-nova-lite-v1",
    "tokens": {
      "prompt": 15000,
      "completion": 3000,
      "total": 18000
    },
    "cost": {
      "input": 0.012,
      "output": 0.0096,
      "total": 0.0216
    }
  },
  "email_notifications": {
    "total_sent": 10,
    "total_failed": 0,
    "notifications": [
      {
        "ejecutivo": "Juan Pérez",
        "recipient": "juan.perez@company.com",
        "status": "success",
        "status_code": 202
      }
    ]
  },
  "recommendations_stored": 30,
  "recommendations_filtered": 5,
  "recommendations_invalid": 0
}
```

**Errores Comunes**

- `400 Bad Request`: Parámetros inválidos
- `503 Service Unavailable`: MongoDB o AWS Bedrock no disponible
- `502 Bad Gateway`: Error en análisis de AI
- `500 Internal Server Error`: Error inesperado

### Health Checks

**General**
```bash
GET /api/health
```

**MongoDB**
```bash
GET /api/health/mongodb
```

**AWS Bedrock**
```bash
GET /api/health/bedrock
```

**SendGrid**
```bash
GET /api/health/sendgrid
```

**Embedding Service**
```bash
GET /api/health/embedding
```

### Ejemplo de Uso con cURL

**Análisis en Modo Testing**
```bash
curl -X POST http://localhost:8000/api/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "current_date": "2026-02-18",
    "is_testing": true
  }'
```

**Análisis en Producción**
```bash
curl -X POST http://localhost:8000/api/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "current_date": "2026-02-18",
    "is_testing": false
  }'
```

### Integración con Azure Functions

Esta API está diseñada para ser invocada periódicamente (1 vez al día) por Azure Functions:

```python
# Azure Function (Timer Trigger)
import azure.functions as func
import requests
from datetime import datetime

def main(mytimer: func.TimerRequest) -> None:
    current_date = datetime.utcnow().strftime("%Y-%m-%d")
    
    response = requests.post(
        "https://your-api-url.com/api/analyze",
        json={
            "current_date": current_date,
            "is_testing": False
        }
    )
    
    if response.status_code == 200:
        print(f"Analysis completed: {response.json()}")
    else:
        print(f"Analysis failed: {response.status_code}")
```

**Configuración de Timer Trigger**
```json
{
  "schedule": "0 0 8 * * *",
  "runOnStartup": false,
  "useMonitor": true
}
```
(Ejecuta todos los días a las 8:00 AM)


## 🧪 Testing

### Estructura de Tests

```
tests/
├── connectivity/          # Tests de conexión a servicios externos
│   ├── test_mongodb.py
│   ├── test_aws_bedrock.py
│   ├── test_sendgrid.py
│   ├── test_embedding.py
│   └── test_api_health.py
├── functionality/         # Tests de comportamiento de la API
│   ├── test_query_execution.py
│   ├── test_border_cases.py
│   └── test_embeddings_memory.py
└── conftest.py           # Configuración y fixtures compartidos
```

### Colecciones de Testing

El proyecto utiliza colecciones MongoDB dedicadas para testing:

- `testing_ejecutivos_border_cases`: Ejecutivos de prueba para casos bordes
- `testing_memory_embedding`: Memoria de embeddings para testing

**Importante**: Estas colecciones se limpian automáticamente antes y después de cada test.

### Ejecutar Tests

**Todos los tests**
```bash
pytest
```

**Tests de conectividad**
```bash
pytest tests/connectivity/
```

**Tests de funcionalidad**
```bash
pytest tests/functionality/
```

**Test específico**
```bash
pytest tests/connectivity/test_mongodb.py::test_mongodb_connection
```

**Con cobertura**
```bash
pytest --cov=app --cov-report=html
```

**Con verbose**
```bash
pytest -v
```

### Tests de Casos Bordes

Los tests de casos bordes verifican:

1. **0 Clientes Disponibles**
   - Todos los clientes fueron recomendados recientemente
   - Verifica que se ejecute reset completo
   - Valida que todos los embeddings se borren

2. **1-2 Clientes Disponibles**
   - Solo 1-2 clientes sin recomendaciones recientes
   - Verifica que se ejecute reset parcial
   - Valida que se liberen los clientes más antiguos

3. **Cooldown Period**
   - Clientes dentro del cooldown no se recomiendan
   - Clientes fuera del cooldown sí se recomiendan
   - Verifica el cálculo correcto de días

4. **Recomendaciones Diferentes Cada Día**
   - Ejecuta análisis en días consecutivos
   - Verifica que los clientes recomendados sean diferentes
   - Valida la rotación de la cartera

5. **No Repetición de Recomendaciones**
   - Genera recomendaciones similares
   - Verifica que se filtren por similitud
   - Valida el threshold de similitud (0.85)

### Configuración de Tests

Editar `tests/conftest.py` para configurar:

```python
@pytest.fixture(scope="session")
def test_config():
    return {
        "mongodb_uri": os.getenv("MONGODB_URI"),
        "api_base_url": os.getenv("API_BASE_URL", "http://localhost:8000"),
        # ... otras configuraciones
    }
```

### CI/CD

Para integración continua, agregar a `.github/workflows/tests.yml`:

```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: '3.9'
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install pytest pytest-cov
      - name: Run tests
        env:
          MONGODB_URI: ${{ secrets.MONGODB_URI }}
          AWS_BEARER_TOKEN_BEDROCK: ${{ secrets.AWS_TOKEN }}
          SENDGRID_API_KEY: ${{ secrets.SENDGRID_KEY }}
          EMBEDDING_API_KEY: ${{ secrets.EMBEDDING_KEY }}
        run: pytest --cov=app
```


## 🔧 Extensibilidad

### Principios de Diseño

El proyecto sigue principios de diseño que facilitan la extensibilidad:

1. **Interfaces (Contratos)**: Todos los clientes implementan interfaces (`IDataClient`, `IAIClient`, `IEmbeddingClient`, `IEmailClient`)
2. **Inyección de Dependencias**: Los servicios reciben sus dependencias en el constructor
3. **Separación de Responsabilidades**: Cada módulo tiene una responsabilidad clara
4. **Configuración Externa**: Toda la configuración está en variables de entorno
5. **Patrones de Diseño**: Strategy, Factory, Repository

### Agregar un Nuevo Cliente de Datos

**1. Crear la implementación**

```python
# app/clients/postgresql_client.py
from app.clients.interfaces import IDataClient

class PostgreSQLClient(IDataClient):
    def __init__(self, connection_string: str):
        self._connection_string = connection_string
        self._connection = None
    
    def connect(self) -> None:
        # Implementar conexión
        pass
    
    def query(self, query_params: Dict[str, Any]) -> List[Dict[str, Any]]:
        # Implementar query
        pass
    
    def disconnect(self) -> None:
        # Implementar desconexión
        pass
```

**2. Configurar en settings**

```python
# app/config/settings.py
class Settings:
    def __init__(self):
        # ...
        self.postgresql_uri: str = os.getenv('POSTGRESQL_URI', '')
```

**3. Integrar en main.py**

```python
# app/main.py
from app.clients.postgresql_client import PostgreSQLClient

def setup_dependencies(app: FastAPI, settings: Settings) -> None:
    # Elegir cliente según configuración
    if settings.use_postgresql:
        data_client = PostgreSQLClient(settings.postgresql_uri)
    else:
        data_client = MongoDBClient(settings.mongodb_uri, settings.mongodb_database)
    
    # ... resto del setup
```

### Agregar un Nuevo Modelo de IA

**1. Crear implementación**

```python
# app/clients/openai_client.py
from app.clients.interfaces import IAIClient

class OpenAIClient(IAIClient):
    def __init__(self, api_key: str, model: str):
        self._api_key = api_key
        self._model = model
    
    def connect(self) -> None:
        # Implementar conexión
        pass
    
    def analyze(self, data: List[Dict[str, Any]], prompt: str = None) -> Dict[str, Any]:
        # Implementar análisis con OpenAI
        pass
```

**2. Configurar y usar**

Similar al ejemplo anterior, agregar configuración y seleccionar en `setup_dependencies`.

### Agregar Nuevas Reglas de Negocio

**1. Crear servicio especializado**

```python
# app/services/priority_service.py
class PriorityService:
    """Servicio para calcular prioridad de clientes."""
    
    def calculate_priority(self, client_data: Dict[str, Any]) -> int:
        """Calcula score de prioridad (0-100)."""
        score = 0
        
        # Regla 1: Riesgo crítico
        if client_data.get('risk_level') == 'red':
            score += 50
        
        # Regla 2: Alto valor
        if client_data.get('is_high_value'):
            score += 30
        
        # Regla 3: Reclamos activos
        if client_data.get('total_reclamos', 0) > 0:
            score += 20
        
        return min(score, 100)
```

**2. Integrar en AnalysisService**

```python
# app/services/analysis_service.py
class AnalysisService:
    def __init__(self, ..., priority_service: PriorityService = None):
        # ...
        self._priority_service = priority_service
    
    def execute_analysis(self, ...):
        # Usar priority_service para ordenar clientes
        if self._priority_service:
            data = self._priority_service.prioritize_clients(data)
        # ... resto del análisis
```

### Agregar Nuevos Endpoints

**1. Crear en routes.py**

```python
# app/api/routes.py
@router.get("/api/executives/{executive_id}/recommendations")
async def get_executive_recommendations(
    executive_id: str,
    service: Annotated[AnalysisService, Depends(get_analysis_service)]
):
    """Obtener recomendaciones históricas de un ejecutivo."""
    try:
        recommendations = service._memory_store.get_historical_recommendations(
            executive_id=executive_id,
            client_id=None,  # Todos los clientes
            limit=50
        )
        return {"recommendations": recommendations}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

**2. Agregar schema si es necesario**

```python
# app/api/schemas.py
class RecommendationResponse(BaseModel):
    recommendations: List[Dict[str, Any]]
    total: int
```

### Modificar el Prompt Dinámicamente

El prompt se puede modificar sin cambiar código:

**1. Actualizar en MongoDB**

```javascript
// MongoDB
db.prompts.updateOne(
  { prompt_id: "bedrock_analysis_prompt" },
  {
    $set: {
      template: "Nuevo prompt con {variables}...",
      version: "2.0",
      variables: ["current_date", "year", "month"]
    }
  }
)
```

**2. El sistema lo cargará automáticamente**

```python
# app/config/queries.py
def get_analysis_prompt(current_date: str, mongodb_client: Optional[MongoDBClient] = None) -> str:
    if mongodb_client:
        try:
            prompt_data = mongodb_client.get_prompt_template("bedrock_analysis_prompt")
            return prompt_data["template"].format(current_date=current_date, ...)
        except Exception:
            # Fallback al prompt por defecto
            pass
    return default_prompt
```

### Mejores Prácticas

1. **Documentar todo**: Usar docstrings en todas las clases y métodos
2. **Type hints**: Usar anotaciones de tipo en Python
3. **Logging**: Agregar logs informativos en puntos clave
4. **Manejo de errores**: Usar excepciones específicas y manejarlas apropiadamente
5. **Tests**: Escribir tests para nuevas funcionalidades
6. **Configuración**: Usar variables de entorno, no hardcodear valores
7. **Versionado**: Actualizar el historial de versiones en README

### Recursos Adicionales

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [AWS Bedrock Documentation](https://docs.aws.amazon.com/bedrock/)
- [MongoDB Aggregation](https://docs.mongodb.com/manual/aggregation/)
- [SendGrid API](https://docs.sendgrid.com/api-reference)
- [OpenAI Embeddings](https://platform.openai.com/docs/guides/embeddings)

## 📄 Licencia

Este proyecto está bajo la licencia MIT. Ver archivo `LICENSE` para más detalles.

## 👥 Contribuciones

Las contribuciones son bienvenidas. Por favor:

1. Fork el repositorio
2. Crea una rama para tu feature (`git checkout -b feature/AmazingFeature`)
3. Commit tus cambios (`git commit -m 'Add some AmazingFeature'`)
4. Push a la rama (`git push origin feature/AmazingFeature`)
5. Abre un Pull Request

## 📞 Soporte

Para preguntas o soporte, contactar al equipo de desarrollo.

---

**Nota**: Esta API está diseñada para ser ejecutada periódicamente (1 vez al día) mediante Azure Functions u otro orquestador externo. La API en sí no incluye funcionalidad de scheduling.
