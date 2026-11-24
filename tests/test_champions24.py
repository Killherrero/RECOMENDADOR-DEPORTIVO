import unittest
from datetime import datetime
from unittest.mock import patch

from resumen.config import MADRID_TZ
from resumen.contexto import valorar_contexto
from resumen.contexto_fuentes import liga_evento, tabla_futbol, ErrorContexto
from resumen.eventos import evaluar_evento
from resumen.perfiles import identidad_basket


def partido():
    e=dict(local='Galatasaray',visitante='Aston Villa',deporte='Fútbol',
           competicion='Champions League Fase Liga',fecha='2026-11-24',hora='18:45',canales=[])
    equipos={}
    for lado, victorias, posicion in [('local',2,18),('visitante',3,6)]:
        equipos[lado]=dict(nombre=e[lado],id=lado,posicion=posicion,jugados=4,victorias=victorias,
            derrotas=4-victorias,forma='WWLL' if lado=='local' else 'WLWW',puntos=victorias*3,
            fase_competicion='league phase',temporada_fuente=2026,
            ultimo_partido='2026-11-03T20:00:00Z',fuentes=['https://example.org/champions'])
    e['contexto']=dict(tipo='champions',competicion='uefa.champions',temporada=2026,
        consultado='2026-11-24T10:00:00+01:00',**equipos)
    return e


class Champions24Tests(unittest.TestCase):
    def test_fase_liga_con_cuatro_jornadas_aceptada_y_afinidad_separada(self):
        e=partido();r=evaluar_evento(e)
        self.assertEqual(r['evaluacion_contexto']['ajuste'],.4)
        self.assertEqual(r['desglose']['afinidad'],1.5)
        self.assertEqual(r['score'],8.3)

    def test_fase_y_muestra_distintas_no_heredan_contexto(self):
        for cambio in [('fase_competicion','qualifying'),('temporada_fuente',2025),
                       ('jugados',2),('jugados',9),('puntos',20)]:
            e=partido();e['contexto']['local'][cambio[0]]=cambio[1]
            self.assertEqual(valorar_contexto(e)['ajuste'],0)
        for comp in ['Europa League Fase Liga','Champions League Final',
                     'UEFA Champions League Sub-19 Fase Liga','AFC Champions League Fase Liga']:
            self.assertNotEqual(liga_evento({**partido(),'competicion':comp}),'uefa.champions')

    def test_tabla_e_historicos_validan_fase_y_descartan_previas(self):
        entradas=[]
        for i in range(36):
            entradas.append(dict(team=dict(id=str(i),displayName='Club '+str(i)),
                stats=[dict(name=k,value=v) for k,v in dict(gamesPlayed=4,wins=3,ties=0,losses=1,rank=i+1,points=9).items()]))
        tabla=dict(season=dict(year=2026),children=[dict(name='League Phase',standings=dict(entries=entradas))])
        eventos=[]
        for i in range(5):
            eventos.append(dict(id=str(i),date=f'2026-10-{i+1:02d}T20:00Z',league=dict(slug='uefa.champions'),
                season=dict(year=2026),seasonType=dict(name='Qualifying' if i==4 else 'League Phase'),
                competitions=[dict(status=dict(type=dict(completed=True)),competitors=[
                    dict(id='0',score=dict(value=2 if i<3 else 0)),dict(id='rival',score=dict(value=1))])]))
        historial=dict(season=dict(year=2026),team=dict(id='0'),events=eventos)
        with patch('resumen.contexto_fuentes.descargar_json',side_effect=[tabla,historial]):
            r=tabla_futbol('uefa.champions',['Club 0'],datetime(2026,11,24,10,tzinfo=MADRID_TZ))
        self.assertEqual(r['Club 0']['jugados'],4)
        self.assertEqual(r['Club 0']['puntos'],9)
        self.assertEqual(r['Club 0']['fase_competicion'],'league phase')
        tabla['children'][0]['name']='Qualifying'
        with patch('resumen.contexto_fuentes.descargar_json',return_value=tabla):
            with self.assertRaises(ErrorContexto):
                tabla_futbol('uefa.champions',['Club 0'],datetime(2026,11,24,10,tzinfo=MADRID_TZ))

    def test_besiktas_alias_exactos_sin_filiales(self):
        self.assertEqual(identidad_basket('Besiktas JK Istanbul'),identidad_basket('Besiktas Fuzul Istanbul'))
        self.assertNotEqual(identidad_basket('Besiktas B'),identidad_basket('Besiktas JK Istanbul'))

    def test_euroliga_muestra_madura_completa_hasta_objetivo(self):
        from resumen.calidad_cruce import valorar_cruce
        e=dict(deporte='Baloncesto',contexto=dict(competicion='euro',
            local=dict(posicion=7,jugados=13,victorias=8),visitante=dict(posicion=5,jugados=13,victorias=8)))
        c=dict(estado='validado',ajuste=0)
        self.assertAlmostEqual(valorar_cruce(e,c,1.5)['ajuste'],.9)
        self.assertEqual(valorar_cruce(e,{**c,'ajuste':1.3},1.5)['ajuste'],0)
        e['contexto']['visitante']['victorias']=5
        self.assertEqual(valorar_cruce(e,c,1.5)['ajuste'],0)

    def test_racha_de_un_grande_se_modera_ante_rival_debil(self):
        e=partido();e['contexto']['local'].update(posicion=30,victorias=1,derrotas=3,puntos=3)
        r=valorar_contexto(e)
        self.assertTrue(r['moderacion_champions'])
        self.assertEqual(r['ajuste'],.2)

    def test_acceso_y_horario_no_alteran_nota(self):
        e=partido()
        self.assertEqual(evaluar_evento(e)['score'],evaluar_evento({**e,'canales':['DAZN'],'vision_parcial':True})['score'])
