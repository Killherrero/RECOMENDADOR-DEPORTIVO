"""Ratings Elo y escenarios por puntos, con desempates conservados como abiertos."""
from datetime import datetime, timedelta
from itertools import permutations, product


def fecha(valor):
    resultado = datetime.fromisoformat(valor.replace('Z', '+00:00'))
    if resultado.tzinfo is None:
        raise ValueError('Fecha sin zona horaria')
    return resultado


def calidad_elo(datos, equipos, inicio, consulta):
    publicado = fecha(datos['publicado'])
    if not timedelta(0) <= consulta - publicado <= timedelta(days=60):
        raise ValueError('Rating fuera del corte temporal')
    if publicado >= inicio or not datos.get('fuentes'):
        raise ValueError('Rating sin fuente anterior al partido')
    ratings = [datos['equipos'][equipo]['rating'] for equipo in equipos]
    if any(type(rating) is not int or not 100 <= rating <= 3000 for rating in ratings):
        raise ValueError('Rating inválido')

    def peso(rating):
        if rating >= 2000:
            return 1.0
        if rating >= 1800:
            return .8
        if rating >= 1600:
            return .5
        if rating >= 1400:
            return .2
        return 0.0

    calidad = sum(peso(rating) for rating in ratings)
    # Un solo equipo fuerte no convierte el cruce en un duelo de élite.
    if abs(ratings[0] - ratings[1]) >= 400:
        calidad = max(0, calidad - .3)
    return round(calidad, 2)


def validar_grupo(datos, miembros, consulta):
    """Reconstruye la tabla con partidos finalizados y exige ida/vuelta completas."""
    if set(datos['tabla']) != set(miembros) or not datos.get('fuentes'):
        raise ValueError('Miembros del grupo incorrectos')
    tabla = {equipo:dict(puntos=0, jugados=0) for equipo in miembros}
    parejas, ids, pendientes = set(), set(), []
    for partido in datos['partidos']:
        pareja = (partido['local'], partido['visitante'])
        if pareja in parejas or partido['id'] in ids or not partido['id']:
            raise ValueError('Partido duplicado')
        parejas.add(pareja)
        ids.add(partido['id'])
        comienzo = fecha(partido['inicio'])
        if comienzo < consulta and partido['estado'] == 'post':
            goles = partido['goles']
            if len(goles) != 2 or any(type(gol) is not int or not 0 <= gol <= 30 for gol in goles):
                raise ValueError('Resultado no válido')
            puntos = (3, 0) if goles[0] > goles[1] else (0, 3) if goles[0] < goles[1] else (1, 1)
            for equipo, valor in zip(pareja, puntos):
                tabla[equipo]['puntos'] += valor
                tabla[equipo]['jugados'] += 1
        elif comienzo > consulta and partido['estado'] == 'pre':
            pendientes.append(partido)
        else:
            raise ValueError('Grupo en curso, aplazado o posterior al corte')
    if parejas != set(permutations(miembros, 2)) or tabla != datos['tabla']:
        raise ValueError('Calendario incompleto o tabla incoherente')
    return tabla, pendientes


def rango_por_puntos(equipo, puntos, partidos):
    """Aplica puntos directos y, cuando están disponibles, goles directos conocidos."""
    empatados = {otro for otro in puntos if puntos[otro] == puntos[equipo]}
    por_delante = sum(valor > puntos[equipo] for valor in puntos.values())
    if len(empatados) == 1:
        return (por_delante + 1, por_delante + 1)
    mini = {otro:[0, 0, 0] for otro in empatados}
    goles_conocidos = True
    for partido in partidos:
        local, visita = partido['local'], partido['visitante']
        if local not in empatados or visita not in empatados:
            continue
        puntos_local, puntos_visita = partido['reparto']
        mini[local][0] += puntos_local
        mini[visita][0] += puntos_visita
        if partido.get('goles') is None:
            goles_conocidos = False
        else:
            a, b = partido['goles']
            mini[local][1] += a - b
            mini[visita][1] += b - a
            mini[local][2] += a
            mini[visita][2] += b
    criterio = {otro:tuple(valores if goles_conocidos else valores[:1]) for otro, valores in mini.items()}
    delante = sum(valor > criterio[equipo] for otro, valor in criterio.items() if otro != equipo)
    iguales = {otro for otro in empatados if criterio[otro] == criterio[equipo]}
    if goles_conocidos and 1 < len(iguales) < len(empatados):
        # Artículo 15: reaplicar los criterios directos al subconjunto aún empatado.
        subpartidos = [partido for partido in partidos
                      if partido['local'] in iguales and partido['visitante'] in iguales]
        mejor, peor = rango_por_puntos(equipo, {otro:0 for otro in iguales}, subpartidos)
        return por_delante + delante + mejor, por_delante + delante + peor
    return por_delante + delante + 1, por_delante + delante + len(iguales)


def escenarios_grupo(datos, miembros, equipos, inicio, consulta, grupo):
    tabla, pendientes = validar_grupo(datos, miembros, consulta)
    objetivo = next((partido for partido in pendientes
                     if (partido['local'], partido['visitante']) == tuple(equipos)
                     and abs(fecha(partido['inicio']) - inicio) <= timedelta(minutes=15)), None)
    if objetivo is None:
        raise ValueError('Encuentro no identificado')
    # Hasta las dos jornadas finales. Se evita una enumeración exponencial temprana.
    if len(pendientes) > 4:
        return dict(ajuste=0.0, estado='fase temprana', fuentes=datos['fuentes'])
    if not grupo.startswith('A'):
        return dict(ajuste=0.0, estado='reglas de ascenso y descenso sin cobertura', fuentes=datos['fuentes'])
    posiciones = {equipo:[] for equipo in equipos}
    condicionado = {equipo:{0:[], 1:[], 2:[]} for equipo in equipos}
    indice = pendientes.index(objetivo)
    for resultados in product(range(3), repeat=len(pendientes)):
        puntos = {equipo:registro['puntos'] for equipo, registro in tabla.items()}
        terminados = []
        for partido in datos['partidos']:
            if partido['estado'] == 'post':
                a, b = partido['goles']
                reparto = (3, 0) if a > b else (0, 3) if a < b else (1, 1)
                terminados.append({**partido, 'reparto':reparto})
        for partido, resultado in zip(pendientes, resultados):
            reparto = ((3, 0), (1, 1), (0, 3))[resultado]
            puntos[partido['local']] += reparto[0]
            puntos[partido['visitante']] += reparto[1]
            terminados.append({**partido, 'reparto':reparto})
        for equipo in equipos:
            mejor, peor = rango_por_puntos(equipo, puntos, terminados)
            posiciones[equipo].append((mejor, peor))
            condicionado[equipo][resultados[indice]].append((mejor, peor))

    def estado(rangos, plaza):
        if all(peor <= plaza for _, peor in rangos):
            return 'asegurado por puntos'
        if all(mejor > plaza for mejor, _ in rangos):
            return 'inalcanzable por puntos'
        return 'abierto o dependiente del desempate'

    detalle, ajuste = {}, 0.0
    for equipo in equipos:
        clasificacion = estado(posiciones[equipo], 2)
        liderato = estado(posiciones[equipo], 1)
        etiquetas = ('victoria local', 'empate', 'victoria visitante')
        por_resultado = {etiquetas[resultado]:estado(rangos, 2)
                         for resultado, rangos in condicionado[equipo].items()}
        # Solo se premia una diferencia demostrable entre ganar, empatar y perder.
        if len(set(por_resultado.values())) > 1:
            ajuste = max(ajuste, .4)
        primero_por_resultado = [estado(rangos, 1) for rangos in condicionado[equipo].values()]
        if len(set(primero_por_resultado)) > 1:
            ajuste = max(ajuste, .15)
        detalle[equipo] = dict(clasificacion=clasificacion, liderato=liderato,
                              clasificacion_por_resultado=por_resultado)
    return dict(ajuste=ajuste, estado='escenarios por puntos validados', equipos=detalle,
                escenarios=3 ** len(pendientes), pendientes=len(pendientes), fuentes=datos['fuentes'],
                limite='Se aplican puntos y goles directos conocidos. Márgenes futuros, goles globales '
                       'y disciplina no disponibles dejan el empate abierto. '
                       'Cobertura de cuartos y primer puesto de Liga A; descenso fuera de cobertura.')


def aplicar_contexto_seleccion(evento, seleccion, miembros, equipos):
    datos = evento.get('contexto_selecciones')
    if not datos:
        return seleccion
    resultado = dict(seleccion)
    resultado['fuentes'] = list(seleccion['fuentes'])
    resultado['motivos'] = list(seleccion['motivos'])
    try:
        from .config import MADRID_TZ
        inicio = datetime.fromisoformat(f"{evento['fecha']}T{evento['hora']}").replace(tzinfo=MADRID_TZ)
        consulta = fecha(datos['consultado'])
        if not timedelta(0) < inicio - consulta <= timedelta(hours=36):
            raise ValueError('Consulta fuera del corte')
    except (ValueError, KeyError, TypeError):
        return seleccion
    resultado['consulta_internacional'] = datos['consultado']
    try:
        elo = datos['elo']
        resultado['cartel'] = calidad_elo(elo, equipos, inicio, consulta)
        resultado['rating'] = dict(proveedor='World Football Elo Ratings', publicado=elo['publicado'],
                                  equipos={equipo:elo['equipos'][equipo] for equipo in equipos})
        resultado['fuentes'].extend(elo['fuentes'])
        resultado['metodo'] = 'División de la edición y calidad conjunta Elo'
        resultado['motivos'] = [motivo for motivo in resultado['motivos']
                                 if motivo != 'Calidad conjunta por siembra oficial de la edición']
        resultado['motivos'].append('Calidad conjunta por rating Elo anterior al partido')
    except (ValueError, KeyError, TypeError):
        resultado['estado_rating'] = datos.get('estado_elo', 'rating no validado; se conserva siembra')
    try:
        trascendencia = escenarios_grupo(datos['grupo'], miembros, equipos, inicio, consulta, seleccion['grupo'])
        resultado['trascendencia'] = trascendencia
        resultado['fuentes'].extend(trascendencia['fuentes'])
        resultado['ajuste_grupo'] = trascendencia['ajuste']
        if trascendencia['ajuste']:
            resultado['motivos'].append('El resultado cambia los escenarios de cuartos o primer puesto del grupo')
    except (ValueError, KeyError, TypeError):
        resultado['estado_grupo'] = datos.get('estado_grupo', 'grupo sin validar')
    return resultado
