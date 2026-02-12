"""
Unit tests for the MongoDBClient class.

These tests verify that the MongoDBClient correctly implements the IDataClient
interface and handles connection management, query execution, and error cases.
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from app.clients.mongodb_client import MongoDBClient


class TestMongoDBClient:
    """Test suite for MongoDBClient class."""
    
    def test_initialization_success(self):
        """Test that MongoDBClient initializes with valid parameters."""
        client = MongoDBClient("mongodb://localhost:27017", "test_db")
        
        assert client._connection_string == "mongodb://localhost:27017"
        assert client._database_name == "test_db"
        assert client._client is None
        assert client._database is None
    
    def test_initialization_empty_connection_string(self):
        """Test that initialization fails with empty connection string."""
        with pytest.raises(ValueError) as exc_info:
            MongoDBClient("", "test_db")
        
        assert "connection_string cannot be empty" in str(exc_info.value)
    
    def test_initialization_empty_database_name(self):
        """Test that initialization fails with empty database name."""
        with pytest.raises(ValueError) as exc_info:
            MongoDBClient("mongodb://localhost:27017", "")
        
        assert "database_name cannot be empty" in str(exc_info.value)
    
    @patch('app.clients.mongodb_client.MongoClient')
    def test_connect_success(self, mock_mongo_client):
        """Test successful connection to MongoDB."""
        # Setup mock
        mock_client_instance = MagicMock()
        mock_mongo_client.return_value = mock_client_instance
        mock_client_instance.admin.command.return_value = {'ok': 1}
        
        # Create and connect client
        client = MongoDBClient("mongodb://localhost:27017", "test_db")
        client.connect()
        
        # Verify connection was established
        mock_mongo_client.assert_called_once_with(
            "mongodb://localhost:27017",
            serverSelectionTimeoutMS=5000
        )
        mock_client_instance.admin.command.assert_called_once_with('ping')
        assert client._client is not None
        assert client._database is not None
    
    @patch('app.clients.mongodb_client.MongoClient')
    def test_connect_failure(self, mock_mongo_client):
        """Test connection failure handling."""
        from pymongo.errors import ConnectionFailure
        
        # Setup mock to raise ConnectionFailure
        mock_mongo_client.side_effect = ConnectionFailure("Connection refused")
        
        # Create client and attempt connection
        client = MongoDBClient("mongodb://localhost:27017", "test_db")
        
        with pytest.raises(ConnectionError) as exc_info:
            client.connect()
        
        assert "Failed to connect to MongoDB" in str(exc_info.value)
    
    @patch('app.clients.mongodb_client.MongoClient')
    def test_query_not_connected(self, mock_mongo_client):
        """Test that query fails when not connected."""
        client = MongoDBClient("mongodb://localhost:27017", "test_db")
        
        with pytest.raises(ConnectionError) as exc_info:
            client.query({"collection": "test_collection"})
        
        assert "Not connected to MongoDB" in str(exc_info.value)
    
    @patch('app.clients.mongodb_client.MongoClient')
    def test_query_missing_collection(self, mock_mongo_client):
        """Test that query fails when collection parameter is missing."""
        # Setup mock
        mock_client_instance = MagicMock()
        mock_mongo_client.return_value = mock_client_instance
        mock_client_instance.admin.command.return_value = {'ok': 1}
        
        # Create and connect client
        client = MongoDBClient("mongodb://localhost:27017", "test_db")
        client.connect()
        
        # Attempt query without collection
        with pytest.raises(ValueError) as exc_info:
            client.query({})
        
        assert "must include 'collection' field" in str(exc_info.value)
    
    @patch('app.clients.mongodb_client.MongoClient')
    def test_query_invalid_collection_type(self, mock_mongo_client):
        """Test that query fails when collection is not a string."""
        # Setup mock
        mock_client_instance = MagicMock()
        mock_mongo_client.return_value = mock_client_instance
        mock_client_instance.admin.command.return_value = {'ok': 1}
        
        # Create and connect client
        client = MongoDBClient("mongodb://localhost:27017", "test_db")
        client.connect()
        
        # Attempt query with invalid collection type
        with pytest.raises(ValueError) as exc_info:
            client.query({"collection": 123})
        
        assert "collection must be a non-empty string" in str(exc_info.value)
    
    @patch('app.clients.mongodb_client.MongoClient')
    def test_query_success_basic(self, mock_mongo_client):
        """Test successful basic query execution."""
        # Setup mock
        mock_client_instance = MagicMock()
        mock_mongo_client.return_value = mock_client_instance
        mock_client_instance.admin.command.return_value = {'ok': 1}
        
        # Setup mock collection and cursor
        mock_db = MagicMock()
        mock_client_instance.__getitem__.return_value = mock_db
        mock_collection = MagicMock()
        mock_db.__getitem__.return_value = mock_collection
        
        # Mock cursor with test data
        mock_cursor = MagicMock()
        mock_cursor.__iter__.return_value = iter([
            {"_id": "507f1f77bcf86cd799439011", "name": "John", "age": 30},
            {"_id": "507f1f77bcf86cd799439012", "name": "Jane", "age": 25}
        ])
        mock_collection.find.return_value = mock_cursor
        
        # Create and connect client
        client = MongoDBClient("mongodb://localhost:27017", "test_db")
        client.connect()
        
        # Execute query
        results = client.query({"collection": "users"})
        
        # Verify results
        assert len(results) == 2
        assert results[0]["name"] == "John"
        assert results[1]["name"] == "Jane"
        # Verify _id was converted to string
        assert isinstance(results[0]["_id"], str)
        
        # Verify find was called with correct parameters
        mock_collection.find.assert_called_once_with({}, None)
    
    @patch('app.clients.mongodb_client.MongoClient')
    def test_query_with_filter(self, mock_mongo_client):
        """Test query execution with filter parameter."""
        # Setup mock
        mock_client_instance = MagicMock()
        mock_mongo_client.return_value = mock_client_instance
        mock_client_instance.admin.command.return_value = {'ok': 1}
        
        # Setup mock collection and cursor
        mock_db = MagicMock()
        mock_client_instance.__getitem__.return_value = mock_db
        mock_collection = MagicMock()
        mock_db.__getitem__.return_value = mock_collection
        
        # Mock cursor with filtered data
        mock_cursor = MagicMock()
        mock_cursor.__iter__.return_value = iter([
            {"_id": "507f1f77bcf86cd799439011", "name": "John", "age": 30}
        ])
        mock_collection.find.return_value = mock_cursor
        
        # Create and connect client
        client = MongoDBClient("mongodb://localhost:27017", "test_db")
        client.connect()
        
        # Execute query with filter
        filter_doc = {"age": {"$gte": 30}}
        results = client.query({
            "collection": "users",
            "filter": filter_doc
        })
        
        # Verify results
        assert len(results) == 1
        assert results[0]["age"] == 30
        
        # Verify find was called with filter
        mock_collection.find.assert_called_once_with(filter_doc, None)
    
    @patch('app.clients.mongodb_client.MongoClient')
    def test_query_with_projection(self, mock_mongo_client):
        """Test query execution with projection parameter."""
        # Setup mock
        mock_client_instance = MagicMock()
        mock_mongo_client.return_value = mock_client_instance
        mock_client_instance.admin.command.return_value = {'ok': 1}
        
        # Setup mock collection and cursor
        mock_db = MagicMock()
        mock_client_instance.__getitem__.return_value = mock_db
        mock_collection = MagicMock()
        mock_db.__getitem__.return_value = mock_collection
        
        # Mock cursor with projected data
        mock_cursor = MagicMock()
        mock_cursor.__iter__.return_value = iter([
            {"_id": "507f1f77bcf86cd799439011", "name": "John"}
        ])
        mock_collection.find.return_value = mock_cursor
        
        # Create and connect client
        client = MongoDBClient("mongodb://localhost:27017", "test_db")
        client.connect()
        
        # Execute query with projection
        projection = {"name": 1}
        results = client.query({
            "collection": "users",
            "projection": projection
        })
        
        # Verify find was called with projection
        mock_collection.find.assert_called_once_with({}, projection)
    
    @patch('app.clients.mongodb_client.MongoClient')
    def test_query_with_limit(self, mock_mongo_client):
        """Test query execution with limit parameter."""
        # Setup mock
        mock_client_instance = MagicMock()
        mock_mongo_client.return_value = mock_client_instance
        mock_client_instance.admin.command.return_value = {'ok': 1}
        
        # Setup mock collection and cursor
        mock_db = MagicMock()
        mock_client_instance.__getitem__.return_value = mock_db
        mock_collection = MagicMock()
        mock_db.__getitem__.return_value = mock_collection
        
        # Mock cursor with limit
        mock_cursor = MagicMock()
        mock_cursor.limit.return_value = mock_cursor
        mock_cursor.__iter__.return_value = iter([
            {"_id": "507f1f77bcf86cd799439011", "name": "John"}
        ])
        mock_collection.find.return_value = mock_cursor
        
        # Create and connect client
        client = MongoDBClient("mongodb://localhost:27017", "test_db")
        client.connect()
        
        # Execute query with limit
        results = client.query({
            "collection": "users",
            "limit": 10
        })
        
        # Verify limit was applied
        mock_cursor.limit.assert_called_once_with(10)
    
    @patch('app.clients.mongodb_client.MongoClient')
    def test_query_invalid_filter_type(self, mock_mongo_client):
        """Test that query fails when filter is not a dictionary."""
        # Setup mock
        mock_client_instance = MagicMock()
        mock_mongo_client.return_value = mock_client_instance
        mock_client_instance.admin.command.return_value = {'ok': 1}
        
        # Create and connect client
        client = MongoDBClient("mongodb://localhost:27017", "test_db")
        client.connect()
        
        # Attempt query with invalid filter type
        with pytest.raises(ValueError) as exc_info:
            client.query({
                "collection": "users",
                "filter": "invalid"
            })
        
        assert "filter must be a dictionary" in str(exc_info.value)
    
    @patch('app.clients.mongodb_client.MongoClient')
    def test_query_invalid_limit(self, mock_mongo_client):
        """Test that query fails when limit is not a positive integer."""
        # Setup mock
        mock_client_instance = MagicMock()
        mock_mongo_client.return_value = mock_client_instance
        mock_client_instance.admin.command.return_value = {'ok': 1}
        
        # Create and connect client
        client = MongoDBClient("mongodb://localhost:27017", "test_db")
        client.connect()
        
        # Attempt query with invalid limit
        with pytest.raises(ValueError) as exc_info:
            client.query({
                "collection": "users",
                "limit": -5
            })
        
        assert "limit must be a positive integer" in str(exc_info.value)
    
    @patch('app.clients.mongodb_client.MongoClient')
    def test_query_empty_results(self, mock_mongo_client):
        """Test query execution that returns no results."""
        # Setup mock
        mock_client_instance = MagicMock()
        mock_mongo_client.return_value = mock_client_instance
        mock_client_instance.admin.command.return_value = {'ok': 1}
        
        # Setup mock collection and cursor with no results
        mock_db = MagicMock()
        mock_client_instance.__getitem__.return_value = mock_db
        mock_collection = MagicMock()
        mock_db.__getitem__.return_value = mock_collection
        
        # Mock empty cursor
        mock_cursor = MagicMock()
        mock_cursor.__iter__.return_value = iter([])
        mock_collection.find.return_value = mock_cursor
        
        # Create and connect client
        client = MongoDBClient("mongodb://localhost:27017", "test_db")
        client.connect()
        
        # Execute query
        results = client.query({"collection": "users"})
        
        # Verify empty results
        assert results == []
    
    @patch('app.clients.mongodb_client.MongoClient')
    def test_disconnect_success(self, mock_mongo_client):
        """Test successful disconnection."""
        # Setup mock
        mock_client_instance = MagicMock()
        mock_mongo_client.return_value = mock_client_instance
        mock_client_instance.admin.command.return_value = {'ok': 1}
        
        # Create and connect client
        client = MongoDBClient("mongodb://localhost:27017", "test_db")
        client.connect()
        
        # Disconnect
        client.disconnect()
        
        # Verify close was called
        mock_client_instance.close.assert_called_once()
        assert client._client is None
        assert client._database is None
    
    @patch('app.clients.mongodb_client.MongoClient')
    def test_disconnect_when_not_connected(self, mock_mongo_client):
        """Test that disconnect is safe when not connected."""
        client = MongoDBClient("mongodb://localhost:27017", "test_db")
        
        # Should not raise any exception
        client.disconnect()
        
        assert client._client is None
        assert client._database is None
    
    @patch('app.clients.mongodb_client.MongoClient')
    def test_disconnect_handles_errors(self, mock_mongo_client):
        """Test that disconnect handles errors gracefully."""
        # Setup mock
        mock_client_instance = MagicMock()
        mock_mongo_client.return_value = mock_client_instance
        mock_client_instance.admin.command.return_value = {'ok': 1}
        mock_client_instance.close.side_effect = Exception("Close error")
        
        # Create and connect client
        client = MongoDBClient("mongodb://localhost:27017", "test_db")
        client.connect()
        
        # Disconnect should not raise exception
        client.disconnect()
        
        # Verify state was reset despite error
        assert client._client is None
        assert client._database is None
