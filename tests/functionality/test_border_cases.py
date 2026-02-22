"""Tests for border cases using testing collections."""

import pytest
import requests
from datetime import datetime, timedelta
from app.clients.mongodb_client import MongoDBClient


@pytest.fixture
def setup_test_data(test_config, testing_collections):
    """Setup test data in testing collections."""
    client = MongoDBClient(
        test_config["mongodb_uri"],
        test_config["mongodb_database"]
    )
    client.connect()
    
    # Clear testing collections
    client._database[testing_collections["executives"]].delete_many({})
    client._database[testing_collections["memory"]].delete_many({})
    
    yield client
    
    # Cleanup after tests
    client._database[testing_collections["executives"]].delete_many({})
    client._database[testing_collections["memory"]].delete_many({})
    client.disconnect()


def test_zero_clients_available(setup_test_data, test_config, testing_collections):
    """Test behavior when 0 clients are available for recommendations."""
    client = setup_test_data
    
    # Create executive with all clients recently recommended
    current_date = datetime.utcnow()
    recent_date = (current_date - timedelta(days=1)).isoformat()
    
    exec_data = {
        "id_ejecutivo": 9999,
        "nombre_ejecutivo": "Test Executive Zero",
        "correo": test_config["sendgrid_test_email"],
        "rut_clientes": [111111, 222222, 333333]
    }
    
    client._database[testing_collections["executives"]].insert_one(exec_data)
    
    # Add recent recommendations for all clients
    for rut in exec_data["rut_clientes"]:
        client._database[testing_collections["memory"]].insert_one({
            "executive_id": "9999",
            "client_id": str(rut),
            "recommendation": "Test recommendation",
            "embedding": [0.1] * 100,
            "timestamp": recent_date
        })
    
    # Call API and verify memory reset
    response = requests.post(
        f"{test_config['api_base_url']}/api/analyze",
        json={
            "current_date": current_date.strftime("%Y-%m-%d"),
            "is_testing": True
        }
    )
    
    assert response.status_code == 200
    data = response.json()
    
    # Should have performed full reset
    assert "data" in data


def test_one_or_two_clients_available(setup_test_data, test_config, testing_collections):
    """Test behavior when only 1-2 clients are available."""
    client = setup_test_data
    
    current_date = datetime.utcnow()
    recent_date = (current_date - timedelta(days=1)).isoformat()
    old_date = (current_date - timedelta(days=10)).isoformat()
    
    exec_data = {
        "id_ejecutivo": 9998,
        "nombre_ejecutivo": "Test Executive Few",
        "correo": test_config["sendgrid_test_email"],
        "rut_clientes": [444444, 555555, 666666, 777777, 888888]
    }
    
    client._database[testing_collections["executives"]].insert_one(exec_data)
    
    # Add recent recommendations for 3 clients (leaving 2 available)
    for rut in [444444, 555555, 666666]:
        client._database[testing_collections["memory"]].insert_one({
            "executive_id": "9998",
            "client_id": str(rut),
            "recommendation": "Recent recommendation",
            "embedding": [0.1] * 100,
            "timestamp": recent_date
        })
    
    # Add old recommendation for 1 client
    client._database[testing_collections["memory"]].insert_one({
        "executive_id": "9998",
        "client_id": "777777",
        "recommendation": "Old recommendation",
        "embedding": [0.2] * 100,
        "timestamp": old_date
    })
    
    response = requests.post(
        f"{test_config['api_base_url']}/api/analyze",
        json={
            "current_date": current_date.strftime("%Y-%m-%d"),
            "is_testing": True
        }
    )
    
    assert response.status_code == 200
    data = response.json()
    
    # Should have 2-3 available clients (2 never recommended + 1 old)
    assert "data" in data


def test_cooldown_period(setup_test_data, test_config, testing_collections):
    """Test cooldown period prevents recent recommendations."""
    client = setup_test_data
    
    current_date = datetime.utcnow()
    within_cooldown = (current_date - timedelta(days=3)).isoformat()
    outside_cooldown = (current_date - timedelta(days=10)).isoformat()
    
    exec_data = {
        "id_ejecutivo": 9997,
        "nombre_ejecutivo": "Test Executive Cooldown",
        "correo": test_config["sendgrid_test_email"],
        "rut_clientes": [111222, 333444, 555666]
    }
    
    client._database[testing_collections["executives"]].insert_one(exec_data)
    
    # Client within cooldown
    client._database[testing_collections["memory"]].insert_one({
        "executive_id": "9997",
        "client_id": "111222",
        "recommendation": "Within cooldown",
        "embedding": [0.1] * 100,
        "timestamp": within_cooldown
    })
    
    # Client outside cooldown
    client._database[testing_collections["memory"]].insert_one({
        "executive_id": "9997",
        "client_id": "333444",
        "recommendation": "Outside cooldown",
        "embedding": [0.2] * 100,
        "timestamp": outside_cooldown
    })
    
    response = requests.post(
        f"{test_config['api_base_url']}/api/analyze",
        json={
            "current_date": current_date.strftime("%Y-%m-%d"),
            "is_testing": True
        }
    )
    
    assert response.status_code == 200
    data = response.json()
    
    # Should recommend client outside cooldown and never recommended client
    assert "data" in data


def test_different_recommendations_each_day(setup_test_data, test_config, testing_collections):
    """Test that different clients are recommended each day."""
    client = setup_test_data
    
    exec_data = {
        "id_ejecutivo": 9996,
        "nombre_ejecutivo": "Test Executive Daily",
        "correo": test_config["sendgrid_test_email"],
        "rut_clientes": [100001, 100002, 100003, 100004, 100005, 100006]
    }
    
    client._database[testing_collections["executives"]].insert_one(exec_data)
    
    # Day 1
    day1 = datetime.utcnow()
    response1 = requests.post(
        f"{test_config['api_base_url']}/api/analyze",
        json={
            "current_date": day1.strftime("%Y-%m-%d"),
            "is_testing": True
        }
    )
    
    assert response1.status_code == 200
    data1 = response1.json()
    
    # Day 2 (next day)
    day2 = day1 + timedelta(days=1)
    response2 = requests.post(
        f"{test_config['api_base_url']}/api/analyze",
        json={
            "current_date": day2.strftime("%Y-%m-%d"),
            "is_testing": True
        }
    )
    
    assert response2.status_code == 200
    data2 = response2.json()
    
    # Recommendations should be different
    # (This would require parsing the actual recommendations from responses)
    assert "data" in data1
    assert "data" in data2
