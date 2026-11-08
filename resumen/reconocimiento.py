"""Reconocimiento editorial moderado; las fuentes no dictan estos pesos."""
import json
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
