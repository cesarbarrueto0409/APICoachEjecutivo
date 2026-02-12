# 📊 Sales Analysis API with AWS Bedrock

> Intelligent sales analysis API powered by AWS Bedrock (Nova Pro) and MongoDB, providing automated insights and recommendations for sales executives.

[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115.0-green.svg)](https://fastapi.tiangolo.com/)
[![Docker](https://img.shields.io/badge/Docker-Ready-blue.svg)](https://www.docker.com/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## 📑 Table of Contents

- [Overview](#-overview)
- [Features](#-features)
- [Architecture](#-architecture)
- [Tech Stack](#-tech-stack)
- [Getting Started](#-getting-started)
- [Usage](#-usage)
- [API Documentation](#-api-documentation)
- [Project Structure](#-project-structure)
- [How It Works](#-how-it-works)
- [Deployment](#-deployment)

---

## 🎯 Overview

This API provides intelligent sales analysis by combining real-time data from MongoDB with AI-powered insights from AWS Bedrock. It analyzes sales performance, calculates metrics, and generates actionable recommendations for sales executives.

### Key Capabilities

- 📈 **Real-time Analysis**: Process sales data dynamically based on date
- 🤖 **AI-Powered Insights**: Leverage AWS Bedrock Nova Pro for intelligent analysis
- 📊 **Performance Metrics**: Calculate sales pace, achievement rates, and portfolio activation
- 🎯 **Smart Recommendations**: Generate specific, actionable advice for each executive
- 🔄 **Dynamic Queries**: MongoDB aggregation pipelines that adapt to the analysis date

---

## ✨ Features

- **Dynamic Date-Based Analysis**: Analyze sales for any specific date
- **Executive Performance Tracking**: Individual metrics and status for each sales executive
- **Sales Pace Calculation**: Compare actual vs required daily sales velocity
- **Portfolio Analysis**: Track client activation and engagement rates
- **AI-Generated Recommendations**: Personalized action items for each executive
- **Alert System**: Automatic detection of performance issues
- **Cost Tracking**: Monitor AWS Bedrock token usage and costs
- **RESTful API**: Clean, documented endpoints with Swagger UI
- **Docker Support**: Easy deployment with Docker Compose

---

## 🏗️ Architecture

```
┌─────────────────┐
│   Client/User   │
└────────┬────────┘
         │ HTTP POST /analyze
         ▼
┌─────────────────────────────────┐
│      FastAPI Application        │
│  ┌───────────────────────────┐ │
│  │  Analysis Service         │ │
│  │  - Query Generation       │ │
│  │  - Data Processing        │ │
│  │  - AI Integration         │ │
│  └───────────────────────────┘ │
└────┬──────────────────────┬────┘
     │                      │
     ▼                      ▼
┌──────────────┐    ┌──────────────────┐
│   MongoDB    │    │  AWS Bedrock     │
│   Atlas      │    │  (Nova Pro)      │
│              │    │                  │
│ - Sales Data │    │ - AI Analysis    │
│ - Goals      │    │ - Insights       │
│ - Clients    │    │ - Recommendations│
└──────────────┘    └──────────────────┘
```

---

## 🛠️ Tech Stack

### Backend
- **FastAPI** - Modern, fast web framework for building APIs
- **Python 3.11+** - Programming language
- **Pydantic** - Data validation using Python type annotations
- **Uvicorn** - ASGI server for production

### Data & AI
- **MongoDB Atlas** - Cloud database for sales data
- **AWS Bedrock** - AI service (Nova Pro model)
- **PyMongo** - MongoDB driver for Python

### DevOps
- **Docker** - Containerization
- **Docker Compose** - Multi-container orchestration

---

## 🚀 Getting Started

### Prerequisites

- Python 3.11 or higher
- Docker and Docker Compose (optional, for containerized deployment)
- MongoDB Atlas account (or local MongoDB instance)
- AWS Bedrock access with Nova Pro model

### Installation

1. **Clone the repository**

```bash
git clone https://github.com/yourusername/sales-analysis-api.git
cd sales-analysis-api
```

2. **Create virtual environment**

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# Linux/Mac
source venv/bin/activate
```

3. **Install dependencies**

```bash
pip install -r requirements.txt
```

### Configuration

Create a `.env` file in the root directory with the following variables:

```bash
# MongoDB Configuration
MONGODB_URI=mongodb+srv://username:password@cluster.mongodb.net/?retryWrites=true&w=majority
MONGODB_DATABASE=your_database_name

# AWS Bedrock Configuration
AWS_REGION=us-east-1
AWS_BEDROCK_MODEL_ID=amazon.nova-pro-v1:0
AWS_BEARER_TOKEN_BEDROCK=your_aws_bearer_token

# API Configuration
API_HOST=0.0.0.0
API_PORT=8000
```

#### Configuration Details

| Variable | Description | Example |
|----------|-------------|---------|
| `MONGODB_URI` | MongoDB connection string | `mongodb+srv://user:pass@cluster.mongodb.net/` |
| `MONGODB_DATABASE` | Database name | `sales_db` |
| `AWS_REGION` | AWS region for Bedrock | `us-east-1` |
| `AWS_BEDROCK_MODEL_ID` | Bedrock model identifier | `amazon.nova-pro-v1:0` |
| `AWS_BEARER_TOKEN_BEDROCK` | AWS authentication token | Your token |
| `API_HOST` | API host address | `0.0.0.0` |
| `API_PORT` | API port number | `8000` |

> ⚠️ **Security Note**: Never commit your `.env` file to version control. It's already included in `.gitignore`.

---

## 💻 Usage

### Running with Docker

The easiest way to run the application:

```bash
# Start the application
docker-compose up

# Run in detached mode
docker-compose up -d

# Stop the application
docker-compose down
```

The API will be available at: **http://localhost:8000**

### Running Locally

```bash
# Activate virtual environment
venv\Scripts\activate  # Windows
source venv/bin/activate  # Linux/Mac

# Run the application
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### API Endpoints

#### 1. Analyze Sales (Main Endpoint)

```http
POST /analyze
Content-Type: application/json

{
  "current_date": "2026-02-12"
}
```

**Response Example:**

```json
{
  "data": {
    "fecha_analisis": "2026-02-12",
    "ejecutivos": [
      {
        "id_ejecutivo": 123,
        "nombre": "Juan Pérez",
        "estado": "Buen ritmo",
        "metricas": {
          "ventas_acumuladas": 15000000,
          "meta_mes": 20000000,
          "avance_porcentual": 0.75
        },
        "cartera": {
          "total_clientes": 50,
          "clientes_activos": 35
        },
        "diagnostico": "Excelente ritmo de ventas...",
        "acciones_recomendadas": ["..."],
        "alertas": []
      }
    ],
    "resumen_general": {
      "total_ejecutivos": 10,
      "ejecutivos_buen_ritmo": 7
    }
  },
  "metadata": {
    "data_count": 150,
    "model": "amazon.nova-pro-v1:0",
    "tokens": {"total": 2300},
    "cost": {"total": 0.00376}
  }
}
```

#### 2. Health Check

```http
GET /health
```

#### 3. Interactive API Documentation

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

---

## 📚 API Documentation

### Status Classifications

| Status | Criteria |
|--------|----------|
| **Excelente ritmo** | Daily average ≥ 120% of required pace |
| **Buen ritmo** | Daily average ≥ 90% of required pace |
| **Ritmo justo** | Daily average ≥ 70% of required pace |
| **Necesita acelerar** | Daily average < 70% of required pace |

---

## 📁 Project Structure

```
sales-analysis-api/
├── app/
│   ├── main.py                 # FastAPI application
│   ├── api/
│   │   ├── routes.py           # API endpoints
│   │   └── schemas.py          # Pydantic models
│   ├── clients/
│   │   ├── mongodb_client.py   # MongoDB connection
│   │   └── aws_bedrock_client.py  # AWS Bedrock
│   ├── config/
│   │   ├── settings.py         # Configuration
│   │   └── queries.py          # Dynamic queries
│   └── services/
│       └── analysis_service.py # Business logic
├── tests/
├── .env                        # Environment variables
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
└── README.md
```

---

## 🔍 How It Works

1. **Request Processing**: Receive date in POST request
2. **Dynamic Query Generation**: Build MongoDB pipelines based on date
3. **Data Retrieval**: Fetch sales, goals, and client data
4. **AI Analysis**: Send to AWS Bedrock for intelligent insights
5. **Response Generation**: Return structured JSON with recommendations

---

## 🚢 Deployment

### Docker Deployment

```bash
docker-compose up --build -d
```

### AWS Deployment

Compatible with:
- AWS ECS/Fargate
- AWS EC2
- AWS Lambda
- AWS App Runner

---

## 🧪 Testing

```bash
pytest
pytest --cov=app tests/
```

---

**Made with ❤️ for better sales insights**
