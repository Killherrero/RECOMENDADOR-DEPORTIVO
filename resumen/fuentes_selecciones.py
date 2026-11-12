"""Fuentes públicas de selecciones, compartidas por ejecución y con plazo acotado."""
from email.utils import parsedate_to_datetime
from datetime import timedelta
import time

import requests

from .selecciones import CATALOGO, identidad_seleccion, valorar_selecciones
from .contexto_internacional import validar_grupo

ELO = 'https://www.eloratings.net/World.tsv'
NOMBRES_ELO = 'https://www.eloratings.net/en.teams.tsv'
TABLA = 'https://site.web.api.espn.com/apis/v2/sports/soccer/uefa.nations/standings?season=2026'
CALENDARIO = 'https://site.api.espn.com/apis/site/v2/sports/soccer/uefa.nations/scoreboard?dates=2026&limit=200'
REGLAS = [
    'https://documents.uefa.com/r/Regulations-of-the-UEFA-Nations-League-2026/27/Article-17-Match-system-League-A-knockout-stage-Online',
    'https://documents.uefa.com/r/Regulations-of-the-UEFA-Nations-League-2026/27/Article-15-Equality-of-points-league-phase-Online',
]


def leer_elo(texto, nombres, publicado, consulta):
    if not timedelta(0) <= consulta - publicado <= timedelta(days=60):
        raise ValueError('Rating futuro o antiguo')
    identidades = {}
    for linea in nombres.splitlines():
        campos = linea.split('\t')
        if len(campos) >= 2:
            identidades[campos[0]] = identidad_seleccion(campos[1])
    equipos, codigos = {}, set()
    for linea in texto.splitlines():
        campos = linea.split('\t')
        if len(campos) < 4:
            raise ValueError('Tabla Elo incompleta')
        codigo = campos[2]
        posicion, rating = int(campos[1]), int(campos[3])
        nombre = identidades[codigo]
        if codigo in codigos or nombre in equipos or not 1 <= posicion <= 300 or not 100 <= rating <= 3000:
            raise ValueError('Identidad o rating Elo inválidos')
        codigos.add(codigo)
        equipos[nombre] = dict(id=codigo, posicion=posicion, rating=rating)
    if not 150 <= len(equipos) <= 300:
        raise ValueError('Tabla Elo truncada')
    return dict(publicado=publicado.isoformat(), equipos=equipos, fuentes=[ELO, NOMBRES_ELO])


def leer_grupos(tablas, calendario, consulta):
    if tablas['season']['year'] != 2026 or len(calendario['events']) >= 200:
        raise ValueError('Edición incorrecta o calendario posiblemente truncado')
    grupos = {}
    for grupo in tablas['children']:
        nombre = grupo['name'].removeprefix('Group ')
        if nombre not in CATALOGO['grupos'] or not nombre.startswith('A'):
            continue
        tabla = {}
        for entrada in grupo['standings']['entries']:
            equipo = identidad_seleccion(entrada['team']['displayName'])
            stats = {stat['name']:stat['value'] for stat in entrada['stats'] if 'value' in stat}
            puntos, jugados = stats['points'], stats['gamesPlayed']
            if puntos != int(puntos) or jugados != int(jugados) or equipo in tabla:
                raise ValueError('Tabla inválida')
            tabla[equipo] = dict(puntos=int(puntos), jugados=int(jugados))
        miembros = CATALOGO['grupos'][nombre]
        partidos = []
        for evento in calendario['events']:
            if evento.get('season', {}).get('year') != 2026:
                continue
            competicion = evento['competitions'][0]
            equipos = {participante['homeAway']:participante for participante in competicion['competitors']}
            local = identidad_seleccion(equipos['home']['team']['displayName'])
            visita = identidad_seleccion(equipos['away']['team']['displayName'])
            if local not in miembros or visita not in miembros:
                continue
            estado = competicion['status']['type']
            if estado['state'] == 'post' and not estado.get('completed'):
                raise ValueError('Resultado sin confirmar')
            goles = ([int(equipos[lado]['score']) for lado in ('home', 'away')]
                     if estado['state'] == 'post' else None)
            partidos.append(dict(id=evento['id'], inicio=evento['date'], local=local,
                                 visitante=visita, estado=estado['state'], goles=goles))
        datos = dict(tabla=tabla, partidos=partidos, fuentes=[TABLA, CALENDARIO, *REGLAS])
        try:
            validar_grupo(datos, miembros, consulta)
        except (ValueError, KeyError, TypeError):
            continue
        grupos[nombre] = datos
    return grupos


def contextos_selecciones(items, ahora):
    from .contexto_fuentes import _PLAZO, descargar_json, ErrorContexto
    from .diagnostico import marcar

    def descargar_texto(url):
        restante = getattr(_PLAZO, 'fin', float('inf')) - time.monotonic()
        if restante <= 0:
            raise ValueError('Tiempo de consulta agotado')
        respuesta = requests.get(url, timeout=(min(5, restante), min(10, restante)))
        respuesta.raise_for_status()
        return respuesta

    elo, grupos = None, {}
    estado_elo = 'fuente Elo no disponible o sin fecha válida'
    estado_grupo = 'calendario y tabla de grupo sin validar'
    try:
        respuesta = descargar_texto(ELO)
        publicado = parsedate_to_datetime(respuesta.headers['Last-Modified'])
        nombres = descargar_texto(NOMBRES_ELO)
        elo = leer_elo(respuesta.text, nombres.text, publicado, ahora)
    except (requests.RequestException, ValueError, KeyError, TypeError, OverflowError):
        pass
    if any((valorar_selecciones(evento) or {}).get('grupo', '').startswith('A') for evento in items):
        try:
            grupos = leer_grupos(descargar_json(TABLA), descargar_json(CALENDARIO), ahora)
        except (ErrorContexto, ValueError, KeyError, TypeError, IndexError):
            pass
    cubiertos = 0
    for evento in items:
        seleccion = valorar_selecciones(evento)
        if not seleccion:
            continue
        equipos = [identidad_seleccion(evento[lado]) for lado in ('local', 'visitante')]
        datos = dict(consultado=ahora.isoformat(), estado_elo=estado_elo, estado_grupo=estado_grupo)
        if elo and all(equipo in elo['equipos'] for equipo in equipos):
            datos['elo'] = {**elo, 'equipos':{equipo:elo['equipos'][equipo] for equipo in equipos}}
        if seleccion['grupo'] in grupos:
            datos['grupo'] = grupos[seleccion['grupo']]
        evento['contexto_selecciones'] = datos
        validos = sum(clave in datos for clave in ('elo', 'grupo'))
        marcar(evento, 'validado' if validos == 2 else 'parcial' if validos else 'sin_datos',
               'datos_internacionales_validados' if validos else 'fuentes_internacionales_sin_validar')
        cubiertos += bool(validos)
    return cubiertos
