# 🏗️ Arquitectura y Principios de Funcionamiento / System Architecture

Esta documentación explica los principios técnicos de funcionamiento de la aplicación de Verificación de Hash de FORVIS MAZARS y detalla el proceso interno de consulta de hashes.

*This documentation explains the technical operating principles of the FORVIS MAZARS Hash Verification application and details the internal hash query process.*

---

## 🧩 Principios Fundamentales / Core Principles

La aplicación funciona bajo un modelo **Cliente-Servidor (Client-Server)** y utiliza un sistema de almacenamiento basado en archivos (**File-based Storage**) en lugar de una base de datos relacional tradicional.

### 1. Almacenamiento de Datos (Data Storage)
El sistema no utiliza SQL ni NoSQL. En su lugar, utiliza el sistema de archivos local para almacenar metadatos en formato JSON.
- **Ubicación**: Directorio `output/`.
- **Estructura**:
  - Cada usuario tiene su propio subdirectorio (`output/{user_id}/`).
  - Cada documento se almacena como un archivo JSON independiente (`metadata_{HASH}_{TRACEID}.json`).
- **Ventaja**: Portabilidad total y facilidad de backup sin dependencias externas.

### 2. Identificación Única (Unique Identification)
Cada documento se identifica por dos claves principales:
- **Full Hash (Código Completo)**: Formato `XX-XXXXXXXXXXXX` (Ej: `CM-A1B2C3D4E5F6`).
  - Los primeros 2 caracteres indican el tipo de documento.
- **Short Code (Código Corto)**: Formato `XXXXXX` (6 caracteres).
  - Se deriva algorítmicamente del hash completo (tomando caracteres en posiciones pares).

---

## 🔍 Lógica de Consulta de Hash / Hash Query Logic

Cuando un usuario introduce un código en el frontend, sucede el siguiente flujo:

### Paso 1: Interacción Frontend (Browser)
1. El usuario ingresa el código (ej: `CM-A1B2...` o `ABCDEF`) en `index.html`.
2. El script `app.js` detecta el formato:
   - Valida si cumple el patrón de **Hash Completo** (Regex: `/^[A-Z]{2}-[A-Z0-9]{12}$/`).
   - O si cumple el patrón de **Código Corto** (Regex: `/^[A-Z0-9]{6}$/`).
3. Envía una petición GET a la API: `/api/verify/{hash_code}`.

### Paso 2: Procesamiento en Backend (FastAPI)
El backend (`main.py`) recibe el código y ejecuta la función `verify_hash`:

1. **Normalización**: Convierte el input a mayúsculas y elimina espacios.
2. **Determinación de Tipo**:
   - Si es un Hash Completo, llama a `search_by_hash()`.
   - Si es un Código Corto, llama a `search_by_short_code()`.

### Paso 3: Algoritmo de Búsqueda (Search Algorithm)
Como no hay índice de base de datos, el sistema realiza una **Búsqueda Iterativa (Linear Scan)**:

```python
def search_by_hash(hash_code, output_dir):
    # 1. Iterar sobre cada carpeta de usuario en output/
    for user_dir in output_dir.iterdir():
        
        # 2. Iterar sobre todos los archivos JSON en esa carpeta
        for metadata_file in user_dir.glob("metadata_*.json"):
            
            # 3. Leer y parsear el JSON
            metadata = json.load(f)
            
            # 4. Comparar hash almacenado con el buscado
            if metadata["hash_info"]["hash_code"] == hash_code:
                return metadata  # ¡Encontrado!
    
    return None  # No encontrado
```

> **Nota Técnica**: Aunque la búsqueda es lineal O(N), para el volumen esperado de documentos es extremadamente rápida debido a la velocidad de lectura del sistema de archivos moderno.

---

## 🛡️ Verificación de Integridad / Integrity Verification

Además de buscar el hash, el sistema puede verificar si un PDF ha sido modificado:

1. El usuario sube el archivo PDF original.
2. El backend calcula el **SHA-256** de los bytes del archivo subido.
3. Busca el metadato correspondiente usando el código hash proporcionado.
4. Compara el SHA-256 calculado con el `content_hash` almacenado en el JSON original.
   - **Coinciden**: El documento es auténtico.
   - **No coinciden**: El documento ha sido alterado.

---

## 📊 Diagrama de Flujo de Datos / Data Flow

```mermaid
graph TD
    User([Usuario]) -->|1. Ingresa Hash| Frontend[Frontend (JS)]
    Frontend -->|2. GET /api/verify/XYZ| API[FastAPI Backend]
    
    API -->|3. Escanea Directorios| Storage[(File System /output)]
    
    Storage -->|4. Lee JSONs| API
    
    subgraph Search Logic
    API -- Identifica --> FullHash{Es Hash Completo?}
    FullHash -- Sí --> MatchFull[Busca coincidencia exacta]
    FullHash -- No --> MatchShort[Genera ShortCode y compara]
    end
    
    API -->|5. Retorna Metadata| Frontend
    Frontend -->|6. Muestra Certificado| User
```
