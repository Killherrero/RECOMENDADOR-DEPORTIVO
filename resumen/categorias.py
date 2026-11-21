"""Categorías verificadas y valores neutrales cuando faltan metadatos."""
import json
import re
import unicodedata
from datetime import datetime
from functools import lru_cache

from .config import ROOT, MADRID_TZ

def normalizar(texto):
    return ''.join(c for c in unicodedata.normalize('NFD', texto.casefold())
                   if unicodedata.category(c) != 'Mn')

@lru_cache(maxsize=1)
def catalogo_tenis():
    return json.loads((ROOT/'data/torneos_tenis.json').read_text(encoding='utf-8'))

def categoria_tenis(evento):
    comp = normalizar(evento['competicion'])
    if re.search(r'\b(?:wta|challenger|itf|junior|qualifying|qualy)\b', comp):
        return None, 'Sin categoría ATP principal reconocida'
    if re.search(r'\b(?:next[ -]?gen|next generation|dobles|doubles)\b', comp):
        return None, 'Fuera del circuito ATP principal de individuales'
    if re.search(r'\batp(?: world tour)? finals\b', comp):
        return 'ATP Finals', 'Categoría oficial ATP Finals: ' + catalogo_tenis()['fuente_atp_finals']
    for patron, categoria in [(r'\bgrand slam\b', 'Grand Slam'),
                               (r'\b(?:atp\s+)?masters\s+1000\b', 'Masters 1000'),
                               (r'\batp\s*500\b', 'ATP 500'),
                               (r'\batp\s*250\b', 'ATP 250')]:
        if re.search(patron, comp):
            return categoria, 'Categoría publicada por la fuente'
    catalogo = catalogo_tenis()
    temporada = int(evento['fecha'][:4]) if evento.get('fecha') else datetime.now(MADRID_TZ).year
    if temporada == catalogo['temporada']:
        for torneo in catalogo['torneos']:
            if any(re.search(r'(?<!\w)' + re.escape(normalizar(alias)) + r'(?!\w)', comp)
                   for alias in torneo['alias']):
                return torneo['categoria'], f"Categoría verificada en calendario ATP {temporada}"
    return None, 'Categoría no identificada: sin penalización por datos ausentes'

def bonus_categoria_tenis(evento):
    categoria, _ = categoria_tenis(evento)
    return {'ATP Finals':3.5, 'Grand Slam':4, 'Masters 1000':3, 'ATP 500':2, 'ATP 250':1}.get(categoria, 0)


def segunda_ronda_octavos(evento):
    """Solo cuadros de individuales de 32 publicados para la edición concreta."""
    if evento.get('deporte') != 'Tenis':return False
    comp = normalizar(evento['competicion'])
    if re.search(r'\b(?:dobles|doubles|qualifying|qualy|wta|challenger|itf|junior)\b', comp):return False
    if not re.search(r'\b(?:2[ªaº]?\s*ronda|segunda ronda)\b',comp):return False
    catalogo = catalogo_tenis()
    if not evento.get('fecha') or int(evento['fecha'][:4]) != catalogo['temporada']:return False
    return any(t.get('cuadro_individual') == 32 and
               any(re.search(r'(?<!\w)' + re.escape(normalizar(a)) + r'(?!\w)',comp) for a in t['alias'])
               for t in catalogo['torneos'])
