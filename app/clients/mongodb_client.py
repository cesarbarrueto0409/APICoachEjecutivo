"""MongoDB client implementation for data retrieval."""

from typing import List, Dict, Any
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, OperationFailure, ServerSelectionTimeoutError
from app.clients.interfaces import IDataClient


class MongoDBClient(IDataClient):
    """MongoDB implementation of the data client interface."""
    
    def __init__(self, connection_string: str, database_name: str):
        if not connection_string:
            raise ValueError("connection_string cannot be empty")
        if not database_name:
            raise ValueError("database_name cannot be empty")
            
        self._connection_string = connection_string
        self._database_name = database_name
        self._client = None
        self._database = None
    
    def connect(self) -> None:
        """Establish connection to MongoDB."""
        try:
            self._client = MongoClient(self._connection_string, serverSelectionTimeoutMS=5000)
            self._client.admin.command('ping')
            self._database = self._client[self._database_name]
        except (ConnectionFailure, ServerSelectionTimeoutError) as e:
            raise ConnectionError(f"Failed to connect to MongoDB: {str(e)}")
        except Exception as e:
            raise ConnectionError(f"Unexpected error connecting to MongoDB: {str(e)}")
    
    def query(self, query_params: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Execute MongoDB query (simple find or aggregation pipeline)."""
        if self._client is None or self._database is None:
            raise ConnectionError("Not connected to MongoDB. Call connect() first.")
        
        if "collection" not in query_params:
            raise ValueError("query_params must include 'collection' field")
        
        collection_name = query_params["collection"]
        if not isinstance(collection_name, str) or not collection_name:
            raise ValueError("collection must be a non-empty string")
        
        try:
            collection = self._database[collection_name]
            
            # Aggregation pipeline
            if "pipeline" in query_params:
                pipeline = query_params["pipeline"]
                if not isinstance(pipeline, list):
                    raise ValueError("pipeline must be a list of aggregation stages")
                
                cursor = collection.aggregate(pipeline)
                results = []
                for doc in cursor:
                    if "_id" in doc and hasattr(doc["_id"], "__str__"):
                        doc["_id"] = str(doc["_id"])
                    results.append(doc)
                return results
            
            # Simple find query
            else:
                filter_doc = query_params.get("filter", {})
                projection = query_params.get("projection", None)
                limit = query_params.get("limit", None)
                
                if not isinstance(filter_doc, dict):
                    raise ValueError("filter must be a dictionary")
                
                if projection is not None and not isinstance(projection, dict):
                    raise ValueError("projection must be a dictionary")
                
                if limit is not None and (not isinstance(limit, int) or limit <= 0):
                    raise ValueError("limit must be a positive integer")
                
                cursor = collection.find(filter_doc, projection)
                
                if limit is not None:
                    cursor = cursor.limit(limit)
                
                results = []
                for doc in cursor:
                    if "_id" in doc:
                        doc["_id"] = str(doc["_id"])
                    results.append(doc)
                
                return results
            
        except OperationFailure as e:
            raise Exception(f"MongoDB query failed: {str(e)}")
        except Exception as e:
            raise Exception(f"Unexpected error executing query: {str(e)}")
    
    def disconnect(self) -> None:
        """Close MongoDB connection and cleanup resources."""
        if self._client is not None:
            try:
                self._client.close()
            except Exception:
                pass
            finally:
                self._client = None
                self._database = None
