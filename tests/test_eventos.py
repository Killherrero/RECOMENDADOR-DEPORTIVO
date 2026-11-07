import ast
import copy
import json
import unittest
from datetime import date, datetime
from unittest.mock import Mock, patch

import requests
from bs4 import BeautifulSoup

from referencia import ROOT, ejecutar_eventos
from resumen.eventos import recomendar_eventos
from resumen.config import MADRID_TZ
from resumen.fuente_eventos import ErrorEventos, descargar_html, extraer_eventos

class EventosTests(unittest.TestCase):
    def test_resultado_mejorado_y_entrada_sin_modificar(self):
        events = json.loads((ROOT/'tests/fixtures/eventos.json').read_text(encoding='utf-8'))
        original_input = copy.deepcopy(events)
        new = recomendar_eventos(events)
        self.assertEqual(new['plan']['imprescindible']['local'], 'Liverpool')
        self.assertTrue(all(0 <= e['score'] <= 10 for e in new['filtrados']))
        self.assertEqual(len(new['plan']),len(new['seleccionados']))
        self.assertEqual([e['hora'] for e in new['alternativas']],
                         sorted(e['hora'] for e in new['alternativas']))
        self.assertEqual(events, original_input)

    def test_dia_sin_recomendaciones(self):
        self.assertEqual(recomendar_eventos([]), {'filtrados': [], 'plan': {}, 'seleccionados': [], 'alternativas': []})

    def test_html_guardado_coincide_con_scraping_original(self):
        html = (ROOT/'tests/fixtures/eventos_real_2026-10-25.html').read_text(encoding='utf-8')
        source = (ROOT/'referencia/eventos_colab.py').read_text(encoding='utf-8')
        tree = ast.parse(source)
        start = next(i for i,n in enumerate(tree.body) if isinstance(n,ast.Assign)
                     and isinstance(n.targets[0],ast.Name) and n.targets[0].id=='soup')
        end = next(i for i,n in enumerate(tree.body) if isinstance(n,ast.Assign)
                   and isinstance(n.targets[0],ast.Name) and n.targets[0].id=='TOP_ATP')
        nodes = [n for n in tree.body[start:end] if not isinstance(n,ast.Expr)]
        ns = {'html':html, 'BeautifulSoup':BeautifulSoup}
        exec(compile(ast.Module(body=nodes,type_ignores=[]),'<scraping original>','exec'),ns)
        actual = extraer_eventos(html,date(2026,10,25))
        self.assertEqual([{k:v for k,v in e.items() if k != 'descripcion'} for e in actual],ns['events'])
        carrera = next(e for e in actual if e['competicion']=='F1 Academy')
        self.assertIn('G.P. Estados Unidos',carrera['descripcion'])
        self.assertEqual(len(actual),283)
        new = recomendar_eventos(actual,ahora=datetime(2026,10,25,8,30,tzinfo=MADRID_TZ))
        self.assertEqual(len(new['filtrados']),54)
        final = next(e for e in new['filtrados'] if e['local']=='JL. Struff')
        self.assertEqual(final['categoria_reconocida'],'ATP 250')
        self.assertEqual(new['plan']['imprescindible']['local'],'FC Barcelona')
        inter = next(e for e in new['filtrados'] if e['local']=='Inter Milan')
        self.assertAlmostEqual(inter['score'],6.6)
        estudiantes = next(e for e in new['filtrados'] if e['visitante']=='Movistar Estudiantes')
        self.assertEqual(estudiantes['score'],4.9)

    def test_estructura_invalida_y_fecha_incorrecta(self):
        for html in ('<html>Acceso denegado</html>', '<table class="tablaPrincipal"></table>',
                     '<table class="tablaPrincipal"><tr class="cabeceraTabla"><td>25/10/2026</td></tr></table>'):
            with self.assertRaises(ErrorEventos):
                extraer_eventos(html,date(2026,10,25))
        html = (ROOT/'tests/fixtures/eventos_real_2026-10-25.html').read_text(encoding='utf-8')
        with self.assertRaisesRegex(ErrorEventos,'se esperaba'):
            extraer_eventos(html,date(2026,10,26))

    @patch('resumen.fuente_eventos.requests.get')
    def test_descarga_y_errores_http(self,get):
        get.return_value=Mock(status_code=200,text='<html>Ejemplo</html>')
        self.assertEqual(descargar_html(),'<html>Ejemplo</html>')
        self.assertEqual(get.call_args.kwargs['timeout'],(5,20))
        for code in (403,429):
            get.return_value=Mock(status_code=code)
            with self.assertRaisesRegex(ErrorEventos,str(code)):
                descargar_html()

    @patch('resumen.fuente_eventos.time.sleep')
    @patch('resumen.fuente_eventos.requests.get')
    def test_reintentos_limitados(self,get,sleep):
        get.side_effect=[requests.Timeout(),Mock(status_code=503),Mock(status_code=200,text='OK')]
        self.assertEqual(descargar_html(),'OK')
        self.assertEqual(get.call_count,3)
        get.reset_mock()
        get.side_effect=requests.ConnectionError('detalle interno')
        with self.assertRaisesRegex(ErrorEventos,'tres intentos'):
            descargar_html()
        self.assertEqual(get.call_count,3)

if __name__ == '__main__':
    unittest.main()
