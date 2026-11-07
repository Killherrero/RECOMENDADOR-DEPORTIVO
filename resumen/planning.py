"""Propuestas de visionado opcionales, sin modificar notas ni selección."""
from datetime import datetime
from .horarios import intervalo
from .config import MADRID_TZ
from .calendario import enlace_calendario
from .estado_eventos import programable


def nombre(e):
    return f"{e['local']} — {e['visitante']}" if e.get('local') else e.get('descripcion') or e['competicion']


def reloj(minutos, e):
    if 'inicio_vision' in e:
        return datetime.fromtimestamp(minutos * 60, MADRID_TZ).strftime('%H:%M')
    return f'{int(minutos // 60) % 24:02d}:{int(minutos % 60):02d}'


def crear_planning(eventos, seleccionados, clave):
    principales = sorted((e for e in seleccionados if programable(e)), key=lambda e: intervalo(e)[0])
    ids = {clave(e) for e in principales}
    bloques = []
    ocupados = []

    def agregar(e, tipo, a, b, detalle):
        bloques.append(dict(tipo=tipo, evento=nombre(e), desde=reloj(a, e), hasta=reloj(b, e),
                            detalle=detalle, inicio=a))
        if 'inicio' in e:
            enlace = enlace_calendario(e, datetime.fromtimestamp(a*60, MADRID_TZ),
                                      datetime.fromtimestamp(b*60, MADRID_TZ), tramo=True)
            if enlace: bloques[-1]['calendario_url'] = enlace
        ocupados.append((a, b))

    # Los solapamientos tolerados por el selector se convierten en un cambio explícito.
    for i, e in enumerate(principales):
        a, b = intervalo(e)
        if i + 1 < len(principales):
            b = min(b, intervalo(principales[i + 1])[0])
        agregar(e, 'Cita principal', a, b, 'Prioriza esta cita. Final estimado.' if b == intervalo(e)[1]
                else 'Cambia a la siguiente cita a esta hora; dejarías el final sin ver.')

    secundarios = sorted((e for e in eventos if programable(e) and clave(e) not in ids and e['score'] >= 4.5
                          and not e.get('madrugada')),
                         key=lambda e: -e.get('prioridad', e['score']))
    usados = set()
    # Como máximo un aperitivo por cita; al menos media hora y como máximo una hora.
    for principal in principales:
        comienzo = intervalo(principal)[0]
        for e in secundarios:
            a, b = intervalo(e)
            desde = max(a, comienzo - 60)
            if (clave(e) not in usados and a < comienzo < b and comienzo - desde >= 30
                    and all(min(comienzo, y) <= max(desde, x) for x, y in ocupados)):
                agregar(e, 'Aperitivo opcional', desde, comienzo,
                        'Solo si te apetece. Cambia a ' + nombre(principal) + ' a las ' + reloj(comienzo, principal) + '; no verías el partido completo.')
                usados.add(clave(e))
                break
    # Una sola opción de fondo, sin rellenar toda la jornada ni alargar la noche.
    for e in secundarios:
        a, b = intervalo(e)
        hora = int(reloj(a, e).split(':')[0])
        if (clave(e) not in usados and hora < 22 and not e.get('vision_parcial')
                and all(min(b, y) <= max(a, x) for x, y in ocupados)):
            agregar(e, 'De fondo · opcional', a, b,
                    'Si acompaña lo que estés haciendo; no hace falta reservarle tiempo.')
            break
    bloques.sort(key=lambda b: b['inicio'])
    return bloques


def lineas_planning(bloques):
    return [f"{b['desde']}–{b['hasta']} · {b['tipo']} · {b['evento']}. {b['detalle']}"
            + ('\n  Añadir tramo a Google Calendar (elige Partidazos): ' + b['calendario_url'] if b.get('calendario_url') else '')
            for b in bloques]
