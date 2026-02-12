"""Analysis service for orchestrating data retrieval and AI analysis."""

from typing import Dict, Any, Optional
from app.clients.interfaces import IDataClient, IAIClient


class ServiceError(Exception):
    """Custom exception for service layer errors."""
    
    def __init__(self, message: str, step: str, details: Optional[str] = None):
        self.message = message
        self.step = step
        self.details = details
        super().__init__(self.message)


class AnalysisService:
    """Service orchestrating the analysis workflow."""
    
    def __init__(self, data_client: IDataClient, ai_client: IAIClient):
        if data_client is None:
            raise ValueError("data_client cannot be None")
        if ai_client is None:
            raise ValueError("ai_client cannot be None")
            
        self._data_client = data_client
        self._ai_client = ai_client
    
    def execute_analysis(
        self,
        query_params: Dict[str, Any],
        analysis_prompt: Optional[str] = None,
        current_date: Optional[str] = None
    ) -> Dict[str, Any]:
        """Execute complete analysis workflow."""
        if not isinstance(query_params, dict):
            raise ValueError("query_params must be a dictionary")
        
        if "collection" not in query_params:
            raise ValueError("query_params must include 'collection' field")
        
        # Query MongoDB
        try:
            data = self._data_client.query(query_params)
        except ConnectionError as e:
            raise ServiceError("Failed to connect to data source", "data_retrieval", str(e))
        except ValueError as e:
            raise ServiceError("Invalid query parameters", "data_retrieval", str(e))
        except Exception as e:
            raise ServiceError("Failed to retrieve data from database", "data_retrieval", str(e))
        
        # Validate data
        if data is None:
            raise ServiceError("Data retrieval returned None", "data_validation", "Expected list but got None")
        
        if not isinstance(data, list):
            raise ServiceError("Data retrieval returned invalid type", "data_validation", f"Expected list but got {type(data).__name__}")
        
        data_count = len(data)
        
        if data_count == 0:
            return {
                "status": "success",
                "data_count": 0,
                "analysis": {"analysis": "No data found matching the query criteria.", "confidence": None, "metadata": {}},
                "query_params": query_params
            }
        
        # Enhance prompt with current date if provided
        enhanced_prompt = analysis_prompt
        if current_date:
            date_context = f"Current date for analysis context: {current_date}. "
            enhanced_prompt = date_context + (analysis_prompt or "Analyze the provided data.")
        
        # AI analysis
        try:
            ai_result = self._ai_client.analyze(data, prompt=enhanced_prompt)
        except ConnectionError as e:
            raise ServiceError("Failed to connect to AI service", "ai_analysis", str(e))
        except Exception as e:
            raise ServiceError("Failed to analyze data with AI service", "ai_analysis", str(e))
        
        # Validate AI response
        if ai_result is None:
            raise ServiceError("AI analysis returned None", "ai_validation", "Expected analysis results but got None")
        
        if not isinstance(ai_result, dict):
            raise ServiceError("AI analysis returned invalid type", "ai_validation", f"Expected dict but got {type(ai_result).__name__}")
        
        return {
            "status": "success",
            "data_count": data_count,
            "analysis": ai_result,
            "query_params": query_params
        }
