# Carpeta Functionality Tests

Esta carpeta contiene tests funcionales que verifican la lógica de negocio y el comportamiento correcto de los servicios.

## Archivos

### `test_analysis_service.py`
**Función:** Tests unitarios del servicio de análisis.

**Tests incluidos:**
- Tests de ejecución exitosa de análisis
- Tests de manejo de errores en diferentes pasos
- Tests con mocks de clientes (MongoDB, AWS Bedrock)
- Verificación de flujo completo de análisis

### `test_analysis_service_memory_integration.py`
**Función:** Tests de integración entre análisis y memoria de recomendaciones.

**Tests incluidos:**
- Integración entre AnalysisService y RecommendationMemoryStore
- Verificación de almacenamiento de recomendaciones
- Tests de recuperación de historial

### `test_api_routes.py`
**Función:** Tests de los endpoints de la API.

**Tests incluidos:**
- Tests del endpoint `/analyze`
- Verificación de validación de requests
- Tests de respuestas HTTP
- Tests con mocks de servicios

### `test_border_cases.py`
**Función:** Tests de casos límite y edge cases.

**Tests incluidos:**
- `test_zero_clients_available` - Comportamiento cuando no hay clientes disponibles
- `test_one_or_two_clients_available` - Comportamiento con pocos clientes
- `test_cooldown_period` - Verificación del período de cooldown
- `test_different_recommendations_each_day` - Recomendaciones diferentes cada día

### `test_embeddings_memory.py`
**Función:** Tests del sistema de embeddings y memoria.

**Tests incluidos:**
- `test_embedding_generation` - Generación de embeddings
- `test_similarity_computation` - Cálculo de similitud coseno
- `test_no_duplicate_recommendations` - Prevención de duplicados
- `test_memory_store_retrieval` - Recuperación de historial

### `test_main.py`
**Función:** Tests de la aplicación principal.

**Tests incluidos:**
- `test_create_app_with_valid_config_returns_fastapi_app` - Creación de app
- `test_create_app_without_config_raises_value_error` - Validación de config
- `test_create_app_includes_api_routes` - Inclusión de rutas
- `test_create_app_configures_cors_middleware` - Configuración de CORS

### `test_python_parser.py`
**Función:** Tests del parser de archivos Python.

**Tests incluidos:**
- `test_parse_simple_function` - Parsing de funciones simples
- `test_parse_function_without_docstring` - Funciones sin docstring
- Tests de extracción de clases y métodos

### `test_query_execution.py`
**Función:** Tests de ejecución de queries y prompts.

**Tests incluidos:**
- `test_query_generation` - Generación de queries MongoDB
- `test_prompt_generation` - Generación de prompts para IA
- `test_mongodb_data_structure` - Estructura de datos en MongoDB
- `test_sales_data_retrieval` - Recuperación de datos de ventas

### `test_parallel_processing.py`
**Función:** Tests del sistema de procesamiento en paralelo.

**Tests incluidos:**
- `test_batch_config_from_env` - Configuración desde variables de entorno
- `test_batch_config_defaults` - Valores por defecto de configuración
- `test_divide_76_executives_into_batches` - División de ejecutivos en lotes
- `test_parallel_processing_integrity` - Integridad de datos en paralelo
- `test_parallel_speedup` - Verificación de mejora de performance
- `test_test_correo_field_preserved` - Preservación de campo test_correo
- `test_testing_mode_filters_correctly` - Filtrado correcto en modo testing

**Categorías de tests:**
- Configuración de lotes (BatchConfig)
- División de ejecutivos (batch division)
- Procesamiento paralelo (parallel execution)
- Manejo de errores (error handling)
- Modo testing de correos (email testing mode)

### `test_settings.py`
**Función:** Tests de configuración de la aplicación.

**Tests incluidos:**
- `test_settings_initialization` - Inicialización de settings
- `test_settings_defaults` - Valores por defecto
- `test_validate_success` - Validación exitosa
- `test_validate_missing_mongodb_uri` - Validación de campos requeridos

### `__init__.py`
**Función:** Marca el directorio como un paquete Python.

## Diagrama de Cobertura

```
┌─────────────────────────────────────────────────────────┐
│           Functionality Test Suite                       │
└─────────────────────────────────────────────────────────┘
                          │
        ┌─────────────────┼─────────────────┐
        │                 │                 │
        ▼                 ▼                 ▼
┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│test_analysis │  │test_api_     │  │test_settings │
│_service      │  │routes        │  │              │
└──────────────┘  └──────────────┘  └──────────────┘
        │                 │                 │
        ▼                 ▼                 ▼
┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│ Analysis     │  │ API Layer    │  │ Configuration│
│ Service      │  │              │  │              │
└──────────────┘  └──────────────┘  └──────────────┘

        ┌─────────────────┬─────────────────┐
        │                 │                 │
        ▼                 ▼                 ▼
┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│test_         │  │test_query_   │  │test_python_  │
│embeddings_   │  │execution     │  │parser        │
│memory        │  │              │  │              │
└──────────────┘  └──────────────┘  └──────────────┘
        │                 │                 │
        ▼                 ▼                 ▼
┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│ Similarity & │  │ Queries &    │  │ Python       │
│ Memory       │  │ Prompts      │  │ Parser       │
└──────────────┘  └──────────────┘  └──────────────┘

        ┌─────────────────┐
        │                 │
        ▼                 ▼
┌──────────────┐  ┌──────────────┐
│test_border_  │  │test_main     │
│cases         │  │              │
└──────────────┘  └──────────────┘
        │                 │
        ▼                 ▼
┌──────────────┐  ┌──────────────┐
│ Edge Cases & │  │ Application  │
│ Limits       │  │ Bootstrap    │
└──────────────┘  └──────────────┘
```

## Tipos de Tests

1. **Tests Unitarios**: Verifican componentes individuales con mocks
2. **Tests de Integración**: Verifican interacción entre componentes
3. **Tests de Edge Cases**: Verifican comportamiento en límites
4. **Tests End-to-End**: Verifican flujo completo de la aplicación

## Relaciones con otros módulos

- **Depende de:** Todos los módulos de `app/`
- **Verifica:** Lógica de negocio, integración, casos límite
