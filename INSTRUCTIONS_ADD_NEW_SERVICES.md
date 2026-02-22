# Guía para Agregar un Nuevo Cliente/Servicio

Esta guía explica cómo agregar un nuevo cliente o servicio externo al proyecto, siguiendo la arquitectura existente y las mejores prácticas.

## Índice
1. [Arquitectura del Proyecto](#arquitectura-del-proyecto)
2. [Contrato Mínimo (Interfaces)](#contrato-mínimo-interfaces)
3. [Paso 1: Crear la Interfaz](#paso-1-crear-la-interfaz)
4. [Paso 2: Implementar el Cliente](#paso-2-implementar-el-cliente)
5. [Paso 3: Integrar en el Flujo de la API](#paso-3-integrar-en-el-flujo-de-la-api)
6. [Paso 4: Agregar Tests de Conectividad](#paso-4-agregar-tests-de-conectividad)
7. [Paso 5: Agregar Health Check](#paso-5-agregar-health-check)
8. [Ejemplos Completos](#ejemplos-completos)

---

## Arquitectura del Proyecto

El proyecto sigue una arquitectura en capas:

```
┌─────────────────────────────────────────┐
│         API Layer (routes.py)           │  ← Endpoints REST
├─────────────────────────────────────────┤
│    Service Layer (services/)            │  ← Lógica de negocio
├─────────────────────────────────────────┤
│    Client Layer (clients/)              │  ← Integración con servicios externos
│  - interfaces.py (contratos)            │
│  - *_client.py (implementaciones)       │
└─────────────────────────────────────────┘
```

### Principios de Diseño

1. **Dependency Injection**: Los servicios reciben sus dependencias en el constructor
2. **Interface Segregation**: Cada tipo de servicio tiene su propia interfaz
3. **Single Responsibility**: Cada cliente maneja un solo servicio externo
4. **Testability**: Interfaces permiten crear mocks para testing

---

## Contrato Mínimo (Interfaces)

Todos los clientes DEBEN implementar una interfaz abstracta que define el contrato mínimo.

### Tipos de Interfaces Existentes

#### 1. IDataClient (Bases de Datos)
```python
from abc import ABC, abstractmethod
from typing import List, Dict, Any

class IDataClient(ABC):
    @abstractmethod
    def connect(self) -> None:
        """Establecer conexión al servicio"""
        pass
    
    @abstractmethod
    def query(self, query_params: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Ejecutar consulta y retornar resultados"""
        pass
    
    @abstractmethod
    def disconnect(self) -> None:
        """Cerrar conexión y liberar recursos"""
        pass
```

**Uso**: MongoDB, PostgreSQL, Redis, etc.

#### 2. IAIClient (Servicios de IA)
```python
class IAIClient(ABC):
    @abstractmethod
    def connect(self) -> None:
        """Establecer conexión al servicio de IA"""
        pass
    
    @abstractmethod
    def analyze(self, data: List[Dict[str, Any]], prompt: str = None) -> Dict[str, Any]:
        """Enviar datos al modelo de IA para análisis"""
        pass
```

**Uso**: AWS Bedrock, OpenAI, Anthropic, etc.

#### 3. IEmbeddingClient (Generación de Embeddings)
```python
class IEmbeddingClient(ABC):
    @abstractmethod
    def connect(self) -> None:
        """Establecer conexión al servicio de embeddings"""
        pass
    
    @abstractmethod
    def generate_embedding(self, text: str) -> List[float]:
        """Generar vector de embedding para un texto"""
        pass
    
    @abstractmethod
    def generate_embeddings_batch(self, texts: List[str]) -> List[List[float]]:
        """Generar embeddings para múltiples textos"""
        pass
```

**Uso**: OpenAI Embeddings, Sentence Transformers, etc.

#### 4. IEmailClient (Envío de Correos)
```python
class IEmailClient(ABC):
    @abstractmethod
    def send_email(
        self,
        to_email: str,
        subject: str,
        html_content: str,
        from_email: Optional[str] = None
    ) -> Dict[str, Any]:
        """Enviar un correo electrónico"""
        pass
```

**Uso**: SendGrid, AWS SES, SMTP, etc.

---

## Paso 1: Crear la Interfaz

Si el servicio que quieres agregar NO encaja en las interfaces existentes, crea una nueva.

### Ubicación
`app/clients/interfaces.py`

### Ejemplo: Agregar IStorageClient para almacenamiento de archivos

```python
class IStorageClient(ABC):
    """Interfaz para clientes de almacenamiento de archivos."""
    
    @abstractmethod
    def connect(self) -> None:
        """
        Establecer conexión al servicio de almacenamiento.
        
        Raises:
            ConnectionError: Si no se puede establecer conexión
        """
        pass
    
    @abstractmethod
    def upload_file(
        self,
        file_path: str,
        destination: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Subir un archivo al almacenamiento.
        
        Args:
            file_path: Ruta local del archivo
            destination: Ruta de destino en el almacenamiento
            metadata: Metadatos opcionales del archivo
            
        Returns:
            Dict con información del archivo subido:
                - url: URL pública del archivo
                - size: Tamaño en bytes
                - checksum: Hash del archivo
                
        Raises:
            FileNotFoundError: Si el archivo no existe
            ValueError: Si los parámetros son inválidos
        """
        pass
    
    @abstractmethod
    def download_file(self, source: str, destination: str) -> None:
        """
        Descargar un archivo del almacenamiento.
        
        Args:
            source: Ruta del archivo en el almacenamiento
            destination: Ruta local de destino
            
        Raises:
            FileNotFoundError: Si el archivo no existe en el almacenamiento
        """
        pass
    
    @abstractmethod
    def delete_file(self, file_path: str) -> bool:
        """
        Eliminar un archivo del almacenamiento.
        
        Args:
            file_path: Ruta del archivo a eliminar
            
        Returns:
            True si se eliminó exitosamente
            
        Raises:
            FileNotFoundError: Si el archivo no existe
        """
        pass
```

### Reglas para Interfaces

1. ✅ Todos los métodos deben ser `@abstractmethod`
2. ✅ Incluir docstrings completos con Args, Returns, Raises
3. ✅ Usar type hints en todos los parámetros y retornos
4. ✅ Incluir método `connect()` para inicialización
5. ✅ Manejar errores con excepciones específicas

---

## Paso 2: Implementar el Cliente

### Ubicación
`app/clients/<nombre>_client.py`

### Ejemplo: Implementar S3StorageClient

```python
"""AWS S3 storage client implementation."""

import os
from typing import Dict, Any, Optional
import boto3
from botocore.exceptions import ClientError
from app.clients.interfaces import IStorageClient


class S3StorageClient(IStorageClient):
    """AWS S3 implementation of storage client interface."""
    
    def __init__(self, bucket_name: str, region: str):
        """
        Initialize S3 storage client.
        
        Args:
            bucket_name: Nombre del bucket de S3
            region: Región de AWS (ej: us-east-1)
            
        Raises:
            ValueError: Si los parámetros son inválidos
        """
        if not bucket_name:
            raise ValueError("bucket_name cannot be empty")
        if not region:
            raise ValueError("region cannot be empty")
            
        self._bucket_name = bucket_name
        self._region = region
        self._client = None
    
    def connect(self) -> None:
        """Establish connection to AWS S3."""
        self._client = boto3.client(
            service_name="s3",
            region_name=self._region
        )
        
        # Verify bucket exists
        try:
            self._client.head_bucket(Bucket=self._bucket_name)
        except ClientError as e:
            raise ConnectionError(
                f"Cannot access S3 bucket '{self._bucket_name}': {str(e)}"
            )
    
    def upload_file(
        self,
        file_path: str,
        destination: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Upload file to S3."""
        if self._client is None:
            raise ConnectionError("Not connected. Call connect() first.")
        
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")
        
        try:
            # Upload file
            extra_args = {}
            if metadata:
                extra_args["Metadata"] = metadata
            
            self._client.upload_file(
                file_path,
                self._bucket_name,
                destination,
                ExtraArgs=extra_args
            )
            
            # Get file info
            response = self._client.head_object(
                Bucket=self._bucket_name,
                Key=destination
            )
            
            # Generate public URL
            url = f"https://{self._bucket_name}.s3.{self._region}.amazonaws.com/{destination}"
            
            return {
                "url": url,
                "size": response["ContentLength"],
                "checksum": response.get("ETag", "").strip('"'),
                "last_modified": response["LastModified"].isoformat()
            }
            
        except ClientError as e:
            raise Exception(f"Failed to upload file: {str(e)}")
    
    def download_file(self, source: str, destination: str) -> None:
        """Download file from S3."""
        if self._client is None:
            raise ConnectionError("Not connected. Call connect() first.")
        
        try:
            self._client.download_file(
                self._bucket_name,
                source,
                destination
            )
        except ClientError as e:
            if e.response["Error"]["Code"] == "404":
                raise FileNotFoundError(f"File not found in S3: {source}")
            raise Exception(f"Failed to download file: {str(e)}")
    
    def delete_file(self, file_path: str) -> bool:
        """Delete file from S3."""
        if self._client is None:
            raise ConnectionError("Not connected. Call connect() first.")
        
        try:
            self._client.delete_object(
                Bucket=self._bucket_name,
                Key=file_path
            )
            return True
        except ClientError as e:
            raise Exception(f"Failed to delete file: {str(e)}")
```

### Reglas para Implementaciones

1. ✅ Heredar de la interfaz correspondiente
2. ✅ Validar parámetros en `__init__`
3. ✅ Inicializar cliente en `connect()`, no en `__init__`
4. ✅ Verificar conexión antes de operaciones (`if self._client is None`)
5. ✅ Manejar excepciones específicas del servicio
6. ✅ Incluir logging para operaciones importantes
7. ✅ Documentar todos los métodos públicos

---

## Paso 3: Integrar en el Flujo de la API

### 3.1 Agregar Configuración

**Ubicación**: `app/config/settings.py`

```python
class Settings:
    def __init__(self):
        # ... configuración existente ...
        
        # S3 Storage Configuration
        self.s3_bucket_name = os.getenv("S3_BUCKET_NAME", "")
        self.s3_region = os.getenv("AWS_REGION", "us-east-1")
        self.storage_enabled = os.getenv("STORAGE_ENABLED", "false").lower() == "true"
    
    def validate(self) -> None:
        """Validate configuration."""
        # ... validaciones existentes ...
        
        # Validate S3 configuration if enabled
        if self.storage_enabled:
            if not self.s3_bucket_name:
                raise ValueError("S3_BUCKET_NAME must be set when STORAGE_ENABLED=true")
```

### 3.2 Inicializar Cliente en main.py

**Ubicación**: `app/main.py`

```python
# Global client instances
_storage_client: S3StorageClient = None

def setup_dependencies(app: FastAPI, settings: Settings) -> None:
    global _storage_client
    
    # ... inicialización de otros clientes ...
    
    # Initialize storage client (optional)
    storage_client = None
    if settings.storage_enabled:
        logger.info("Initializing storage client...")
        _storage_client = S3StorageClient(
            bucket_name=settings.s3_bucket_name,
            region=settings.s3_region
        )
        storage_client = _storage_client
        logger.info("Storage client initialized")
    
    # Pass to services that need it
    # analysis_service = AnalysisService(..., storage_client=storage_client)

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting AWS Bedrock API Service...")
    
    # ... conexiones existentes ...
    
    # Connect to S3 Storage (if enabled)
    if _storage_client:
        _storage_client.connect()
        logger.info("S3 Storage connected")
    
    yield
    
    # Shutdown phase
    logger.info("Shutting down...")
    # S3 client doesn't need explicit disconnect
```

### 3.3 Usar en Servicios

**Ubicación**: `app/services/<servicio>.py`

```python
class ReportService:
    def __init__(
        self,
        data_client: IDataClient,
        storage_client: Optional[IStorageClient] = None
    ):
        self._data_client = data_client
        self._storage_client = storage_client
    
    def generate_and_upload_report(self, report_data: Dict[str, Any]) -> str:
        """Generate report and upload to storage."""
        # Generate report file
        report_path = self._generate_report_file(report_data)
        
        # Upload to storage if available
        if self._storage_client:
            result = self._storage_client.upload_file(
                file_path=report_path,
                destination=f"reports/{report_data['id']}.pdf",
                metadata={"type": "sales_report"}
            )
            return result["url"]
        
        return report_path
```

### 3.4 Agregar Endpoint (Opcional)

**Ubicación**: `app/api/routes.py`

```python
@router.post("/api/v1/upload-report")
async def upload_report(file: UploadFile = File(...)):
    """Upload a report file to storage."""
    # Save temporary file
    temp_path = f"/tmp/{file.filename}"
    with open(temp_path, "wb") as f:
        f.write(await file.read())
    
    # Upload to storage
    result = storage_client.upload_file(
        file_path=temp_path,
        destination=f"uploads/{file.filename}"
    )
    
    # Clean up
    os.remove(temp_path)
    
    return {"url": result["url"], "size": result["size"]}
```

---

## Paso 4: Agregar Tests de Conectividad

### Ubicación
`tests/connectivity/test_<nombre>.py`

### Ejemplo: test_s3_storage.py

```python
"""Tests for S3 Storage connectivity."""

import pytest
import os
from app.clients.s3_storage_client import S3StorageClient


def test_s3_connection(test_config):
    """Test S3 connection can be established."""
    client = S3StorageClient(
        bucket_name=test_config["s3_bucket_name"],
        region=test_config["s3_region"]
    )
    
    # Should connect without errors
    client.connect()


def test_s3_upload_download(test_config, tmp_path):
    """Test S3 can upload and download files."""
    client = S3StorageClient(
        bucket_name=test_config["s3_bucket_name"],
        region=test_config["s3_region"]
    )
    client.connect()
    
    # Create test file
    test_file = tmp_path / "test.txt"
    test_file.write_text("Hello S3!")
    
    # Upload file
    result = client.upload_file(
        file_path=str(test_file),
        destination="test/test.txt",
        metadata={"test": "true"}
    )
    
    assert "url" in result
    assert result["size"] > 0
    
    # Download file
    download_path = tmp_path / "downloaded.txt"
    client.download_file("test/test.txt", str(download_path))
    
    assert download_path.read_text() == "Hello S3!"
    
    # Clean up
    client.delete_file("test/test.txt")


def test_s3_file_not_found(test_config):
    """Test S3 raises error for non-existent files."""
    client = S3StorageClient(
        bucket_name=test_config["s3_bucket_name"],
        region=test_config["s3_region"]
    )
    client.connect()
    
    with pytest.raises(FileNotFoundError):
        client.download_file("nonexistent.txt", "/tmp/test.txt")
```

### Agregar Configuración de Test

**Ubicación**: `tests/conftest.py`

```python
@pytest.fixture
def test_config():
    """Test configuration."""
    return {
        # ... configuración existente ...
        "s3_bucket_name": os.getenv("S3_BUCKET_NAME_TEST", "test-bucket"),
        "s3_region": os.getenv("AWS_REGION", "us-east-1"),
    }
```

---

## Paso 5: Agregar Health Check

### Ubicación
`app/api/routes.py`

### Agregar al Endpoint de Health

```python
@router.get("/api/health")
async def health_check():
    """
    Health check endpoint.
    
    Returns service status and connectivity to external services.
    """
    health_status = {
        "status": "healthy",
        "services": {
            "mongodb": "unknown",
            "aws_bedrock": "unknown",
            "embedding": "unknown",
            "storage": "unknown"  # ← NUEVO
        }
    }
    
    # ... checks existentes ...
    
    # Check S3 Storage connectivity
    if _storage_client:
        try:
            # Try to list objects (lightweight operation)
            _storage_client._client.list_objects_v2(
                Bucket=_storage_client._bucket_name,
                MaxKeys=1
            )
            health_status["services"]["storage"] = "healthy"
        except Exception as e:
            health_status["services"]["storage"] = f"unhealthy: {str(e)}"
            health_status["status"] = "degraded"
    else:
        health_status["services"]["storage"] = "disabled"
    
    return health_status
```

---

## Ejemplos Completos

### Ejemplo 1: Cliente de Cache (Redis)

#### 1. Interfaz
```python
class ICacheClient(ABC):
    @abstractmethod
    def connect(self) -> None:
        pass
    
    @abstractmethod
    def get(self, key: str) -> Optional[str]:
        pass
    
    @abstractmethod
    def set(self, key: str, value: str, ttl: int = 3600) -> bool:
        pass
    
    @abstractmethod
    def delete(self, key: str) -> bool:
        pass
```

#### 2. Implementación
```python
import redis
from app.clients.interfaces import ICacheClient

class RedisClient(ICacheClient):
    def __init__(self, host: str, port: int, db: int = 0):
        self._host = host
        self._port = port
        self._db = db
        self._client = None
    
    def connect(self) -> None:
        self._client = redis.Redis(
            host=self._host,
            port=self._port,
            db=self._db,
            decode_responses=True
        )
        self._client.ping()  # Verify connection
    
    def get(self, key: str) -> Optional[str]:
        if self._client is None:
            raise ConnectionError("Not connected")
        return self._client.get(key)
    
    def set(self, key: str, value: str, ttl: int = 3600) -> bool:
        if self._client is None:
            raise ConnectionError("Not connected")
        return self._client.setex(key, ttl, value)
    
    def delete(self, key: str) -> bool:
        if self._client is None:
            raise ConnectionError("Not connected")
        return self._client.delete(key) > 0
```

#### 3. Test
```python
def test_redis_connection(test_config):
    client = RedisClient(
        host=test_config["redis_host"],
        port=test_config["redis_port"]
    )
    client.connect()
    
    # Test set/get
    assert client.set("test_key", "test_value")
    assert client.get("test_key") == "test_value"
    
    # Clean up
    client.delete("test_key")
```

### Ejemplo 2: Cliente de Notificaciones (Slack)

#### 1. Interfaz
```python
class INotificationClient(ABC):
    @abstractmethod
    def connect(self) -> None:
        pass
    
    @abstractmethod
    def send_notification(
        self,
        channel: str,
        message: str,
        attachments: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        pass
```

#### 2. Implementación
```python
import requests
from app.clients.interfaces import INotificationClient

class SlackClient(INotificationClient):
    def __init__(self, webhook_url: str):
        if not webhook_url:
            raise ValueError("webhook_url cannot be empty")
        self._webhook_url = webhook_url
        self._session = None
    
    def connect(self) -> None:
        self._session = requests.Session()
        # Test webhook
        response = self._session.post(
            self._webhook_url,
            json={"text": "Connection test"}
        )
        if response.status_code != 200:
            raise ConnectionError("Failed to connect to Slack")
    
    def send_notification(
        self,
        channel: str,
        message: str,
        attachments: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        if self._session is None:
            raise ConnectionError("Not connected")
        
        payload = {
            "channel": channel,
            "text": message
        }
        
        if attachments:
            payload["attachments"] = attachments
        
        response = self._session.post(self._webhook_url, json=payload)
        
        return {
            "success": response.status_code == 200,
            "status_code": response.status_code
        }
```

---

## Checklist de Implementación

Usa este checklist para asegurarte de que tu nuevo cliente está completo:

### Interfaz
- [ ] Interfaz definida en `app/clients/interfaces.py`
- [ ] Todos los métodos son `@abstractmethod`
- [ ] Incluye método `connect()`
- [ ] Docstrings completos con Args, Returns, Raises
- [ ] Type hints en todos los parámetros

### Implementación
- [ ] Archivo creado en `app/clients/<nombre>_client.py`
- [ ] Hereda de la interfaz correcta
- [ ] Validación de parámetros en `__init__`
- [ ] Cliente inicializado en `connect()`, no en `__init__`
- [ ] Verificación de conexión antes de operaciones
- [ ] Manejo de excepciones específicas
- [ ] Logging de operaciones importantes

### Configuración
- [ ] Variables de entorno agregadas en `app/config/settings.py`
- [ ] Validación de configuración en `Settings.validate()`
- [ ] Flag de habilitación (ej: `STORAGE_ENABLED`)

### Integración
- [ ] Cliente inicializado en `app/main.py`
- [ ] Conexión en `lifespan()` startup
- [ ] Desconexión en `lifespan()` shutdown (si aplica)
- [ ] Inyección de dependencias configurada

### Tests
- [ ] Archivo de test creado en `tests/connectivity/test_<nombre>.py`
- [ ] Test de conexión básica
- [ ] Test de operaciones principales
- [ ] Test de manejo de errores
- [ ] Configuración de test en `conftest.py`

### Health Check
- [ ] Check agregado en `/api/health` endpoint
- [ ] Manejo de estado "disabled" si no está habilitado
- [ ] Manejo de errores sin romper el health check

---

## Variables de Entorno

Agrega las variables de entorno necesarias en `.env`:

```bash
# S3 Storage Configuration (ejemplo)
STORAGE_ENABLED=true
S3_BUCKET_NAME=my-bucket
AWS_REGION=us-east-1

# Redis Cache Configuration (ejemplo)
CACHE_ENABLED=true
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0

# Slack Notifications (ejemplo)
NOTIFICATIONS_ENABLED=true
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/YOUR/WEBHOOK/URL
```

---

## Mejores Prácticas

1. **Separación de Responsabilidades**: Un cliente = un servicio externo
2. **Fail Gracefully**: Si un servicio opcional falla, la app debe continuar
3. **Logging**: Registra conexiones, desconexiones y errores importantes
4. **Timeouts**: Configura timeouts apropiados para operaciones de red
5. **Retry Logic**: Implementa reintentos para operaciones transitorias
6. **Secrets**: NUNCA hardcodees credenciales, usa variables de entorno
7. **Testing**: Escribe tests antes de integrar en producción
8. **Documentation**: Documenta todos los métodos públicos

---

## Recursos Adicionales

- [FastAPI Dependency Injection](https://fastapi.tiangolo.com/tutorial/dependencies/)
- [Python ABC Module](https://docs.python.org/3/library/abc.html)
- [Pytest Fixtures](https://docs.pytest.org/en/stable/fixture.html)
- [Type Hints](https://docs.python.org/3/library/typing.html)

---

**Última actualización**: 2026-02-22
