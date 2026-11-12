import copy
import json
from datetime import datetime, timedelta
from pathlib import Path
import unittest
from unittest.mock import patch, Mock
import requests

from resumen.contexto_internacional import escenarios_grupo, rango_por_puntos, validar_grupo
from resumen.contexto_fuentes import enriquecer_eventos, ErrorContexto
from resumen.diagnostico import preparar_diagnostico, reproducir
from resumen.eventos import evaluar_evento, recomendar_eventos
from resumen.fuentes_selecciones import leer_elo
from resumen.selecciones import CATALOGO

FIXTURES = Path(__file__).parent / 'fixtures'
DATOS = json.loads((FIXTURES / 'internacional_2026-11-12.json').read_text(encoding='utf-8'))
CORTE = datetime.fromisoformat(DATOS['consultado'])


def partido(local='República Checa', visita='España'):
    return dict(local=local, visitante=visita, deporte='Fútbol',
                competicion='UEFA Nations League Fase de grupos', fecha='2026-11-12',
                hora='20:45', canales=[])


def elo():
    return leer_elo((FIXTURES / 'elo_2026-11-12.tsv').read_text(encoding='utf-8'),
                    (FIXTURES / 'elo_nombres.tsv').read_text(encoding='utf-8'),
                    datetime.fromisoformat(DATOS['elo_publicado']), CORTE)


class ContextoInternacionalTests(unittest.TestCase):
    def test_consulta_compartida_en_la_entrada_normal(self):
        tablas = dict(season=dict(year=2026), children=[])
        calendario = dict(events=[])
        for nombre, grupo in DATOS['grupos'].items():
            entradas = [dict(team=dict(displayName=equipo),
                             stats=[dict(name='points', value=registro['puntos']),
                                    dict(name='gamesPlayed', value=registro['jugados'])])
                        for equipo, registro in grupo['tabla'].items()]
            tablas['children'].append(dict(name='Group ' + nombre, standings=dict(entries=entradas)))
            for encuentro in grupo['partidos']:
                competidores = [dict(homeAway=lado, team=dict(displayName=encuentro[campo]),
                                     score=str(encuentro['goles'][indice]) if encuentro['goles'] else '0')
                                for indice, (lado, campo) in enumerate((('home','local'), ('away','visitante')))]
                calendario['events'].append(dict(id=encuentro['id'], date=encuentro['inicio'], season=dict(year=2026),
                    competitions=[dict(competitors=competidores,
                                       status=dict(type=dict(state=encuentro['estado'], completed=encuentro['estado']=='post')))]))
        respuesta_elo = Mock()
        respuesta_elo.text = (FIXTURES / 'elo_2026-11-12.tsv').read_text(encoding='utf-8')
        respuesta_elo.headers = {'Last-Modified':'Thu, 12 Nov 2026 09:50:56 GMT'}
        respuesta_nombres = Mock()
        respuesta_nombres.text = (FIXTURES / 'elo_nombres.tsv').read_text(encoding='utf-8')
        eventos = [partido(), partido('Italia', 'Francia')]
        with patch('resumen.fuentes_selecciones.requests.get', side_effect=[respuesta_elo, respuesta_nombres]) as texto:
            with patch('resumen.contexto_fuentes.descargar_json', side_effect=[tablas, calendario]) as fuente:
                enriquecer_eventos(eventos, CORTE)
        self.assertEqual(texto.call_count, 2)
        self.assertEqual(fuente.call_count, 2)
        self.assertTrue(all('elo' in evento['contexto_selecciones'] for evento in eventos))
        self.assertEqual(evaluar_evento(eventos[1])['desglose']['grupo_selecciones'], .4)

    def test_elo_cubre_selecciones_fuera_de_fifa(self):
        datos = elo()
        self.assertEqual(datos['equipos']['espana']['rating'], 2287)
        self.assertIn('guadalupe', datos['equipos'])
        self.assertIn('martinica', datos['equipos'])

    def test_elo_futuro_antiguo_truncado_y_duplicado_se_rechaza(self):
        texto = (FIXTURES / 'elo_2026-11-12.tsv').read_text(encoding='utf-8')
        nombres = (FIXTURES / 'elo_nombres.tsv').read_text(encoding='utf-8')
        for publicado, contenido in [(CORTE + timedelta(hours=1), texto),
                                      (CORTE - timedelta(days=61), texto),
                                      (CORTE, texto.splitlines()[0]),
                                      (CORTE, texto + texto.splitlines()[0])]:
            with self.assertRaises(ValueError):
                leer_elo(contenido, nombres, publicado, CORTE)

    def test_grupo_reconstruye_puntos_y_detecta_datos_incompletos(self):
        datos = DATOS['grupos']['A3']
        tabla, pendientes = validar_grupo(datos, CATALOGO['grupos']['A3'], CORTE)
        self.assertEqual(tabla['espana'], dict(puntos=12, jugados=4))
        self.assertEqual(len(pendientes), 4)
        for cambio in ['duplicado', 'tabla', 'vivo', 'incompleto']:
            otro = copy.deepcopy(datos)
            if cambio == 'duplicado':
                otro['partidos'].append(otro['partidos'][0])
            elif cambio == 'tabla':
                otro['tabla']['espana']['puntos'] += 1
            elif cambio == 'vivo':
                otro['partidos'][-1]['estado'] = 'in'
            else:
                otro['partidos'].pop()
            with self.assertRaises(ValueError):
                validar_grupo(otro, CATALOGO['grupos']['A3'], CORTE)

    def test_espana_clasificada_y_chequia_eliminada_sin_extra_automatico(self):
        resultado = escenarios_grupo(DATOS['grupos']['A3'], CATALOGO['grupos']['A3'],
                                    ['chequia', 'espana'], CORTE.replace(hour=20, minute=45), CORTE, 'A3')
        self.assertEqual(resultado['equipos']['espana']['clasificacion'], 'asegurado por puntos')
        self.assertEqual(resultado['equipos']['chequia']['clasificacion'], 'inalcanzable por puntos')
        self.assertEqual(resultado['ajuste'], 0)
        self.assertEqual(resultado['escenarios'], 81)

    def test_grupo_abierto_tiene_bonus_acotado_por_resultado(self):
        resultado = escenarios_grupo(DATOS['grupos']['A1'], CATALOGO['grupos']['A1'],
                                    ['italia', 'francia'], CORTE.replace(hour=20, minute=45), CORTE, 'A1')
        self.assertEqual(resultado['ajuste'], .4)
        self.assertIn('desempate', resultado['equipos']['italia']['clasificacion'])

    def test_desempates_directos_y_margen_futuro_abierto(self):
        puntos = dict(a=6, b=6, c=0)
        partidos = [dict(local='a', visitante='b', reparto=(3, 0), goles=[2, 0]),
                    dict(local='b', visitante='a', reparto=(1, 1), goles=[0, 0])]
        self.assertEqual(rango_por_puntos('a', puntos, partidos), (1, 1))
        partidos[1].update(reparto=(3, 0), goles=None)
        self.assertEqual(rango_por_puntos('a', puntos, partidos), (1, 2))
        partidos[1]['goles'] = [1, 0]
        self.assertEqual(rango_por_puntos('a', puntos, partidos), (1, 1))

    def test_rating_sustituye_siembra_y_no_se_suma_dos_veces(self):
        evento = partido()
        evento['contexto_selecciones'] = dict(consultado=CORTE.isoformat(), elo=elo(), grupo=DATOS['grupos']['A3'])
        nota = evaluar_evento(evento)
        self.assertEqual(nota['desglose']['cartel'], 1.2)
        self.assertEqual(nota['desglose']['grupo_selecciones'], 0)
        self.assertEqual(nota['score'], 8.5)
        sin_contexto = evaluar_evento(partido())
        evento['contexto_selecciones']['elo']['publicado'] = (CORTE + timedelta(days=1)).isoformat()
        self.assertEqual(evaluar_evento(evento)['score'], sin_contexto['score'])

    def test_diagnostico_reproduce_rating_y_escenarios(self):
        evento = partido('Italia', 'Francia')
        evento['contexto_selecciones'] = dict(consultado=CORTE.isoformat(), elo=elo(), grupo=DATOS['grupos']['A1'])
        resultado = recomendar_eventos([evento], ahora=CORTE)
        snapshot = preparar_diagnostico(resultado, CORTE)
        reproducido = reproducir(snapshot)
        self.assertEqual(resultado['filtrados'][0]['score'], reproducido['filtrados'][0]['score'])
        self.assertEqual(reproducido['filtrados'][0]['evaluacion_selecciones']['trascendencia']['escenarios'], 81)

    @patch('resumen.fuentes_selecciones.requests.get', side_effect=requests.RequestException('caída'))
    @patch('resumen.contexto_fuentes.descargar_json', side_effect=ErrorContexto('caída'))
    def test_caida_de_fuentes_conserva_nota_y_elimina_contexto_viejo(self, descarga, texto):
        evento = partido()
        evento['contexto_selecciones'] = dict(elo=elo())
        enriquecer_eventos([evento], CORTE)
        self.assertNotIn('elo', evento['contexto_selecciones'])
        self.assertEqual(evaluar_evento(evento)['score'], 8.4)
