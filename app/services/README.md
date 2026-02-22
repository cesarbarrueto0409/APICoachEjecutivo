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
- Manejar errores de envío de emails
- Generar contenido HTML atractivo y legible

**Clase principal:**
- `EmailNotificationService` - Gestiona envío de notificaciones

**Formato de email:**
- Saludo personalizado
- Lista de clientes recomendados
- Razones de cada recomendación
- Formato HTML con estilos

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
        ├──────────────┬──────────────┬──────────────┬─────────────┐
        │              │              │              │             │
        ▼              ▼              ▼              ▼             ▼
┌──────────────┐ ┌──────────┐ ┌──────────┐ ┌──────────────┐ ┌─────────┐
│ MongoDB      │ │ AWS      │ │similarity│ │recommendation│ │ memory_ │
│ Client       │ │ Bedrock  │ │_service  │ │_memory_store │ │ reset_  │
│              │ │ Client   │ │          │ │              │ │ service │
└──────────────┘ └──────────┘ └──────────┘ └──────────────┘ └─────────┘
        │              │              │              │             │
        │              │              │              │             │
        ▼              ▼              ▼              ▼             ▼
┌──────────────┐ ┌──────────┐ ┌──────────┐ ┌──────────────┐ ┌─────────┐
│ Datos de     │ │ Análisis │ │ Filtrado │ │ Historial de │ │ Limpieza│
│ Ventas       │ │ con IA   │ │ por      │ │ Recomenda-   │ │ Periódica│
└──────────────┘ └──────────┘ │ Similitud│ │ ciones       │ └─────────┘
                               └──────────┘ └──────────────┘
                                      │              │
                                      └──────┬───────┘
                                             ▼
                                  ┌────────────────────┐
                                  │ email_notification_│
                                  │ service.py         │
                                  └─────────┬──────────┘
                                            │
                                            ▼
                                  ┌────────────────────┐
                                  │ Emails enviados    │
                                  │ a ejecutivos       │
                                  └────────────────────┘
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
4. Enviar datos a IA          │
   (aws_bedrock_client)       │
                              ▼
5. Parsear recomendaciones    │
   de la IA                   │
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
8. Enviar emails              │
   (email_notification_       │
    service)                  │
                              ▼
9. Retornar resultado a API
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
