"""Ajuste contextual acotado y auditable, independiente del horario y el acceso."""
from datetime import datetime, timedelta

from .config import MADRID_TZ
from .contexto_fuentes import fecha_iso, temporada, liga_evento
from .perfiles import normalizar


def valorar_contexto(evento):
    vacio = {'ajuste': 0.0, 'motivos': [], 'fuentes': [], 'estado': 'sin datos'}
    c = evento.get('contexto')
    if not c:
        return vacio
    try:
        inicio = evento.get('inicio') or datetime.fromisoformat(
            f"{evento['fecha']}T{evento['hora']}").replace(tzinfo=MADRID_TZ)
        consulta = fecha_iso(c['consultado'])
        if not timedelta(0) <= inicio - consulta <= timedelta(hours=36):
            return {**vacio, 'estado': 'datos fuera del corte temporal'}
        if c['temporada'] != temporada(inicio):
            return {**vacio, 'estado': 'otra temporada'}
        if c.get('competicion') == 'bra.1' and any(c[lado].get('temporada_fuente') != inicio.year for lado in ('local', 'visitante')):
            raise ValueError('Temporada brasileña no validada')
        if c.get('tipo') == 'nba':
            if (evento['deporte'] != 'Baloncesto' or 'nba' not in normalizar(evento['competicion']).split()
                    or c.get('competicion') != 'nba' or c.get('estado_partido') != 'pre'
                    or not c.get('partido_id') or not c.get('fuentes')
                    or fecha_iso(c['inicio']) <= consulta
                    or abs(fecha_iso(c['inicio']) - inicio) > timedelta(minutes=15)
                    or any(c[k]['nombre'] != evento[k] or not c[k].get('id') for k in ('local','visitante'))
                    or c['local']['id'] == c['visitante']['id']):
                raise ValueError()
            fase = c.get('fase')
            ajuste = {'grupos':.3, 'cuartos':.6, 'semifinal':.9, 'final':1.2}.get(fase, 0) if c.get('copa') is True else 0
            from .contexto_nba_directo import valorar_forma
            forma = valorar_forma(c, consulta)
            return {'ajuste':ajuste + forma['ajuste'], 'ajuste_fase_nba':ajuste,
                    'ajuste_forma_nba':forma['ajuste'], 'forma_nba':forma,
                    'estado':'validado', 'fase_nba':fase,
                    'motivos':([f'NBA Cup: {fase} confirmado por encuentro'] if ajuste else []) + forma['motivos'],
                    'fuentes':list(dict.fromkeys(c['fuentes'] + forma['fuentes'])), 'consultado':c['consultado']}
        if c.get('tipo') == 'tenis':
            if evento['deporte'] != 'Tenis' or c.get('competicion') != 'atp' or not c.get('fuentes'):
                raise ValueError()
            if not timedelta(0) <= consulta - fecha_iso(c['publicado']) <= timedelta(days=10):
                raise ValueError()
            individuales = {k:c[k] for k in ('local','visitante') if k in c}
            for k, p in individuales.items():
                if p['nombre'] != evento[k] or type(p['ranking']) is not int or not 1 <= p['ranking'] <= 1000:
                    raise ValueError()
            if not individuales:
                raise ValueError()
            if len(individuales) == 1:
                return {**vacio, 'estado':'parcial', 'jugadores':individuales, 'fuentes':c['fuentes'],
                        'consultado':c['consultado'], 'publicado':c['publicado']}
            jugadores = [individuales['local'], individuales['visitante']]
            ranking = sorted(p['ranking'] for p in jugadores)
            ajuste = .6 if ranking[1] <= 10 else .4 if ranking[0] <= 10 and ranking[1] <= 30 else .2 if ranking[1] <= 30 else 0
            motivos = []
            if ajuste:
                motivos.append(f'Contexto: ranking ATP {jugadores[0]["ranking"]} frente a {jugadores[1]["ranking"]}')
            afinidad = 0
            for p, rival in ((jugadores[0], jugadores[1]), (jugadores[1], jugadores[0])):
                if (p.get('pais') == 'ESP' and type(p.get('edad')) is int and 18 <= p['edad'] <= 22
                        and p['ranking'] <= 100 and rival['ranking'] <= 10):
                    afinidad = .6
                    motivos.append('Contexto de afinidad: joven español del top-100 frente a un top-10')
            return {'ajuste': ajuste, 'afinidad': afinidad, 'motivos': motivos, 'fuentes': c['fuentes'], 'jugadores':individuales,
                    'estado': 'validado', 'consultado': c['consultado'], 'publicado': c['publicado']}
        if c.get('tipo') == 'copa':
            copa = c['copa']
            if (evento['deporte'] != 'Fútbol' or c['competicion'] != 'esp.copa_del_rey'
                    or c['local']['nombre'] != evento['local'] or c['visitante']['nombre'] != evento['visitante']
                    or copa.get('partido_unico') is not True or not copa.get('fuentes')):
                raise ValueError()
            ajuste = .6 if copa.get('contraste_primera') is True else 0.0
            motivos = ['Contexto: partido único con local fuera de Primera y visitante de Primera'] if ajuste else []
            if (not ajuste and copa.get('contraste_segunda') is True
                    and c['local'].get('categoria') == 'Fuera de Primera y Segunda'
                    and c['visitante'].get('categoria') == 'Segunda'):
                ajuste = .3
                motivos.append('Contexto: partido único con local fuera de Primera y Segunda frente a un Segunda')
            fuentes = list(copa['fuentes'])
            f = copa.get('forma_visitante', {})
            extra = 0.0
            try:
                forma = f['forma']
                if (ajuste and f['nombre'] == evento['visitante'] and f['id'] == c['visitante']['id']
                        and type(f['jugados']) is int and f['jugados'] >= 5
                        and len(forma) == 5 and not set(forma) - set('WDL') and f['fuentes']
                        and fecha_iso(f['ultimo_partido']) + timedelta(hours=3) <= consulta):
                    if forma.count('L') >= 3 or 'W' not in forma:
                        extra = .3
                        motivos.append('Contexto de Copa: visitante con tres derrotas o cinco partidos sin ganar en su liga')
                    fuentes.extend(f['fuentes'])
            except (KeyError, TypeError, ValueError, AttributeError):
                pass  # Un historial incompleto no invalida las categorías contrastadas.
            return {'ajuste': ajuste + extra, 'contraste': ajuste, 'vulnerabilidad': extra,
                    'estado_forma': copa.get('estado_forma', 'Historial no consultado'),
                    'motivos': motivos, 'detalle_copa': f"{c['local'].get('categoria','Categoría no precisada')} frente a {c['visitante'].get('categoria','Categoría no precisada')}",
                    'fuentes': list(dict.fromkeys(fuentes)), 'estado': 'validado', 'consultado': c['consultado']}
        if evento['deporte'] == 'Fútbol' and c['competicion'] != liga_evento(evento):
            raise ValueError()
        if evento['deporte'] == 'Baloncesto' and (c['competicion'] != 'euro' or not any(x in normalizar(evento['competicion']) for x in ('euroliga','euroleague'))):
            raise ValueError()
        if evento['deporte'] not in ('Fútbol','Baloncesto'):
            raise ValueError()
        equipos = [c['local'], c['visitante']]
        for k, e in zip(('local', 'visitante'), equipos):
            if e['nombre'] != evento[k]:
                raise ValueError()
            if any(type(e[n]) is not int for n in ('posicion', 'jugados', 'victorias', 'derrotas')):
                raise ValueError()
            if not 1 <= e['posicion'] <= 40 or not 0 <= e['victorias'] <= e['jugados']:
                raise ValueError()
            if not 0 <= e['derrotas'] <= e['jugados'] - e['victorias']:
                raise ValueError()
            if not 1 <= len(e['forma']) <= 5 or set(e['forma']) - set('WDL'):
                raise ValueError()
            if fecha_iso(e['ultimo_partido']) + timedelta(hours=3) > consulta:
                raise ValueError()
            if not e['fuentes']:
                raise ValueError()
        if c.get('tipo') == 'champions':
            if c.get('competicion') != 'uefa.champions' or any(
                    e.get('fase_competicion') != 'league phase' or e.get('temporada_fuente') != temporada(inicio)
                    or not 3 <= e['jugados'] <= 8 or not 1 <= e['posicion'] <= 36 or e.get('puntos') != e['victorias']*3 + e['jugados']-e['victorias']-e['derrotas']
                    for e in equipos):
                raise ValueError('Fase, edición o muestra Champions sin validar')
            ajuste = max(.4 if any(e['victorias']/e['jugados'] >= .75 for e in equipos) else 0,
                         .25 if any(e['forma'].startswith('WW') for e in equipos) else 0)
            fuerte, debil = sorted(equipos, key=lambda equipo:equipo['posicion'])
            desequilibrio = debil['posicion']-fuerte['posicion'] >= 16 and debil['victorias']/debil['jugados'] <= .25
            if desequilibrio:
                ajuste = min(ajuste, .2)
            fuentes = list(dict.fromkeys(url for e in equipos for url in e['fuentes']))
            return dict(ajuste=ajuste, estado='validado', consultado=c['consultado'], fuentes=fuentes,
                        moderacion_champions=desequilibrio,
                        motivos=['Rendimiento europeo anterior al encuentro contrastado'] if ajuste else [],
                        fase_champions='league phase')
        if any(e['jugados'] < 5 for e in equipos):
            return {**vacio, 'estado': 'muestra inferior a cinco partidos'}
        candidatos = [(0.0, 'Sin señal excepcional en el contexto disponible')]
        zona_alta = all(e['posicion'] <= 5 for e in equipos)
        if zona_alta:
            candidatos.append((1.0, 'Cruce entre dos equipos situados entre los cinco primeros'))
        if zona_alta and any(e['forma'].startswith('WWW') for e in equipos):
            candidatos.append((1.3, 'Cruce de zona alta con una racha de tres victorias consecutivas'))
        if all(e['forma'].startswith('WWW') for e in equipos):
            candidatos.append((1.0, 'Ambos equipos encadenan tres victorias en esta competición'))
        for e in equipos:
            if e['posicion'] <= 3:
                candidatos.append((0.5, f"{e['nombre']}: entre los tres primeros"))
                if e['victorias'] / e['jugados'] >= .8 and e['derrotas'] == 0:
                    candidatos.append((1.2, f"{e['nombre']}: entre los tres primeros, invicto y con al menos un 80% de victorias"))
            if e['forma'].count('W') >= 4:
                candidatos.append((0.6, f"{e['nombre']}: al menos cuatro victorias en los últimos cinco partidos"))
            elif e['forma'].startswith('WWW'):
                candidatos.append((0.5, f"{e['nombre']}: tres victorias consecutivas"))
        # Las señales relacionadas compiten: no sumar posición, invicto y racha por separado.
        ajuste, motivo = max(candidatos, key=lambda x: x[0])
        moderacion = 0.0
        if evento['deporte'] == 'Fútbol':
            fuerte, debil = sorted(equipos, key=lambda e: e['posicion'])
            if (len(fuerte['forma']) == len(debil['forma']) == 5
                    and fuerte['forma'].count('W') >= 4 and debil['forma'].count('L') >= 4
                    and debil['posicion'] - fuerte['posicion'] >= 10):
                # Moderar solo el extra contextual; nunca restar a la base ni por horario.
                moderacion = round(max(0, ajuste - .6), 2)
                ajuste = min(ajuste, .6)
        motivos = ['Contexto: ' + motivo] if ajuste else []
        if moderacion:
            motivos.append('Extra de forma moderado: gran diferencia de posición y rachas opuestas en la misma liga')
        fuentes = list(dict.fromkeys(u for e in equipos for u in e['fuentes']))
        return {'ajuste': min(1.5, ajuste), 'motivos': motivos, 'moderacion_forma': moderacion,
                'fuentes': fuentes, 'estado': 'validado', 'consultado': c['consultado']}
    except (KeyError, ValueError, TypeError, AttributeError):
        return {**vacio, 'estado': 'contexto no válido'}
