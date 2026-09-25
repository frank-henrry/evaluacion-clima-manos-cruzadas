# Casos de prueba

La suite automatizada cubre los siguientes comportamientos:

| Área | Caso | Resultado esperado |
| --- | --- | --- |
| Validación | Correo y contraseña vacíos | Muestra ambos errores sin llamar al backend |
| Validación | Correo con espacios o formato inválido | Muestra un error asociado al campo |
| Login | Credenciales válidas | Envía `POST /auth/login` y abre la consulta meteorológica |
| Login | Respuesta 401 | Muestra un mensaje genérico que no filtra detalles |
| Clima | Sin ciudad seleccionada | `Consultar` permanece deshabilitado |
| Clima | Consulta en curso | Deshabilita controles y anuncia `Consultando…` |
| Clima | Respuesta correcta | Renderiza ubicación, temperatura, estado y humedad |
| Clima | Error recuperable | Muestra un alert y permite reintentar |
| Sesión | Respuesta 401 al consultar | Descarta el JWT, vuelve al login y avisa la expiración |
| Seguridad | Petición de clima | Envía el JWT mediante `Authorization: Bearer` |

Ejecutar con `npm test` desde `frontend/`.
