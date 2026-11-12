"""División y siembra confirmadas de Nations League, con vigencia por edición."""
import json
import re
from datetime import date

from .config import ROOT
from .perfiles import normalizar
from .contexto_internacional import aplicar_contexto_seleccion

CATALOGO = json.loads((ROOT / 'data/selecciones_2026.json').read_text(encoding='utf-8'))


def identidad_seleccion(nombre):
    nombre = normalizar(nombre)
    return CATALOGO['alias'].get(nombre, nombre)


def valorar_selecciones(evento):
    competicion = normalizar(evento.get('competicion', ''))
    texto = competicion + ' ' + normalizar(evento.get('descripcion', ''))
    if (evento.get('deporte') != 'Fútbol' or 'nations league' not in competicion
            or re.search(r'\b(?:women|femenin[oa]|sub\s*\d+|u\s*\d+|juvenil|junior)\b', texto)):
        return None
    try:
        dia = date.fromisoformat(evento['fecha'])
    except (KeyError, ValueError, TypeError):
        return None
    if not date.fromisoformat(CATALOGO['inicio']) <= dia <= date.fromisoformat(CATALOGO['fin']):
        return None
    equipos = [identidad_seleccion(evento.get(lado, '')) for lado in ('local', 'visitante')]
    if len(set(equipos)) != 2:
        return None
    concacaf = 'concacaf' in competicion
    if re.search(r'\b(?:final|semifinal|cuartos|octavos)\b', texto):
        return None
    grupos = CATALOGO['concacaf_grupos'] if concacaf else CATALOGO['grupos']
    for grupo, miembros in grupos.items():
        if all(equipo in miembros for equipo in equipos):
            liga = grupo[0]
            if concacaf:
                base, cartel = 3.5, 0.0
                fuentes = [CATALOGO['concacaf_fuente']]
                bombos = []
            else:
                base = {'A':5.8, 'B':4.6, 'C':3.6, 'D':3.0}[liga]
                bombos = [CATALOGO['bombos'].get(equipo) for equipo in equipos]
                calidad = sum({1:.9, 2:.7, 3:.5, 4:.2}.get(bombo, 0) for bombo in bombos)
                cartel = round(calidad * {'A':1, 'B':.6, 'C':.4, 'D':0}[liga], 2)
                fuentes = CATALOGO['fuentes']
            seleccion = {'base':base, 'cartel':cartel, 'grupo':grupo, 'bombos':bombos,
                    'fuentes':fuentes, 'vigencia':CATALOGO['fin'],
                    'metodo':'División y siembra de la edición; ranking FIFA pendiente',
                    'motivos':[f'Nations League {"CONCACAF" if concacaf else "UEFA"}: grupo {grupo}']
                              + (['Calidad conjunta por siembra oficial de la edición'] if bombos else [])}
            return aplicar_contexto_seleccion(evento, seleccion, miembros, equipos)
    if concacaf and dia >= date(2026, 11, 12):
        for pareja in CATALOGO['playin']:
            if set(equipos) == set(pareja):
                seleccion = {'base':3.8, 'cartel':0.0, 'grupo':'Play-in A/C',
                        'fuentes':[CATALOGO['playin_fuente']], 'vigencia':CATALOGO['fin'],
                        'metodo':'Cruce play-in confirmado; ranking FIFA pendiente',
                        'motivos':['Nations League CONCACAF: play-in entre ligas A y C']}
                return aplicar_contexto_seleccion(evento, seleccion, [], equipos)
    return None
