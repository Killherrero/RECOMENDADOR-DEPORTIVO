import unittest
from datetime import datetime

from resumen.config import MADRID_TZ
from resumen.contexto_fuentes import alias_futbol
from resumen.diagnostico import preparar_diagnostico, reproducir
from resumen.eventos import evaluar_evento, recomendar_eventos
from resumen.selecciones import valorar_selecciones


def partido(local, visitante, competicion='UEFA Nations League Fase de grupos', **extra):
    return dict(local=local, visitante=visitante, competicion=competicion,
                deporte='Fútbol', fecha='2026-11-12', hora='20:45', canales=[], **extra)


class SeleccionesTests(unittest.TestCase):
    def test_espana_recibe_afinidad_personal_y_no_repite_bonus(self):
        evento = evaluar_evento(partido('República Checa', 'España'))
        self.assertEqual(evento['desglose']['afinidad'], 1.5)
        self.assertEqual(evento['score'], 8.4)
        self.assertEqual(evento['score'], evaluar_evento(partido('Czechia', 'Spain'))['score'])

    def test_liga_y_calidad_conjunta_diferencian_selecciones(self):
        grande = evaluar_evento(partido('Italia', 'Francia'))
        modesto = evaluar_evento(partido('Armenia', 'Chipre'))
        self.assertGreater(grande['score'], modesto['score'])
        self.assertEqual(grande['evaluacion_selecciones']['grupo'], 'A1')
        self.assertEqual(grande['desglose']['cartel'], 1.6)
        self.assertEqual(evaluar_evento(partido('Inglaterra', 'Croacia'))['score'], 7.2)

    def test_concacaf_y_miembros_sin_ranking_fifa(self):
        evento = evaluar_evento(partido('Barbados', 'Guadalupe', 'CONCACAF Nations League'))
        self.assertEqual(evento['score'], 3.7)
        self.assertEqual(evento['evaluacion_selecciones']['grupo'], 'BB')
        playin = evaluar_evento(partido('Aruba', 'Martinica', 'CONCACAF Nations League'))
        self.assertEqual(playin['score'], 4.0)

    def test_catalogo_no_heredado_por_otras_ediciones_ni_juveniles(self):
        for cambio in [dict(fecha='2027-11-12'), dict(fecha='2026-01-12'),
                       dict(competicion='UEFA Nations League Sub-19'),
                       dict(competicion='UEFA Nations League Femenina'),
                       dict(competicion='LaLiga'), dict(local='Italia B'),
                       dict(competicion='UEFA Nations League Final'),
                       dict(local='Italia', visitante='España'),
                       dict(competicion='CONCACAF Nations League')]:
            self.assertIsNone(valorar_selecciones({**partido('Italia', 'Francia'), **cambio}))

    def test_fecha_y_canales_no_crean_bonus_por_jornada(self):
        uno = evaluar_evento(partido('Italia', 'Francia'))
        dos = evaluar_evento({**partido('Italia', 'Francia'), 'fecha':'2026-09-25', 'canales':['DAZN']})
        self.assertEqual(uno['score'], dos['score'])

    def test_alias_coperos_exactos_sin_confundir_filiales(self):
        for proveedor, agenda in [('CD Artistico Navalcarnero', 'Navalcarnero'),
                                  ('CS Puertollano', 'Calvo Sotelo Puertollano'),
                                  ('CD Tarancon', 'Tarancón')]:
            self.assertEqual(alias_futbol(proveedor), alias_futbol(agenda))
        self.assertNotEqual(alias_futbol('Navalcarnero B'), alias_futbol('Navalcarnero'))

    def test_agenda_y_diagnostico_conservan_fuentes_y_nota(self):
        corte = datetime(2026, 11, 12, 10, tzinfo=MADRID_TZ)
        resultado = recomendar_eventos([partido('República Checa', 'España')], ahora=corte)
        snapshot = preparar_diagnostico(resultado, corte)
        datos = snapshot['eventos'][0]['evaluacion_selecciones']
        self.assertTrue(datos['fuentes'])
        self.assertEqual(reproducir(snapshot)['filtrados'][0]['score'], 8.4)
