"""
Dynamic query configuration and prompts for sales analysis.

Nueva estructura adaptada a:
- clientes_por_ejecutivo con rut_ejecutivo y cartera_clientes[]
- Límite de 20 clientes por ejecutivo (ordenados por relevancia)
- Clientes activos primero (is_active_last_month: true)
"""

from datetime import datetime
from typing import List, Dict, Any, Optional
from app.clients.mongodb_client import MongoDBClient


def parse_date(date_str: str) -> tuple:
    """Parse date string and extract year, month, day components."""
    date_obj = datetime.strptime(date_str, "%Y-%m-%d")
    return date_obj.year, date_obj.month, date_obj.day


def get_queries(current_date: str) -> List[Dict[str, Any]]:
    """
    Generate MongoDB aggregation pipeline for new structure.
    
    Nueva estructura:
    {
        "rut_ejecutivo": "177496030",
        "cartera_clientes": [
            {"rut_cliente": "65091146", "is_active_last_month": true}
        ],
        "correo": "ejemplo@correo.com",
        "rut_jefatura": "14228821"
    }
    
    Cambios clave:
    - Limita a 20 clientes por ejecutivo (ya vienen ordenados por relevancia)
    - Clientes activos primero (is_active_last_month: true)
    - Usa rut_ejecutivo en lugar de id_ejecutivo
    """
    year, month, day = parse_date(current_date)
    
    return [
        {
            "name": "ventas_por_ejecutivo_enriquecido",
            "collection": "clientes_por_ejecutivo",
            "pipeline": [
                # Limitar cartera a primeros 20 clientes (ya vienen ordenados)
                {
                    "$addFields": {
                        "cartera_clientes_limitada": {"$slice": ["$cartera_clientes", 20]}
                    }
                },
                
                # Unwind para procesar cada cliente individualmente
                {"$unwind": "$cartera_clientes_limitada"},
                
                # Extraer rut_cliente
                {
                    "$addFields": {
                        "rut_cliente_str": {"$toString": "$cartera_clientes_limitada.rut_cliente"},
                        "is_active_last_month": "$cartera_clientes_limitada.is_active_last_month"
                    }
                },
                
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
                
                # Lookup 2: Client data (métricas de riesgo)
                {
                    "$lookup": {
                        "from": "clients_data",
                        "let": {"rut": "$rut_cliente_str"},
                        "pipeline": [
                            {
                                "$match": {
                                    "$expr": {
                                        "$or": [
                                            {"$eq": [{"$toString": "$rut_key"}, "$$rut"]},
                                            {"$eq": ["$rut_key", "$$rut"]}
                                        ]
                                    }
                                }
                            },
                            {
                                "$project": {
                                    "_id": 0,
                                    "nombre": 1,
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
                
                # Lookup 3: Claims data (solo resumen)
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
                                    "reclamos_pendientes": {
                                        "$size": {
                                            "$filter": {
                                                "input": {"$ifNull": ["$reclamos", []]},
                                                "as": "reclamo",
                                                "cond": {
                                                    "$in": [
                                                        "$$reclamo.Estado",
                                                        ["Abierto", "En Proceso", "Pendiente", "Nuevo"]
                                                    ]
                                                }
                                            }
                                        }
                                    },
                                    "valor_total_reclamado": {
                                        "$sum": {
                                            "$map": {
                                                "input": {"$ifNull": ["$reclamos", []]},
                                                "as": "reclamo",
                                                "in": {"$ifNull": ["$$reclamo.Valor_Reclamado", 0]}
                                            }
                                        }
                                    }
                                }
                            }
                        ],
                        "as": "claims_data"
                    }
                },
                
                # Lookup 4: Pickup/retiros data (solo resumen)
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
                                    "tasa_cumplimiento": {
                                        "$cond": [
                                            {"$gt": ["$cant_retiros_programados", 0]},
                                            {
                                                "$divide": [
                                                    "$cant_retiros_efectuados",
                                                    "$cant_retiros_programados"
                                                ]
                                            },
                                            None
                                        ]
                                    }
                                }
                            }
                        ],
                        "as": "pickup_data"
                    }
                },
                
                # Lookup 5: Memory embeddings (últimas 3 recomendaciones)
                {
                    "$lookup": {
                        "from": "memory_embeddings",
                        "let": {
                            "exec_rut": "$rut_ejecutivo",
                            "client_rut": "$rut_cliente_str"
                        },
                        "pipeline": [
                            {
                                "$match": {
                                    "$expr": {
                                        "$and": [
                                            {"$eq": ["$executive_id", "$$exec_rut"]},
                                            {"$eq": ["$client_id", "$$client_rut"]}
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
                
                # Consolidar información del cliente
                {
                    "$addFields": {
                        "ventas_cliente": {"$ifNull": [{"$first": "$sales.ventas_cliente"}, 0]},
                        "cliente_detalle": {
                            "rut_key": "$rut_cliente_str",
                            "nombre": {"$ifNull": [{"$first": "$client_data.nombre"}, ""]},
                            "ventas_mes": {"$ifNull": [{"$first": "$sales.ventas_cliente"}, 0]},
                            "is_active_last_month": "$is_active_last_month",
                            "client_metrics": {"$first": "$client_data"},
                            "claims": {"$first": "$claims_data"},
                            "pickups": {"$first": "$pickup_data"},
                            "memory_recs": "$memory_recommendations"
                        }
                    }
                },
                
                # Agrupar por ejecutivo
                {
                    "$group": {
                        "_id": {
                            "rut_ejecutivo": "$rut_ejecutivo",
                            "correo": "$correo",
                            "test_correo": "$test_correo",
                            "rut_jefatura": "$rut_jefatura"
                        },
                        "ventas_total_mes": {"$sum": "$ventas_cliente"},
                        "clientes_con_ventas": {
                            "$sum": {"$cond": [{"$gt": ["$ventas_cliente", 0]}, 1, 0]}
                        },
                        "clientes_activos_mes": {
                            "$sum": {"$cond": [{"$eq": ["$is_active_last_month", True]}, 1, 0]}
                        },
                        "clientes_unicos": {"$addToSet": "$rut_cliente_str"},
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
                
                # Lookup: Sales goal (por rut_ejecutivo)
                {
                    "$lookup": {
                        "from": "sales_goal",
                        "localField": "_id.rut_ejecutivo",
                        "foreignField": "rut_ejecutivo",
                        "as": "goal"
                    }
                },
                {"$addFields": {"goal_doc": {"$first": "$goal"}}},
                
                # Calcular metas y avance
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
                        "rut_ejecutivo": "$_id.rut_ejecutivo",
                        "nombre_ejecutivo": "$goal_doc.nombre_ejecutivo",
                        "correo": "$_id.correo",
                        "test_correo": "$_id.test_correo",
                        "rut_jefatura": "$_id.rut_jefatura",
                        "agno": 1,
                        "mes": 1,
                        "ventas_total_mes": 1,
                        "goal_mes": 1,
                        "goal_year": 1,
                        "avance_pct": 1,
                        "faltante": 1,
                        "n_clientes": 1,
                        "clientes_con_ventas": 1,
                        "clientes_activos_mes": 1,
                        "cartera_detallada": 1
                    }
                },
                {"$sort": {"avance_pct": -1, "ventas_total_mes": -1}}
            ]
        }
    ]


def get_analysis_prompt(current_date: str, mongodb_client: Optional[MongoDBClient] = None) -> str:
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
    
    dias_restantes = dias_mes - day
    avance_esperado = round(day / dias_mes, 3)
    avance_esperado_pct = round(day / dias_mes * 100, 1)
    
    # Try to get prompt from MongoDB
    if mongodb_client:
        try:
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
        except Exception as e:
            print(f"Warning: Could not fetch prompt from MongoDB: {e}")
            # Fall through to default prompt
    
    # Default prompt (fallback)
    return f"""
Eres un Coach Ejecutivo de Ventas especializado en análisis de cartera y gestión de clientes.

CONTEXTO:
- Fecha de corte: {current_date}
- Año: {year}, Mes: {month}, Día: {day}
- Días del mes: {dias_mes}, Días restantes: {dias_restantes}
- Avance esperado: {avance_esperado_pct}%

IMPORTANTE - LENGUAJE CLARO Y ACCESIBLE:
Usa términos que un ejecutivo comercial pueda entender fácilmente. Evita jerga técnica.
En lugar de "drop_flag", di "riesgo de pérdida del cliente".
En lugar de "consec_below_p25", di "ventas consistentemente bajas".

ESTRUCTURA DE DATOS:
Cada ejecutivo tiene máximo 20 clientes (los más relevantes, ordenados por importancia):
- Clientes ACTIVOS primero (is_active_last_month: true) - compraron el mes pasado
- Luego clientes INACTIVOS - no compraron el mes pasado
- Información: rut, nombre, ventas_mes, métricas de riesgo
- claims: resumen de reclamos (total_reclamos, reclamos_pendientes, valor_total_reclamado)
- pickups: resumen de retiros (cant_retiros_programados, cant_retiros_efectuados, tasa_cumplimiento)
- memory_recs: últimas 3 recomendaciones previas (para evitar repetir)

CRITERIOS DE PRIORIDAD Y ACCIONES:

1) **RIESGO CRÍTICO** → VISITA PRESENCIAL (urgente, cara a cara)
   Cuándo: Cliente de alto valor + alta probabilidad de pérdida
   - Ventas históricas altas (monto_neto_mes_mean > $500,000) Y
   - Caída drástica reciente (avg_last3 < avg_prev3 * 0.5) O
   - Inactivo el mes pasado (is_active_last_month: false) Y era activo antes O
   - Múltiples reclamos pendientes (reclamos_pendientes >= 2) con valor alto
   
   Ejemplo: "Visitar a EMPRESA XYZ (RUT: 12345678): Cliente clave con ventas históricas de $800K mensuales, 
   pero sin compras este mes y 3 reclamos pendientes por $150K. Riesgo inminente de pérdida."

2) **RIESGO ALTO** → REUNIÓN (urgente, pero puede ser virtual)
   Cuándo: Cliente importante con señales de alerta
   - Ventas moderadas-altas (monto_neto_mes_mean > $200,000) Y
   - Ventas bajo lo normal (ventas_mes < p25) por 2+ meses consecutivos O
   - Problemas operacionales: tasa_cumplimiento < 0.7 O
   - 1-2 reclamos pendientes
   
   Ejemplo: "Reunión con EMPRESA ABC (RUT: 87654321): Ventas de $300K mensuales, pero últimos 2 meses 
   bajo $100K. Tiene 2 reclamos pendientes. Necesita atención para evitar deterioro."

3) **RIESGO MEDIO** → LLAMADA (seguimiento, menos urgente)
   Cuándo: Cliente con señales tempranas de alerta
   - Ventas bajas-moderadas (monto_neto_mes_mean < $200,000) Y
   - Ligera caída en ventas (avg_last3 < avg_prev3 * 0.8) O
   - 1 reclamo pendiente O
   - Problemas menores de retiros (tasa_cumplimiento 0.7-0.85)
   
   Ejemplo: "Llamar a EMPRESA DEF (RUT: 11223344): Ventas de $150K mensuales, bajaron a $100K. 
   Tiene 1 reclamo pendiente. Llamada para entender situación y ofrecer soluciones."

4) **OPORTUNIDAD GRANDE** → VISITA PRESENCIAL (capitalizar crecimiento)
   Cuándo: Cliente con potencial significativo
   - Crecimiento exponencial (avg_last3 > avg_prev3 * 1.5) Y
   - Ventas altas o en aumento (ventas_mes > $300,000) O
   - Cliente nuevo con primeras compras grandes
   
   Ejemplo: "Visitar a EMPRESA GHI (RUT: 99887766): Ventas crecieron de $200K a $450K en 3 meses. 
   Oportunidad de fortalecer relación y aumentar participación."

5) **OPORTUNIDAD MEDIA** → LLAMADA (explorar potencial)
   Cuándo: Cliente con señales positivas pero menor impacto
   - Crecimiento moderado (avg_last3 > avg_prev3 * 1.2) Y
   - Ventas bajas-moderadas (< $200,000) O
   - Cliente reactivo después de inactividad
   
   Ejemplo: "Llamar a EMPRESA JKL (RUT: 55443322): Ventas de $80K, subieron a $120K. 
   Llamada para explorar necesidades y ofrecer productos adicionales."

SISTEMA DE MEMORIA - EVITAR REPETICIONES:
Cada cliente tiene "memory_recs" con últimas 3 recomendaciones:
- SI tiene memory_recs: VARÍA completamente la acción y enfoque
  * Ya se sugirió "Llamar" → Ahora sugiere "Reunión" o "Visitar"
  * Ya se abordó "riesgo" → Ahora aborda "oportunidad" o "reclamos"
- SI NO tiene memory_recs: PRIORIZA este cliente (no ha sido contactado recientemente)

SUGERENCIAS POR EJECUTIVO (según clientes disponibles):
- Si el ejecutivo tiene 3 o más clientes: genera EXACTAMENTE 3 sugerencias
- Si el ejecutivo tiene 2 clientes: genera EXACTAMENTE 2 sugerencias
- Si el ejecutivo tiene 1 cliente: genera EXACTAMENTE 1 sugerencia
- Prioriza clientes SIN memory_recs (no contactados recientemente)
- Distribuye: al menos 1 riesgo/problema + al menos 1 oportunidad/seguimiento (si hay suficientes clientes)
- Si no hay suficientes riesgos, incluye oportunidades de crecimiento o seguimiento preventivo
- Cada sugerencia debe ser de un cliente DIFERENTE (no repetir clientes)
- Cada sugerencia: "ACCIÓN con CLIENTE [Nombre - RUT]: RAZÓN con datos específicos"

FORMATO DE SALIDA JSON:
{{
  "fecha_analisis": "{current_date}",
  "ejecutivos": [
    {{
      "rut_ejecutivo": "<rut>",
      "nombre": "<nombre>",
      "correo": "<correo>",
      "estado": "<Excelente ritmo|Buen ritmo|Ritmo justo|Necesita acelerar>",
      "metricas": {{
        "ventas_acumuladas": <float>,
        "meta_mes": <float>,
        "avance_porcentual": <float>,
        "avance_esperado": {avance_esperado},
        "faltante": <float>,
        "dias_transcurridos": {day},
        "dias_restantes": {dias_restantes},
        "venta_diaria_actual": <calculado>,
        "venta_diaria_requerida": <calculado>
      }},
      "cartera": {{
        "total_clientes": <int>,
        "clientes_activos_mes": <int>,
        "clientes_con_ventas": <int>,
        "clientes_riesgo_critico": <count>,
        "clientes_riesgo_alto": <count>,
        "total_reclamos_cartera": <int>,
        "clientes_con_reclamos_activos": <int>,
        "tasa_cumplimiento_retiros": <float>,
        "porcentaje_activacion": <float>
      }},
      "diagnostico": "<Máximo 2 oraciones concisas sobre estado de clientes y ritmo de ventas>",
      "sugerencias_clientes": [
        {{
          "prioridad": "CRÍTICA|ALTA|MEDIA",
          "cliente_rut": "<rut>",
          "cliente_nombre": "<nombre>",
          "accion": "Visitar|Reunión|Llamar",
          "razon": "<Razón concisa con datos clave: ventas, reclamos, retiros o tendencias. Máximo 1 oración>",
          "origen": "riesgo_critico|riesgo_alto|riesgo_medio|oportunidad|problema_operacional"
        }}
      ],
      "alertas": [
        "<Alertas específicas concisas. Máximo 2 alertas por ejecutivo>"
      ]
    }}
  ]
}}

REGLAS FINALES:
1. Retorna SOLO JSON, sin texto adicional
2. Usa lenguaje claro, evita términos técnicos
3. Acciones coherentes con urgencia y tamaño del cliente
4. Prioriza clientes sin memory_recs
5. Número de sugerencias según clientes disponibles: 3+ clientes = 3 sugerencias, 2 clientes = 2 sugerencias, 1 cliente = 1 sugerencia
6. Cada sugerencia con cliente específico (nombre + RUT) y todos los clientes deben ser DIFERENTES
7. Números sin formato (sin separadores de miles)
8. SÉ CONCISO: diagnóstico máximo 2 oraciones, razones máximo 1 oración, máximo 2 alertas
"""
