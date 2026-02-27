"""AWS Bedrock client implementation."""

import os
import re
import logging
from typing import List, Dict, Any, Optional
import boto3
from botocore.exceptions import ClientError
from app.clients.interfaces import IAIClient

logger = logging.getLogger(__name__)


class AWSBedrockClient(IAIClient):
    """AWS Bedrock implementation of the AI client interface."""
    
    def __init__(self, region: str, model_id: str):
        if not region:
            raise ValueError("AWS region cannot be empty")
        if not model_id:
            raise ValueError("AWS Bedrock model ID cannot be empty")
            
        self._region = region
        self._model_id = model_id
        
        # Pricing configuration
        self._input_price_per_1k_tokens = float(os.getenv("AWS_INPUT_PRICE_PER_1K_TOKENS", "0.0008"))
        self._output_price_per_1k_tokens = float(os.getenv("AWS_OUTPUT_PRICE_PER_1K_TOKENS", "0.0032"))
        
        # Token optimization configuration
        self._max_clients_per_exec = int(os.getenv("MAX_CLIENTS_PER_EXEC", "30"))
        
        # Validate model identifier
        self._validate_model_id(self._model_id)
        
        self._client: Optional[Any] = None
    
    def _validate_model_id(self, model_id: str) -> None:
        """Validate model id format."""
        if not model_id:
            raise ValueError(
                "AWS_BEDROCK_MODEL_ID is not set. Set it to the model ID or inference profile ARN."
            )
        
        # Accept both short model names and ARNs
        # Short format: amazon.nova-lite-v1:0
        # ARN format: arn:aws:bedrock:us-east-1::inference-profile/amazon-nova-lite-v1
        
        # If it's an ARN, validate basic structure
        if model_id.startswith("arn:"):
            if not model_id.startswith("arn:aws:bedrock:"):
                raise ValueError(
                    "AWS_BEDROCK_MODEL_ID does not look like a valid Bedrock ARN. "
                    "Expected format: arn:aws:bedrock:<region>::inference-profile/<name>."
                )
    
    def connect(self) -> None:
        """Establish connection to AWS Bedrock service."""
        from botocore.config import Config
        
        # Configure with extended timeout for large requests
        config = Config(
            read_timeout=600,  # 10 minutes
            connect_timeout=60,
            retries={'max_attempts': 3}
        )
        
        # boto3 will automatically use AWS_BEARER_TOKEN_BEDROCK from environment
        self._client = boto3.client(
            service_name="bedrock-runtime",
            region_name=self._region,
            config=config
        )
    
    def analyze(self, data: List[Dict[str, Any]], prompt: Optional[str] = None) -> Dict[str, Any]:
        """Send data to AWS Bedrock model for analysis."""
        if self._client is None:
            raise ConnectionError("Client not connected. Call connect() first.")
        
        messages = self._format_request(data, prompt)
        response = self._invoke_model(messages)
        return self._parse_response(response)
    
    def analyze_batch(
        self,
        batch_data: List[Dict[str, Any]],
        batch_num: int,
        prompt: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Analyze a single batch of data.
        
        This method is designed to be called by BatchProcessor for parallel processing.
        
        Args:
            batch_data: List of executive data for this batch
            batch_num: Batch number (for logging)
            prompt: Optional analysis prompt
            
        Returns:
            Dictionary with parsed analysis results
        """
        import json
        
        logger.info(f"[Batch {batch_num}] Analyzing {len(batch_data)} executives...")
        
        # Perform analysis
        result = self.analyze(batch_data, prompt)
        
        # Parse the analysis JSON
        analysis_text = result.get("analysis", "")
        
        try:
            analysis_json = json.loads(analysis_text)
            ejecutivos = analysis_json.get("ejecutivos", [])
            
            logger.info(
                f"[Batch {batch_num}] Successfully analyzed {len(ejecutivos)} executives"
            )
            
            # Return ejecutivos list (will be consolidated by BatchProcessor)
            return ejecutivos
            
        except json.JSONDecodeError as e:
            logger.error(f"[Batch {batch_num}] JSON parsing error: {e.msg}")
            raise RuntimeError(f"Failed to parse analysis JSON: {e.msg}")
    
    def _format_request(self, data: List[Dict[str, Any]], prompt: Optional[str] = None) -> List[Dict[str, Any]]:
        """Format data and prompt for AWS Bedrock API."""
        import json
        
        default_prompt = "Analyze the following data and provide insights."
        analysis_prompt = prompt if prompt else default_prompt
        
        # Optimize data to reduce token count
        optimized_data = self._optimize_data_for_tokens(data, max_clients_per_exec=self._max_clients_per_exec)
        
        # Add field mapping explanation for abbreviated fields
        field_mapping = """
NOTA: Los datos están optimizados con campos abreviados para reducir tokens:
- rut: RUT del cliente
- nom: Nombre del cliente (truncado a 30 chars)
- vta: Ventas del mes
- m: Métricas del cliente
  - risk: Nivel de riesgo (red/yellow/green)
  - drop: Flag de riesgo de pérdida (1=sí, 0=no)
  - act: Cliente activo (true/false)
  - attn: Necesita atención (true/false)
  - hv: Alto valor (true/false)
  - avg: Promedio histórico de ventas
  - l3: Promedio últimos 3 meses
  - p3: Promedio 3 meses anteriores
  - p25: Percentil 25
  - cb25: Meses consecutivos bajo p25
- clm: Reclamos
  - tot: Total de reclamos
  - r: Lista de reclamos (solo el más reciente)
- pck: Retiros/pickups
  - prg: Retiros programados
  - efe: Retiros efectuados
- mem: Recomendaciones previas (últimas 2)
  - r: Texto de recomendación (truncado a 80 chars)
  - t: Fecha (YYYY-MM-DD)
- cart: Cartera de clientes (limitada a 10 más críticos)

"""
        
        # Use JSON format for better token efficiency
        data_str = json.dumps(optimized_data, ensure_ascii=False, separators=(',', ':'))
        
        # Format messages for Bedrock converse API
        messages = [
            {
                "role": "user",
                "content": [{"text": f"{field_mapping}\n{analysis_prompt}\n\nData:\n{data_str}"}]
            }
        ]
        
        return messages
    
    def _prefilter_clients_by_memory(self, data: List[Dict[str, Any]], days_threshold: int = 1, reference_date: Optional[str] = None) -> List[Dict[str, Any]]:
        """Pre-filter clients that were recommended recently to ensure diversity.
        
        This function removes clients from the cartera_detallada that have been
        recommended within the last N days, forcing the AI to recommend different clients.
        
        Cooldown logic:
        - If days_threshold = 7, a client recommended on day 0 can be recommended again on day 7
        - Example: Recommended on 2026-02-18, can be recommended again on 2026-02-25 (7 days later)
        
        Args:
            data: List of executive data with cartera_detallada
            days_threshold: Number of days for cooldown period (default: 1 = yesterday)
            reference_date: Optional reference date in ISO format (YYYY-MM-DD). If None, uses current date.
            
        Returns:
            Filtered data with clients removed if they were recommended recently
        """
        from datetime import datetime, timedelta
        
        # Use reference date if provided, otherwise use current date
        if reference_date:
            ref_dt = datetime.fromisoformat(reference_date.split('T')[0])
        else:
            ref_dt = datetime.utcnow()
        
        # Calculate cutoff date: recommendations AFTER this date will be filtered
        # For 7-day cooldown: if today is 2026-02-25, cutoff is 2026-02-18 00:00:00
        # Recommendations from 2026-02-18 00:00:01 onwards will be filtered
        cutoff_date = ref_dt - timedelta(days=days_threshold)
        cutoff_str = cutoff_date.isoformat()
        
        filtered_data = []
        total_removed = 0
        total_kept = 0
        
        for ejecutivo in data:
            filtered_ejecutivo = ejecutivo.copy()
            cartera = ejecutivo.get("cartera_detallada", [])
            
            if not cartera:
                filtered_data.append(filtered_ejecutivo)
                continue
            
            # Filter clients
            filtered_cartera = []
            removed_count = 0
            
            for cliente in cartera:
                memory_recs = cliente.get("memory_recs", [])
                
                # Check if client has recent recommendations
                has_recent_rec = False
                if memory_recs:
                    for rec in memory_recs:
                        rec_timestamp = rec.get("timestamp", "")
                        if rec_timestamp:
                            # Extract only the date part (YYYY-MM-DD) for comparison
                            # This ensures that all recommendations from the same day are treated equally
                            rec_date = rec_timestamp.split('T')[0] if 'T' in rec_timestamp else rec_timestamp[:10]
                            cutoff_date_str = cutoff_str.split('T')[0] if 'T' in cutoff_str else cutoff_str[:10]
                            
                            # Filter if recommendation date is AFTER cutoff date
                            # Example: If cutoff is 2026-02-18
                            #   - Rec from 2026-02-19 → FILTERED (too recent)
                            #   - Rec from 2026-02-18 → FILTERED (too recent)
                            #   - Rec from 2026-02-17 → NOT FILTERED (old enough)
                            # This means: cooldown of 7 days = can recommend again on day 8
                            if rec_date > cutoff_date_str:
                                has_recent_rec = True
                                break
                
                if has_recent_rec:
                    # Skip this client (was recommended recently)
                    removed_count += 1
                    total_removed += 1
                else:
                    # Include this client
                    filtered_cartera.append(cliente)
                    total_kept += 1
            
            # Update cartera with filtered list
            filtered_ejecutivo["cartera_detallada"] = filtered_cartera
            
            # Add metadata about filtering
            if removed_count > 0:
                filtered_ejecutivo["_prefilter_note"] = f"{removed_count} clients filtered (recommended in last {days_threshold} days)"
            
            filtered_data.append(filtered_ejecutivo)
        
        # Log filtering results
        if total_removed > 0:
            print(f"Pre-filtering: Removed {total_removed} clients, kept {total_kept} clients (threshold: {days_threshold} days)")
        
        return filtered_data
    
    def _optimize_data_for_tokens(self, data: List[Dict[str, Any]], max_clients_per_exec: int = 30) -> List[Dict[str, Any]]:
        """Optimize data structure to reduce token count while preserving essential information.
        
        Args:
            data: List of executive data dictionaries
            max_clients_per_exec: Maximum number of clients to include per executive (default: 30)
        
        Returns:
            Optimized data structure
        """
        optimized = []
        
        for item in data:
            optimized_item = {}
            
            # Copy basic fields
            for key in ['rut_ejecutivo', 'nombre_ejecutivo', 'correo', 
                       'ventas_total_mes', 'goal_mes', 'avance_pct', 'faltante']:
                if key in item:
                    optimized_item[key] = item[key]
            
            # Optimize cartera_detallada - this is the biggest data source
            if 'cartera_detallada' in item and isinstance(item['cartera_detallada'], list):
                cartera = item['cartera_detallada']
                
                # Prioritize clients: high risk, with claims, or high value
                def client_priority(cliente):
                    """Calculate priority score for client (higher = more important)."""
                    score = 0
                    
                    # Check metrics
                    if 'client_metrics' in cliente and cliente['client_metrics']:
                        cm = cliente['client_metrics']
                        
                        # High priority: risk level
                        if cm.get('risk_level') == 'red':
                            score += 100
                        elif cm.get('risk_level') == 'yellow':
                            score += 50
                        
                        # High priority: drop flag
                        if cm.get('drop_flag') == 1:
                            score += 80
                        
                        # Medium priority: needs attention
                        if cm.get('needs_attention'):
                            score += 40
                        
                        # Medium priority: high value
                        if cm.get('is_high_value'):
                            score += 30
                        
                        # Low priority: inactive
                        if not cm.get('is_active'):
                            score += 20
                    
                    # Priority: has claims
                    if 'claims' in cliente and cliente['claims']:
                        if cliente['claims'].get('total_reclamos', 0) > 0:
                            score += 60
                    
                    # Priority: has pickup issues
                    if 'pickups' in cliente and cliente['pickups']:
                        programados = cliente['pickups'].get('cant_retiros_programados', 0)
                        efectuados = cliente['pickups'].get('cant_retiros_efectuados', 0)
                        if programados > 0 and (efectuados / programados) < 0.8:
                            score += 30
                    
                    # Priority: has sales this month
                    if cliente.get('ventas_mes', 0) > 0:
                        score += 10
                    
                    return score
                
                # Sort clients by priority and limit to max_clients_per_exec
                sorted_cartera = sorted(cartera, key=client_priority, reverse=True)
                limited_cartera = sorted_cartera[:max_clients_per_exec]
                
                optimized_cartera = []
                
                for cliente in limited_cartera:
                    optimized_cliente = {
                        'rut_key': cliente.get('rut_key'),
                        'nombre': cliente.get('nombre'),
                        'ventas_mes': cliente.get('ventas_mes', 0)
                    }
                    
                    # Include client_metrics but only essential fields
                    if 'client_metrics' in cliente and cliente['client_metrics']:
                        cm = cliente['client_metrics']
                        optimized_cliente['metrics'] = {
                            'drop_flag': cm.get('drop_flag'),
                            'risk_level': cm.get('risk_level'),
                            'is_active': cm.get('is_active'),
                            'needs_attention': cm.get('needs_attention'),
                            'is_high_value': cm.get('is_high_value'),
                            'monto_neto_mes_mean': cm.get('monto_neto_mes_mean'),
                            'avg_last3': cm.get('avg_last3'),
                            'avg_prev3': cm.get('avg_prev3'),
                            'p25': cm.get('p25'),
                            'consec_below_p25': cm.get('consec_below_p25')
                        }
                    
                    # Include claims summary (solo números)
                    if 'claims' in cliente and cliente['claims']:
                        claims = cliente['claims']
                        optimized_cliente['claims'] = {
                            'total': claims.get('total_reclamos', 0),
                            'pendientes': claims.get('reclamos_pendientes', 0),
                            'valor_total': claims.get('valor_total_reclamado', 0)
                        }
                    
                    # Include pickup summary (solo números)
                    if 'pickups' in cliente and cliente['pickups']:
                        pickups = cliente['pickups']
                        optimized_cliente['pickups'] = {
                            'programados': pickups.get('cant_retiros_programados', 0),
                            'efectuados': pickups.get('cant_retiros_efectuados', 0),
                            'tasa': pickups.get('tasa_cumplimiento')
                        }
                    
                    # Include memory_recs (last 2 recommendations)
                    if 'memory_recs' in cliente and cliente['memory_recs']:
                        memory_recs = cliente['memory_recs']
                        optimized_cliente['memory_recs'] = [
                            {
                                'rec': rec.get('recommendation', '')[:100],
                                'timestamp': rec.get('timestamp', '')[:10]
                            }
                            for rec in memory_recs[:2]
                        ]
                    
                    optimized_cartera.append(optimized_cliente)
                
                optimized_item['cartera_detallada'] = optimized_cartera
            
            optimized.append(optimized_item)
        
        return optimized
    
    def prefilter_clients_by_memory(self, data: List[Dict[str, Any]], days_threshold: int = 1) -> List[Dict[str, Any]]:
        """Pre-filter clients that were recommended recently to ensure diversity.

        This function removes clients from the cartera_detallada that have been
        recommended within the last N days, forcing the AI to recommend different clients.

        Args:
            data: List of executive data with cartera_detallada
            days_threshold: Number of days to consider as "recent" (default: 1 = yesterday)

        Returns:
            Filtered data with clients removed if they were recommended recently
        """
        from datetime import datetime, timedelta

        cutoff_date = datetime.utcnow() - timedelta(days=days_threshold)
        cutoff_str = cutoff_date.isoformat()

        filtered_data = []
        total_removed = 0
        total_kept = 0

        for ejecutivo in data:
            filtered_ejecutivo = ejecutivo.copy()
            cartera = ejecutivo.get("cartera_detallada", [])

            if not cartera:
                filtered_data.append(filtered_ejecutivo)
                continue

            # Filter clients
            filtered_cartera = []
            removed_count = 0

            for cliente in cartera:
                memory_recs = cliente.get("memory_recs", [])

                # Check if client has recent recommendations
                has_recent_rec = False
                if memory_recs:
                    for rec in memory_recs:
                        rec_timestamp = rec.get("timestamp", "")
                        if rec_timestamp and rec_timestamp > cutoff_str:
                            has_recent_rec = True
                            break

                if has_recent_rec:
                    # Skip this client (was recommended recently)
                    removed_count += 1
                    total_removed += 1
                else:
                    # Include this client
                    filtered_cartera.append(cliente)
                    total_kept += 1

            # Update cartera with filtered list
            filtered_ejecutivo["cartera_detallada"] = filtered_cartera

            # Add metadata about filtering
            if removed_count > 0:
                filtered_ejecutivo["_prefilter_note"] = f"{removed_count} clients filtered (recommended in last {days_threshold} days)"

            filtered_data.append(filtered_ejecutivo)

        # Log filtering results
        if total_removed > 0:
            print(f"Pre-filtering: Removed {total_removed} clients, kept {total_kept} clients (threshold: {days_threshold} days)")

        return filtered_data
    
    def _invoke_model(self, messages: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Invoke AWS Bedrock model using converse API."""
        system_prompt = """You are a data analysis assistant. Provide thorough, complete responses 
        and analyze the data comprehensively.

CRITICAL: Your response MUST be valid JSON. Follow these rules strictly:
1. All string values must have properly escaped quotes: use \\" for quotes inside strings
2. All string values must be properly terminated with closing quotes
3. Do not include line breaks inside string values - use \\n instead
4. Ensure all brackets and braces are properly closed
5. Return ONLY the JSON object, no additional text before or after"""
        
        # Determine max tokens based on model
        # Nova Pro supports up to 300K input tokens and 5K output tokens
        # Nova Lite supports up to 300K input tokens and 5K output tokens
        max_output_tokens = 5000 if "nova-pro" in self._model_id else 4096
        
        try:
            response = self._client.converse(
                modelId=self._model_id,
                messages=messages,
                system=[{"text": system_prompt}],
                inferenceConfig={
                    "maxTokens": max_output_tokens,
                    "temperature": 0.2
                }
            )
            return response
        except ClientError as e:
            error_msg = e.response.get('Error', {}).get('Message', str(e))
            
            # Check if it's an input token limit error
            if "Input Tokens Exceeded" in error_msg or "input tokens exceeds" in error_msg.lower():
                # Try to estimate input size and suggest batch processing
                import json
                data_str = messages[0]["content"][0]["text"]
                estimated_tokens = len(data_str) // 4  # Rough estimate: 1 token ≈ 4 chars
                
                raise RuntimeError(
                    f"AWS Bedrock input token limit exceeded. "
                    f"Estimated input tokens: ~{estimated_tokens:,}. "
                    f"Model '{self._model_id}' supports up to 300K input tokens. "
                    f"Consider enabling batch processing or reducing data size."
                ) from e
            
            raise RuntimeError(
                f"AWS Bedrock Converse failed for model '{self._model_id}': {error_msg}"
            ) from e
    
    def _parse_response(self, response: Dict[str, Any]) -> Dict[str, Any]:
        """Parse AWS Bedrock response into standardized format."""
        # Extract text from response
        analysis_text = response["output"]["message"]["content"][0]["text"]
        
        # Clean markdown code blocks from JSON responses
        analysis_text = self._clean_markdown_json(analysis_text)
        
        # Validate and fix JSON
        analysis_text = self._validate_and_fix_json(analysis_text)
        
        # Extract metadata
        metadata = {
            "model": self._model_id,
            "region": self._region
        }
        
        # Extract token usage if available
        if "usage" in response:
            usage = response["usage"]
            metadata["tokens"] = {
                "prompt": usage.get("inputTokens"),
                "completion": usage.get("outputTokens"),
                "total": usage.get("totalTokens")
            }
            
            # Calculate cost if token usage is available
            if "inputTokens" in usage and "outputTokens" in usage:
                input_cost = (usage["inputTokens"] / 1000) * self._input_price_per_1k_tokens
                output_cost = (usage["outputTokens"] / 1000) * self._output_price_per_1k_tokens
                metadata["cost"] = {
                    "input": round(input_cost, 6),
                    "output": round(output_cost, 6),
                    "total": round(input_cost + output_cost, 6)
                }
        
        return {
            "analysis": analysis_text,
            "confidence": None,
            "metadata": metadata
        }
    
    def _validate_and_fix_json(self, text: str) -> str:
        """Validate JSON and attempt to fix common issues."""
        import json
        
        # Try to parse as-is first
        try:
            json.loads(text)
            return text  # Valid JSON, return as-is
        except json.JSONDecodeError as e:
            print(f"Warning: JSON parsing error at position {e.pos}: {e.msg}")
            print(f"Attempting to fix JSON...")
            
            # Common fixes
            fixed_text = text
            
            # Fix 1: Remove any text before first { or [
            first_brace = fixed_text.find('{')
            first_bracket = fixed_text.find('[')
            if first_brace >= 0 and (first_bracket < 0 or first_brace < first_bracket):
                fixed_text = fixed_text[first_brace:]
            elif first_bracket >= 0:
                fixed_text = fixed_text[first_bracket:]
            
            # Fix 2: Remove any text after last } or ]
            last_brace = fixed_text.rfind('}')
            last_bracket = fixed_text.rfind(']')
            if last_brace >= 0 and last_brace > last_bracket:
                fixed_text = fixed_text[:last_brace + 1]
            elif last_bracket >= 0:
                fixed_text = fixed_text[:last_bracket + 1]
            
            # Fix 3: Replace unescaped newlines in strings
            # This is tricky - we need to find strings and escape newlines within them
            # For now, replace literal \n with escaped version
            fixed_text = fixed_text.replace('\n', '\\n')
            fixed_text = fixed_text.replace('\r', '\\r')
            fixed_text = fixed_text.replace('\t', '\\t')
            
            # Try parsing again
            try:
                json.loads(fixed_text)
                print("✅ JSON fixed successfully")
                return fixed_text
            except json.JSONDecodeError as e2:
                print(f"❌ Could not fix JSON: {e2.msg} at position {e2.pos}")
                
                # Save problematic JSON for debugging
                with open('debug_invalid_json.txt', 'w', encoding='utf-8') as f:
                    f.write(text)
                print("Saved invalid JSON to debug_invalid_json.txt")
                
                # Return original text and let caller handle the error
                return text
    
    def _clean_markdown_json(self, text: str) -> str:
        """Remove markdown code block formatting from JSON responses."""
        # Remove ```json and ``` markers
        text = re.sub(r'^```json\s*\n', '', text, flags=re.MULTILINE)
        text = re.sub(r'^```\s*\n?', '', text, flags=re.MULTILINE)
        text = re.sub(r'\n```\s*$', '', text, flags=re.MULTILINE)
        return text.strip()
