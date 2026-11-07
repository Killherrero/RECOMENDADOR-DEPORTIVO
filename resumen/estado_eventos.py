"""Estado de la fuente: una fecha escrita no hace programable un aplazado."""
import re
from .perfiles import normalizar


def estado_evento(evento):
    textos = [evento.get(k, '') for k in ('estado', 'estado_fuente', 'status', 'competicion', 'descripcion')]
    textos.extend(evento.get('canales') or [])
    texto = normalizar(' '.join(str(t) for t in textos))
    for patron, estado in [
        (r'\b(?:aplazad[oa]|postponed|eventpostponed)\b', 'aplazado'),
        (r'\b(?:cancelad[oa]|cancelled|canceled|eventcancelled)\b', 'cancelado'),
        (r'\b(?:suspendid[oa]|suspended|abandoned)\b', 'suspendido'),
        (r'\b(?:fecha por confirmar|horario por confirmar|sin fecha|fecha pendiente|eventrescheduled)\b', 'sin fecha confirmada'),
    ]:
        if re.search(patron, texto):
            return estado
    if any(normalizar(str(evento.get(k,''))) in ('por confirmar','pendiente','tbd') for k in ('estado','status','hora')):
        return 'sin fecha confirmada'
    return 'programado'


def programable(evento):
    return estado_evento(evento) == 'programado'
