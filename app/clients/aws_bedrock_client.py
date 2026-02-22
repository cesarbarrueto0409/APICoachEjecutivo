"""AWS Bedrock client implementation."""

import os
import re
from typing import List, Dict, Any, Optional
import boto3
from botocore.exceptions import ClientError
from app.clients.interfaces import IAIClient


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
        # boto3 will automatically use AWS_BEARER_TOKEN_BEDROCK from environment
        self._client = boto3.client(
            service_name="bedrock-runtime",
            region_name=self._region
        )
    
    def analyze(self, data: List[Dict[str, Any]], prompt: Optional[str] = None) -> Dict[str, Any]:
        """Send data to AWS Bedrock model for analysis."""
        if self._client is None:
            raise ConnectionError("Client not connected. Call connect() first.")
        
        messages = self._format_request(data, prompt)
        response = self._invoke_model(messages)
        return self._parse_response(response)
    
    def _format_request(self, data: List[Dict[str, Any]], prompt: Optional[str] = None) -> List[Dict[str, Any]]:
        """Format data and prompt for AWS Bedrock API."""
        import json
        
        default_prompt = "Analyze the following data and provide insights."
        analysis_prompt = prompt if prompt else default_prompt
        
        # Optimize data to reduce token count
        optimized_data = self._optimize_data_for_tokens(data, max_clients_per_exec=self._max_clients_per_exec)
        
        # Use JSON format for better token efficiency
        data_str = json.dumps(optimized_data, ensure_ascii=False, separators=(',', ':'))
        
        # Format messages for Bedrock converse API
        messages = [
            {
                "role": "user",
                "content": [{"text": f"{analysis_prompt}\n\nData:\n{data_str}"}]
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
            for key in ['id_ejecutivo', 'nombre_ejecutivo', 'correo', 'agno', 'mes', 
                       'ventas_total_mes', 'goal_mes', 'goal_year', 'avance_pct', 
                       'faltante', 'n_clientes', 'clientes_con_ventas']:
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
                
                # Sort clients by priority and limit
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
                            'risk_score': cm.get('risk_score'),
                            'is_active': cm.get('is_active'),
                            'needs_attention': cm.get('needs_attention'),
                            'is_high_value': cm.get('is_high_value'),
                            'monto_neto_mes_mean': cm.get('monto_neto_mes_mean'),
                            'avg_last3': cm.get('avg_last3'),
                            'avg_prev3': cm.get('avg_prev3'),
                            'p25': cm.get('p25'),
                            'p50': cm.get('p50'),
                            'consec_below_p25': cm.get('consec_below_p25')
                        }
                    
                    # Include claims summary (not full details)
                    if 'claims' in cliente and cliente['claims']:
                        claims = cliente['claims']
                        total_reclamos = claims.get('total_reclamos', 0)
                        
                        if total_reclamos > 0:
                            # Only include essential claim info, limit to 3 most recent
                            reclamos_list = claims.get('reclamos', [])[:3]
                            optimized_cliente['claims'] = {
                                'total': total_reclamos,
                                'reclamos': [
                                    {
                                        'caso': r.get('numero_caso'),
                                        'motivo': r.get('motivo'),
                                        'estado': r.get('estado'),
                                        'valor': r.get('valor_reclamado')
                                    }
                                    for r in reclamos_list
                                ]
                            }
                    
                    # Include pickup summary (not full details)
                    if 'pickups' in cliente and cliente['pickups']:
                        pickups = cliente['pickups']
                        optimized_cliente['pickups'] = {
                            'programados': pickups.get('cant_retiros_programados', 0),
                            'efectuados': pickups.get('cant_retiros_efectuados', 0)
                        }
                    
                    # Include previous recommendation (summary only)
                    if 'recommendation' in cliente and cliente['recommendation']:
                        rec = cliente['recommendation']
                        if 'bedrock_recommendation' in rec:
                            # Truncate recommendation to first 200 chars
                            rec_text = str(rec.get('bedrock_recommendation', ''))[:200]
                            optimized_cliente['prev_rec'] = rec_text
                    
                    # Include memory_recs (last 3 recommendations from memory system)
                    if 'memory_recs' in cliente and cliente['memory_recs']:
                        memory_recs = cliente['memory_recs']
                        # Include last 3 recommendations with timestamp
                        optimized_cliente['memory_recs'] = [
                            {
                                'rec': rec.get('recommendation', '')[:150],  # Truncar a 150 chars
                                'timestamp': rec.get('timestamp', '')[:10]  # Solo fecha YYYY-MM-DD
                            }
                            for rec in memory_recs[:3]
                        ]
                    
                    optimized_cartera.append(optimized_cliente)
                
                # Add note if clients were limited
                if len(cartera) > max_clients_per_exec:
                    optimized_item['_note'] = f"Showing top {max_clients_per_exec} priority clients of {len(cartera)} total"
                
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
        and analyze the data comprehensively."""
        
        try:
            response = self._client.converse(
                modelId=self._model_id,
                messages=messages,
                system=[{"text": system_prompt}],
                inferenceConfig={
                    "maxTokens": 4096,  # Increased from 3000
                    "temperature": 0.2
                }
            )
            return response
        except ClientError as e:
            error_msg = e.response.get('Error', {}).get('Message', str(e))
            raise RuntimeError(
                f"AWS Bedrock Converse failed for model '{self._model_id}': {error_msg}"
            ) from e
    
    def _parse_response(self, response: Dict[str, Any]) -> Dict[str, Any]:
        """Parse AWS Bedrock response into standardized format."""
        # Extract text from response
        analysis_text = response["output"]["message"]["content"][0]["text"]
        
        # Clean markdown code blocks from JSON responses
        analysis_text = self._clean_markdown_json(analysis_text)
        
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
    
    def _clean_markdown_json(self, text: str) -> str:
        """Remove markdown code block formatting from JSON responses."""
        # Remove ```json and ``` markers
        text = re.sub(r'^```json\s*\n', '', text, flags=re.MULTILINE)
        text = re.sub(r'^```\s*\n?', '', text, flags=re.MULTILINE)
        text = re.sub(r'\n```\s*$', '', text, flags=re.MULTILINE)
        return text.strip()
