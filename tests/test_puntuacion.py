import copy
import unittest
from datetime import date
from itertools import product

from resumen.eventos import evaluar_evento, recomendar_eventos, build_daily_plan
from resumen.informe import generar_informe
from resumen.__main__ import demostracion

def evento(local='Equipo A',visitante='Equipo B',comp='LaLiga EA Sports',sport='Fútbol',**extra):
    return {'hora':'19:00','local':local,'visitante':visitante,'competicion':comp,
            'deporte':sport,'canales':[],'fecha':'2026-10-26',**extra}

class PuntuacionTests(unittest.TestCase):
    def test_notas_acotadas_en_variedad_de_casos(self):
        for sport,comp,teams in product(['Fútbol','Baloncesto','Tenis','Automovilismo'],
                                       ['Liga regular','Champions League Final','Grand Slam Final','NBA Final'],
                                       [('Equipo A','Equipo B'),('Atlético de Madrid','Real Madrid'),('Celtics','Warriors')]):
            e=evento(*teams,comp,sport)
            r=evaluar_evento(e)
            self.assertGreaterEqual(r['score'],0)
            self.assertLessEqual(r['score'],10)
            self.assertAlmostEqual(round(r['desglose']['deportivo']+r['desglose']['afinidad'],1),r['score'])

    def test_canal_no_cambia_interes_y_no_tenerlo_no_castiga(self):
        e=evento('PSG','Lyon','Ligue 1')
        sin=evaluar_evento(e)
        dazn=evaluar_evento({**e,'canales':['DAZN']})
        movistar=evaluar_evento({**e,'canales':['Movistar Plus+ (M7)']})
        extra=evaluar_evento({**e,'canales':['M+ Liga de Campeones']})
        self.assertEqual(sin['score'],dazn['score'])
        self.assertEqual(sin['score'],movistar['score'])
        self.assertEqual(sin['prioridad'],extra['prioridad'])
        self.assertAlmostEqual(dazn['prioridad']-sin['prioridad'],0.2)

    def test_parcial_y_madrugada_cambian_encaje_no_nota(self):
        e=evento('Celtics','Warriors','NBA',sport='Baloncesto')
        completo=evaluar_evento(e)
        limitado=evaluar_evento({**e,'madrugada':True,'vision_parcial':True})
        self.assertEqual(completo['score'],limitado['score'])
        self.assertAlmostEqual(completo['prioridad']-limitado['prioridad'],1.1)

    def test_final_de_otro_deporte_puede_superar_futbol_ordinario(self):
        futbol=evaluar_evento(evento('Sevilla FC','Osasuna'))
        final=evaluar_evento(evento('España','Francia','Copa del Mundo Final',sport='Baloncesto'))
        tenis=evaluar_evento(evento('Jugador A','Jugador B','Wimbledon Final',sport='Tenis'))
        self.assertGreater(final['score'],futbol['score'])
        self.assertGreaterEqual(final['score'],8)
        self.assertGreater(tenis['score'],futbol['score'])
        playoff=evaluar_evento(evento('Celtics','Warriors','NBA Playoffs',sport='Baloncesto'))
        final_nba=evaluar_evento(evento('Celtics','Warriors','NBA Playoffs Final',sport='Baloncesto'))
        self.assertGreater(final_nba['score'],playoff['score'])

    def test_favoritos_en_los_tres_equipos_sin_forzar_siempre_un_diez(self):
        for sport,fav,otro,comp in [('Fútbol','Atlético de Madrid','Rival','LaLiga EA Sports'),
                                  ('Fútbol','Aston Villa','Rival','Premier League'),
                                  ('Baloncesto','Boston Celtics','Rival','NBA')]:
            personal=evaluar_evento(evento(fav,otro,comp,sport))
            neutral=evaluar_evento(evento('Equipo A',otro,comp,sport))
            self.assertGreater(personal['score'],neutral['score'])
            self.assertGreaterEqual(personal['desglose']['afinidad'],1.3)
            self.assertLess(personal['score'],8)

    def test_dia_flojo_no_se_reescala_ni_rellena(self):
        e=evento('Equipo A','Equipo B','Primera División Argentina')
        solo=recomendar_eventos([e],fecha=date(2026,10,26))
        mixto=recomendar_eventos([e,evento('PSG','Lyon','Ligue 1')],fecha=date(2026,10,26))
        self.assertEqual(solo['filtrados'][0]['score'],mixto['filtrados'][0]['score'])
        self.assertEqual(solo['plan'],{})

    def test_los_mejores_del_dia_sin_nota_ocho_no_se_llaman_imprescindibles(self):
        r=demostracion('eventos')
        r['eventos']=recomendar_eventos([evento('PSG','Lyon','Ligue 1')],fecha=date(2026,10,26))
        informe=generar_informe(r)
        self.assertIn('Lo mejor del día',informe['texto'])
        self.assertNotIn('📺 Imprescindible',informe['texto'])
        self.assertIn('/10',informe['html'])
        self.assertNotIn('Interés deportivo',informe['html'])

    def test_prioridad_ordena_sin_ocultar_nota_y_entrada_inmutable(self):
        e=evento('PSG','Lyon','Ligue 1',canales=['DAZN'])
        original=copy.deepcopy(e)
        r=recomendar_eventos([e],fecha=date(2026,10,26))
        self.assertEqual(e,original)
        value=r['filtrados'][0]
        self.assertIn('desglose',value)
        self.assertIn('motivos',value)
        self.assertEqual(value['escala'],'personal-10-v2')

if __name__ == '__main__':
    unittest.main()
