"""Enlaces de revisión manual en Google Calendar, sin acceso ni escritura a cuentas."""
from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode

from .config import MADRID_TZ
from .horarios import duracion_evento
from .canales import canal_texto
from .estado_eventos import programable


def fecha_con_zona(valor):
    if isinstance(valor, str):
        valor = datetime.fromisoformat(valor)
    if not isinstance(valor, datetime):
        raise ValueError('Fecha no válida')
    return valor.replace(tzinfo=MADRID_TZ) if valor.tzinfo is None else valor


def enlace_calendario(evento, inicio=None, fin=None, tramo=False):
    """Vacío sin fecha cierta. El enlace abre un formulario; nunca guarda eventos."""
    if not programable(evento):
        return ''
    try:
        comienzo = fecha_con_zona(inicio if inicio is not None else
                                 evento.get('inicio') or f"{evento['fecha']}T{evento['hora']}")
        if fin is not None:
            final = fecha_con_zona(fin)
        elif evento.get('fin_estimado'):
            final = fecha_con_zona(evento['fin_estimado'])
        else:
            duracion = duracion_evento(evento)
            final = datetime.fromtimestamp(comienzo.timestamp() + duracion*60, MADRID_TZ)
        if final.timestamp() <= comienzo.timestamp():
            return ''
    except (KeyError, TypeError, ValueError, OverflowError):
        return ''
    nombre = (f"{evento['local']} — {evento['visitante']}" if evento.get('local')
              else evento.get('descripcion') or evento.get('competicion','Deporte'))
    titulo = f"{nombre} · {evento.get('competicion','')}"
    if tramo:
        titulo = 'Ver: ' + titulo
    canales = ' · '.join(canal_texto(c) for c in evento.get('canales',[])) or 'Canal por confirmar'
    detalle = ['Tu día de deporte',
               'Tramo recomendado del planning; no es el partido completo.' if tramo else
               'Partido completo. Final y duración estimados; pueden variar.',
               'Canales: ' + canales,
               'Zona horaria de referencia: Europe/Madrid.']
    detalle.extend(evento.get('explicacion',{}).get('motivos',[])[:3])
    detalle.extend(['Agenda: https://www.futbolenlatv.es/deporte',
                    'Elige el calendario Partidazos y revisa las horas antes de guardar.',
                    'Este enlace no sincroniza cambios posteriores de horario.'])
    formato = lambda d:d.astimezone(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    return 'https://calendar.google.com/calendar/render?' + urlencode({
        'action':'TEMPLATE','text':titulo,'dates':formato(comienzo)+'/'+formato(final),
        'ctz':'Europe/Madrid','stz':'Europe/Madrid','etz':'Europe/Madrid',
        'details':'\n'.join(detalle)})
