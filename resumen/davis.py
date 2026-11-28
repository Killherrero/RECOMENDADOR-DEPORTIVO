"""Copa Davis absoluta: selecciones y partidos de eliminatoria, no ranking ATP."""
import re
from .perfiles import normalizar


def eliminatoria_davis(evento):
    if evento.get('deporte') != 'Tenis':
        return None
    comp = normalizar(evento.get('competicion', ''))
    if not re.search(r'\b(?:davis cup|copa davis)\b', comp):
        return None
    if re.search(r'\b(?:junior|juvenil|sub\s*\d+|u\s*\d+|qualif\w*|clasifica\w*|previa)\b', comp):
        return None
    fase = ('semifinal' if re.search(r'\bsemi\s*final\w*\b', comp) else
            'cuartos' if re.search(r'\bcuartos\b|\bquarter\s*final\w*\b|\b1 4\b', comp) else
            'final' if re.search(r'\bfinal\b', comp) else None)
    if not fase:
        return None
    espana = any(normalizar(evento.get(k,'')) in ('espana','spain','seleccion espanola') for k in ('local','visitante'))
    # En Final 8 el tercer partido (dobles) solo es necesario con empate.
    condicional = bool(re.search(r'\b(?:partido|match) 3\b|\b(?:dobles|doubles)\b', comp))
    return dict(fase=fase, espana=espana, condicional=condicional,
                fuente='https://www.daviscup.com/en/news/schedule-confirmed-for-davis-cup-by-generali-final-8')
