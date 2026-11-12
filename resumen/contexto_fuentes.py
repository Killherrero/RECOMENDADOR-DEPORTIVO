"""Contexto anterior al partido: tablas e históricos, sin credenciales nuevas."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone

import requests
import threading
import time
import re

from .config import MADRID_TZ
from .perfiles import normalizar, identidad_basket, CODIGOS_EUROLIGA
from .categorias import categoria_tenis
from .diagnostico import ResultadoContexto, marcar
from .ligas import liga_futbol

ESPN = 'https://site.api.espn.com/apis/site/v2/sports/soccer'
TABLAS = 'https://site.web.api.espn.com/apis/v2/sports/soccer'
EURO = 'https://api-live.euroleague.net'
_PLAZO = threading.local()

REGLA_COPA_2026 = 'https://www.ftf.es/pnfg/NNws_ShwNewDup?cod_primaria=3001822&cod_secundaria=3001822&codigo=1062147'


class ErrorContexto(Exception):
    def __init__(self, mensaje, codigo='fuente_no_disponible'):
        super().__init__(mensaje)
        self.codigo = codigo


def descargar_json(url):
    try:
        restante = getattr(_PLAZO, 'fin', float('inf')) - time.monotonic()
        if restante <= 0:
            raise ErrorContexto('Agotado el tiempo disponible para contexto.', 'tiempo_agotado')
        r = requests.get(url, timeout=(min(5, restante), min(15, restante)))
        r.raise_for_status()
        datos = r.json()
        if not isinstance(datos, dict):
            raise ValueError()
        return datos
    except requests.RequestException:
        raise ErrorContexto('Fuente no disponible.', 'fuente_no_disponible') from None
    except ValueError:
        raise ErrorContexto('Formato de fuente no válido.', 'formato_no_valido') from None


def fecha_iso(valor):
    fecha = datetime.fromisoformat(valor.replace('Z', '+00:00'))
    if fecha.tzinfo is None:
        raise ValueError('Fecha de fuente sin zona horaria.')
    return fecha


def temporada(ahora):
    if ahora.tzinfo is not None:
        ahora = ahora.astimezone(MADRID_TZ)
    return ahora.year if ahora.month >= 7 else ahora.year - 1


def liga_evento(e):
    if e.get('deporte') != 'Fútbol':
        return None
    comp = normalizar(e['competicion'])
    if 'bundesliga' in comp:
        return 'ger.1' if liga_futbol(e['competicion']) == 'ger.1' else None
    for tokens, liga in [(['hypermotion'], 'esp.2'),
                         (['laliga', 'la liga', 'ea sports'], 'esp.1'),
                         (['premier league'], 'eng.1'), (['serie a italiana', 'italian serie a'], 'ita.1'),
                         (['bundesliga'], 'ger.1'), (['ligue 1'], 'fra.1')]:
        if any(t in comp for t in tokens):
            return liga
    return None


def alias_futbol(nombre):
    # Alias exactos: nunca emparejar por una subcadena ambigua.
    n = normalizar(nombre)
    aliases = {'as roma': 'roma', 'as roma fc': 'roma', 'sevilla fc': 'sevilla',
               'at madrid': 'atletico madrid', 'atletico de madrid': 'atletico madrid',
               'fc barcelona': 'barcelona', 'manchester utd': 'manchester united',
               'man utd': 'manchester united', 'fc bayern': 'bayern munich',
               'bayern munchen': 'bayern munich', 'paris saint germain': 'psg',
               'o lyonnais': 'lyon', 'olympique lyonnais': 'lyon',
               'inter milan': 'internazionale', 'ac milan': 'milan', 'como 1907': 'como',
               'sestao': 'sestao river', 'cd manacor': 'manacor', 'cd tudelano': 'tudelano',
               'cd atletico paso': 'atletico paso', 'arosa sc': 'arosa', 'rsd alcala': 'alcala',
               'ud llanera': 'llanera', 'at tordesillas': 'atletico tordesillas',
               'g segoviana': 'gimnastica segoviana', 'cultural d leonesa': 'cultural leonesa',
               'ud las palmas': 'las palmas', 'cf calamocha': 'calamocha', 'ce manresa': 'manresa', 'ud almeria': 'almeria'}
    aliases.update({'us lecce':'lecce', 'cadiz cf':'cadiz', 'cd cieza':'cieza', 'granada cf':'granada',
                    'cd castellon':'castellon', 'burgos cf':'burgos', 'cd covadonga':'covadonga',
                    'ribadesella cf':'ribadesella', 'auriense cented':'auriense cented academy',
                    'at baleares':'atletico baleares', 'ad ceuta':'ceuta', 'zamora cf':'zamora',
                    'ud sanse':'san sebastian de los reyes', 'cd coria':'coria',
                    'antequera cf':'antequera', 'aguilas fc':'aguilas',
                    'cp mijas las lagunas':'mijas las lagunas', 'real jaen cf':'real jaen',
                    'unionistas':'unionistas de salamanca',
                    'cd artistico navalcarnero':'navalcarnero',
                    'cs puertollano':'calvo sotelo puertollano',
                    'cd tarancon':'tarancon'})
    return aliases.get(n, n)


def entradas_tabla(datos):
    entries = []
    for hijo in datos.get('children', []):
        entries.extend(hijo.get('standings', {}).get('entries', []))
    if len(entries) < 10:
        raise ErrorContexto('Tabla incompleta.', 'tabla_incompleta')
    return entries


def historial_futbol(datos, equipo_id, liga, year, corte):
    if datos.get('season', {}).get('year') != year or str(datos.get('team', {}).get('id')) != equipo_id:
        raise ErrorContexto('Histórico de otra temporada o equipo.', 'historico_no_corresponde')
    resultados, vistos = [], set()
    for e in datos.get('events', []):
        if e.get('league', {}).get('slug') != liga or e.get('season', {}).get('year') != year:
            continue
        comp = e.get('competitions', [{}])[0]
        if comp.get('status', {}).get('type', {}).get('completed') is not True:
            continue
        fecha = fecha_iso(e['date'])
        # El estado es final, pero no se usa un encuentro iniciado hace menos de 3h.
        if fecha + timedelta(hours=3) > corte or e['id'] in vistos:
            continue
        vistos.add(e['id'])
        equipos = comp['competitors']
        propio = next(t for t in equipos if str(t['id']) == equipo_id)
        rival = next(t for t in equipos if str(t['id']) != equipo_id)
        a, b = float(propio['score']['value']), float(rival['score']['value'])
        if min(a, b) < 0 or not a.is_integer() or not b.is_integer():
            raise ErrorContexto('Marcador histórico no válido.', 'resultado_no_valido')
        resultados.append((fecha, 'W' if a > b else 'D' if a == b else 'L'))
    resultados.sort(reverse=True)
    return resultados


def tabla_futbol(liga, nombres, ahora):
    year = temporada(ahora)
    url = f'{TABLAS}/{liga}/standings'
    datos = descargar_json(url)
    if datos.get('season', {}).get('year') != year:
        raise ErrorContexto('Tabla de otra temporada.', 'otra_temporada')
    entries = entradas_tabla(datos)
    esperados = {'esp.1':20,'esp.2':22,'ita.1':20,'eng.1':20,'ger.1':18,'fra.1':18}
    if len({str(r['team']['id']) for r in entries}) != esperados[liga]:
        raise ErrorContexto('Clasificación parcial o con equipos duplicados.', 'tabla_incompleta')
    encontrados = ResultadoContexto()
    historiales = {}
    for nombre in nombres:
        candidatos = [r for r in entries if alias_futbol(nombre) in
                      {alias_futbol(r['team'].get(k, '')) for k in ('displayName', 'shortDisplayName', 'name', 'location')}]
        if len(candidatos) != 1:
            encontrados.fallo(nombre, 'identidad_ambigua' if candidatos else 'identidad_no_resuelta')
            continue
        r = candidatos[0]
        stats = {s['name']: s.get('value') for s in r['stats']}
        gp, wins, draws, losses = (int(stats[k]) for k in ('gamesPlayed', 'wins', 'ties', 'losses'))
        position = int(stats['rank'])
        if gp != wins + draws + losses or gp < 1 or not 1 <= position <= len(entries):
            encontrados.fallo(nombre, 'balance_no_valido')
            continue
        equipo_id = str(r['team']['id'])
        historial_url = f'{ESPN}/{liga}/teams/{equipo_id}/schedule?season={year}'
        try:
            if equipo_id not in historiales:
                historiales[equipo_id] = historial_futbol(descargar_json(historial_url), equipo_id, liga, year, ahora)
            hist = historiales[equipo_id]
        except (ErrorContexto, KeyError, ValueError, TypeError, StopIteration) as error:
            encontrados.fallo(nombre, getattr(error, 'codigo', 'formato_no_valido'))
            continue
        # La tabla solo se acepta si coincide íntegramente con los resultados anteriores al corte.
        balance = [sum(resultado == x for _, resultado in hist) for x in ('W', 'D', 'L')]
        if len(hist) != gp or balance != [wins, draws, losses]:
            encontrados.fallo(nombre, 'historico_y_tabla_no_coinciden')
            continue
        encontrados[nombre] = {'nombre': nombre, 'id':equipo_id, 'posicion': position, 'jugados': gp,
                              'victorias': wins, 'derrotas': losses, 'forma': ''.join(x for _, x in hist[:5]),
                              'fuentes': [url, historial_url], 'ultimo_partido': hist[0][0].isoformat()}
    return encontrados


def identidad_club(club):
    nombres = {identidad_basket(club.get(k, '')) for k in ('name', 'abbreviatedName', 'editorialName', 'clubPermanentName')}
    if club.get('code') in CODIGOS_EUROLIGA:
        nombres.add(CODIGOS_EUROLIGA[club['code']])
    return nombres


def tabla_euroliga(nombres, ahora):
    year = temporada(ahora)
    url = f'{EURO}/v2/competitions/E/seasons/E{year}/games?limit=1000'
    datos = descargar_json(url)
    games = datos.get('data', [])
    if not games or len(games) != datos.get('total') or len(games) >= 1000:
        raise ErrorContexto('Calendario de Euroliga incompleto.', 'calendario_incompleto')
    regulares = [g for g in games if g.get('season', {}).get('code') == f'E{year}'
                 and g.get('phaseType', {}).get('code') == 'RS']
    if not regulares:
        raise ErrorContexto('No hay calendario de la temporada solicitada.', 'otra_temporada')
    anteriores = [g for g in regulares if g.get('played') is True
                  and fecha_iso(g['utcDate']) + timedelta(hours=3) <= ahora]
    rondas = {g['round'] for g in anteriores}
    completas = [n for n in rondas if all(g in anteriores for g in regulares if g['round'] == n)]
    if not completas:
        raise ErrorContexto('No hay una jornada completa anterior al corte.', 'sin_jornada_completa')
    ronda = max(completas)
    tabla_url = f'{EURO}/v3/competitions/E/seasons/E{year}/rounds/{ronda}/basicstandings'
    tabla = descargar_json(tabla_url).get('teams', [])
    if len(tabla) < 10:
        raise ErrorContexto('Clasificación de Euroliga incompleta.', 'tabla_incompleta')
    encontrados = ResultadoContexto()
    for nombre in nombres:
        candidatos = [r for r in tabla if identidad_basket(nombre) in identidad_club(r['club'])]
        if len(candidatos) != 1:
            encontrados.fallo(nombre, 'identidad_ambigua' if candidatos else 'identidad_no_resuelta')
            continue
        r = candidatos[0]
        code = r['club']['code']
        hist = []
        for g in anteriores:
            propios = [g[k] for k in ('local', 'road') if g[k]['club']['code'] == code]
            if not propios or g['round'] > ronda:
                continue
            a = propios[0]['score']
            b = g['road' if g['local']['club']['code'] == code else 'local']['score']
            if not isinstance(a, int) or not isinstance(b, int) or min(a, b) < 0 or a == b:
                raise ErrorContexto('Resultado de Euroliga no válido.', 'resultado_no_valido')
            hist.append((fecha_iso(g['utcDate']), 'W' if a > b else 'L'))
        hist.sort(reverse=True)
        wins = sum(x == 'W' for _, x in hist)
        if len(hist) != r['gamesPlayed'] or wins != r['gamesWon'] or len(hist) - wins != r['gamesLost']:
            encontrados.fallo(nombre, 'historico_y_tabla_no_coinciden')
            continue
        encontrados[nombre] = {'nombre': nombre, 'id':code, 'posicion': int(r['position']), 'jugados': len(hist),
                              'victorias': wins, 'derrotas': len(hist) - wins,
                              'forma': ''.join(x for _, x in hist[:5]), 'fuentes': [url, tabla_url], 'ronda':ronda,
                              'ultimo_partido': hist[0][0].isoformat()}
    return encontrados


def contextos_copa(items, ahora):
    # Esta fuente confirma el formato de la primera ronda 2026/27, no otras ediciones.
    if temporada(ahora) != 2026:
        for e in items: marcar(e, 'sin_datos', 'edicion_no_cubierta')
        return 0
    tabla_url = f'{TABLAS}/esp.1/standings'
    datos = descargar_json(tabla_url)
    if datos.get('season', {}).get('year') != 2026:
        for e in items: marcar(e, 'sin_datos', 'otra_temporada')
        return 0
    ids_primera = {str(r['team']['id']) for r in entradas_tabla(datos)}
    if len(ids_primera) != 20:
        for e in items: marcar(e, 'sin_datos', 'tabla_incompleta')
        return 0
    dias = {e.get('fecha', ahora.date().isoformat()) for e in items}
    consulta = {}
    for dia in dias:
        url = f'{ESPN}/esp.copa_del_rey/scoreboard?dates={dia.replace("-", "")}&limit=100'
        consulta[dia] = (url, descargar_json(url).get('events', []))
    cubiertos = 0
    for e in items:
        marcar(e, 'sin_datos', 'partido_no_identificado')
        if not any(t in normalizar(e['competicion']) for t in ('1a ronda', '1 ronda', 'primera ronda')):
            marcar(e, 'sin_datos', 'ronda_no_cubierta')
            continue
        dia = e.get('fecha', ahora.date().isoformat())
        url, partidos = consulta[dia]
        candidatos = []
        for p in partidos:
            comp = p.get('competitions', [{}])[0]
            equipos = comp.get('competitors', [])
            if comp.get('status', {}).get('type', {}).get('state') != 'pre':
                continue
            local = next((t for t in equipos if t.get('homeAway') == 'home'), None)
            visita = next((t for t in equipos if t.get('homeAway') == 'away'), None)
            if not local or not visita:
                continue
            def coincide(nombre, t):
                return alias_futbol(nombre) in {alias_futbol(t['team'].get(k, ''))
                                                for k in ('displayName', 'shortDisplayName', 'name')}
            if coincide(e['local'], local) and coincide(e['visitante'], visita):
                inicio = datetime.fromisoformat(f"{dia}T{e['hora']}").replace(tzinfo=MADRID_TZ)
                if abs(fecha_iso(p['date']) - inicio) <= timedelta(minutes=15):
                    candidatos.append((local, visita, p.get('id')))
                else:
                    marcar(e, 'sin_datos', 'horario_no_coincide')
        if len(candidatos) != 1:
            if candidatos: marcar(e, 'sin_datos', 'identidad_ambigua')
            continue
        marcar(e, 'validado', 'datos_validados')
        local, visita, id_partido = candidatos[0]
        contraste = str(local['id']) not in ids_primera and str(visita['id']) in ids_primera
        e['contexto'] = {'tipo': 'copa', 'temporada': 2026, 'consultado': ahora.isoformat(),
                         'competicion': 'esp.copa_del_rey',
                         'local': {'nombre': e['local'], 'id':str(local['id'])}, 'visitante': {'nombre': e['visitante'], 'id':str(visita['id'])},
                         'copa': {'partido_unico': True, 'contraste_primera': contraste,
                                  'id_partido': id_partido, 'fecha_evento': dia,
                                  'fuentes': [url, tabla_url, REGLA_COPA_2026]}}
        cubiertos += 1
    completar_contextos_copa(items, ahora, ids_primera, tabla_url)
    return cubiertos


def completar_contextos_copa(items, ahora, ids_primera, tabla_url):
    """La ampliación opcional nunca borra un contraste de Primera ya validado."""
    if not any(e.get('contexto', {}).get('tipo') == 'copa' for e in items):
        return
    segunda_url = f'{TABLAS}/esp.2/standings'
    ids_segunda = None
    try:
        datos = descargar_json(segunda_url)
        ids = {str(r['team']['id']) for r in entradas_tabla(datos)}
        if datos.get('season', {}).get('year') == temporada(ahora) and len(ids) == 22 and not ids & ids_primera:
            ids_segunda = ids
    except (ErrorContexto, KeyError, ValueError, TypeError, StopIteration):
        pass
    grupos = {}
    for e in items:
        c = e.get('contexto', {})
        if c.get('tipo') != 'copa':
            continue
        for lado in ('local', 'visitante'):
            p = c[lado]
            p['categoria'] = ('Primera' if p['id'] in ids_primera else
                              'Segunda' if ids_segunda is not None and p['id'] in ids_segunda else
                              'Fuera de Primera y Segunda' if ids_segunda is not None else 'Fuera de Primera')
        copa = c['copa']
        copa['contraste_segunda'] = (ids_segunda is not None and c['local']['id'] not in ids_primera | ids_segunda
                                     and c['visitante']['id'] in ids_segunda)
        copa['estado_categorias'] = 'Primera y Segunda verificadas' if ids_segunda is not None else 'Segunda sin validar'
        if ids_segunda is not None:
            copa['fuentes'].append(segunda_url)
        if copa['contraste_primera'] or copa['contraste_segunda']:
            liga = 'esp.1' if copa['contraste_primera'] else 'esp.2'
            grupos.setdefault(liga, []).append(e)
    for liga, eventos in grupos.items():
        try:
            formas = tabla_futbol(liga, sorted({e['visitante'] for e in eventos}), ahora)
        except (ErrorContexto, KeyError, ValueError, TypeError, StopIteration):
            formas = {}
        for e in eventos:
            p = formas.get(e['visitante'])
            copa = e['contexto']['copa']
            if p and p['id'] == e['contexto']['visitante']['id']:
                copa['forma_visitante'] = p
                copa['estado_forma'] = 'Historial y tabla coinciden'
            else:
                copa['estado_forma'] = getattr(formas, 'fallos', {}).get(e['visitante'], 'Historial no validado')


def contextos_tenis(items, ahora):
    url = 'https://site.api.espn.com/apis/site/v2/sports/tennis/atp/rankings'
    datos = descargar_json(url)
    tablas = [r for r in datos.get('rankings', []) if r.get('type') == 'atp']
    if len(tablas) != 1:
        for e in items: marcar(e, 'sin_datos', 'ranking_no_disponible')
        return 0
    tabla = tablas[0]
    publicado = fecha_iso(tabla['update'])
    if not timedelta(0) <= ahora - publicado <= timedelta(days=10):
        for e in items: marcar(e, 'sin_datos', 'ranking_fuera_de_fecha')
        return 0
    ranks = tabla.get('ranks', [])
    if len(ranks) < 50:
        for e in items: marcar(e, 'sin_datos', 'ranking_incompleto')
        return 0
    cubiertos = 0
    for e in items:
        marcar(e, 'sin_datos', 'identidad_no_resuelta')
        categoria, _ = categoria_tenis(e)
        if categoria is None:
            marcar(e, 'sin_datos', 'categoria_no_confirmada')
            continue
        jugadores = {}
        estados = {}
        for k in ('local', 'visitante'):
            # Alias documental exacto; no deducir identidades a partir del apellido.
            nombre = {'jl struff':'jan lennard struff'}.get(normalizar(e[k]), normalizar(e[k]))
            candidatos = [r for r in ranks if nombre in
                          {normalizar(r['athlete'].get(n, '')) for n in ('displayName', 'shortname', 'shortName', 'fullName')}]
            if len(candidatos) != 1:
                estados[k] = 'identidad_ambigua' if candidatos else 'identidad_no_resuelta'
                continue
            r = candidatos[0]
            if type(r.get('current')) is not int or not 1 <= r['current'] <= 1000:
                estados[k] = 'ranking_no_valido'
                continue
            a = r['athlete']
            if not a.get('id'):
                estados[k] = 'identidad_no_resuelta'
                continue
            jugadores[k] = {'nombre': e[k], 'id': str(a['id']), 'ranking': r['current'],
                              'edad': a.get('age'), 'pais': a.get('citizenshipCountry')}
            estados[k] = 'validado'
        if len(jugadores) == 2 and jugadores['local']['id'] == jugadores['visitante']['id']:
            marcar(e, 'sin_datos', 'identidad_ambigua')
            continue
        if not jugadores:
            marcar(e, 'sin_datos', 'identidad_no_resuelta', participantes=estados)
            continue
        completo = len(jugadores) == 2
        marcar(e, 'validado' if completo else 'parcial', 'datos_validados' if completo else 'participante_sin_datos', participantes=estados)
        e['contexto'] = {'tipo': 'tenis', 'competicion': 'atp', 'temporada': temporada(ahora),
                         'consultado': ahora.isoformat(), 'publicado': publicado.isoformat(),
                         **jugadores, 'fuentes': [url]}
        cubiertos += int(completo)
    return cubiertos


def contextos_nba(items, ahora):
    """Solo metadatos prospectivos; nunca conservar resultados o estadísticas."""
    fechas = {}
    for e in items:
        inicio = datetime.fromisoformat(f"{e['fecha']}T{e['hora']}").replace(tzinfo=MADRID_TZ)
        fechas.setdefault(inicio.astimezone(timezone.utc).strftime('%Y%m%d'), []).append(e)
    cubiertos = 0
    for dia, eventos in fechas.items():
        url = f'https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard?dates={dia}&limit=100'
        datos = descargar_json(url)
        for e in eventos:
            inicio = datetime.fromisoformat(f"{e['fecha']}T{e['hora']}").replace(tzinfo=MADRID_TZ)
            candidatos = []
            for ficha in datos.get('events', []):
                for partido in ficha.get('competitions', []):
                    if partido.get('status', ficha.get('status', {})).get('type', {}).get('state') != 'pre':
                        continue
                    try:
                        inicio_fuente = fecha_iso(partido.get('date') or ficha.get('date'))
                    except (ValueError, TypeError, AttributeError):
                        continue
                    if inicio_fuente <= ahora or abs(inicio_fuente - inicio) > timedelta(minutes=15):
                        continue
                    equipos = {}
                    for lado, rol in (('local', 'home'), ('visitante', 'away')):
                        opciones = [t['team'] for t in partido.get('competitors', [])
                                    if t.get('homeAway') == rol and normalizar(e[lado]) in
                                    {normalizar(t.get('team', {}).get(k, '')) for k in ('displayName', 'shortDisplayName', 'name')}]
                        if len(opciones) == 1 and opciones[0].get('id'):
                            equipos[lado] = {'nombre': e[lado], 'id': str(opciones[0]['id'])}
                    if len(equipos) != 2 or equipos['local']['id'] == equipos['visitante']['id']:
                        continue
                    notas = ' '.join(str(n.get('headline') or '') for n in (partido.get('notes') or []))
                    texto = normalizar(notas)
                    es_copa = bool(re.search(r'\bnba cup\b', texto))
                    fase = ('grupos' if 'group play' in texto else
                            'cuartos' if 'quarterfinal' in texto or 'quarter final' in texto else
                            'semifinal' if 'semifinal' in texto or 'semi final' in texto else
                            'final' if re.search(r'\b(?:final|championship)\b', texto) else 'sin confirmar') if es_copa else 'liga regular'
                    if ficha.get('id'):
                        candidatos.append({'tipo': 'nba', 'competicion': 'nba', 'temporada': temporada(ahora),
                                           'consultado': ahora.isoformat(), 'inicio': inicio_fuente.isoformat(),
                                           'partido_id': str(ficha['id']), 'estado_partido': 'pre',
                                           'copa': es_copa, 'fase': fase, **equipos, 'fuentes': [url]})
            if len(candidatos) == 1:
                e['contexto'] = candidatos[0]
                marcar(e, 'validado', 'datos_validados')
                cubiertos += 1
            else:
                marcar(e, 'sin_datos', 'identidad_ambigua' if candidatos else 'partido_no_confirmado')
    return cubiertos


def enriquecer_eventos(eventos, ahora):
    """Añade contexto solo a encuentros futuros; no sustituye ni bloquea la agenda."""
    if ahora.tzinfo is None:
        raise ValueError('El contexto requiere fecha con zona horaria.')
    ahora = ahora.astimezone(MADRID_TZ)
    grupos = {}
    for e in eventos:
        e.pop('contexto', None)
        marcar(e, 'sin_datos', 'competicion_no_cubierta')
        if e.get('deporte') == 'Fútbol' and liga_futbol(e.get('competicion','')) == 'aut.1':
            marcar(e, 'sin_datos', 'liga_austriaca_sin_cobertura')
        elif e.get('deporte') == 'Fútbol' and liga_futbol(e.get('competicion','')) in ('bel.1','ned.1','por.1'):
            marcar(e, 'sin_datos', 'liga_sin_cobertura', liga=liga_futbol(e['competicion']))
        try:
            inicio = datetime.fromisoformat(f"{e.get('fecha', ahora.date().isoformat())}T{e['hora']}").replace(tzinfo=MADRID_TZ)
        except (ValueError, KeyError, TypeError):
            marcar(e, 'sin_datos', 'fecha_no_valida')
            continue
        if inicio <= ahora:
            marcar(e, 'sin_datos', 'evento_iniciado')
            continue
        liga = liga_evento(e)
        if e.get('deporte') == 'Tenis':
            liga = 'tenis'
        if e.get('deporte') == 'Fútbol' and 'copa del rey' in normalizar(e['competicion']):
            liga = 'copa'
        if e.get('deporte') == 'Baloncesto' and any(t in normalizar(e['competicion']) for t in ('euroliga', 'euroleague')):
            liga = 'euro'
        if e.get('deporte') == 'Baloncesto' and re.search(r'\bnba\b', normalizar(e['competicion'])):
            liga = 'nba'
        if liga:
            marcar(e, 'pendiente', 'pendiente')
            grupos.setdefault(liga, []).append(e)

    fin = time.monotonic() + 45

    def procesar(item):
        _PLAZO.fin = fin
        liga, items = item
        nombres = sorted({e[k] for e in items for k in ('local', 'visitante')})
        try:
            if liga == 'tenis':
                return contextos_tenis(items, ahora)
            if liga == 'copa':
                return contextos_copa(items, ahora)
            if liga == 'nba':
                return contextos_nba(items, ahora)
            datos = tabla_euroliga(nombres, ahora) if liga == 'euro' else tabla_futbol(liga, nombres, ahora)
        except (ErrorContexto, KeyError, ValueError, TypeError, IndexError, StopIteration) as error:
            for e in items: marcar(e, 'sin_datos', getattr(error, 'codigo', 'formato_no_valido'))
            datos = {}
        for e in items:
            general = e.get('diagnostico_contexto',{}).get('motivo','sin_datos')
            if general == 'pendiente': general = 'identidad_no_resuelta'
            estados = {k: ('validado' if e[k] in datos else getattr(datos, 'fallos', {}).get(e[k], general)) for k in ('local','visitante')}
            validos = sum(v == 'validado' for v in estados.values())
            marcar(e, 'validado' if validos == 2 else 'parcial' if validos else 'sin_datos', 'datos_validados' if validos == 2 else 'participante_sin_datos' if validos else next(iter(estados.values())), participantes=estados)
            if validos == 1:
                e['diagnostico_contexto']['datos_parciales'] = {k:datos[e[k]] for k in ('local','visitante') if e[k] in datos}
            if e['local'] in datos and e['visitante'] in datos:
                e['contexto'] = {'consultado': ahora.isoformat(), 'temporada': temporada(ahora),
                                 'competicion': liga, 'local': datos[e['local']], 'visitante': datos[e['visitante']]}
        return sum('contexto' in e for e in items)

    if not grupos:
        return []
    with ThreadPoolExecutor(max_workers=3) as pool:
        cubiertos = sum(pool.map(procesar, grupos.items()))
    elegibles = sum(len(items) for items in grupos.values())
    return [f'Contexto deportivo validado en {cubiertos}/{elegibles} encuentros futuros de las ligas cubiertas. '
            'En el resto se mantiene la nota básica. Cobertura actual: ligas principales de fútbol, Euroliga '
            'y contraste de categorías en primera ronda de Copa del Rey 2026/27, ranking ATP y fase de NBA Cup. '
            'Las competiciones o jugadores sin datos conservan su valoración básica.']
