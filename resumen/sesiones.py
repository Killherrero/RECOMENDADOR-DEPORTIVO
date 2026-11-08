"""Sesiones de motor y finales de selecciones de pádel, sin inferir fases."""
import re
from .perfiles import normalizar


def sesion_motor(evento):
    if evento.get('deporte') not in ('Automovilismo', 'Motociclismo'):
        return None
    texto = normalizar(evento.get('competicion', '') + ' ' + evento.get('descripcion', ''))
    categoria = ('F1' if re.search(r'\b(?:f1|formula\s*1)\b', texto) else
                 'MotoGP' if re.search(r'\bmotogp\b', texto) else
                 'NASCAR Cup' if re.search(r'\bnascar cup series\b', texto) and 'enascar' not in texto else None)
    if not categoria:
        return None
    if re.search(r'\b(?:libres?|entrenamientos?|practice|warm up|fp[123])\b', texto):
        tipo = 'entrenamientos'
    elif re.search(r'\b(?:clasificacion|qualifying|qualy|shootout|q[12])\b', texto):
        tipo = 'clasificacion'
    elif re.search(r'\bsprint\b', texto):
        tipo = 'sprint'
    elif re.search(r'\b(?:carrera|race)\b', texto):
        tipo = 'carrera'
    else:
        return None
    notas = {'entrenamientos':4.7, 'clasificacion':5.4, 'sprint':6.0, 'carrera':6.4}
    if categoria == 'MotoGP':
        notas = {**notas, 'entrenamientos':4.0, 'clasificacion':5.0}
    if categoria == 'NASCAR Cup':
        notas = {'entrenamientos':3.5, 'clasificacion':4.2, 'sprint':5.2, 'carrera':5.2}
    duraciones = {'entrenamientos':75, 'clasificacion':75 if categoria == 'F1' else 60,
                  'sprint':45, 'carrera':150 if categoria == 'F1' else 60}
    if categoria == 'NASCAR Cup':
        duraciones = {'entrenamientos':75,'clasificacion':75,'sprint':180,'carrera':180}
    return {'categoria':categoria, 'tipo':tipo, 'base':notas[tipo], 'duracion':duraciones[tipo],
            **({'importancia_titulo':'Sin verificar; Championship no añade bonus'} if categoria == 'NASCAR Cup' else {})}


def final_padel_espana(evento):
    if normalizar(evento.get('deporte', '')) != 'padel':
        return False
    texto = normalizar(evento.get('competicion', '') + ' ' + evento.get('descripcion', ''))
    if re.search(r'\b(?:semi\s*final(?:es|s)?|semifinal(?:es|s)?|quarter\s*finals?|cuartos|octavos|fase final|1\s+[248]|sub\s*\d+|u\s*\d+|junior|juvenil)\b', texto):
        return False
    return (bool(re.search(r'\bfinal\b', texto)) and
            any(t in texto for t in ('mundial', 'campeonato del mundo', 'world cup', 'world championship', 'europeo', 'european championship')) and
            any(normalizar(evento.get(k,'')) in ('espana','spain','espana femenino','espana femenina','spain women')
                for k in ('local','visitante')))
