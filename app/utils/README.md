# Carpeta Utils

Esta carpeta contiene utilidades y herramientas auxiliares que pueden ser usadas por diferentes partes de la aplicación.

## Archivos

### `python_parser.py`
**Función:** Parser para analizar archivos de código Python y extraer información estructurada.

**Responsabilidades:**
- Parsear archivos Python usando AST (Abstract Syntax Tree)
- Extraer información de funciones (nombre, parámetros, docstring, decoradores)
- Extraer información de clases (nombre, métodos, herencia, docstring)
- Proporcionar estructura de datos para análisis de código

**Clases principales:**
- `FunctionInfo` - Dataclass que representa información de una función
- `ClassInfo` - Dataclass que representa información de una clase
- `ParseResult` - Dataclass que contiene el resultado del parsing (funciones y clases)
- `PythonFileParser` - Parser principal que analiza archivos Python

**Información extraída de funciones:**
- Nombre de la función
- Lista de parámetros
- Docstring (documentación)
- Decoradores aplicados
- Número de línea en el archivo

**Información extraída de clases:**
- Nombre de la clase
- Clases base (herencia)
- Lista de métodos
- Docstring (documentación)
- Número de línea en el archivo

### `__init__.py`
**Función:** Marca el directorio como un paquete Python.

## Diagrama de Uso

```
┌─────────────────────────────────────────────────────────┐
│                  Archivo Python (.py)                    │
│  class MyClass:                                          │
│      def my_method(self, param1):                        │
│          """Docstring"""                                 │
│          pass                                            │
└────────────────────┬────────────────────────────────────┘
                     │
                     │ lee y parsea
                     ▼
            ┌────────────────────┐
            │ PythonFileParser   │
            │  (python_parser.py)│
            └─────────┬──────────┘
                      │
                      │ usa AST
                      ▼
            ┌────────────────────┐
            │   ast.parse()      │
            │   (Python stdlib)  │
            └─────────┬──────────┘
                      │
                      │ extrae
                      ▼
        ┌─────────────┴─────────────┐
        │                           │
        ▼                           ▼
┌───────────────┐         ┌────────────────┐
│ FunctionInfo  │         │   ClassInfo    │
│ - name        │         │   - name       │
│ - params      │         │   - bases      │
│ - docstring   │         │   - methods    │
│ - decorators  │         │   - docstring  │
└───────────────┘         └────────────────┘
        │                           │
        └─────────────┬─────────────┘
                      ▼
            ┌────────────────────┐
            │   ParseResult      │
            │   - functions: []  │
            │   - classes: []    │
            └────────────────────┘
```

## Ejemplo de Uso

```python
from app.utils.python_parser import PythonFileParser

# Crear parser
parser = PythonFileParser()

# Parsear archivo
result = parser.parse_file("mi_archivo.py")

# Acceder a funciones encontradas
for func in result.functions:
    print(f"Función: {func.name}")
    print(f"Parámetros: {func.params}")
    print(f"Docstring: {func.docstring}")

# Acceder a clases encontradas
for cls in result.classes:
    print(f"Clase: {cls.name}")
    print(f"Métodos: {[m.name for m in cls.methods]}")
```

## Casos de Uso

Este parser puede ser útil para:
- Análisis estático de código
- Generación automática de documentación
- Herramientas de refactoring
- Análisis de calidad de código
- Extracción de métricas de código
- Generación de diagramas de clases

## Tecnologías Utilizadas

- **ast** (Abstract Syntax Tree) - Módulo estándar de Python para parsing
- **dataclasses** - Para definir estructuras de datos inmutables
- **typing** - Para anotaciones de tipos

## Relaciones con otros módulos

- **Depende de:** Módulos estándar de Python (ast, dataclasses, typing)
- **Usado por:** Potencialmente cualquier módulo que necesite analizar código Python
- **Independiente:** No tiene dependencias con otros módulos de la aplicación
