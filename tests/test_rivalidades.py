import unittest
from html import escape
from resumen.rivalidades import valorar_rivalidad, REGISTRO
from resumen.eventos import evaluar_evento
from resumen.diseno_correo import desglose_html


def evento(a, b, deporte='Fútbol', comp='Copa del Rey'):
    return dict(local=a, visitante=b, deporte=deporte, competicion=comp,
                fecha='2026-10-28', hora='21:00', canales=[])


class RivalidadesTests(unittest.TestCase):
    def test_registro_documentado_sin_parejas_duplicadas(self):
        claves = [(r['deporte'],frozenset(r['equipos'])) for r in REGISTRO]
        self.assertEqual(len(claves),len(set(claves)))
        for r in REGISTRO:
            self.assertTrue(r['fuente'].startswith('https://'))
            self.assertTrue(0 < r['bonus'] <= (2.2 if r.get('intensidad') == 'maxima' else .6))
            self.assertIn(r['tipo'], ('Derbi local','Rivalidad histórica'))

    def test_simetria_todas_las_parejas(self):
        for r in REGISTRO:
            a,b=r['equipos']
            # ID interno de Xerez tiene su nombre público exacto.
            a='Xerez CD' if a == 'xerez-cd' else a
            comp='Eurocopa' if r.get('ambito') == 'selecciones' else 'Copa del Rey'
            self.assertEqual(valorar_rivalidad(evento(a,b,r['deporte'],comp))['ajuste'],r['bonus'])
            self.assertEqual(valorar_rivalidad(evento(b,a,r['deporte'],comp))['ajuste'],r['bonus'])

    def test_xerez_abreviado_solo_en_ficha_confirmada(self):
        e=evento('Xerez','Cádiz CF')
        self.assertEqual(valorar_rivalidad(e)['ajuste'],.6)
        self.assertEqual(valorar_rivalidad({**e,'fecha':'2026-11-01'})['ajuste'],0)
        self.assertEqual(valorar_rivalidad(evento('Xerez Deportivo FC','Cádiz CF'))['ajuste'],0)

    def test_sin_coincidencias_por_fragmentos_o_geografia(self):
        for a,b in [('Real Madrid Castilla','FC Barcelona'),('Valencia','FC Barcelona'),
                    ('Sevilla Atlético','Real Betis'),('Xerez CD B','Cádiz CF')]:
            self.assertEqual(valorar_rivalidad(evento(a,b))['ajuste'],0)

    def test_baloncesto_alias_y_deporte_independientes(self):
        e=evento('Panathinaikos BC','Olympiacos Piraeus','Baloncesto','Euroliga')
        self.assertEqual(valorar_rivalidad(e)['ajuste'],.6)
        self.assertEqual(valorar_rivalidad({**e,'deporte':'Fútbol'})['ajuste'],0)

    def test_bonus_copa_una_vez_y_fuente_visible(self):
        e=evento('Xerez CD','Cádiz CF'); r=evaluar_evento(e)
        self.assertEqual(r['desglose']['rivalidad'],.6)
        self.assertEqual(r['desglose']['contexto'],0)
        self.assertEqual(r['desglose']['cartel'],0)
        self.assertAlmostEqual(r['score'],5.3)
        html=desglose_html({**e,**r})
        self.assertIn('Derbi gaditano',html)
        self.assertIn(escape(r['evaluacion_rivalidad']['fuente'],quote=True),html)

    def test_acceso_no_cambia_nota(self):
        e=evento('Real Madrid','FC Barcelona')
        self.assertEqual(evaluar_evento(e)['score'],evaluar_evento({**e,'canales':['DAZN'],'vision_parcial':True})['score'])
