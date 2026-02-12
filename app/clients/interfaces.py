"""Client interfaces for external service integrations."""

from abc import ABC, abstractmethod
from typing import List, Dict, Any


class IDataClient(ABC):
    """Interface for data retrieval clients."""
    
    @abstractmethod
    def connect(self) -> None:
        """Establish connection to the data source."""
        pass
    
    @abstractmethod
    def query(self, query_params: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Execute a query and return results."""
        pass
    
    @abstractmethod
    def disconnect(self) -> None:
        """Close connection to the data source."""
        pass


class IAIClient(ABC):
    """Interface for AI service clients."""
    
    @abstractmethod
    def connect(self) -> None:
        """Establish connection to the AI service."""
        pass
    
    @abstractmethod
    def analyze(self, data: List[Dict[str, Any]], prompt: str = None) -> Dict[str, Any]:
        """Send data to AI model for analysis."""
        pass
