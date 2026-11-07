"""Reconocimiento editorial moderado; las fuentes no dictan estos pesos."""
import json
from .config import ROOT
from .perfiles import normalizar

PERFILES = json.loads((ROOT/'data/perfiles_futbol.json').read_text(encoding='utf-8'))


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
