"""
Dynamic query configuration and prompts for sales analysis.

This module generates MongoDB aggregation pipelines and AI analysis prompts dynamically
based on the current date. It handles complex data enrichment by joining multiple
collections and calculating various metrics.

The module provides two main functions:
    - get_queries(): Generates MongoDB aggregation pipelines
    - get_analysis_prompt(): Generates AI analysis prompts with date context

Example:
    Generate queries for a specific date:
    
    >>> from app.config.queries import get_queries, get_analysis_prompt
    >>> queries = get_queries("2024-02-18")
    >>> prompt = get_analysis_prompt("2024-02-18")
    >>> print(f"Generated {len(queries)} queries")
    >>> print(f"Prompt length: {len(prompt)} characters")
"""

from datetime import datetime
from typing import List, Dict, Any, Optional
from app.clients.mongodb_client import MongoDBClient


def parse_date(date_str: str) -> tuple:
    """
    Parse date string and extract year, month, day components.
    
    This function converts a date string in YYYY-MM-DD format into separate
    integer components for year, month, and day. These components are used
    throughout the query generation process.
    
    Args:
        date_str: Date string in format "YYYY-MM-DD" (e.g., "2024-02-18")
    
    Returns:
        Tuple of (year, month, day) as integers
        
    Raises:
        ValueError: If date_str is not in correct format
        
    Example:
        >>> year, month, day = parse_date("2024-02-18")
        >>> print(f"Year: {year}, Month: {month}, Day: {day}")
        Year: 2024, Month: 2, Day: 18
    """
    date_obj = datetime.strptime(date_str, "%Y-%m-%d")
    return date_obj.year, date_obj.month, date_obj.day


def get_queries(current_date: str) -> List[Dict[str, Any]]:
    """
    Generate MongoDB aggregation pipeline queries based on current date.
    
    This function creates a complex aggregation pipeline that enriches executive
    sales data by joining multiple collections and calculating various metrics.
    The pipeline performs the following operations:
    
    1. Unwinds client list for individual processing
    2. Joins sales data for the current month
    3. Joins client metrics (risk, drop_flag, etc.)
    4. Joins claims/complaints data
    5. Joins pickup/retiros data
    6. Joins previous Bedrock recommendations (legacy)
    7. Joins memory embeddings (last 3 recommendations)
    8. Consolidates all client information
    9. Groups by executive with detailed portfolio
    10. Adds sales goals and calculates advancement metrics
    
    The resulting data structure provides a complete view of each executive's
    portfolio with all necessary information for AI analysis.
    
    Args:
        current_date: Date string in format "YYYY-MM-DD" (e.g., "2024-02-18")
            This date determines which month's data to retrieve and is used
            for filtering sales, claims, and pickup data.
    
    Returns:
        List containing one dictionary with the aggregation pipeline configuration:
        [
            {
                "name": "ventas_por_ejecutivo_enriquecido",
                "collection": "clientes_por_ejecutivo",
                "pipeline": [...]  # MongoDB aggregation stages
            }
        ]
    
    Example:
        Generate queries for February 18, 2024:
        >>> queries = get_queries("2024-02-18")
        >>> print(queries[0]["name"])
        ventas_por_ejecutivo_enriquecido
        >>> print(queries[0]["collection"])
        clientes_por_ejecutivo
        >>> print(len(queries[0]["pipeline"]))  # Number of aggregation stages
        15
        
        Use with MongoDB client:
        >>> from app.clients.mongodb_client import MongoDBClient
        >>> client = MongoDBClient("mongodb://localhost", "sales_db")
        >>> client.connect()
        >>> queries = get_queries("2024-02-18")
        >>> results = client.query(queries[0])
        >>> print(f"Found {len(results)} executives")
        >>> for exec_data in results:
        ...     print(f"{exec_data['nombre_ejecutivo']}: {exec_data['ventas_total_mes']}")
    
    Collections Used:
        - clientes_por_ejecutivo: Executive-client mappings (base collection)
        - sales_last_month: Monthly sales data
        - clients_data: Client metrics (risk_level, drop_flag, is_active, etc.)
        - claims_last_month: Claims/complaints data
        - pickup_last_month: Pickup/retiros data
        - clients_recomendations: Previous Bedrock recommendations (legacy)
        - memory_embeddings: Semantic memory with embeddings (last 3 per client)
        - sales_goal: Sales targets by executive
    
    Output Structure:
        Each document in the result represents one executive with:
        {
            "id_ejecutivo": int,
            "nombre_ejecutivo": str,
            "correo": str,
            "agno": int,
            "mes": int,
            "ventas_total_mes": float,
            "goal_mes": float,
            "goal_year": float,
            "avance_pct": float,
            "faltante": float,
            "n_clientes": int,
            "clientes_con_ventas": int,
            "cartera_detallada": [
                {
                    "rut_key": str,
                    "nombre": str,
                    "ventas_mes": float,
                    "client_metrics": {
                        "drop_flag": int,
                        "risk_level": str,  # "red", "yellow", "green"
                        "risk_score": float,
                        "is_active": bool,
                        "needs_attention": bool,
                        "is_high_value": bool,
                        "monto_neto_mes_mean": float,
                        "avg_last3": float,
                        "avg_prev3": float,
                        "p25": float,
                        "p50": float,
                        "consec_below_p25": int
                    },
                    "claims": {
                        "total_reclamos": int,
                        "reclamos": [
                            {
                                "numero_caso": str,
                                "fecha_creacion": str,
                                "motivo": str,
                                "subcategoria": str,
                                "estado": str,
                                "valor_reclamado": float,
                                "descripcion_caso": str
                            }
                        ]
                    },
                    "pickups": {
                        "cant_retiros_programados": int,
                        "cant_retiros_efectuados": int,
                        "lista_retiros": [...]
                    },
                    "recommendation": {
                        "bedrock_recommendation": str,
                        "execution_date": str,
                        "cluster": str
                    },
                    "memory_recs": [
                        {
                            "recommendation": str,
                            "timestamp": str,
                            "metadata": dict
                        }
                    ]
                }
            ]
        }
    """
    year, month, day = parse_date(current_date)
    
    return [
        {
            "name": "ventas_por_ejecutivo_enriquecido",
            "collection": "clientes_por_ejecutivo",
            "pipeline": [
                # Unwind to process each client individually
                {"$unwind": "$rut_clientes"},
                {"$addFields": {"rut_cliente_str": {"$toString": "$rut_clientes"}}},
                
                # Lookup 1: Sales data
                {
                    "$lookup": {
                        "from": "sales_last_month",
                        "let": {"rut": "$rut_cliente_str"},
                        "pipeline": [
                            {
                                "$match": {
                                    "$expr": {
                                        "$and": [
                                            {"$eq": ["$rut_cliente", "$$rut"]},
                                            {"$eq": ["$agno", year]},
                                            {"$eq": ["$mes", month]}
                                        ]
                                    }
                                }
                            },
                            {"$unwind": {"path": "$ventas", "preserveNullAndEmptyArrays": True}},
                            {
                                "$group": {
                                    "_id": None,
                                    "ventas_cliente": {"$sum": "$ventas.MONTO_VENTAS_NETAS"}
                                }
                            }
                        ],
                        "as": "sales"
                    }
                },
                
                # Lookup 2: Client data (risk, drop_flag, metrics)
                {
                    "$lookup": {
                        "from": "clients_data",
                        "let": {"rut": "$rut_clientes"},
                        "pipeline": [
                            {
                                "$match": {
                                    "$expr": {
                                        "$or": [
                                            {"$eq": ["$rut_key", "$$rut"]},
                                            {"$eq": [{"$toString": "$rut_key"}, {"$toString": "$$rut"}]}
                                        ]
                                    }
                                }
                            },
                            {
                                "$project": {
                                    "_id": 0,
                                    "nombre": 1,
                                    "tipo_cartera": 1,
                                    "nombre_cartera": 1,
                                    "monto_neto_mes_mean": 1,
                                    "drop_flag": 1,
                                    "risk_level": 1,
                                    "risk_score": 1,
                                    "drop_pct_6m": 1,
                                    "consec_below_p25": 1,
                                    "below_p50_frac": 1,
                                    "p25": 1,
                                    "p50": 1,
                                    "avg_last3": 1,
                                    "avg_prev3": 1,
                                    "avg_prev6": 1,
                                    "is_high_value": 1,
                                    "is_active": 1,
                                    "needs_attention": 1
                                }
                            }
                        ],
                        "as": "client_data"
                    }
                },
                
                # Lookup 3: Claims data
                {
                    "$lookup": {
                        "from": "claims_last_month",
                        "let": {"rut": "$rut_cliente_str"},
                        "pipeline": [
                            {
                                "$match": {
                                    "$expr": {
                                        "$and": [
                                            {"$eq": ["$rut_cliente", "$$rut"]},
                                            {"$eq": ["$agno", year]},
                                            {"$eq": ["$mes", month]}
                                        ]
                                    }
                                }
                            },
                            {
                                "$project": {
                                    "_id": 0,
                                    "total_reclamos": {"$size": {"$ifNull": ["$reclamos", []]}},
                                    "reclamos": {
                                        "$map": {
                                            "input": {"$ifNull": ["$reclamos", []]},
                                            "as": "reclamo",
                                            "in": {
                                                "numero_caso": "$$reclamo.Numero_Caso",
                                                "fecha_creacion": "$$reclamo.Fecha_Creacion",
                                                "motivo": "$$reclamo.Motivo",
                                                "subcategoria": "$$reclamo.Subcategoria",
                                                "estado": "$$reclamo.Estado",
                                                "valor_reclamado": "$$reclamo.Valor_Reclamado",
                                                "descripcion_caso": "$$reclamo.Descripcion_del_caso"
                                            }
                                        }
                                    }
                                }
                            }
                        ],
                        "as": "claims_data"
                    }
                },
                
                # Lookup 4: Pickup/retiros data
                {
                    "$lookup": {
                        "from": "pickup_last_month",
                        "let": {"rut": "$rut_cliente_str"},
                        "pipeline": [
                            {
                                "$match": {
                                    "$expr": {
                                        "$and": [
                                            {"$eq": ["$rut_cliente", "$$rut"]},
                                            {"$eq": ["$agno", year]},
                                            {"$eq": ["$mes", month]}
                                        ]
                                    }
                                }
                            },
                            {
                                "$project": {
                                    "_id": 0,
                                    "cant_retiros_programados": 1,
                                    "cant_retiros_efectuados": 1,
                                    "lista_retiros": 1
                                }
                            }
                        ],
                        "as": "pickup_data"
                    }
                },
                
                # Lookup 5: Previous Bedrock recommendations
                {
                    "$lookup": {
                        "from": "clients_recomendations",
                        "let": {"rut": "$rut_clientes"},
                        "pipeline": [
                            {
                                "$match": {
                                    "$expr": {
                                        "$or": [
                                            {"$eq": ["$rut_key", "$$rut"]},
                                            {"$eq": [{"$toString": "$rut_key"}, {"$toString": "$$rut"}]}
                                        ]
                                    }
                                }
                            },
                            {"$sort": {"execution_date": -1}},
                            {"$limit": 1},
                            {
                                "$project": {
                                    "_id": 0,
                                    "bedrock_recommendation": 1,
                                    "execution_date": 1,
                                    "cluster": 1
                                }
                            }
                        ],
                        "as": "recommendation_data"
                    }
                },
                
                # Lookup 6: Memory embeddings recommendations (last 3 recommendations)
                {
                    "$lookup": {
                        "from": "memory_embeddings",
                        "let": {
                            "exec_id": {"$toString": "$id_ejecutivo"},
                            "client_id": {"$toString": "$rut_clientes"}
                        },
                        "pipeline": [
                            {
                                "$match": {
                                    "$expr": {
                                        "$and": [
                                            {"$eq": ["$executive_id", "$$exec_id"]},
                                            {"$eq": ["$client_id", "$$client_id"]}
                                        ]
                                    }
                                }
                            },
                            {"$sort": {"timestamp": -1}},
                            {"$limit": 3},
                            {
                                "$project": {
                                    "_id": 0,
                                    "recommendation": 1,
                                    "timestamp": 1,
                                    "metadata": 1
                                }
                            }
                        ],
                        "as": "memory_recommendations"
                    }
                },
                
                # Consolidate all client information
                {
                    "$addFields": {
                        "ventas_cliente": {"$ifNull": [{"$first": "$sales.ventas_cliente"}, 0]},
                        "cliente_detalle": {
                            "rut_key": "$rut_clientes",
                            "nombre": {"$ifNull": [{"$first": "$client_data.nombre"}, ""]},
                            "ventas_mes": {"$ifNull": [{"$first": "$sales.ventas_cliente"}, 0]},
                            "client_metrics": {"$first": "$client_data"},
                            "claims": {"$first": "$claims_data"},
                            "pickups": {"$first": "$pickup_data"},
                            "recommendation": {"$first": "$recommendation_data"},
                            "memory_recs": "$memory_recommendations"
                        }
                    }
                },
                
                # Group by executive with all client information
                {
                    "$group": {
                        "_id": {
                            "id_ejecutivo": "$id_ejecutivo",
                            "nombre_ejecutivo": "$nombre_ejecutivo",
                            "correo": "$correo"
                        },
                        "ventas_total_mes": {"$sum": "$ventas_cliente"},
                        "clientes_con_ventas": {
                            "$sum": {"$cond": [{"$gt": ["$ventas_cliente", 0]}, 1, 0]}
                        },
                        "clientes_unicos": {"$addToSet": "$rut_clientes"},
                        "cartera_detallada": {"$push": "$cliente_detalle"}
                    }
                },
                
                # Add executive metrics
                {
                    "$addFields": {
                        "agno": year,
                        "mes": month,
                        "n_clientes": {"$size": "$clientes_unicos"}
                    }
                },
                
                # Lookup: Sales goal
                {
                    "$lookup": {
                        "from": "sales_goal",
                        "localField": "_id.id_ejecutivo",
                        "foreignField": "id_ejecutivo",
                        "as": "goal"
                    }
                },
                {"$addFields": {"goal_doc": {"$first": "$goal"}}},
                
                # Calculate goals and progress
                {
                    "$addFields": {
                        "goal_mes": {
                            "$ifNull": [
                                {
                                    "$getField": {
                                        "field": {"$toString": month},
                                        "input": "$goal_doc.goal_months"
                                    }
                                },
                                0
                            ]
                        },
                        "goal_year": {"$ifNull": ["$goal_doc.goal_year", 0]}
                    }
                },
                {
                    "$addFields": {
                        "avance_pct": {
                            "$cond": [
                                {"$gt": ["$goal_mes", 0]},
                                {"$divide": ["$ventas_total_mes", "$goal_mes"]},
                                None
                            ]
                        },
                        "faltante": {"$subtract": ["$goal_mes", "$ventas_total_mes"]}
                    }
                },
                
                # Final projection
                {
                    "$project": {
                        "_id": 0,
                        "id_ejecutivo": "$_id.id_ejecutivo",
                        "nombre_ejecutivo": "$_id.nombre_ejecutivo",
                        "correo": "$_id.correo",
                        "agno": 1,
                        "mes": 1,
                        "ventas_total_mes": 1,
                        "goal_mes": 1,
                        "goal_year": 1,
                        "avance_pct": 1,
                        "faltante": 1,
                        "n_clientes": 1,
                        "clientes_con_ventas": 1,
                        "cartera_detallada": 1
                    }
                },
                {"$sort": {"avance_pct": -1, "ventas_total_mes": -1}}
            ]
        }
    ]


def get_analysis_prompt(current_date: str, mongodb_client: Optional[MongoDBClient] = None) -> str:
    """Generate analysis prompt based on current date.
    
    Args:
        current_date: Date string in format YYYY-MM-DD
        mongodb_client: Optional MongoDB client to fetch prompt from database
        
    Returns:
        Formatted prompt string with date variables replaced
    """
    year, month, day = parse_date(current_date)
    
    if month in [1, 3, 5, 7, 8, 10, 12]:
        dias_mes = 31
    elif month in [4, 6, 9, 11]:
        dias_mes = 30
    else:
        if (year % 4 == 0 and year % 100 != 0) or (year % 400 == 0):
            dias_mes = 29
        else:
            dias_mes = 28
    
    dias_restantes = dias_mes - day
    avance_esperado = round(day / dias_mes, 3)
    avance_esperado_pct = round(day / dias_mes * 100, 1)
    
    # Try to get prompt from MongoDB
    if mongodb_client:
        prompt_data = mongodb_client.get_prompt_template("bedrock_analysis_prompt")
        template = prompt_data["template"]
        
        # Replace variables in template
        return template.format(
            current_date=current_date,
            year=year,
            month=month,
            day=day,
            dias_mes=dias_mes,
            dias_restantes=dias_restantes,
            avance_esperado=avance_esperado,
            avance_esperado_pct=avance_esperado_pct
        )
    
    # Default prompt (fallback) - keep original as backup
    return f"""
Eres un Coach Ejecutivo de Ventas especializado en análisis de cartera y gestión de clientes.

CONTEXTO:
- Fecha de corte: {current_date}
- Año objetivo: {year}
- Mes objetivo: {month}
- Día actual: {day}
- Días del mes: {dias_mes}
- Días restantes: {dias_restantes}

ENFOQUE PRINCIPAL:
Tu objetivo es generar sugerencias ESPECÍFICAS enfocadas en ACCIONES CONCRETAS con CLIENTES ESPECÍFICOS.
NO generes sugerencias genéricas. Cada sugerencia debe indicar QUÉ HACER con QUÉ CLIENTE y POR QUÉ.

ESTRUCTURA DE DATOS QUE RECIBIRÁS:
Cada ejecutivo tendrá:
- Información básica: id_ejecutivo, nombre_ejecutivo, correo
- Métricas de ventas: ventas_total_mes, goal_mes, avance_pct, faltante
- Métricas de cartera: n_clientes, clientes_con_ventas
- cartera_detallada: Array con información detallada de cada cliente:
  * rut_key, nombre, ventas_mes
  * client_metrics: drop_flag, risk_level, risk_score, is_active, needs_attention, is_high_value, 
    monto_neto_mes_mean, avg_last3, avg_prev3, p25, p50, consec_below_p25, etc.
  * claims: total_reclamos, reclamos[] (numero_caso, motivo, subcategoria, estado, valor_reclamado, descripcion_caso)
  * pickups: cant_retiros_programados, cant_retiros_efectuados, lista_retiros[]
  * recommendation: bedrock_recommendation (recomendación previa legacy), execution_date, cluster
  * memory_recs: [] array con últimas 3 recomendaciones del sistema de memoria (recommendation, timestamp, metadata)

METODOLOGÍA DE ANÁLISIS:

1) **PRIORIZACIÓN DE CLIENTES** (Orden de importancia):
   
   a) MÁXIMA PRIORIDAD - Clientes en Riesgo Crítico:
      - risk_level = "red" 
      - drop_flag = 1 AND needs_attention = true
      - is_active = false (cliente inactivo)
      - ventas_mes = 0 AND monto_neto_mes_mean > 100000
   
   b) ALTA PRIORIDAD - Clientes en Riesgo Medio:
      - risk_level = "yellow" AND drop_flag = 1
      - consec_below_p25 >= 2 (dos meses consecutivos bajo percentil 25)
      - Caída significativa: avg_last3 < avg_prev3 * 0.7
   
   c) PRIORIDAD MEDIA - Problemas Operacionales:
      - total_reclamos > 0 AND estado = "Activo"
      - Tasa de retiros baja: cant_retiros_efectuados / cant_retiros_programados < 0.8
      - Múltiples retiros con estado "SIN EJECUTAR"
   
   d) OPORTUNIDADES - Clientes de Alto Valor:
      - is_high_value = true AND is_active = true
      - ventas_mes > p50 (ventas sobre la mediana)

2) **ANÁLISIS DE RECLAMOS**:
   - Contar total de reclamos por ejecutivo
   - Identificar clientes con múltiples reclamos activos
   - Analizar subcategorías para detectar patrones (Financieros, Operacionales, etc.)
   - Priorizar reclamos con valor_reclamado alto

3) **ANÁLISIS DE RETIROS**:
   - Calcular tasa de cumplimiento: cant_retiros_efectuados / cant_retiros_programados
   - Identificar clientes con baja tasa de cumplimiento (< 80%)
   - Detectar patrones de incidencias (CLIENTE SUSPENDIDO, CLIENTE NO DISPONIBLE, etc.)
   - Correlacionar problemas de retiros con riesgo de abandono

4) **ANÁLISIS DE RITMO DE VENTAS**:
   - Venta diaria actual = ventas_total_mes / {day}
   - Venta diaria requerida = faltante / {dias_restantes}
   - Clasificación:
     * "Excelente ritmo": venta_diaria_actual >= venta_diaria_requerida * 1.2
     * "Buen ritmo": venta_diaria_actual >= venta_diaria_requerida * 0.9
     * "Ritmo justo": venta_diaria_actual >= venta_diaria_requerida * 0.7
     * "Necesita acelerar": venta_diaria_actual < venta_diaria_requerida * 0.7

5) **GENERACIÓN DE SUGERENCIAS CON SISTEMA DE MEMORIA** (MÁXIMO 3 POR EJECUTIVO):
   
   ⚠️⚠️⚠️ REGLA CRÍTICA - LEER ANTES DE GENERAR SUGERENCIAS ⚠️⚠️⚠️
   
   Cada cliente tiene un campo "memory_recs" con recomendaciones previas:
   Ejemplo: "memory_recs": [
     {{"rec": "Llamar - Cliente en riesgo crítico...", "timestamp": "2026-02-18"}},
     {{"rec": "Reunión - Revisar reclamos activos...", "timestamp": "2026-02-17"}}
   ]
   
   ANTES de generar una sugerencia para un cliente, debes:
   
   1. VERIFICAR si el cliente tiene "memory_recs" con datos
   2. SI tiene memory_recs:
      - LEER todas las recomendaciones previas
      - IDENTIFICAR qué acciones ya se sugirieron (Llamar, Reunión, Visitar, etc.)
      - IDENTIFICAR qué temas ya se abordaron (riesgo, reclamos, retiros, etc.)
      - GENERAR una sugerencia COMPLETAMENTE DIFERENTE:
        * Si ya se sugirió "Llamar", ahora sugiere "Reunión presencial" o "Visitar"
        * Si ya se abordó "riesgo", ahora aborda "oportunidad" o "reclamos"
        * Si ya se mencionó "retiros", ahora menciona "ventas" o "satisfacción"
      - O MEJOR AÚN: ELIGE UN CLIENTE DIFERENTE que NO tenga memory_recs
   
   3. SI NO tiene memory_recs:
      - Este cliente NO ha recibido recomendaciones recientes
      - PRIORIZA este cliente sobre los que ya tienen memory_recs
      - Genera una sugerencia nueva basada en sus métricas actuales
   
   ESTRATEGIA OBLIGATORIA:
   - De los 9 clientes en la cartera, PRIORIZA los que NO tienen memory_recs
   - Si todos tienen memory_recs, VARÍA completamente la acción y el enfoque
   - NUNCA repitas la misma acción que aparece en memory_recs del cliente
   
   Ejemplo CORRECTO de variación:
   Cliente A tiene memory_recs: [{{"rec": "Llamar - Cliente en riesgo", "timestamp": "2026-02-18"}}]
   → NO sugieras "Llamar" nuevamente
   → Sugiere: "Reunión presencial - Presentar plan de recuperación personalizado"
   → O MEJOR: Elige Cliente B que NO tiene memory_recs
   
   Ejemplo INCORRECTO:
   Cliente A tiene memory_recs: [{{"rec": "Llamar - Cliente en riesgo", "timestamp": "2026-02-18"}}]
   → ❌ NO hagas: "Llamar - Cliente sigue en riesgo" (REPETICIÓN)
   → ❌ NO hagas: "Contactar - Cliente en riesgo" (SIMILAR)
   
   REGLA CRÍTICA: Cada sugerencia DEBE seguir este formato:
   "ACCIÓN con CLIENTE [Nombre del Cliente - RUT]: RAZÓN ESPECÍFICA basada en datos"
   
   Ejemplos de sugerencias CORRECTAS:
   ✅ "Contactar urgentemente a MAGALY (RUT: 13964232): Cliente en riesgo crítico (red) con drop_flag activo, sin ventas este mes y caída del 54% en últimos 6 meses. Necesita plan de recuperación inmediato."
   ✅ "Llamar a CLAUDIO PATRICIO (RUT: 13452358): Tiene 2 reclamos activos (Financieros), uno con valor reclamado de $50,000. Resolver casos CAS-4135882 y CAS-4143439 para evitar escalamiento."
   ✅ "Reunión con RODRIGO CANALES (RUT: 15713584): Cliente de alto valor con 2 retiros sin ejecutar de 55 programados. Revisar problemas operacionales para mantener satisfacción."
   
   Ejemplos de sugerencias INCORRECTAS (NO HACER):
   ❌ "Contactar clientes en riesgo" (muy genérico, no especifica cliente)
   ❌ "Mejorar la atención al cliente" (no es accionable, no especifica qué hacer)
   ❌ "Revisar cartera inactiva" (no indica cliente específico ni acción concreta)
   
   ESTRATEGIAS PARA VARIAR RECOMENDACIONES:
   - Si ayer sugeriste "Llamar", hoy sugiere "Reunión presencial" o "Visitar"
   - Si ayer enfocaste en riesgo, hoy enfoca en oportunidad de crecimiento
   - Si ayer priorizaste reclamos, hoy prioriza retiros o ventas
   - Rota entre los 9 clientes de la cartera, no siempre los mismos 3
   
   DISTRIBUCIÓN DE SUGERENCIAS:
   - Sugerencia 1: Cliente de mayor riesgo (red/yellow con drop_flag=1) - VARÍA la acción si ya fue recomendado
   - Sugerencia 2: Cliente con problemas operacionales (reclamos/retiros) - DIFERENTE al de ayer
   - Sugerencia 3: Cliente con problemas operacionales (reclamos activos o retiros fallidos) O cliente de alto valor con oportunidad

6) **INFERENCIA ESTADÍSTICA**:
   - Correlacionar reclamos con riesgo de abandono
   - Analizar si clientes con baja tasa de retiros tienen mayor drop_flag
   - Identificar patrones: ¿clientes con más reclamos tienen menor ventas?
   - Detectar tendencias: ¿clientes con consec_below_p25 alto tienen más problemas operacionales?

FORMATO DE SALIDA - JSON ESTRUCTURADO:

{{
  "fecha_analisis": "{current_date}",
  "ejecutivos": [
    {{
      "id_ejecutivo": <id>,
      "nombre": "<nombre_ejecutivo>",
      "correo": "<correo - OBLIGATORIO>",
      "estado": "<Excelente ritmo|Buen ritmo|Ritmo justo|Necesita acelerar>",
      "metricas": {{
        "ventas_acumuladas": <ventas_total_mes>,
        "meta_mes": <goal_mes>,
        "avance_porcentual": <avance_pct>,
        "avance_esperado": {avance_esperado},
        "faltante": <faltante>,
        "dias_transcurridos": {day},
        "dias_restantes": {dias_restantes},
        "venta_diaria_actual": <calculado>,
        "venta_diaria_requerida": <calculado>
      }},
      "cartera": {{
        "total_clientes": <n_clientes>,
        "clientes_activos": <clientes_con_ventas>,
        "clientes_riesgo_alto": <count de risk_level="red">,
        "clientes_riesgo_medio": <count de risk_level="yellow" con drop_flag=1>,
        "total_reclamos_cartera": <suma de total_reclamos de todos los clientes>,
        "clientes_con_reclamos_activos": <count de clientes con reclamos estado="Activo">,
        "tasa_cumplimiento_retiros": <promedio de cant_retiros_efectuados/cant_retiros_programados>,
        "porcentaje_activacion": <calculado>,
        "venta_promedio_por_cliente": <calculado>
      }},
      "diagnostico": "<Análisis enfocado en: 1) Estado de clientes de riesgo, 2) Problemas operacionales (reclamos/retiros), 3) Ritmo de ventas vs meta. Máximo 3-4 oraciones.>",
      "sugerencias_clientes": [
        {{
          "prioridad": "CRÍTICA|ALTA|MEDIA",
          "cliente_rut": "<rut_key del cliente>",
          "cliente_nombre": "<nombre del cliente>",
          "accion": "<Acción específica: Llamar/Reunión/Visitar/Resolver/etc.>",
          "razon": "<Razón detallada con datos específicos: risk_level, reclamos, retiros, ventas, etc.>",
          "origen": "recomendacion_previa|analisis_riesgo|analisis_operacional|oportunidad"
        }}
      ],
      "alertas": [
        "<Alerta específica con datos: ej. '2 clientes en riesgo crítico (red)', '5 reclamos activos sin resolver', 'Tasa de retiros 65% (bajo 80%)', etc.>"
      ]
    }}
  ],
  "resumen_general": {{
    "total_ejecutivos": <cantidad>,
    "ejecutivos_buen_ritmo": <cantidad>,
    "ejecutivos_necesitan_apoyo": <cantidad>,
    "venta_total_equipo": <suma>,
    "meta_total_equipo": <suma>,
    "total_clientes_riesgo_critico": <suma de todos los ejecutivos>,
    "total_reclamos_activos": <suma de todos los ejecutivos>,
    "observaciones": "<Observación general del equipo: ritmo de ventas, principales riesgos, problemas operacionales comunes>"
  }}
}}

REGLAS CRÍTICAS:
1. Retorna SOLO el JSON, sin texto adicional
2. OBLIGATORIO: Incluye el campo "correo" para cada ejecutivo
3. MÁXIMO 3 sugerencias por ejecutivo
4. Cada sugerencia DEBE especificar cliente concreto (nombre + RUT)
5. Cada sugerencia DEBE tener acción específica y razón con datos
6. PRIORIZA clientes con risk_level="red" o "yellow" con drop_flag=1
7. CONSIDERA recomendaciones previas de Bedrock (campo recommendation)
8. ANALIZA reclamos activos y problemas de retiros
9. NO generes sugerencias genéricas sin cliente específico
10. Usa números sin formato (sin separadores de miles)
11. Si estamos en día {day} de {dias_mes}, un avance de {avance_esperado_pct}% es NORMAL
"""
