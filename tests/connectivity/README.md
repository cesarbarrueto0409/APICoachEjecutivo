# Carpeta Connectivity Tests

Esta carpeta contiene tests de conectividad para verificar que todos los servicios externos están configurados correctamente y son accesibles.

## Archivos

### `test_api_health.py`
**Función:** Tests para verificar los endpoints de health check de la API.

**Tests incluidos:**
- `test_api_health_endpoint` - Verifica que el endpoint `/health` responde correctamente
- `test_mongodb_health_endpoint` - Verifica el health check de MongoDB
- `test_bedrock_health_endpoint` - Verifica el health check de AWS Bedrock
- `test_sendgrid_health_endpoint` - Verifica el health check de SendGrid
- `test_embedding_health_endpoint` - Verifica el health check del servicio de embeddings

### `test_aws_bedrock.py`
**Función:** Tests de conectividad con AWS Bedrock.

**Tests incluidos:**
- `test_bedrock_connection` - Verifica que se puede conectar a AWS Bedrock
- `test_bedrock_analysis_response` - Verifica que Bedrock puede analizar datos y retornar respuestas

### `test_embedding.py`
**Función:** Tests de conectividad con el servicio de embeddings de OpenAI.

**Tests incluidos:**
- `test_embedding_connection` - Verifica conexión con la API de OpenAI
- `test_embedding_batch_generation` - Verifica generación de embeddings en batch

### `test_mongodb.py`
**Función:** Tests de conectividad con MongoDB.

**Tests incluidos:**
- `test_mongodb_connection` - Verifica conexión a MongoDB
- `test_mongodb_query_execution` - Verifica ejecución de queries agregadas
- `test_mongodb_prompt_retrieval` - Verifica recuperación de prompts desde MongoDB

### `test_sendgrid.py`
**Función:** Tests de conectividad con SendGrid.

**Tests incluidos:**
- `test_sendgrid_configuration` - Verifica configuración de SendGrid
- `test_sendgrid_test_email` - Verifica envío de email de prueba

### `__init__.py`
**Función:** Marca el directorio como un paquete Python.

## Diagrama de Tests

```
┌─────────────────────────────────────────────────────────┐
│              Connectivity Test Suite                     │
└─────────────────────────────────────────────────────────┘
                          │
        ┌─────────────────┼─────────────────┐
        │                 │                 │
        ▼                 ▼                 ▼
┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│test_mongodb  │  │test_aws_     │  │test_embedding│
│              │  │bedrock       │  │              │
└──────┬───────┘  └──────┬───────┘  └──────┬───────┘
       │                 │                 │
       ▼                 ▼                 ▼
┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│   MongoDB    │  │ AWS Bedrock  │  │  OpenAI API  │
│   Database   │  │   Service    │  │   Embeddings │
└──────────────┘  └──────────────┘  └──────────────┘

        ┌─────────────────┬─────────────────┐
        │                 │                 │
        ▼                 ▼                 ▼
┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│test_sendgrid │  │test_api_     │  │              │
│              │  │health        │  │              │
└──────┬───────┘  └──────┬───────┘  └──────────────┘
       │                 │
       ▼                 ▼
┌──────────────┐  ┌──────────────┐
│   SendGrid   │  │  FastAPI     │
│   Service    │  │  Endpoints   │
└──────────────┘  └──────────────┘
```

## Propósito

Estos tests verifican que:
1. Todas las credenciales están configuradas correctamente
2. Los servicios externos son accesibles
3. Las APIs responden como se espera
4. La configuración de red permite la comunicación

## Relaciones con otros módulos

- **Depende de:** `app.clients`, `app.config`, `app.api`
- **Verifica:** Conectividad con servicios externos
