1. Información General
Módulo / Característica: Consulta Meteorológica.

Actor Principal: Usuario autenticado.

Objetivo: Permitir al usuario visualizar el estado del clima de una ciudad específica para facilitar la planificación de sus actividades.

2. Requerimientos Funcionales
El sistema debe validar que el usuario cuente con una sesión activa antes de permitir la consulta.

La interfaz (UI) debe proporcionar un componente de selección (menú desplegable) con las ciudades disponibles.

Las ciudades disponibles deben ser Huánuco, Perú y Tingo María, Perú.

La UI debe incluir un botón de acción etiquetado como "Consultar" para disparar la petición.

El sistema debe integrarse con un proveedor externo del clima (WeatherAPI) para obtener los datos en tiempo real.

La aplicación debe renderizar la información meteorológica obtenida de forma clara (Temperatura, Estado, Humedad).

3. Criterios de Aceptación (Formato BDD / Gherkin)
Escenario 1: Consulta exitosa del clima para una ciudad seleccionada.

Dado que el usuario se encuentra logueado en el sistema y está ubicado en la vista de consulta meteorológica. Cuando selecciona Huánuco o Tingo María. Y presiona el botón "Consultar"
Entonces el sistema realiza la búsqueda y muestra correctamente los datos del clima de la ubicación seleccionada.

Escenario 2: Intento de consulta sin sesión activa (Opcional pero recomendado).

Dado que un usuario sin autenticar intenta acceder a la funcionalidad Cuando intenta realizar una consulta.
Entonces el sistema debe bloquear la acción y redirigirlo a la pantalla de inicio de sesión.

4. Diseño de API
Endpoint: GET /api/v1/weather
Query Params: ?location={city_name}
Headers: Authorization: Bearer <token_jwt>
Respuesta Exitosa (200 OK):

JSON
{
  "location": "Huanuco",
  "temperature": "24°C",
  "condition": "Despejado",
  "humidity": "60%"
}
