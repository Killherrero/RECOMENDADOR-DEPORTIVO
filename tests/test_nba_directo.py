import copy
import json
import unittest
from datetime import datetime, timedelta
from unittest.mock import patch

from resumen.config import MADRID_TZ
from resumen.contexto import valorar_contexto
from resumen.contexto_fuentes import enriquecer_eventos, ErrorContexto
from resumen.contexto_nba_directo import historial, valorar_forma
from resumen.diagnostico import preparar_diagnostico, reproducir
from resumen.eventos import evaluar_evento, recomendar_eventos

CORTE = datetime(2026,11,21,10,tzinfo=MADRID_TZ)


def evento():
    return dict(local='Philadelphia 76ers',visitante='Milwaukee Bucks',deporte='Baloncesto',
                competicion='NBA Liga Regular',fecha='2026-11-21',hora='19:00',canales=[])


def ficha():
    return dict(id='actual',date='2026-11-21T18:00Z',competitions=[dict(
        date='2026-11-21T18:00Z',status=dict(type=dict(state='pre')),
        competitors=[dict(homeAway=lado,team=dict(id=identidad,displayName=nombre))
                     for lado,identidad,nombre in [('home','20','Philadelphia 76ers'),('away','15','Milwaukee Bucks')]])])


def tabla():
    conferencias = []
    for conferencia, ids in [('este',list(range(1,16))),('oeste',list(range(16,31)))]:
        entradas = []
        for posicion, identidad in enumerate(ids,1):
            nombre = {20:'Philadelphia 76ers',15:'Milwaukee Bucks'}.get(identidad,'Equipo '+str(identidad))
            entradas.append(dict(team=dict(id=str(identidad),displayName=nombre),stats=[
                dict(name='wins',value=8),dict(name='losses',value=2),
                dict(name='playoffSeed',value=1 if identidad in (15,20) else posicion)]))
        # Posiciones completas y únicas, con ambos participantes en la zona alta.
        objetivo = 15 if conferencia=='este' else 20
        entradas.sort(key=lambda entrada:entrada['team']['id']!=str(objetivo))
        for posicion,entrada in enumerate(entradas,1):
            entrada['stats'][2]['value']=posicion
        conferencias.append(dict(id=conferencia,standings=dict(entries=entradas)))
    return dict(season=dict(year=2027),children=conferencias)


def calendario(identidad):
    partidos = []
    for indice in range(10):
        victoria = indice >= 2
        partidos.append(dict(id=f'{identidad}-{indice}',date=f'2026-11-{indice+1:02d}T00:00Z',
            season=dict(year=2027),seasonType=dict(type=2),competitions=[dict(
                status=dict(type=dict(completed=True)),competitors=[
                    dict(id=identidad,score=dict(value=110 if victoria else 90),winner=victoria),
                    dict(id='rival',score=dict(value=100),winner=not victoria)])]))
    return dict(season=dict(year=2027,type=2),team=dict(id=identidad),events=partidos)


def consultar(fallo=None):
    def fuente(url):
        if 'scoreboard' in url:
            return dict(events=[ficha()])
        if 'standings' in url:
            if fallo=='tabla':
                raise ErrorContexto('caída')
            return tabla()
        identidad = '20' if '/20/' in url else '15'
        datos = calendario(identidad)
        if fallo=='historial' and identidad=='15':
            datos['events'].pop()
        return datos
    e=evento()
    with patch('resumen.contexto_fuentes.descargar_json',side_effect=fuente) as descarga:
        enriquecer_eventos([e],CORTE)
    return e, descarga.call_count


class NBADirectoTests(unittest.TestCase):
    def test_entrada_normal_valida_ambos_equipos_y_comparte_tabla(self):
        e,llamadas=consultar()
        self.assertEqual(llamadas,4)
        self.assertEqual(e['contexto']['estado_forma'],'Balances e históricos NBA contrastados')
        valor=evaluar_evento(e)
        self.assertEqual(valor['evaluacion_contexto']['forma_nba']['objetivo_cartel'],2)
        self.assertEqual(valor['desglose']['cartel']+valor['evaluacion_contexto']['ajuste_forma_nba']+valor['desglose']['calidad_cruce'],2)
        for clave in ['"score":','"winner":','"goles":']:
            self.assertNotIn(clave,json.dumps(e['contexto']))

    def test_tabla_caida_y_historial_incompleto_conservan_fase_y_base(self):
        for fallo in ['tabla','historial']:
            e,_=consultar(fallo)
            self.assertNotIn('forma_nba',e['contexto'])
            self.assertEqual(evaluar_evento(e)['score'],evaluar_evento(evento())['score'])
            self.assertEqual(e['contexto']['estado_partido'],'pre')

    def test_datos_posteriores_al_corte_no_entran_en_el_balance(self):
        datos=calendario('20')
        ultimo=datos['events'][-1]
        ultimo['date']=(CORTE-timedelta(hours=2)).isoformat()
        self.assertEqual(len(historial(datos,'20',2027,CORTE)),9)
        datos['season']['year']=2026
        with self.assertRaises(ValueError):
            historial(datos,'20',2027,CORTE)

    def test_historial_duplicado_no_se_acepta(self):
        datos=calendario('20');datos['events'].append(datos['events'][0])
        with self.assertRaises(ValueError):
            historial(datos,'20',2027,CORTE)

    def test_identidad_muestra_y_balance_invalidos_no_ajustan(self):
        e,_=consultar()
        for campo,valor in [('id','otro'),('jugados',4),('victorias',30),('temporada_fuente',2026),
                            ('victorias_ultimos5',6),('ultimo_partido',CORTE.isoformat()),
                            ('ultimo_partido',(CORTE-timedelta(days=15)).isoformat())]:
            otro=copy.deepcopy(e['contexto']);otro['forma_nba']['local'][campo]=valor
            self.assertEqual(valorar_forma(otro,CORTE)['estado'],'sin datos de forma NBA')

    def test_desequilibrio_modera_el_extra(self):
        e,_=consultar();c=e['contexto']
        c['forma_nba']['visitante'].update(victorias=1,derrotas=9,victorias_ultimos5=1,posicion=15)
        r=valorar_forma(c,CORTE)
        self.assertTrue(r['moderacion']);self.assertEqual(r['objetivo_cartel'],0)
        self.assertLessEqual(r['ajuste'],.2)

    def test_copa_no_duplica_ronda_y_conserva_forma(self):
        e,_=consultar();e['contexto'].update(copa=True,fase='cuartos')
        e['competicion']='NBA Cup Cuartos de Final'
        r=evaluar_evento(e)
        self.assertEqual(r['desglose']['fase'],1)
        self.assertEqual(r['evaluacion_contexto']['ajuste'],.6)
        self.assertEqual(r['evaluacion_contexto']['ajuste_forma_nba'],.6)

    def test_instantanea_reproduce_nota_y_agregados_sin_red(self):
        e,_=consultar();r=recomendar_eventos([e],ahora=CORTE)
        snapshot=preparar_diagnostico(r,CORTE)
        with patch('resumen.contexto_fuentes.descargar_json',side_effect=AssertionError('sin red')):
            copia=reproducir(snapshot)
        self.assertEqual(copia['filtrados'][0]['score'],r['filtrados'][0]['score'])
