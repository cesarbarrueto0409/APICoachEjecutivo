"""Email notification service for sending analysis results to ejecutivos."""

from typing import Dict, Any, List
import logging
from app.clients.email_client import IEmailClient


class EmailNotificationService:
    """Service for sending email notifications after analysis."""
    
    def __init__(self, email_client: IEmailClient):
        """
        Initialize notification service.
        
        Args:
            email_client: Implementation of IEmailClient
            
        Raises:
            ValueError: If email_client is None
        """
        if email_client is None:
            raise ValueError("email_client cannot be None")
            
        self._email_client = email_client
        self._logger = logging.getLogger(__name__)
    
    def send_analysis_notifications(
        self,
        analysis_result: Dict[str, Any],
        current_date: str
    ) -> Dict[str, Any]:
        """
        Send email notifications to all ejecutivos in analysis result.
        
        Args:
            analysis_result: Result from analysis service
            current_date: Current date for context
            
        Returns:
            Dict with keys:
                - total_sent: int
                - total_failed: int
                - notifications: List[Dict] with details of each email
        """
        notifications = []
        sent_count = 0
        failed_count = 0
        
        # Extract ejecutivos from analysis
        data = analysis_result.get("data", {})
        ejecutivos = data.get("ejecutivos", [])
        
        if not ejecutivos:
            self._logger.warning("No ejecutivos found in analysis result")
            return {
                "total_sent": 0,
                "total_failed": 0,
                "notifications": []
            }
        
        # Send email to each ejecutivo
        for ejecutivo in ejecutivos:
            try:
                # Extract ejecutivo data
                correo = ejecutivo.get("correo")
                nombre = ejecutivo.get("nombre", "Ejecutivo")
                
                if not correo:
                    self._logger.warning(
                        f"No email found for ejecutivo: {nombre}"
                    )
                    notifications.append({
                        "ejecutivo": nombre,
                        "recipient": None,
                        "subject": None,
                        "status": "failed",
                        "error": "No email address found"
                    })
                    failed_count += 1
                    continue
                
                # Format email
                subject = f"Reporte diario Coach Ejecutivo ({nombre})"
                html_content = self._format_email_html(ejecutivo, current_date)
                
                # Send email
                result = self._email_client.send_email(
                    to_email=correo,
                    subject=subject,
                    html_content=html_content
                )
                
                # Record result
                notification = {
                    "ejecutivo": nombre,
                    "recipient": result.get("recipient"),
                    "original_recipient": result.get("original_recipient"),
                    "subject": subject,
                    "body": html_content,
                    "status": "success" if result["success"] else "failed",
                    "status_code": result.get("status_code"),
                    "error": None if result["success"] else result.get("message")
                }
                
                notifications.append(notification)
                
                if result["success"]:
                    sent_count += 1
                else:
                    failed_count += 1
                    
            except Exception as e:
                self._logger.error(
                    f"Unexpected error sending email to {nombre}: {str(e)}"
                )
                notifications.append({
                    "ejecutivo": nombre,
                    "recipient": correo if 'correo' in locals() else None,
                    "subject": None,
                    "status": "failed",
                    "error": str(e)
                })
                failed_count += 1
        
        return {
            "total_sent": sent_count,
            "total_failed": failed_count,
            "notifications": notifications
        }
    
    def _format_email_html(
        self,
        ejecutivo: Dict[str, Any],
        current_date: str
    ) -> str:
        """
        Format ejecutivo data into HTML email content.
        
        Args:
            ejecutivo: Dictionary with ejecutivo data
            current_date: Current date string
            
        Returns:
            HTML formatted email content
        """
        # Extract data
        nombre = ejecutivo.get("nombre", "Ejecutivo")
        estado = ejecutivo.get("estado", "N/A")
        metricas = ejecutivo.get("metricas", {})
        cartera = ejecutivo.get("cartera", {})
        diagnostico = ejecutivo.get("diagnostico", "")
        sugerencias = ejecutivo.get("sugerencias_clientes", [])
        alertas = ejecutivo.get("alertas", [])
        
        # Format numbers
        ventas = metricas.get("ventas_acumuladas", 0)
        meta = metricas.get("meta_mes", 0)
        faltante = metricas.get("faltante", 0)
        avance_pct = metricas.get("avance_porcentual", 0)
        avance_esperado = metricas.get("avance_esperado", 0)
        venta_diaria_actual = metricas.get("venta_diaria_actual", 0)
        venta_diaria_requerida = metricas.get("venta_diaria_requerida", 0)
        dias_restantes = metricas.get("dias_restantes", 0)
        
        # Cartera metrics
        total_clientes = cartera.get("total_clientes", 0)
        clientes_activos = cartera.get("clientes_activos", 0)
        clientes_riesgo_alto = cartera.get("clientes_riesgo_alto", 0)
        clientes_riesgo_medio = cartera.get("clientes_riesgo_medio", 0)
        total_reclamos = cartera.get("total_reclamos_cartera", 0)
        reclamos_activos = cartera.get("clientes_con_reclamos_activos", 0)
        tasa_retiros = cartera.get("tasa_cumplimiento_retiros", 0)
        porcentaje_activacion = cartera.get("porcentaje_activacion", 0)
        
        # Determine status color and emoji
        if "Excelente" in estado:
            status_color = "#28a745"
            status_emoji = "🟢"
        elif "Buen" in estado:
            status_color = "#17a2b8"
            status_emoji = "🔵"
        elif "justo" in estado:
            status_color = "#ffc107"
            status_emoji = "🟡"
        else:
            status_color = "#dc3545"
            status_emoji = "🔴"
        
        # Build HTML with modern design
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <style>
                body {{ 
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
                    line-height: 1.6; 
                    color: #333; 
                    background-color: #f5f7fa;
                    margin: 0;
                    padding: 0;
                }}
                .container {{ 
                    max-width: 650px; 
                    margin: 20px auto; 
                    background-color: #ffffff;
                    border-radius: 12px;
                    box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
                    overflow: hidden;
                }}
                .header {{ 
                    background: linear-gradient(135deg, #003d7a 0%, #0056b3 100%);
                    color: white !important; 
                    padding: 30px 20px; 
                    text-align: center; 
                }}
                .header h1 {{ 
                    margin: 0 0 10px 0; 
                    font-size: 28px; 
                    font-weight: 600;
                    color: white !important;
                }}
                .header p {{ 
                    margin: 5px 0; 
                    font-size: 16px; 
                    opacity: 0.95;
                    color: white !important;
                }}
                .status-badge {{ 
                    background-color: {status_color}; 
                    color: white; 
                    padding: 15px 20px; 
                    margin: 0;
                    text-align: center; 
                    font-size: 20px; 
                    font-weight: 600;
                    border-bottom: 4px solid rgba(0,0,0,0.1);
                }}
                .content {{ 
                    padding: 30px 25px; 
                }}
                .section {{ 
                    margin-bottom: 30px; 
                }}
                .section-title {{ 
                    font-size: 20px; 
                    font-weight: 600; 
                    color: #003d7a !important; 
                    margin-bottom: 15px;
                    padding-bottom: 8px;
                    border-bottom: 2px solid #e9ecef;
                }}
                .metrics-grid {{ 
                    display: grid;
                    grid-template-columns: 1fr 1fr;
                    gap: 15px;
                    margin-bottom: 20px;
                }}
                .metric-card {{ 
                    background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
                    padding: 15px; 
                    border-radius: 8px;
                    border-left: 4px solid #003d7a;
                }}
                .metric-label {{ 
                    font-size: 12px; 
                    color: #6c757d; 
                    text-transform: uppercase; 
                    font-weight: 600;
                    margin-bottom: 5px;
                }}
                .metric-value {{ 
                    font-size: 22px; 
                    font-weight: 700; 
                    color: #003d7a;
                }}
                .metric-value.small {{ 
                    font-size: 18px; 
                }}
                .progress-bar-container {{ 
                    background-color: #e9ecef; 
                    height: 30px; 
                    border-radius: 15px; 
                    overflow: hidden;
                    margin: 15px 0;
                    position: relative;
                }}
                .progress-bar {{ 
                    background: linear-gradient(90deg, #28a745 0%, #20c997 100%);
                    height: 100%; 
                    border-radius: 15px;
                    transition: width 0.3s ease;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    color: white;
                    font-weight: 600;
                    font-size: 14px;
                }}
                .progress-bar.warning {{ 
                    background: linear-gradient(90deg, #ffc107 0%, #ffb300 100%);
                }}
                .progress-bar.danger {{ 
                    background: linear-gradient(90deg, #dc3545 0%, #c82333 100%);
                }}
                .diagnostico-box {{ 
                    background-color: #f8f9fa; 
                    padding: 20px; 
                    border-radius: 8px;
                    border-left: 4px solid #17a2b8;
                    font-size: 15px;
                    line-height: 1.7;
                }}
                .sugerencia-card {{ 
                    background-color: #ffffff; 
                    border: 2px solid #e9ecef;
                    border-radius: 8px; 
                    padding: 18px; 
                    margin-bottom: 15px;
                    transition: transform 0.2s, box-shadow 0.2s;
                }}
                .sugerencia-card:hover {{ 
                    transform: translateY(-2px);
                    box-shadow: 0 4px 12px rgba(0,0,0,0.1);
                }}
                .sugerencia-card.critica {{ 
                    border-left: 5px solid #dc3545;
                    background: linear-gradient(to right, #fff5f5 0%, #ffffff 100%);
                }}
                .sugerencia-card.alta {{ 
                    border-left: 5px solid #ff8c00;
                    background: linear-gradient(to right, #fff8f0 0%, #ffffff 100%);
                }}
                .sugerencia-card.media {{ 
                    border-left: 5px solid #ffc107;
                    background: linear-gradient(to right, #fffbf0 0%, #ffffff 100%);
                }}
                .sugerencia-header {{ 
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                    margin-bottom: 12px;
                }}
                .sugerencia-prioridad {{ 
                    font-size: 11px; 
                    font-weight: 700; 
                    padding: 4px 10px; 
                    border-radius: 12px;
                    text-transform: uppercase;
                    letter-spacing: 0.5px;
                }}
                .sugerencia-prioridad.critica {{ 
                    background-color: #dc3545; 
                    color: white; 
                }}
                .sugerencia-prioridad.alta {{ 
                    background-color: #ff8c00; 
                    color: white; 
                }}
                .sugerencia-prioridad.media {{ 
                    background-color: #ffc107; 
                    color: #000; 
                }}
                .sugerencia-cliente {{ 
                    font-size: 18px; 
                    font-weight: 600; 
                    color: #003d7a;
                    margin-bottom: 8px;
                }}
                .sugerencia-rut {{ 
                    font-size: 13px; 
                    color: #6c757d;
                    margin-bottom: 10px;
                }}
                .sugerencia-accion {{ 
                    font-size: 15px; 
                    font-weight: 600; 
                    color: #0056b3;
                    margin-bottom: 8px;
                }}
                .sugerencia-razon {{ 
                    font-size: 14px; 
                    color: #495057;
                    line-height: 1.6;
                }}
                .alert-box {{ 
                    background-color: #fff3cd; 
                    border: 1px solid #ffc107; 
                    border-left: 4px solid #ffc107;
                    padding: 15px; 
                    margin: 10px 0; 
                    border-radius: 6px;
                    font-size: 14px;
                }}
                .risk-indicators {{ 
                    display: flex;
                    gap: 10px;
                    margin: 15px 0;
                }}
                .risk-badge {{ 
                    flex: 1;
                    text-align: center;
                    padding: 12px;
                    border-radius: 8px;
                    font-weight: 600;
                }}
                .risk-badge.high {{ 
                    background-color: #f8d7da;
                    color: #721c24;
                    border: 1px solid #f5c6cb;
                }}
                .risk-badge.medium {{ 
                    background-color: #fff3cd;
                    color: #856404;
                    border: 1px solid #ffeaa7;
                }}
                .risk-badge.low {{ 
                    background-color: #d4edda;
                    color: #155724;
                    border: 1px solid #c3e6cb;
                }}
                .footer {{ 
                    background-color: #f8f9fa;
                    text-align: center; 
                    color: #6c757d; 
                    font-size: 13px; 
                    padding: 25px 20px;
                    border-top: 1px solid #dee2e6;
                }}
                .footer p {{ 
                    margin: 5px 0; 
                }}
                @media only screen and (max-width: 600px) {{
                    .metrics-grid {{ 
                        grid-template-columns: 1fr;
                    }}
                    .container {{ 
                        margin: 10px; 
                    }}
                    .content {{ 
                        padding: 20px 15px; 
                    }}
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <!-- Header -->
                <div class="header">
                    <h1>📊 Reporte Coach Ejecutivo</h1>
                    <p><strong>{nombre}</strong></p>
                    <p>📅 {current_date}</p>
                </div>
                
                <!-- Status Badge -->
                <div class="status-badge">
                    {status_emoji} {estado}
                </div>
                
                <!-- Content -->
                <div class="content">
                    <!-- Métricas de Ventas -->
                    <div class="section">
                        <div class="section-title">💰 Métricas de Ventas</div>
                        
                        <div class="metrics-grid">
                            <div class="metric-card">
                                <div class="metric-label">Ventas Acumuladas</div>
                                <div class="metric-value">${ventas:,.0f}</div>
                            </div>
                            <div class="metric-card">
                                <div class="metric-label">Meta del Mes</div>
                                <div class="metric-value">${meta:,.0f}</div>
                            </div>
                            <div class="metric-card">
                                <div class="metric-label">Faltante</div>
                                <div class="metric-value small">${faltante:,.0f}</div>
                            </div>
                            <div class="metric-card">
                                <div class="metric-label">Días Restantes</div>
                                <div class="metric-value">{dias_restantes}</div>
                            </div>
                        </div>
                        
                        <div class="progress-bar-container">
                            <div class="progress-bar {'warning' if avance_pct < avance_esperado else ''} {'danger' if avance_pct < 0.3 else ''}" style="width: {min(avance_pct * 100, 100):.1f}%">
                                {avance_pct:.1%} de avance
                            </div>
                        </div>
                        
                        <div class="metrics-grid">
                            <div class="metric-card">
                                <div class="metric-label">Venta Diaria Actual</div>
                                <div class="metric-value small">${venta_diaria_actual:,.0f}</div>
                            </div>
                            <div class="metric-card">
                                <div class="metric-label">Venta Diaria Requerida</div>
                                <div class="metric-value small">${venta_diaria_requerida:,.0f}</div>
                            </div>
                        </div>
                    </div>
                    
                    <!-- Análisis de Cartera -->
                    <div class="section">
                        <div class="section-title">👥 Análisis de Cartera</div>
                        
                        <div class="metrics-grid">
                            <div class="metric-card">
                                <div class="metric-label">Total Clientes</div>
                                <div class="metric-value">{total_clientes}</div>
                            </div>
                            <div class="metric-card">
                                <div class="metric-label">Clientes Activos</div>
                                <div class="metric-value">{clientes_activos}</div>
                            </div>
                            <div class="metric-card">
                                <div class="metric-label">% Activación</div>
                                <div class="metric-value small">{porcentaje_activacion:.1f}%</div>
                            </div>
                            <div class="metric-card">
                                <div class="metric-label">Total Reclamos</div>
                                <div class="metric-value">{total_reclamos}</div>
                            </div>
                        </div>
                        
                        <div class="risk-indicators">
                            <div class="risk-badge high">
                                <div style="font-size: 24px; margin-bottom: 5px;">{clientes_riesgo_alto}</div>
                                <div style="font-size: 11px;">Riesgo ALTO</div>
                            </div>
                            <div class="risk-badge medium">
                                <div style="font-size: 24px; margin-bottom: 5px;">{clientes_riesgo_medio}</div>
                                <div style="font-size: 11px;">Riesgo MEDIO</div>
                            </div>
                            <div class="risk-badge low">
                                <div style="font-size: 24px; margin-bottom: 5px;">{reclamos_activos}</div>
                                <div style="font-size: 11px;">Reclamos Activos</div>
                            </div>
                        </div>
                        
                        {f'<div class="metric-card" style="margin-top: 15px;"><div class="metric-label">Tasa Cumplimiento Retiros</div><div class="metric-value small">{tasa_retiros*100:.1f}%</div></div>' if tasa_retiros > 0 else ''}
                    </div>
                    
                    <!-- Diagnóstico -->
                    <div class="section">
                        <div class="section-title">🔍 Diagnóstico</div>
                        <div class="diagnostico-box">
                            {diagnostico}
                        </div>
                    </div>
                    
                    <!-- Sugerencias de Acción -->
                    <div class="section">
                        <div class="section-title">🎯 Acciones Prioritarias con Clientes</div>
        """
        
        # Add sugerencias
        if sugerencias:
            for sug in sugerencias:
                prioridad = sug.get('prioridad', 'MEDIA').lower()
                cliente_nombre = sug.get('cliente_nombre', 'N/A')
                cliente_rut = sug.get('cliente_rut', 'N/A')
                accion = sug.get('accion', 'N/A')
                razon = sug.get('razon', 'N/A')
                
                # Emoji por prioridad
                emoji_prioridad = {
                    'crítica': '🔴',
                    'alta': '🟠',
                    'media': '🟡'
                }.get(prioridad, '⚪')
                
                html += f"""
                        <div class="sugerencia-card {prioridad}">
                            <div class="sugerencia-header">
                                <span class="sugerencia-prioridad {prioridad}">{emoji_prioridad} {sug.get('prioridad', 'MEDIA')}</span>
                            </div>
                            <div class="sugerencia-cliente">{cliente_nombre}</div>
                            <div class="sugerencia-rut">RUT: {cliente_rut}</div>
                            <div class="sugerencia-accion">✅ Acción: {accion}</div>
                            <div class="sugerencia-razon">{razon}</div>
                        </div>
                """
        else:
            html += """
                        <div class="diagnostico-box">
                            No hay sugerencias específicas en este momento. Continúa con el seguimiento regular de tu cartera.
                        </div>
            """
        
        html += """
                    </div>
        """
        
        # Add alertas
        if alertas:
            html += """
                    <div class="section">
                        <div class="section-title">⚠️ Alertas Importantes</div>
            """
            for alerta in alertas:
                html += f'<div class="alert-box">⚠️ {alerta}</div>\n'
            html += "</div>"
        
        html += f"""
                </div>
                
                <!-- Footer -->
                <div class="footer">
                    <p><strong>Coach Ejecutivo Chilexpress</strong></p>
                    <p>Este es un reporte automático generado por el sistema de análisis de ventas</p>
                    <p style="margin-top: 15px; font-size: 12px;">Para consultas o soporte, contacta al equipo de análisis</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        return html
