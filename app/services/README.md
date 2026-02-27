# Carpeta Services

Esta carpeta contiene la lógica de negocio de la aplicación, orquestando clientes y ejecutando procesos complejos.

## Archivos

### `analysis_service.py`
**Función:** Servicio principal que orquesta el análisis de datos y generación de recomendaciones.

**Responsabilidades:**
- Ejecutar queries en MongoDB para obtener datos de ventas
- Enviar datos a AWS Bedrock para análisis con IA
- Filtrar recomendaciones duplicadas usando embeddings
- Gestionar el flujo completo de análisis
- Manejar errores en cada paso del proceso

**Clase principal:**
- `AnalysisService` - Orquesta el proceso completo de análisis
- `ServiceError` - Excepción personalizada para errores del servicio

**Flujo de ejecución:**
1. Obtener datos de MongoDB
2. Enviar a IA para análisis
3. Verificar similitud con recomendaciones previas
4. Retornar recomendaciones filtradas

### `similarity_service.py`
**Función:** Calcula similitud entre recomendaciones usando embeddings vectoriales.

**Responsabilidades:**
- Calcular similitud coseno entre vectores de embeddings
- Determinar si dos recomendaciones son similares (threshold)
- Verificar si una recomendación ya fue enviada recientemente
- Aplicar período de cooldown para evitar repeticiones

**Clase principal:**
- `SimilarityService` - Gestiona cálculos de similitud

**Parámetros configurables:**
- `similarity_threshold` - Umbral para considerar recomendaciones similares (default: 0.85)
- `cooldown_days` - Días que deben pasar antes de repetir recomendación similar (default: 14)

### `recommendation_memory_store.py`
**Función:** Almacena y recupera historial de recomendaciones enviadas.

**Responsabilidades:**
- Generar embeddings de nuevas recomendaciones
- Guardar recomendaciones en MongoDB con sus embeddings
- Recuperar historial de recomendaciones por ejecutivo
- Mantener registro de qué se ha recomendado a cada ejecutivo

**Clase principal:**
- `RecommendationMemoryStore` - Gestiona persistencia de recomendaciones

**Datos almacenados:**
- ID de ejecutivo
- ID de cliente recomendado
- Texto de la recomendación
- Embedding vectorial
- Timestamp de creación

### `memory_reset_service.py`
**Función:** Gestiona el reseteo periódico de memoria de recomendaciones.

**Responsabilidades:**
- Verificar si es necesario resetear la memoria (cada 90 días)
- Eliminar embeddings antiguos de ejecutivos
- Mantener registro de últimos resets
- Limpiar datos de memoria cuando se cumple el período

**Clase principal:**
- `MemoryResetService` - Gestiona ciclos de reseteo de memoria

**Lógica de reseteo:**
- Cada 90 días se eliminan embeddings antiguos
- Permite que recomendaciones pasadas puedan repetirse
- Mantiene el sistema actualizado con datos recientes

### `email_notification_service.py`
**Función:** Envía notificaciones por email con las recomendaciones generadas.

**Responsabilidades:**
- Formatear recomendaciones en HTML para emails
- Enviar emails a ejecutivos con sus recomendaciones
- Manejar modo testing (envío solo a test_correo)
- Manejar errores de envío de emails
- Generar contenido HTML atractivo y legible

**Clase principal:**
- `EmailNotificationService` - Gestiona envío de notificaciones

**Formato de email:**
- Saludo personalizado
- Métricas visuales (progress bars, badges)
- Lista de clientes recomendados con prioridad
- Razones de cada recomendación
- Alertas destacadas
- Formato HTML con estilos inline (email-safe)

**Modo Testing:**
- Parámetro `is_testing` para activar modo prueba
- Solo envía a ejecutivos con campo `test_correo`
- Agrega prefijo `[TEST]` al asunto
- Tracking de correos omitidos (`total_skipped`)

### `batch_processor.py`
**Función:** Procesa ejecutivos en lotes paralelos para mejorar performance.

**Responsabilidades:**
- Dividir ejecutivos en lotes configurables
- Procesar lotes en paralelo usando ThreadPoolExecutor
- Consolidar resultados de múltiples lotes
- Manejar errores por lote sin afectar otros
- Optimizar uso de recursos y tiempo de procesamiento

**Clases principales:**
- `BatchConfig` - Configuración de lotes (tamaño, paralelismo)
- `BatchProcessor` - Procesador de lotes en paralelo

**Configuración (variables de entorno):**
- `BATCH_SIZE` - Ejecutivos por lote (default: 5)
- `MAX_PARALLEL_BATCHES` - Lotes simultáneos (default: 20)
- `ENABLE_PARALLEL_BATCHES` - Activar/desactivar paralelismo (default: true)
- `MAX_CLIENTS_PER_EXEC` - Clientes máximos por ejecutivo (default: 30)

**Performance:**
- Procesamiento paralelo: ~5.2x más rápido que secuencial
- 76 ejecutivos: De ~12 minutos a ~2.3 minutos
- Configuración óptima: 16 lotes de 5 ejecutivos

### `__init__.py`
**Función:** Marca el directorio como un paquete Python.

## Diagrama de Arquitectura

```
┌─────────────────────────────────────────────────────────────┐
│                    analysis_service.py                       │
│                   (Orquestador Principal)                    │
└───────┬─────────────────────────────────────────────────────┘
        │
        │ coordina
        │
        ├──────────────┬──────────────┬──────────────┬─────────────┬──────────────┐
        │              │              │              │             │              │
        ▼              ▼              ▼              ▼             ▼              ▼
┌──────────────┐ ┌──────────┐ ┌──────────┐ ┌──────────────┐ ┌─────────┐ ┌──────────┐
│ MongoDB      │ │ batch_   │ │similarity│ │recommendation│ │ memory_ │ │ email_   │
│ Client       │ │ processor│ │_service  │ │_memory_store │ │ reset_  │ │notification│
│              │ │          │ │          │ │              │ │ service │ │_service  │
└──────────────┘ └────┬─────┘ └──────────┘ └──────────────┘ └─────────┘ └──────────┘
        │              │              │              │             │             │
        │              │              │              │             │             │
        │              ▼              │              │             │             │
        │       ┌──────────┐          │              │             │             │
        │       │ AWS      │          │              │             │             │
        │       │ Bedrock  │          │              │             │             │
        │       │ Client   │          │              │             │             │
        │       │(parallel)│          │              │             │             │
        │       └──────────┘          │              │             │             │
        │              │              │              │             │             │
        ▼              ▼              ▼              ▼             ▼             ▼
┌──────────────┐ ┌──────────┐ ┌──────────┐ ┌──────────────┐ ┌─────────┐ ┌──────────┐
│ Datos de     │ │ Análisis │ │ Filtrado │ │ Historial de │ │ Limpieza│ │ Emails   │
│ Ventas       │ │ con IA   │ │ por      │ │ Recomenda-   │ │ Periódica│ │ enviados │
│              │ │(en lotes)│ │ Similitud│ │ ciones       │ │         │ │          │
└──────────────┘ └──────────┘ └──────────┘ └──────────────┘ └─────────┘ └──────────┘
```

## Flujo Completo del Sistema

```
1. API recibe request → analysis_service.execute_analysis()
                              │
2. Verificar reset de memoria │
   (memory_reset_service)     │
                              ▼
3. Ejecutar queries MongoDB   │
   (mongodb_client)           │
                              ▼
4. Dividir en lotes           │
   (batch_processor)          │
                              ▼
5. Procesar lotes en paralelo │
   a. Enviar lote a IA        │
      (aws_bedrock_client)    │
   b. Parsear recomendaciones │
   c. Consolidar resultados   │
                              ▼
6. Para cada recomendación:   │
   a. Generar embedding       │
      (embedding_client)      │
   b. Verificar similitud     │
      (similarity_service)    │
   c. Filtrar duplicados      │
                              ▼
7. Guardar recomendaciones    │
   (recommendation_memory_    │
    store)                    │
                              ▼
8. Enriquecer con test_correo │
   (desde datos originales)   │
                              ▼
9. Enviar emails              │
   (email_notification_       │
    service)                  │
   - Modo testing: solo       │
     test_correo              │
   - Producción: todos        │
                              ▼
10. Retornar resultado a API
```

## Patrones de Diseño

- **Service Layer Pattern**: Encapsula lógica de negocio
- **Dependency Injection**: Servicios reciben clientes como dependencias
- **Strategy Pattern**: Diferentes estrategias de similitud y notificación
- **Repository Pattern**: RecommendationMemoryStore actúa como repositorio

## Relaciones con otros módulos

- **Depende de:** `app.clients` (todos los clientes), `app.config` (Settings, queries)
- **Usado por:** `app.api.routes` (endpoints de la API)
- **Colabora con:** Otros servicios dentro de la misma carpeta
