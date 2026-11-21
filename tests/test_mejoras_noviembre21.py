import unittest
from datetime import date, datetime
from unittest.mock import patch

from resumen.categorias import categoria_tenis
from resumen.config import MADRID_TZ
from resumen.eventos import evaluar_evento, recomendar_eventos
from resumen.reconocimiento import fase_argentina
from resumen.rivalidades import valorar_rivalidad
from resumen.contexto_fuentes import liga_evento, tabla_futbol, ErrorContexto


def evento(local, visita, comp, deporte='Fútbol', fecha='2026-11-21'):
    return dict(local=local, visitante=visita, competicion=comp, deporte=deporte,
                fecha=fecha, hora='20:30', canales=[])


class MejorasNoviembre21Tests(unittest.TestCase):
    def test_finals_reconocidas_con_grupos_semifinal_y_final_distintos(self):
        notas = []
        for ronda, esperado in [('Fase de grupos',0), ('Semifinal 1',1.6), ('Final',2.4)]:
            e = evento('C. Alcaraz', 'B. Shelton', 'Nitto ATP Finals ' + ronda, 'Tenis')
            self.assertEqual(categoria_tenis(e)[0], 'ATP Finals')
            resultado = evaluar_evento(e)
            self.assertEqual(resultado['desglose']['fase'], esperado)
            self.assertEqual(resultado['desglose']['base'], 5.6)
            notas.append(resultado['score'])
        self.assertEqual(notas, sorted(notas))
        self.assertGreaterEqual(notas[1], 8.5)

    def test_finales_dobles_y_next_gen_no_heredan_la_categoria(self):
        for comp in ['Next Gen ATP Finals Semifinal', 'ATP Finals Dobles Final',
                     'WTA Finals Final', 'Challenger ATP Finals', 'Torneo desconocido Final']:
            self.assertIsNone(categoria_tenis(evento('A','B',comp,'Tenis'))[0])

    def test_ambas_semifinales_pueden_entrar_sin_avisos_de_categoria(self):
        entradas = [evento('C. Alcaraz','B. Shelton','ATP Finals Semifinal 1','Tenis'),
                    evento('A. Zverev','D. Medvedev','ATP Finals Semifinal 2','Tenis')]
        resultado = recomendar_eventos(entradas, fecha=date(2026,11,21))
        self.assertTrue(all(e['categoria_reconocida']=='ATP Finals' and not e['avisos_datos']
                            for e in resultado['filtrados']))

    def test_derbi_sevillano_maximo_y_rotterdam_moderado_sin_filiales(self):
        sevilla = evento('Sevilla FC','Real Betis','LaLiga EA Sports')
        self.assertEqual(valorar_rivalidad(sevilla)['ajuste'], 2.2)
        self.assertGreaterEqual(evaluar_evento(sevilla)['score'], 7.5)
        self.assertEqual(valorar_rivalidad(evento('Feyenoord','Excelsior Rotterdam','Eredivisie'))['ajuste'],.35)
        for club in ['Sevilla Atlético', 'Sevilla FC B', 'Sevilla FC Femenino']:
            self.assertEqual(valorar_rivalidad({**sevilla,'local':club})['ajuste'],0)

    def test_brasil_reconoce_ambos_clubes_sin_inventar_contexto(self):
        grande = evaluar_evento(evento('Palmeiras','CR Flamengo','Serie A Brasil'))
        neutral = evaluar_evento(evento('Bahía','Coritiba','Serie A Brasil'))
        self.assertEqual(grande['desglose']['cartel'],2)
        self.assertEqual(grande['score'],6.2)
        self.assertEqual(neutral['score'],4.2)
        self.assertEqual(grande['desglose']['contexto'],0)
        self.assertEqual(evaluar_evento(evento('Palmeiras B','CR Flamengo','Serie A Brasil'))['desglose']['cartel'],.8)

    def test_argentina_partido_unico_sustituye_y_no_duplica_el_peso(self):
        e = evento('Argentinos Juniors','Independiente','Primera División Argentina 1/8 de Final')
        resultado = evaluar_evento(e)
        self.assertEqual(resultado['desglose']['fase'],1.2)
        self.assertEqual(resultado['score'],5.4)
        self.assertEqual(evaluar_evento({**e,'competicion':'Primera División Argentina Torneo Clausura'})['desglose']['fase'],0)
        for cambio in [dict(fecha='2027-11-21'),dict(competicion='Copa Argentina Octavos'),
                       dict(competicion='Primera División Argentina Octavos Ida'),
                       dict(competicion='Primera División Argentina Sub-20 Octavos')]:
            self.assertIsNone(fase_argentina({**e,**cambio},1,.6))

    def test_favoritos_siguen_con_su_bonus_completo(self):
        for club in ['Aston Villa','Borussia Dortmund','Roma','Atlético de Madrid']:
            self.assertEqual(evaluar_evento(evento(club,'Rival','Premier League'))['desglose']['afinidad'],1.5)

    @patch('resumen.contexto_fuentes.descargar_json', return_value={'season':{'year':2026}})
    def test_brasil_usa_temporada_natural_y_rechaza_otra_edicion(self, descarga):
        e = evento('Palmeiras','Flamengo','Serie A Brasil')
        self.assertEqual(liga_evento(e),'bra.1')
        with self.assertRaises(ErrorContexto) as error:
            tabla_futbol('bra.1', ['Palmeiras'], datetime(2027,1,15,tzinfo=MADRID_TZ))
        self.assertEqual(error.exception.codigo,'otra_temporada')
