"""Reconocimiento editorial moderado; las fuentes no dictan estos pesos."""
import json
import re
from .config import ROOT
from .perfiles import normalizar, identidad_basket

PERFILES = json.loads((ROOT/'data/perfiles_futbol.json').read_text(encoding='utf-8'))
PERFILES_ACB = json.loads((ROOT/'data/perfiles_acb.json').read_text(encoding='utf-8'))


def perfiles_acb(evento):
    comp = normalizar(evento.get('competicion',''))
    if (evento.get('deporte') != 'Baloncesto' or
            not any(t in comp for t in ('endesa','acb','copa del rey')) or
            any(t in comp for t in ('minicopa','juvenil','junior'))):
        return []
    return [{**p,'lado':lado} for lado in ('local','visitante') for p in PERFILES_ACB
            if identidad_basket(evento.get(lado,'')) == p['id']]


def perfiles_futbol(evento):
    if evento.get('deporte') != 'Fútbol':
        return []
    comp = normalizar(evento.get('competicion',''))
    parejas = []
    for lado in ('local','visitante'):
        nombre = normalizar(evento.get(lado,''))
        for p in PERFILES:
            if p.get('ambito') == 'argentina' and 'argentina' not in comp:
                continue
            if nombre in p['alias']:
                parejas.append({**p, 'lado':lado})
                break
    return parejas


def fase_argentina(evento, ronda, fase):
    """Edición AFA 2026: sustitución acotada del peso de eliminatorias a partido único."""
    comp = normalizar(evento.get('competicion', ''))
    if (evento.get('deporte') != 'Fútbol' or 'primera division argentina' not in comp
            or not str(evento.get('fecha') or '').startswith('2026-')
            or re.search(r'\b(?:ida|vuelta|sub\s*\d+|u\s*\d+|femenin[oa]|women|juvenil|junior)\b', comp)):
        return None
    pesos = {1.0:1.2, 1.5:1.6, 2.0:2.0, 2.5:2.4}
    if ronda not in pesos:
        return None
    return dict(ajuste=max(fase, pesos[ronda]), formato='Eliminatoria a partido único',
                fuente='https://assets1.afa.com.ar/2026/BOLETINES/Boletin-Resoluciones-6818---Complementario-01---Reglamento-Torneos-LPF-Primera-2026.pdf',
                temporada=2026)
