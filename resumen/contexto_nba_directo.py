"""Contexto prospectivo NBA. Se conservan agregados, sin resultados individuales."""
from datetime import timedelta


def historial(datos, equipo_id, year, corte):
    from .contexto_fuentes import fecha_iso
    if (datos.get('season', {}).get('year') != year
            or datos.get('season', {}).get('type') != 2
            or str(datos.get('team', {}).get('id')) != equipo_id):
        raise ValueError('Otra temporada o equipo NBA')
    juegos, vistos = [], set()
    for evento in datos.get('events', []):
        if evento.get('season', {}).get('year') != year or evento.get('seasonType', {}).get('type') != 2:
            continue
        partido = evento['competitions'][0]
        if partido.get('status', {}).get('type', {}).get('completed') is not True:
            continue
        inicio = fecha_iso(evento['date'])
        if inicio + timedelta(hours=4) > corte:
            continue
        if evento['id'] in vistos:
            raise ValueError('Histórico NBA duplicado')
        vistos.add(evento['id'])
        equipos = partido['competitors']
        if len(equipos) != 2 or len({str(equipo['id']) for equipo in equipos}) != 2:
            raise ValueError('Participantes históricos inválidos')
        propio = next(equipo for equipo in equipos if str(equipo['id']) == equipo_id)
        rival = next(equipo for equipo in equipos if str(equipo['id']) != equipo_id)
        a, b = float(propio['score']['value']), float(rival['score']['value'])
        if not a.is_integer() or not b.is_integer() or not 0 <= min(a,b) < max(a,b) <= 250:
            raise ValueError('Resultado histórico NBA inválido')
        juegos.append((inicio, a > b))
    juegos.sort(reverse=True)
    return juegos


def completar_nba(items, ahora):
    from .contexto_fuentes import descargar_json, temporada, ErrorContexto
    confirmados = [evento for evento in items if evento.get('contexto', {}).get('tipo') == 'nba']
    if not confirmados:
        return
    year = temporada(ahora) + 1
    url = f'https://site.web.api.espn.com/apis/v2/sports/basketball/nba/standings?season={year}'
    try:
        datos = descargar_json(url)
        if datos.get('season', {}).get('year') != year or len(datos.get('children', [])) != 2:
            raise ValueError('Tabla NBA incompleta o de otra temporada')
        registros, ids, conferencias = {}, set(), set()
        for conferencia in datos['children']:
            conferencia_id = str(conferencia['id'])
            if not conferencia_id or conferencia_id in conferencias:
                raise ValueError('Conferencia NBA duplicada')
            conferencias.add(conferencia_id)
            entradas = conferencia['standings']['entries']
            if len(entradas) != 15:
                raise ValueError('Conferencia NBA incompleta')
            posiciones = set()
            for entrada in entradas:
                equipo_id = str(entrada['team']['id'])
                stats = {stat['name']:stat['value'] for stat in entrada['stats'] if 'value' in stat}
                valores = [stats[campo] for campo in ('wins','losses','playoffSeed')]
                if any(valor != int(valor) for valor in valores):
                    raise ValueError('Balance o posición no enteros')
                victorias, derrotas, posicion = map(int, valores)
                if equipo_id in ids or posicion in posiciones or not 1 <= posicion <= 15 or min(victorias,derrotas) < 0:
                    raise ValueError('Identidad, posición o balance no válidos')
                ids.add(equipo_id)
                posiciones.add(posicion)
                registros[equipo_id] = dict(id=equipo_id, victorias=victorias, derrotas=derrotas,
                    jugados=victorias+derrotas, posicion=posicion, conferencia=str(conferencia['id']),
                    nombres={str(entrada['team'].get(campo,'')) for campo in ('displayName','shortDisplayName','name')})
    except (ErrorContexto, ValueError, KeyError, TypeError, IndexError, OverflowError):
        for evento in confirmados:
            evento['contexto']['estado_forma'] = 'Tabla NBA sin validar'
        return
    cache = {}
    for evento in confirmados:
        contexto = evento['contexto']
        agregados = {}
        for lado in ('local','visitante'):
            equipo = contexto[lado]
            equipo_id = equipo['id']
            try:
                registro = registros[equipo_id]
                from .perfiles import normalizar
                if normalizar(evento[lado]) not in {normalizar(nombre) for nombre in registro['nombres']}:
                    raise ValueError('Identidad NBA de tabla no coincide')
                if registro['jugados'] < 5:
                    raise ValueError('Muestra NBA insuficiente')
                historial_url = f'https://site.api.espn.com/apis/site/v2/sports/basketball/nba/teams/{equipo_id}/schedule?season={year}&seasontype=2'
                if equipo_id not in cache:
                    try:
                        cache[equipo_id] = historial(descargar_json(historial_url), equipo_id, year, ahora)
                    except (ErrorContexto, ValueError, KeyError, TypeError, IndexError, StopIteration):
                        cache[equipo_id] = None
                juegos = cache[equipo_id]
                if juegos is None or len(juegos) != registro['jugados'] or sum(victoria for _,victoria in juegos) != registro['victorias']:
                    raise ValueError('Tabla e histórico NBA no coinciden')
                agregados[lado] = {campo:registro[campo] for campo in ('id','jugados','victorias','derrotas','posicion','conferencia')}
                agregados[lado].update(nombre=evento[lado], temporada_fuente=year,
                    victorias_ultimos5=sum(victoria for _,victoria in juegos[:5]),
                    ultimo_partido=juegos[0][0].isoformat(), fuentes=[url,historial_url])
            except (ValueError, KeyError, TypeError):
                continue
        if len(agregados) == 2:
            contexto['forma_nba'] = agregados
            contexto['estado_forma'] = 'Balances e históricos NBA contrastados'
        else:
            contexto['estado_forma'] = 'Datos de ambos equipos sin validar'


def valorar_forma(contexto, consulta):
    from .contexto_fuentes import fecha_iso
    vacio = dict(ajuste=0.0, objetivo_cartel=0.0, estado='sin datos de forma NBA', motivos=[], fuentes=[])
    try:
        forma = contexto['forma_nba']
        equipos = [forma[lado] for lado in ('local','visitante')]
        for lado, equipo in zip(('local','visitante'), equipos):
            if equipo['id'] != contexto[lado]['id'] or equipo['nombre'] != contexto[lado]['nombre']:
                raise ValueError('Identidad NBA no coincide')
            if any(type(equipo[campo]) is not int for campo in ('jugados','victorias','derrotas','posicion','victorias_ultimos5','temporada_fuente')):
                raise ValueError('Agregado NBA inválido')
            if (equipo['temporada_fuente'] != contexto['temporada']+1 or not 5 <= equipo['jugados'] <= 82
                    or equipo['victorias']+equipo['derrotas'] != equipo['jugados']
                    or min(equipo['victorias'],equipo['derrotas']) < 0 or not 1 <= equipo['posicion'] <= 15
                    or not 0 <= equipo['victorias_ultimos5'] <= min(5,equipo['victorias'])
                    or not equipo.get('fuentes') or not equipo.get('conferencia')
                    or not timedelta(hours=4) <= consulta-fecha_iso(equipo['ultimo_partido']) <= timedelta(days=14)):
                raise ValueError('Balance, muestra o fecha NBA inválidos')
        porcentajes = [equipo['victorias']/equipo['jugados'] for equipo in equipos]
        objetivo = (2.0 if min(equipo['jugados'] for equipo in equipos) >= 10
                    and max(equipo['posicion'] for equipo in equipos) <= 4 and min(porcentajes) >= .6 else
                    1.2 if max(equipo['posicion'] for equipo in equipos) <= 8 and min(porcentajes) >= .5 else 0.0)
        ajuste = .6 if min(equipo['victorias_ultimos5'] for equipo in equipos) >= 4 else .3 if max(equipo['victorias_ultimos5'] for equipo in equipos) >= 4 else 0.0
        desequilibrio = max(porcentajes)-min(porcentajes) >= .35
        if desequilibrio:
            ajuste = min(ajuste,.2)
            objetivo = 0.0
        return dict(ajuste=ajuste, objetivo_cartel=objetivo, estado='validado',
                    moderacion=desequilibrio, motivos=['Forma NBA reciente contrastada'] if ajuste else [],
                    fuentes=list(dict.fromkeys(url for equipo in equipos for url in equipo['fuentes'])))
    except (KeyError, ValueError, TypeError, AttributeError):
        return vacio
