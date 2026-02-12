"""Configuración de consultas dinámicas y prompts para el análisis."""

from datetime import datetime
from typing import List, Dict, Any


def parse_date(date_str: str) -> tuple:
    """Parse date string and extract year, month, day."""
    date_obj = datetime.strptime(date_str, "%Y-%m-%d")
    return date_obj.year, date_obj.month, date_obj.day


def get_queries(current_date: str) -> List[Dict[str, Any]]:
    """Generate queries based on current date."""
    year, month, day = parse_date(current_date)
    
    return [
        {
            "name": "ventas_por_ejecutivo_enriquecido",
            "collection": "clientes_por_ejecutivo",
            "pipeline": [
                # Unwind para procesar cada cliente individualmente
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
                
                # Consolidar toda la información del cliente
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
                            "recommendation": {"$first": "$recommendation_data"}
                        }
                    }
                },
                
                # Agrupar por ejecutivo con toda la información de clientes
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
                
                # Agregar métricas del ejecutivo
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
                
                # Calcular metas y avances
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
                
                # Proyección final
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


def get_analysis_prompt(current_date: str) -> str:
    """Generate analysis prompt based on current date."""
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
    
    return f"""
Eres un Coach Ejecutivo de Ventas especializado en análisis de cartera y gestión de clientes.

CONTEXTO:
- Fecha de corte: {current_date}
- Año objetivo: {year}
- Mes objetivo: {month}
- Día actual: {day}
- Días del mes: {dias_mes}
- Días restantes: {dias_mes - day}

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
  * recommendation: bedrock_recommendation (recomendación previa), execution_date, cluster

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
   - Venta diaria requerida = faltante / {dias_mes - day}
   - Clasificación:
     * "Excelente ritmo": venta_diaria_actual >= venta_diaria_requerida * 1.2
     * "Buen ritmo": venta_diaria_actual >= venta_diaria_requerida * 0.9
     * "Ritmo justo": venta_diaria_actual >= venta_diaria_requerida * 0.7
     * "Necesita acelerar": venta_diaria_actual < venta_diaria_requerida * 0.7

5) **GENERACIÓN DE SUGERENCIAS** (MÁXIMO 3 POR EJECUTIVO):
   
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
   
   DISTRIBUCIÓN DE SUGERENCIAS:
   - Sugerencia 1: Priorizar recomendación previa de Bedrock (si existe y es relevante)
   - Sugerencia 2: Cliente de mayor riesgo (red/yellow con drop_flag=1)
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
        "avance_esperado": {round(day/dias_mes, 3)},
        "faltante": <faltante>,
        "dias_transcurridos": {day},
        "dias_restantes": {dias_mes - day},
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
11. Si estamos en día {day} de {dias_mes}, un avance de {round(day/dias_mes*100, 1)}% es NORMAL
"""
