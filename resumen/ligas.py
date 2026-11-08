"""Identidad explícita antes de nombres compartidos por distintos países."""
import re
from .perfiles import normalizar


def liga_futbol(competicion):
    comp = normalizar(competicion)
    if 'bundesliga' in comp:
        if re.search(r'\b(?:admiral|tipico|austria|austrian|osterreich)\b', comp):
            return 'aut.1'
        if re.search(r'\b2\s+bundesliga\b', comp):
            return 'ger.2'
        if re.fullmatch(r'bundesliga(?: (?:jornada|liga regular|regular season)\b.*)?', comp) or re.search(r'\b(?:alemania|alemana|german|deutsche)\b', comp):
            return 'ger.1'
        return None
    for palabras, liga in [(('jupiler','liga belga','belgian pro league'),'bel.1'),
                           (('eredivisie',),'ned.1'), (('liga portuguesa','primeira liga'),'por.1')]:
        if any(t in comp for t in palabras):
            return liga
    return None
