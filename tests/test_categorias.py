import unittest
from datetime import date

from resumen.categorias import categoria_tenis
from resumen.eventos import calculate_score, recomendar_eventos, normalize_team_name, evaluar_evento
from resumen.__main__ import demostracion
from resumen.informe import generar_informe

def tenis(comp='Torneo de Basilea 1ª Ronda', local='H. Rune', visitante='Q. Halys',fecha='2026-10-26'):
    return {'hora':'15:00','deporte':'Tenis','competicion':comp,'local':local,'visitante':visitante,
            'canales':['ATP Tennis TV','M+ Deportes (63)'],'fecha':fecha}

class CategoriasTests(unittest.TestCase):
    def test_categoria_por_alias_verificados_y_temporada(self):
        for nombre,categoria in [('Basilea','ATP 500'),('Basel','ATP 500'),('Swiss Indoors','ATP 500'),
                                  ('Viena','ATP 500'),('Vienna','ATP 500'),('Almaty','ATP 250')]:
            with self.subTest(nombre=nombre):
                self.assertEqual(categoria_tenis(tenis(f'Torneo de {nombre} 1ª Ronda'))[0],categoria)
        self.assertIsNone(categoria_tenis(tenis(fecha='2027-10-26'))[0])
        self.assertIsNone(categoria_tenis(tenis('Challenger Basel'))[0])
        self.assertIsNone(categoria_tenis(tenis('WTA Torneo de Viena'))[0])
        for torneo, categoria in [('Wimbledon Final','Grand Slam'),('Roland Garros Final','Grand Slam'),
                                  ('Torneo de Rotterdam 1ª Ronda','ATP 500'),('Cincinnati Final','Masters 1000')]:
            self.assertEqual(categoria_tenis(tenis(torneo))[0],categoria)

    def test_categoria_explicita_prevalece_y_no_confunde_numeros(self):
        self.assertEqual(categoria_tenis(tenis('Torneo de Basilea ATP 250'))[0],'ATP 250')
        self.assertEqual(categoria_tenis(tenis('ATP Masters 1000 Shanghai'))[0],'Masters 1000')
        self.assertIsNone(categoria_tenis(tenis('Torneo desconocido Premio 500 euros'))[0])

    def test_categoria_desconocida_y_afinidad_ausente_son_neutrales(self):
        self.assertEqual(calculate_score(tenis()),4.5)
        self.assertEqual(calculate_score(tenis('Torneo desconocido')),3.3)
        self.assertEqual(calculate_score(tenis('Torneo desconocido',local='C. Alcaraz')),4.7)

    def test_final_con_jugadores_fuera_de_lista_no_se_pierde(self):
        final=tenis('Torneo de Viena Final',local='Jugador A',visitante='Jugador B')
        final['canales']=['DAZN']
        result=recomendar_eventos([final],fecha=date(2026,10,26))
        self.assertEqual(len(result['filtrados']),1)
        self.assertEqual(result['filtrados'][0]['score'],6.4)
        self.assertEqual(result['plan'],{})
        self.assertEqual(recomendar_eventos([tenis('Torneo de Viena 1ª Ronda',local='Jugador A',visitante='Jugador B')],fecha=date(2026,10,26))['filtrados'],[])

    def test_liga_neutral_y_reconocimiento_argentino_acotado(self):
        e={'hora':'23:00','deporte':'Fútbol','competicion':'Primera División Argentina Torneo Clausura',
           'local':'Unión Santa Fe','visitante':'Estudiantes LP','canales':['Fanatiz']}
        result=recomendar_eventos([e],fecha=date(2026,10,26))['filtrados'][0]
        self.assertEqual(result['score'],3.9) # Estudiantes LP: reconocimiento editorial +0,35.
        self.assertEqual(result['prioridad'],3.4) # La limitación horaria cambia encaje, no interés.
        self.assertEqual(calculate_score({**e,'competicion':'Conference League'}),5.0)

    def test_alias_y_puntuaciones_equivalentes_sin_inventar_favoritos(self):
        for nombres in [('O. Lyonnais','Olympique Lyonnais','Lyon'),('SL Benfica','Benfica'),
                         ('O. Marseille','Olympique de Marseille','Olympique Marsella'),
                         ('FC Porto','Porto'),('Newcastle Utd.','Newcastle United')]:
            self.assertEqual(len({normalize_team_name(n) for n in nombres}),1)
        e={'hora':'19:45','deporte':'Fútbol','competicion':'Liga portuguesa','local':'Benfica','visitante':'Santa Clara','canales':['DAZN']}
        self.assertEqual(calculate_score(e),calculate_score({**e,'local':'SL Benfica'}))
        self.assertEqual(evaluar_evento(e)['desglose']['afinidad'],0.2) # Solo preferencia por fútbol.

    def test_categoria_visible_en_correo_y_adjunto(self):
        result=demostracion('eventos')
        result['eventos']=recomendar_eventos([tenis()],fecha=date(2026,10,26))
        report=generar_informe(result)
        for key in ('texto','html','listado_html'):
            self.assertIn('ATP 500',report[key])

if __name__ == '__main__':
    unittest.main()
