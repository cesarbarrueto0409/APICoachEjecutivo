# Carpeta Clients

Esta carpeta contiene los clientes que se comunican con servicios externos (bases de datos, APIs de IA, servicios de email).

## Archivos

### `interfaces.py`
**Función:** Define las interfaces (protocolos) que deben implementar los clientes.

**Responsabilidades:**
- Define `IDataClient` - Interfaz para clientes de bases de datos
- Define `IAIClient` - Interfaz para clientes de IA
- Define `IEmbeddingClient` - Interfaz para clientes de embeddings
- Establece el contrato que deben cumplir las implementaciones concretas

**Interfaces:**
- `IDataClient`: `connect()`, `query()`, `disconnect()`
- `IAIClient`: `connect()`, `analyze()`
- `IEmbeddingClient`: `connect()`, `generate_embedding()`, `generate_embeddings_batch()`

### `mongodb_client.py`
**Función:** Cliente para interactuar con MongoDB.

**Responsabilidades:**
- Conectar y desconectar de MongoDB
- Ejecutar queries agregadas complejas
- Insertar documentos en colecciones
- Implementa la interfaz `IDataClient`

**Clase principal:**
- `MongoDBClient` - Gestiona conexiones y operaciones con MongoDB

### `aws_bedrock_client.py`
**Función:** Cliente para interactuar con AWS Bedrock (servicio de IA de AWS).

**Responsabilidades:**
- Conectar con AWS Bedrock
- Enviar datos y prompts para análisis con modelos de IA
- Validar IDs de modelos soportados
- Parsear respuestas de la IA
- Implementa la interfaz `IAIClient`

**Clase principal:**
- `AWSBedrockClient` - Gestiona llamadas a modelos de IA en AWS Bedrock

**Modelos soportados:**
- Claude 3.5 Sonnet, Claude 3 Opus, Claude 3 Sonnet, Claude 3 Haiku

### `embedding_client.py`
**Función:** Cliente para generar embeddings de texto usando OpenAI.

**Responsabilidades:**
- Conectar con la API de OpenAI
- Generar embeddings vectoriales de textos individuales
- Generar embeddings en batch para múltiples textos
- Implementa la interfaz `IEmbeddingClient`

**Clase principal:**
- `EmbeddingClient` - Genera vectores de embeddings usando modelos de OpenAI

### `email_client.py`
**Función:** Cliente para enviar emails usando SendGrid.

**Responsabilidades:**
- Definir interfaz `IEmailClient` para servicios de email
- Implementar envío de emails con SendGrid
- Soportar múltiples destinatarios y contenido HTML
- Manejar errores de envío

**Clases principales:**
- `IEmailClient` - Interfaz para clientes de email
- `SendGridEmailClient` - Implementación con SendGrid

### `__init__.py`
**Función:** Marca el directorio como un paquete Python.

## Diagrama de Arquitectura

```
┌─────────────────────────────────────────────────────────────┐
│                      interfaces.py                           │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐  │
│  │ IDataClient  │  │  IAIClient   │  │ IEmbeddingClient │  │
│  └──────────────┘  └──────────────┘  └──────────────────┘  │
└───────┬──────────────────┬──────────────────┬───────────────┘
        │                  │                  │
        │ implementa       │ implementa       │ implementa
        ▼                  ▼                  ▼
┌──────────────┐   ┌──────────────┐   ┌──────────────┐
│ mongodb_     │   │ aws_bedrock_ │   │ embedding_   │
│ client.py    │   │ client.py    │   │ client.py    │
└──────┬───────┘   └──────┬───────┘   └──────┬───────┘
       │                  │                  │
       ▼                  ▼                  ▼
┌──────────────┐   ┌──────────────┐   ┌──────────────┐
│   MongoDB    │   │ AWS Bedrock  │   │  OpenAI API  │
│   Database   │   │   (Claude)   │   │  (Embeddings)│
└──────────────┘   └──────────────┘   └──────────────┘

┌─────────────────────────────────────┐
│         email_client.py             │
│  ┌──────────────┐                   │
│  │ IEmailClient │                   │
│  └──────┬───────┘                   │
│         │ implementa                │
│         ▼                           │
│  ┌──────────────────────┐          │
│  │ SendGridEmailClient  │          │
│  └──────────┬───────────┘          │
└─────────────┼────────────────────────┘
              ▼
       ┌──────────────┐
       │   SendGrid   │
       │   Service    │
       └──────────────┘
```

## Patrón de Diseño

Todos los clientes siguen el patrón **Adapter** e **Interface Segregation**:
- Las interfaces definen contratos claros
- Las implementaciones concretas adaptan servicios externos
- Facilita testing con mocks
- Permite cambiar implementaciones sin afectar el resto del código

## Relaciones con otros módulos

- **Depende de:** Servicios externos (MongoDB, AWS, OpenAI, SendGrid)
- **Usado por:** `app.services` (AnalysisService, EmailNotificationService, RecommendationMemoryStore)
