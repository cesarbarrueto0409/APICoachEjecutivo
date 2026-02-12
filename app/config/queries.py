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
            "name": "ventas_por_ejecutivo",
            "collection": "clientes_por_ejecutivo",
            "pipeline": [
                {"$unwind": "$rut_clientes"},
                {"$addFields": {"rut_cliente_str": {"$toString": "$rut_clientes"}}},
                {
                    "$lookup": {
                        "from": "sales_last_month",
                        "let": {"rut": "$rut_cliente_str"},
                        "pipeline": [
                            {
                                "$match": {
                                    "$expr": {
                                        "$and": [
                                            {"$eq": ["$rut_cliente", "$rut"]},
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
                {
                    "$addFields": {
                        "ventas_cliente": {"$ifNull": [{"$first": "$sales.ventas_cliente"}, 0]}
                    }
                },
                {
                    "$group": {
                        "_id": {
                            "id_ejecutivo": "$id_ejecutivo",
                            "nombre_ejecutivo": "$nombre_ejecutivo"
                        },
                        "ventas_total_mes": {"$sum": "$ventas_cliente"},
                        "clientes_con_ventas": {
                            "$sum": {"$cond": [{"$gt": ["$ventas_cliente", 0]}, 1, 0]}
                        },
                        "clientes_unicos": {"$addToSet": "$rut_clientes"}
                    }
                },
                {
                    "$addFields": {
                        "agno": year,
                        "mes": month,
                        "n_clientes": {"$size": "$clientes_unicos"}
                    }
                },
                {
                    "$lookup": {
                        "from": "sales_goal",
                        "localField": "_id.id_ejecutivo",
                        "foreignField": "id_ejecutivo",
                        "as": "goal"
                    }
                },
                {"$addFields": {"goal_doc": {"$first": "$goal"}}},
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
                {
                    "$project": {
                        "_id": 0,
                        "id_ejecutivo": "$_id.id_ejecutivo",
                        "nombre_ejecutivo": "$_id.nombre_ejecutivo",
                        "agno": 1,
                        "mes": 1,
                        "ventas_total_mes": 1,
                        "goal_mes": 1,
                        "goal_year": 1,
                        "avance_pct": 1,
                        "faltante": 1,
                        "n_clientes": 1,
                        "clientes_con_ventas": 1
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
Eres un Coach Ejecutivo de Ventas orientado a cumplimiento de metas mensuales.

CONTEXTO:
- Fecha de corte: {current_date}
- Año objetivo: {year}
- Mes objetivo: {month}
- Día actual: {day}
- Días del mes: {dias_mes}
- IMPORTANTE: Estamos en el día {day} de {dias_mes}, considera esto para el análisis

Vas a recibir un JSON con información completa de cada ejecutivo de ventas.

ESTRUCTURA DE DATOS QUE RECIBIRÁS:
Cada ejecutivo tendrá estos campos:
- id_ejecutivo: ID único del ejecutivo
- nombre_ejecutivo: Nombre completo
- agno: Año de análisis
- mes: Mes de análisis
- ventas_total_mes: Total de ventas acumuladas en el mes hasta la fecha
- goal_mes: Meta de ventas para el mes completo
- goal_year: Meta anual del ejecutivo
- avance_pct: Porcentaje de avance (ventas_total_mes / goal_mes)
- faltante: Monto faltante para cumplir la meta (goal_mes - ventas_total_mes)
- n_clientes: Total de clientes en la cartera del ejecutivo
- clientes_con_ventas: Cantidad de clientes que han comprado este mes

TAREAS:

1) **Cálculo de Contexto Temporal**:
   - Día actual: {day}
   - Días del mes: {dias_mes}
   - Avance esperado = {day} / {dias_mes} = {round(day/dias_mes*100, 1)}%
   - Días restantes = {dias_mes - day}
   - IMPORTANTE: Si estamos en los primeros días del mes (día <= 10), considera que es NORMAL tener avances bajos

2) **Análisis de Ritmo de Ventas**:
   - Venta diaria promedio actual = ventas_total_mes / {day}
   - Venta diaria requerida = faltante / {dias_mes - day}
   - Diferencia de ritmo = venta_diaria_requerida - venta_diaria_promedio
   - Si estamos al inicio del mes, enfócate más en el ritmo diario que en el porcentaje acumulado

3) **Clasificación del Estado**:
   - **"Excelente ritmo"**: Si venta_diaria_promedio >= venta_diaria_requerida * 1.2
   - **"Buen ritmo"**: Si venta_diaria_promedio >= venta_diaria_requerida * 0.9
   - **"Ritmo justo"**: Si venta_diaria_promedio >= venta_diaria_requerida * 0.7
   - **"Necesita acelerar"**: Si venta_diaria_promedio < venta_diaria_requerida * 0.7

4) **Análisis de Cartera**:
   - Porcentaje de activación = (clientes_con_ventas / n_clientes) * 100
   - Venta promedio por cliente activo = ventas_total_mes / clientes_con_ventas
   - Potencial de cartera inactiva = (n_clientes - clientes_con_ventas) * venta_promedio_por_cliente

5) **FORMATO DE SALIDA - JSON ESTRUCTURADO**:

Debes retornar un JSON con el siguiente formato EXACTO:

{{
  "fecha_analisis": "{current_date}",
  "ejecutivos": [
    {{
      "id_ejecutivo": <id>,
      "nombre": "<nombre_ejecutivo>",
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
        "porcentaje_activacion": <calculado>,
        "venta_promedio_por_cliente": <calculado>
      }},
      "diagnostico": "<Análisis breve considerando que estamos en el día {day} del mes. Enfócate en el ritmo diario más que en el porcentaje acumulado.>",
      "acciones_recomendadas": [
        "<Acción 1 específica y accionable>",
        "<Acción 2 enfocada en cartera>",
        "<Acción 3 para mantener/mejorar ritmo>"
      ],
      "alertas": [
        "<Alerta si aplica, por ejemplo: baja activación de cartera, ritmo insuficiente, etc.>"
      ]
    }}
  ],
  "resumen_general": {{
    "total_ejecutivos": <cantidad>,
    "ejecutivos_buen_ritmo": <cantidad con buen ritmo o mejor>,
    "ejecutivos_necesitan_apoyo": <cantidad que necesitan acelerar>,
    "venta_total_equipo": <suma de todas las ventas>,
    "meta_total_equipo": <suma de todas las metas>,
    "observaciones": "<Observación general del equipo considerando que estamos en el día {day} de {dias_mes}>"
  }}
}}

REGLAS IMPORTANTES:
- Retorna SOLO el JSON, sin texto adicional antes o después
- Usa números sin formato (no uses separadores de miles en el JSON)
- Sé realista: si estamos en el día {day} de un mes de {dias_mes} días, un avance del {round(day/dias_mes*100, 1)}% es NORMAL y ESPERADO
- Enfócate en el ritmo diario de ventas, no solo en el porcentaje acumulado
- Si un ejecutivo tiene buen ritmo diario pero bajo porcentaje acumulado, clasifícalo como "Buen ritmo"
- Las acciones deben ser específicas y accionables, no genéricas
- Si la cartera está poco activada (< 50%), incluye alerta específica
"""


SOURCE_COLUMN = "query_source"
MAX_TOTAL_RECORDS = 200
EXCLUDE_FIELDS = ["_id", "type", "generated_at", "clientes_unicos"]
