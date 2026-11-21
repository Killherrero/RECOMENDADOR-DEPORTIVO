"""Parejas editoriales exactas y documentadas, separadas por deporte."""
import json
import re
from .config import ROOT
from .perfiles import normalizar, identidad_basket

REGISTRO = json.loads((ROOT/'data/rivalidades.json').read_text(encoding='utf-8'))
ALIAS = {
    'real madrid cf':'real madrid', 'barcelona':'fc barcelona', 'barca':'fc barcelona',
    'at madrid':'atletico madrid', 'atletico de madrid':'atletico madrid',
    'sevilla':'sevilla fc', 'real betis':'betis', 'real betis balompie':'betis',
    'athletic club':'athletic', 'athletic bilbao':'athletic',
    'manchester utd':'manchester united', 'man utd':'manchester united',
    'tottenham hotspur':'tottenham', 'fc bayern':'bayern munich',
    'bayern munchen':'bayern munich', 'fc bayern munchen':'bayern munich',
    'schalke 04':'schalke04', 'fc schalke 04':'schalke04',
    'inter':'inter milan', 'internazionale':'inter milan',
    'cadiz cf':'cadiz', 'xerez cd':'xerez-cd', 'xerez c d':'xerez-cd',
}
ALIAS.update(json.loads((ROOT/'data/alias_rivalidades.json').read_text(encoding='utf-8')))


def ambito_selecciones(evento):
    comp = normalizar(evento.get('competicion', ''))
    return any(t in comp for t in ('mundial', 'world cup', 'eurocopa', 'copa america',
                                  'nations league', 'selecciones', 'international friendly',
                                  'amistoso internacional', 'eliminatorias mundial', 'european qualifiers'))


def identidad(evento, campo):
    nombre = normalizar(evento[campo])
    if evento['deporte'] == 'Baloncesto':
        return identidad_basket(nombre)
    if nombre == 'xerez':
        from .contexto import valorar_contexto
        c = evento.get('contexto', {})
        if (c.get('tipo') == 'copa' and c.get(campo, {}).get('id') == '3835'
                and valorar_contexto(evento).get('estado') == 'validado'):
            return 'xerez-cd'
    # La abreviatura Xerez solo queda resuelta para la ficha oficial contrastada.
    if (nombre == 'xerez' and evento.get('fecha') == '2026-10-28'
            and evento.get('hora') == '21:00'
            and 'copa del rey' in normalizar(evento.get('competicion', ''))
            and normalizar(evento['visitante' if campo == 'local' else 'local']) in ('cadiz','cadiz cf')):
        return 'xerez-cd'
    return ALIAS.get(nombre, nombre)


def valorar_rivalidad(evento):
    vacio = {'ajuste': 0.0, 'estado': 'sin pareja verificada'}
    if evento['deporte'] not in ('Fútbol', 'Baloncesto'):
        return vacio
    # Nunca heredar la rivalidad de los primeros equipos a filiales o categorías juveniles.
    texto = ' '.join(normalizar(evento.get(k, '')) for k in ('local','visitante','competicion','descripcion'))
    if re.search(r'\b(?:femenin[oa]|women|u\s*\d{2}|sub\s*\d{2}|juvenil|junior)\b', texto):
        return vacio
    pareja = {identidad(evento, k) for k in ('local','visitante')}
    for r in REGISTRO:
        if r.get('ambito') == 'selecciones' and not ambito_selecciones(evento):
            continue
        if r['deporte'] == evento['deporte'] and pareja == set(r['equipos']):
            limite = {'maxima':2.2, 'destacada':1.2}.get(r.get('intensidad'), .6)
            return {**r, 'ajuste': min(limite, r['bonus']), 'estado': 'verificada'}
    return vacio
