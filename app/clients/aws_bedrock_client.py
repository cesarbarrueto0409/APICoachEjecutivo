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
        try:
            # boto3 will automatically use AWS_BEARER_TOKEN_BEDROCK from environment
            # No need to pass credentials explicitly
            self._client = boto3.client(
                service_name="bedrock-runtime",
                region_name=self._region
            )
        except Exception as e:
            raise ConnectionError(f"Failed to connect to AWS Bedrock service: {str(e)}") from e
    
    def analyze(self, data: List[Dict[str, Any]], prompt: Optional[str] = None) -> Dict[str, Any]:
        """Send data to AWS Bedrock model for analysis."""
        if self._client is None:
            raise ConnectionError("Client not connected. Call connect() first.")
        
        try:
            messages = self._format_request(data, prompt)
            response = self._invoke_model(messages)
            return self._parse_response(response)
        except ClientError as e:
            error_msg = e.response.get('Error', {}).get('Message', str(e))
            raise Exception(f"AWS Bedrock service error: {error_msg}") from e
        except Exception as e:
            raise Exception(f"Failed to analyze data: {str(e)}") from e
    
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
                    
                    optimized_cartera.append(optimized_cliente)
                
                # Add note if clients were limited
                if len(cartera) > max_clients_per_exec:
                    optimized_item['_note'] = f"Showing top {max_clients_per_exec} priority clients of {len(cartera)} total"
                
                optimized_item['cartera_detallada'] = optimized_cartera
            
            optimized.append(optimized_item)
        
        return optimized
    
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
        try:
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
        except (KeyError, IndexError, TypeError) as e:
            raise RuntimeError("Unexpected response structure from Bedrock converse call") from e
    
    def _clean_markdown_json(self, text: str) -> str:
        """Remove markdown code block formatting from JSON responses."""
        # Remove ```json and ``` markers
        text = re.sub(r'^```json\s*\n', '', text, flags=re.MULTILINE)
        text = re.sub(r'^```\s*\n?', '', text, flags=re.MULTILINE)
        text = re.sub(r'\n```\s*$', '', text, flags=re.MULTILINE)
        return text.strip()
