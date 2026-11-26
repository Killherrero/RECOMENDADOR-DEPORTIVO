import unittest
from datetime import datetime
from unittest.mock import patch
from resumen.config import MADRID_TZ
from resumen.contexto_fuentes import liga_evento, tabla_futbol
from resumen.eventos import evaluar_evento
from resumen.contexto import valorar_contexto


def partido(comp='Europa League Fase Liga', local='Ajax', visitante='Benfica', deporte='Fútbol'):
    e=dict(local=local,visitante=visitante,competicion=comp,deporte=deporte,fecha='2026-11-26',hora='21:00',canales=[])
    return e


def contextual(e, liga='uefa.europa', posiciones=(4,7), wins=(3,3)):
    e['contexto']=dict(tipo='europa',competicion=liga,temporada=2026,consultado='2026-11-26T10:00:00+01:00')
    for lado,pos,w in zip(('local','visitante'),posiciones,wins):
        e['contexto'][lado]=dict(nombre=e[lado],id=lado,posicion=pos,jugados=4,victorias=w,derrotas=4-w,
            forma='WWWL' if w==3 else 'WLLL',puntos=w*3,fase_competicion='league phase',temporada_fuente=2026,
            ultimo_partido='2026-11-05T20:00:00Z',fuentes=['https://example.org/source'])
    return e


class Mejoras26Tests(unittest.TestCase):
    def test_favorita_basket_y_clasificatorio_distinto_del_torneo_y_amistoso(self):
        notas=[]
        for comp in ['Amistoso internacional','FIBA Copa Mundial Fase de Clasificación','FIBA Copa Mundial Fase de grupos']:
            r=evaluar_evento(partido(comp,'Montenegro','España','Baloncesto'))
            self.assertEqual(r['favorito_declarado'],'España')
            notas.append(r['score'])
        self.assertEqual(notas,[4.9,6.6,7.2])
        self.assertIsNone(evaluar_evento(partido('FIBA Mundial','Montenegro','España Sub-18','Baloncesto'))['favorito_declarado'])

    def test_ncaa_solo_alias_exactos_sin_convertir_reconocimiento_en_ranking(self):
        uno=evaluar_evento(partido('NCAA','Oklahoma','Purdue','Baloncesto'))
        dos=evaluar_evento(partido('NCAA','UCLA','Duke','Baloncesto'))
        otro=evaluar_evento(partido('NCAA','Purdue Fort Wayne','Kansas State','Baloncesto'))
        self.assertEqual((uno['score'],dos['score'],otro['score']),(4.9,5.3,4.1))

    def test_fuentes_solo_fase_liga_senior(self):
        for comp,liga in [('Europa League Fase Liga','uefa.europa'),('UEFA Conference League Fase Liga','uefa.europa.conf')]:
            self.assertEqual(liga_evento(partido(comp)),liga)
        for comp in ['Europa League Final','Europa League Sub-19 Fase Liga','Conference League Women Fase Liga','Conference League Previa']:
            self.assertIsNone(liga_evento(partido(comp)))

    def test_dos_equipos_fuertes_completan_sin_sumar_dos_veces(self):
        e=contextual(partido())
        r=evaluar_evento(e)
        self.assertEqual(r['evaluacion_contexto']['estado'],'validado')
        self.assertAlmostEqual(r['desglose']['cartel']+r['desglose']['calidad_cruce']+r['evaluacion_contexto']['ajuste'],2.4)
        # 2.0 de catálogo y .4 de contexto ya superan el objetivo conjunto de 2.2.
        self.assertEqual(r['desglose']['calidad_cruce'],0)
        e=contextual(partido(local='Club A',visitante='Club B'))
        self.assertAlmostEqual(evaluar_evento(e)['desglose']['calidad_cruce'],1.8)

    def test_moderar_solo_desequilibrio_contrastado_no_ausencia_de_datos(self):
        e=partido(local='Ajax',visitante='Club desconocido')
        original=evaluar_evento(e)['score']
        r=evaluar_evento(contextual(e,posiciones=(3,31),wins=(3,1)))
        self.assertLess(r['score'],original)
        self.assertEqual(r['desglose']['calidad_cruce'],-.3)
        e['contexto'].pop('visitante')
        self.assertEqual(evaluar_evento(e)['score'],original)

    def test_conference_no_acepta_mas_de_seis_jornadas_ni_otra_edicion(self):
        for clave,valor in [('jugados',7),('fase_competicion','qualifying'),('temporada_fuente',2025),('puntos',100)]:
            e=contextual(partido('Conference League Fase Liga'),liga='uefa.europa.conf')
            e['contexto']['local'][clave]=valor
            self.assertNotEqual(valorar_contexto(e)['estado'],'validado')
        e=contextual(partido())
        e['contexto']['consultado']='2026-11-26T22:00:00+01:00'
        self.assertNotEqual(valorar_contexto(e)['estado'],'validado')

    def test_tabla_incoherente_no_aplica_contexto(self):
        entradas=[dict(team=dict(id=str(i),displayName='Club '+str(i)),stats=[dict(name=k,value=v) for k,v in dict(gamesPlayed=7,wins=3,ties=0,losses=4,rank=i+1,points=9).items()]) for i in range(36)]
        tabla=dict(season=dict(year=2026),children=[dict(name='League Phase',standings=dict(entries=entradas))])
        with patch('resumen.contexto_fuentes.descargar_json',return_value=tabla) as descarga:
            resultado=tabla_futbol('uefa.europa.conf',['Club 0'],datetime(2026,11,26,10,tzinfo=MADRID_TZ))
        self.assertNotIn('Club 0',resultado)
        self.assertEqual(descarga.call_count,1)

    def test_alias_del_correo_sin_confundir_clubes_distintos(self):
        from resumen.contexto_fuentes import alias_futbol
        for a,b in [('Lillestrøm SK','Lillestrom'),('Crvena Zvezda','Red Star Belgrade'),
                    ('AC Omonia','Omonia Nicosia'),("Inter Club d'Escaldes","Inter D'Escaldes")]:
            self.assertEqual(alias_futbol(a),alias_futbol(b))
        self.assertNotEqual(alias_futbol('FCU Craiova 1948'),alias_futbol('CSU Craiova'))
        self.assertNotEqual(alias_futbol('Celtic FC B'),alias_futbol('Celtic'))

    def test_ampliacion_conserva_tipo_y_diagnostico_integrados(self):
        from resumen.contexto_fuentes import enriquecer_eventos
        for comp,liga in [('Europa League Fase Liga','uefa.europa'),('Conference League Fase Liga','uefa.europa.conf')]:
            e=contextual(partido(comp),liga)
            tabla={e[k]:e['contexto'][k] for k in ('local','visitante')}
            with patch('resumen.contexto_fuentes.tabla_futbol',return_value=tabla):
                enriquecer_eventos([e],datetime(2026,11,26,10,tzinfo=MADRID_TZ))
            self.assertEqual(e['contexto']['tipo'],'europa')
            self.assertEqual(valorar_contexto(e)['estado'],'validado')
            self.assertEqual(e['diagnostico_contexto']['estado'],'validado')

    def test_ninguna_afinidad_general_para_clubes_espanoles(self):
        r=evaluar_evento(partido(local='Celta',visitante='Bournemouth'))
        self.assertIsNone(r['favorito_declarado'])
        self.assertLess(r['desglose']['afinidad'],1.3)
