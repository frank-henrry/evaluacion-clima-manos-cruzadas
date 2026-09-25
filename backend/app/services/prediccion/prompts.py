"""Prompts del Agente Analista (SPEC 06).

`SYSTEM_PROMPT` y la plantilla del mensaje de usuario son literales del SPEC 06
§4; no se reescriben aqui. Funciones puras: sin red, sin BD, sin logs.
"""

from datetime import date

from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage

from app.models.prediccion import ContextoCalendario, ContextoClima, ResumenHistorico

SYSTEM_PROMPT = (
    "Eres un experto en gestión turística del sitio arqueológico de Kotosh "
    "(Las Manos Cruzadas), en Huánuco, Perú.\n"
    "Tu tarea es estimar el número de visitantes para una fecha usando SOLO el "
    "contexto y los datos históricos que se te entregan.\n"
    "Reglas:\n"
    "- No inventes datos históricos ni eventos que no estén en el contexto.\n"
    "- Considera el día de la semana, el clima, los feriados/fiestas locales y "
    "la temporada (escolar o vacacional).\n"
    '- Si la fuente del clima es "estimado_historico", indica que la confianza '
    "es menor y amplía el rango.\n"
    "- Si el nivel de coincidencia histórica es 3 o 4, amplía el rango y "
    "menciónalo.\n"
    "- rango_minimo <= prediccion_estimada <= rango_maximo, todos enteros >= 0.\n"
    "- razonamiento_explicado: máximo 3 oraciones, en español."
)

USER_PROMPT_TEMPLATE = (
    "Contexto actual: El usuario quiere predecir el flujo para el {fecha}. "
    "Es {dia_semana}.\n"
    "El pronóstico es de {temperatura_max}°C y {condicion_clima} "
    "(fuente: {fuente}).\n"
    "Feriado/fiesta: {nombre_feriado}. Temporada: {temporada}.\n"
    "Datos históricos recuperados (nivel {nivel_coincidencia}): {resumen_texto}\n"
    "Instrucción: Analiza estos datos y estima una cifra concreta de visitantes."
)

# Valor de `{nombre_feriado}` cuando la fecha no es feriado ni fiesta local.
SIN_FERIADO = "ninguno"


def construir_mensajes(
    fecha: date,
    clima: ContextoClima,
    calendario: ContextoCalendario,
    historicos: ResumenHistorico,
) -> list[BaseMessage]:
    """Devuelve `[SystemMessage(SYSTEM_PROMPT), HumanMessage(plantilla rellena)]`.

    `fecha` se formatea en ISO (`YYYY-MM-DD`); `nombre_feriado` None -> "ninguno".
    """
    contenido = USER_PROMPT_TEMPLATE.format(
        fecha=fecha.isoformat(),
        dia_semana=calendario.dia_semana,
        temperatura_max=clima.temperatura_max,
        condicion_clima=clima.condicion_clima,
        fuente=clima.fuente,
        nombre_feriado=calendario.nombre_feriado or SIN_FERIADO,
        temporada=calendario.temporada,
        nivel_coincidencia=historicos.nivel_coincidencia,
        resumen_texto=historicos.resumen_texto,
    )
    return [SystemMessage(content=SYSTEM_PROMPT), HumanMessage(content=contenido)]
