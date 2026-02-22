# Carpeta Config

Esta carpeta contiene la configuración de la aplicación, incluyendo settings, queries de base de datos y prompts para IA.

## Archivos

### `settings.py`
**Función:** Gestiona toda la configuración de la aplicación desde variables de entorno.

**Responsabilidades:**
- Cargar variables de entorno desde archivo `.env`
- Validar que todas las configuraciones requeridas estén presentes
- Proporcionar acceso centralizado a configuraciones
- Configurar parámetros de servicios externos (MongoDB, AWS, OpenAI, SendGrid)

**Clase principal:**
- `Settings` - Contiene todas las configuraciones de la aplicación

**Configuraciones incluidas:**
- MongoDB: URI, nombre de base de datos, colecciones
- AWS Bedrock: región, modelo, credenciales
- OpenAI: API key, endpoint, modelo de embeddings
- SendGrid: API key, emails de origen y destino
- Parámetros de negocio: umbral de similitud, días de cooldown, límite de recomendaciones

### `queries.py`
**Función:** Define las queries de MongoDB y prompts para análisis de IA.

**Responsabilidades:**
- Generar queries agregadas de MongoDB para extraer datos de ventas
- Construir prompts dinámicos para el análisis de IA
- Parsear fechas y calcular rangos temporales
- Obtener información adicional de ejecutivos desde MongoDB

**Funciones principales:**
- `get_queries(current_date)` - Retorna lista de queries de MongoDB para análisis
- `get_analysis_prompt(current_date, mongodb_client)` - Genera el prompt para la IA
- `parse_date(date_str)` - Convierte strings de fecha a tuplas

**Queries incluidas:**
- Ventas por ejecutivo en diferentes períodos
- Clientes atendidos por ejecutivo
- Análisis de tendencias temporales
- Datos de contacto de ejecutivos

### `__init__.py`
**Función:** Marca el directorio como un paquete Python.

## Diagrama de Flujo

```
┌─────────────────────────────────────────────────────────┐
│                    Archivo .env                          │
│  MONGODB_URI=...                                         │
│  AWS_REGION=...                                          │
│  OPENAI_API_KEY=...                                      │
│  SENDGRID_API_KEY=...                                    │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
            ┌────────────────┐
            │  settings.py   │
            │   (Settings)   │
            └────────┬───────┘
                     │
                     │ proporciona configuración
                     │
        ┌────────────┴────────────┐
        │                         │
        ▼                         ▼
┌───────────────┐         ┌──────────────┐
│  queries.py   │         │   Servicios  │
│               │         │   y Clientes │
└───────┬───────┘         └──────────────┘
        │
        │ genera
        ▼
┌───────────────────────────────────┐
│  Queries MongoDB + Prompts IA     │
│  - get_queries()                  │
│  - get_analysis_prompt()          │
└───────────────────────────────────┘
        │
        ▼
┌───────────────────────────────────┐
│  Datos estructurados para         │
│  análisis y recomendaciones       │
└───────────────────────────────────┘

Flujo de configuración:
1. Aplicación inicia → settings.py carga .env
2. Settings valida configuraciones requeridas
3. Servicios obtienen configuración de Settings
4. queries.py usa Settings para generar queries dinámicas
5. Queries se ejecutan en MongoDB
6. Prompts se envían a AWS Bedrock
```

## Estructura de Queries

Las queries en `queries.py` están organizadas para extraer:
1. **Ventas del mes actual** por ejecutivo
2. **Ventas del mes anterior** por ejecutivo
3. **Ventas del mismo mes año anterior** por ejecutivo
4. **Clientes únicos atendidos** por ejecutivo
5. **Información de contacto** de ejecutivos

## Estructura del Prompt

El prompt generado incluye:
- Contexto de la fecha actual
- Instrucciones para análisis de datos de ventas
- Criterios para generar recomendaciones
- Formato esperado de respuesta (JSON)
- Reglas de negocio (top 3 clientes, evitar duplicados)

## Relaciones con otros módulos

- **Depende de:** Variables de entorno (`.env`)
- **Usado por:** Todos los módulos de la aplicación (`app.services`, `app.clients`, `app.api`)
- **Proporciona:** Configuración centralizada y queries/prompts dinámicos
