# TaskFlow API

API REST con FastAPI y JWT para autenticación de usuarios.

## Características

- Registro de usuarios
- Login con JWT
- Actualización de perfil
- Base de datos PostgreSQL
- Documentación automática con Swagger

## Instalación local

```bash
# Crear entorno virtual
python -m venv venv
source venv/bin/activate  # Linux/Mac
# En Windows: venv\Scripts\activate

# Instalar dependencias
pip install -r requirements.txt

# Configurar variables de entorno
cp .env.example .env
# Editar .env con tu configuración

# Ejecutar servidor
uvicorn app.main:app --reload
```

## Endpoints

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| POST | `/auth/register` | Registrar nuevo usuario |
| POST | `/auth/login` | Login y obtener token JWT |
| GET | `/users/me` | Obtener perfil del usuario actual |
| PUT | `/users/me` | Actualizar perfil del usuario |

## Documentación

Accede a `/docs` para ver la documentación Swagger interactiva.

## Despliegue

Desplegado en Railway: [URL aquí]

## Tests

```bash
pytest
```
