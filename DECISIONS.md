# DECISIONS.md - Decisiones Técnicas

Este documento explica las decisiones técnicas más relevantes del proyecto.

## ¿Por qué PostgreSQL?

- **Confiabilidad**: PostgreSQL es una base de datos relacional robusta y probada en producción
- **Características**: Soporta tipos avanzados, índices compuestos, transacciones ACID
- **Escalabilidad**: Railway proporciona PostgreSQL gestionado con alta disponibilidad
- **Ecosistema**: Amplia documentación y soporte comunitario

## ¿Por qué refresh tokens con rotación?

- **Seguridad**: Los access tokens de corta duración (15 min) limitan el daño si son comprometidos
- **UX**: Los usuarios no necesitan login frecuentemente gracias al refresh token
- **Rotación**: Cada uso del refresh token genera uno nuevo, invalidando el anterior
- **Revocación**: Posibilidad de invalidar tokens en logout o por sospecha de compromiso

## ¿Por qué paginación con cursor en lugar de offset?

- **Rendimiento**: offset es lento en tablas grandes porque salta filas
- **Consistencia**: Cursor-based pagination es más estable cuando hay datos nuevos entre páginas
- **Estandar cursor**: Usamos el ID de la última tarea como cursor

## ¿Por qué structlog para logging?

- **Formato estructurado**: JSON con campos definidos (request_id, método, ruta, duración)
- **Trazabilidad**: Cada request tiene un request_id único para hacer tracking
- **Integración**: Funciona bien con Sentry y sistemas de log централизованный

## ¿Por qué rate limiting con slowapi?

- **Facilidad**: Integración nativa con FastAPI
- **Flexibilidad**: Límites por IP y por endpoint configurables
- **UX**: Respuestas claras con código 429 cuando se excede el límite

## ¿Por qué Railway?

- **Gestionado**: No necesitamos gestionar infraestructura
- **PostgreSQL + Redis**: Soporte nativo para ambos
- **Deploy automático**: Integración con GitHub
- **Variables de entorno**: Configuración segura sin código

## ¿Por qué división CRUD/Servicios?

- **Separación de responsabilidades**: CRUD solo acceso a datos, servicios orquestan lógica
- **Testabilidad**: Más fácil testear lógica de negocio aislada
- **Mantenibilidad**: Cambios en reglas de negocio no tocan código de DB

## ¿Por qué versionado API con /api/v1/?

- **Futuro**: Permite mantener múltiples versiones concurrently
- **Breaking changes**: Nueva versión sin afectar clientes existentes
- **Claridad**: Endpoints claramente diferenciados por versión
