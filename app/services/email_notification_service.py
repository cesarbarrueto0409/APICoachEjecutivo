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
        current_date: str,
        is_testing: bool = False
    ) -> Dict[str, Any]:
        """
        Send email notifications to all ejecutivos in analysis result.
        
        Args:
            analysis_result: Result from analysis service
            current_date: Current date for context
            is_testing: If True, only send to ejecutivos with test_correo field
            
        Returns:
            Dict with keys:
                - total_sent: int
                - total_failed: int
                - total_skipped: int (only in testing mode)
                - notifications: List[Dict] with details of each email
        """
        notifications = []
        sent_count = 0
        failed_count = 0
        skipped_count = 0
        
        # Extract ejecutivos from analysis
        data = analysis_result.get("data", {})
        ejecutivos = data.get("ejecutivos", [])
        
        if not ejecutivos:
            self._logger.warning("No ejecutivos found in analysis result")
            return {
                "total_sent": 0,
                "total_failed": 0,
                "total_skipped": 0,
                "notifications": []
            }
        
        # Log testing mode
        if is_testing:
            self._logger.info("TESTING MODE: Only sending to ejecutivos with test_correo field")
        
        # Send email to each ejecutivo
        for ejecutivo in ejecutivos:
            try:
                # Extract ejecutivo data
                correo = ejecutivo.get("correo")
                test_correo = ejecutivo.get("test_correo")
                nombre = ejecutivo.get("nombre", "Ejecutivo")
                
                # In testing mode, skip ejecutivos without test_correo
                if is_testing and not test_correo:
                    self._logger.info(f"Skipping {nombre} (no test_correo field)")
                    notifications.append({
                        "ejecutivo": nombre,
                        "recipient": None,
                        "subject": None,
                        "status": "skipped",
                        "error": "Testing mode: no test_correo field"
                    })
                    skipped_count += 1
                    continue
                
                # Use test_correo if in testing mode, otherwise use regular correo
                email_to_send = test_correo if is_testing else correo
                
                if not email_to_send:
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
                if is_testing:
                    subject = f"[TEST] {subject}"
                
                html_content = self._format_email_html(ejecutivo, current_date)
                
                # Send email
                result = self._email_client.send_email(
                    to_email=email_to_send,
                    subject=subject,
                    html_content=html_content
                )
                
                # Record result
                notification = {
                    "ejecutivo": nombre,
                    "recipient": result.get("recipient"),
                    "original_recipient": result.get("original_recipient"),
                    "test_mode": is_testing,
                    "test_correo": test_correo if is_testing else None,
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
            "total_skipped": skipped_count,
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
        
        # Progress bar
        avance_pct = avance_pct or 0  # Handle None case
        if avance_pct < 0.3:
            progress_color = "#dc3545"
        elif avance_pct < avance_esperado:
            progress_color = "#ffc107"
        else:
            progress_color = "#28a745"
        
        progress_width = int(min(avance_pct * 100, 100))
        progress_remaining = 100 - progress_width
        
        # Build HTML - Outlook compatible (ONLY inline styles, NO <style> tag)
        html = f"""<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"></head>
<body style="margin:0;padding:0;font-family:Arial,sans-serif;background-color:#f5f5f5;">
<table width="100%" cellpadding="0" cellspacing="0" border="0" style="background-color:#f5f5f5;">
<tr><td align="center" style="padding:20px;">
<table width="650" cellpadding="0" cellspacing="0" border="0" style="background-color:#ffffff;border:1px solid #cccccc;">
<tr><td style="padding:25px 20px;text-align:center;border-bottom:4px solid #0056b3;">
<h1 style="margin:0 0 10px 0;font-size:26px;font-weight:bold;color:#0056b3;">📊 Reporte Coach Ejecutivo</h1>
<p style="margin:5px 0;font-size:16px;color:#000000;"><strong>{nombre}</strong></p>
<p style="margin:5px 0;font-size:14px;color:#666666;">{current_date}</p>
</td></tr>
<tr><td style="background-color:{status_color};color:#ffffff;padding:15px 20px;text-align:center;font-size:20px;font-weight:bold;">
{status_emoji} {estado}
</td></tr>
<tr><td style="padding:25px 20px;">

<table width="100%" cellpadding="0" cellspacing="0" border="0" style="margin-bottom:25px;">
<tr><td style="font-size:20px;font-weight:bold;color:#000000;padding-bottom:8px;border-bottom:3px solid #0056b3;">💰 Métricas de Ventas</td></tr>
<tr><td style="height:15px;"></td></tr>
<tr><td style="background-color:#e3f2fd;padding:12px;border-left:4px solid #0056b3;">
<div style="font-size:14px;color:#000000;font-weight:bold;margin-bottom:5px;">Ventas Acumuladas</div>
<div style="font-size:22px;font-weight:bold;color:#000000;">${ventas:,.0f}</div>
</td></tr>
<tr><td style="height:12px;"></td></tr>
<tr><td style="background-color:#e3f2fd;padding:12px;border-left:4px solid #0056b3;">
<div style="font-size:14px;color:#000000;font-weight:bold;margin-bottom:5px;">Meta del Mes</div>
<div style="font-size:22px;font-weight:bold;color:#000000;">${meta:,.0f}</div>
</td></tr>
<tr><td style="height:12px;"></td></tr>
<tr><td style="background-color:#e3f2fd;padding:12px;border-left:4px solid #0056b3;">
<div style="font-size:14px;color:#000000;font-weight:bold;margin-bottom:5px;">Faltante</div>
<div style="font-size:22px;font-weight:bold;color:#000000;">${faltante:,.0f}</div>
</td></tr>
<tr><td style="height:15px;"></td></tr>
<tr><td>
<table width="100%" cellpadding="0" cellspacing="0" border="0" style="background-color:#e0e0e0;height:30px;">
<tr>
<td width="{progress_width}%" style="background-color:{progress_color};color:#ffffff;text-align:center;font-weight:bold;font-size:14px;padding:5px 0;">{avance_pct:.1%}</td>
<td width="{progress_remaining}%" style="background-color:#e0e0e0;"></td>
</tr>
</table>
</td></tr>
<tr><td style="height:15px;"></td></tr>
<tr><td style="background-color:#e3f2fd;padding:12px;border-left:4px solid #0056b3;">
<div style="font-size:14px;color:#000000;font-weight:bold;margin-bottom:5px;">Venta Diaria Actual</div>
<div style="font-size:22px;font-weight:bold;color:#000000;">${venta_diaria_actual:,.0f}</div>
</td></tr>
<tr><td style="height:12px;"></td></tr>
<tr><td style="background-color:#e3f2fd;padding:12px;border-left:4px solid #0056b3;">
<div style="font-size:14px;color:#000000;font-weight:bold;margin-bottom:5px;">Venta Diaria Requerida</div>
<div style="font-size:22px;font-weight:bold;color:#000000;">${venta_diaria_requerida:,.0f}</div>
</td></tr>
<tr><td style="height:12px;"></td></tr>
<tr><td style="background-color:#e3f2fd;padding:12px;border-left:4px solid #0056b3;">
<div style="font-size:14px;color:#000000;font-weight:bold;margin-bottom:5px;">Días Restantes</div>
<div style="font-size:22px;font-weight:bold;color:#000000;">{dias_restantes}</div>
</td></tr>
</table>

<table width="100%" cellpadding="0" cellspacing="0" border="0" style="margin-bottom:25px;">
<tr><td style="font-size:20px;font-weight:bold;color:#000000;padding-bottom:8px;border-bottom:3px solid #0056b3;">👥 Análisis de Cartera</td></tr>
<tr><td style="height:15px;"></td></tr>
<tr><td style="background-color:#e8f5e9;padding:12px;border-left:4px solid #4caf50;">
<div style="font-size:14px;color:#000000;font-weight:bold;margin-bottom:5px;">Total Clientes</div>
<div style="font-size:22px;font-weight:bold;color:#000000;">{total_clientes}</div>
</td></tr>
<tr><td style="height:12px;"></td></tr>
<tr><td style="background-color:#e8f5e9;padding:12px;border-left:4px solid #4caf50;">
<div style="font-size:14px;color:#000000;font-weight:bold;margin-bottom:5px;">Clientes Activos</div>
<div style="font-size:22px;font-weight:bold;color:#000000;">{clientes_activos}</div>
</td></tr>
<tr><td style="height:12px;"></td></tr>
<tr><td style="background-color:#e8f5e9;padding:12px;border-left:4px solid #4caf50;">
<div style="font-size:14px;color:#000000;font-weight:bold;margin-bottom:5px;">Porcentaje de Activación</div>
<div style="font-size:22px;font-weight:bold;color:#000000;">{porcentaje_activacion:.1f}%</div>
</td></tr>
<tr><td style="height:15px;"></td></tr>
<tr><td style="background-color:#fff3e0;padding:15px;border-left:4px solid #ff9800;">
<span style="font-size:14px;color:#000000;font-weight:bold;margin-right:20px;">Riesgo ALTO: <strong style="font-size:18px;color:#d32f2f;">{clientes_riesgo_alto}</strong></span>
<span style="font-size:14px;color:#000000;font-weight:bold;margin-right:20px;">Riesgo MEDIO: <strong style="font-size:18px;color:#f57c00;">{clientes_riesgo_medio}</strong></span>
<span style="font-size:14px;color:#000000;font-weight:bold;">Reclamos: <strong style="font-size:18px;color:#1976d2;">{reclamos_activos}</strong></span>
</td></tr>
<tr><td style="height:12px;"></td></tr>
<tr><td style="background-color:#e8f5e9;padding:12px;border-left:4px solid #4caf50;">
<div style="font-size:14px;color:#000000;font-weight:bold;margin-bottom:5px;">Total Reclamos</div>
<div style="font-size:22px;font-weight:bold;color:#000000;">{total_reclamos}</div>
</td></tr>
{f'<tr><td style="height:12px;"></td></tr><tr><td style="background-color:#e8f5e9;padding:12px;border-left:4px solid #4caf50;"><div style="font-size:14px;color:#000000;font-weight:bold;margin-bottom:5px;">Tasa Cumplimiento Retiros</div><div style="font-size:22px;font-weight:bold;color:#000000;">{tasa_retiros*100:.1f}%</div></td></tr>' if tasa_retiros > 0 else ''}
</table>

<table width="100%" cellpadding="0" cellspacing="0" border="0" style="margin-bottom:25px;">
<tr><td style="font-size:20px;font-weight:bold;color:#000000;padding-bottom:8px;border-bottom:3px solid #0056b3;">🔍 Diagnóstico</td></tr>
<tr><td style="height:15px;"></td></tr>
<tr><td style="background-color:#e1f5fe;padding:15px;border-left:4px solid #0288d1;font-size:15px;color:#000000;">{diagnostico}</td></tr>
</table>

<table width="100%" cellpadding="0" cellspacing="0" border="0" style="margin-bottom:25px;">
<tr><td style="font-size:20px;font-weight:bold;color:#000000;padding-bottom:8px;border-bottom:3px solid #0056b3;">🎯 Acciones Prioritarias</td></tr>
<tr><td style="height:15px;"></td></tr>
"""
        
        # Add sugerencias
        if sugerencias:
            for sug in sugerencias:
                prioridad = sug.get('prioridad', 'MEDIA').upper()
                cliente_nombre = sug.get('cliente_nombre', 'N/A')
                cliente_rut = sug.get('cliente_rut', 'N/A')
                accion = sug.get('accion', 'N/A')
                razon = sug.get('razon', 'N/A')
                
                # Set colors based on priority (pastel backgrounds)
                if 'CRÍTICA' in prioridad or 'CRITICA' in prioridad:
                    border_color = "#dc3545"
                    bg_color = "#ffe6e6"
                    badge_bg = "#ffcccc"
                    badge_text = "#000000"
                elif 'ALTA' in prioridad:
                    border_color = "#ff8c00"
                    bg_color = "#fff4e6"
                    badge_bg = "#ffd699"
                    badge_text = "#000000"
                else:  # MEDIA
                    border_color = "#ffc107"
                    bg_color = "#fffbf0"
                    badge_bg = "#ffe680"
                    badge_text = "#000000"
                
                html += f"""<tr><td style="background-color:{bg_color};border:2px solid {border_color};border-left:5px solid {border_color};padding:15px;margin-bottom:15px;">
<div style="margin-bottom:10px;">
<span style="background-color:{badge_bg};color:{badge_text};font-size:12px;font-weight:bold;padding:5px 10px;border-radius:3px;display:inline-block;">{prioridad}</span>
</div>
<div style="font-size:18px;font-weight:bold;color:#000000;margin-bottom:8px;">{cliente_nombre}</div>
<div style="font-size:13px;color:#333333;margin-bottom:10px;">RUT: {cliente_rut}</div>
<div style="font-size:15px;font-weight:bold;color:#000000;margin-bottom:8px;">Acción: {accion}</div>
<div style="font-size:14px;color:#000000;">{razon}</div>
</td></tr>
<tr><td style="height:15px;"></td></tr>
"""
        else:
            html += """<tr><td style="background-color:#e1f5fe;padding:15px;border-left:4px solid #0288d1;font-size:15px;color:#000000;">No hay sugerencias en este momento.</td></tr>
"""
        
        html += """</table>
"""
        
        # Add alertas
        if alertas:
            html += """<table width="100%" cellpadding="0" cellspacing="0" border="0" style="margin-bottom:25px;">
<tr><td style="font-size:20px;font-weight:bold;color:#000000;padding-bottom:8px;border-bottom:3px solid #0056b3;">⚠️ Alertas Importantes</td></tr>
<tr><td style="height:15px;"></td></tr>
"""
            for alerta in alertas:
                html += f"""<tr><td style="background-color:#fff3cd;border:2px solid #ffc107;border-left:5px solid #ffc107;padding:15px;margin:10px 0;font-size:14px;color:#000000;">{alerta}</td></tr>
<tr><td style="height:10px;"></td></tr>
"""
            html += """</table>
"""
        
        html += f"""</td></tr>
<tr><td style="background-color:#f8f9fa;text-align:center;color:#666666;font-size:13px;padding:20px;border-top:1px solid #dee2e6;">
<p style="margin:5px 0;color:#666666;"><strong>Coach Ejecutivo Chilexpress</strong></p>
<p style="margin:5px 0;color:#666666;">Este es un reporte automático generado por el sistema de análisis de ventas</p>
<p style="margin:15px 0 5px 0;font-size:12px;color:#666666;">Para consultas o soporte, contacta al equipo de análisis</p>
</td></tr>
</table>
</td></tr>
</table>
</body>
</html>
"""
        
        return html
