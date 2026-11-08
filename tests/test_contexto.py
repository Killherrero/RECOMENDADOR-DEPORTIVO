import copy
import unittest
from datetime import datetime
from unittest.mock import patch

import requests

from resumen.config import MADRID_TZ
from resumen.contexto import valorar_contexto
from resumen.contexto_fuentes import enriquecer_eventos, historial_futbol, descargar_json, ErrorContexto, temporada, tabla_futbol, tabla_euroliga, contextos_copa, contextos_tenis
from resumen.eventos import evaluar_evento, recomendar_eventos
from resumen.__main__ import demostracion
from resumen.informe import generar_informe


def evento():
    return dict(local='Equipo A', visitante='Equipo B', fecha='2026-10-27', hora='20:00',
                deporte='Fútbol', competicion='Serie A Italiana', canales=[])


def equipo(nombre, posicion=8, forma='WLWDL', jugados=8, victorias=4, derrotas=2):
    return dict(nombre=nombre, posicion=posicion, forma=forma, jugados=jugados,
                victorias=victorias, derrotas=derrotas, ultimo_partido='2026-10-24T18:00:00Z',
                fuentes=['https://example.org/tabla'])


def contextual():
    e = evento()
    e['contexto'] = dict(consultado='2026-10-27T10:00:00+01:00', temporada=2026, competicion='ita.1',
                         local=equipo(e['local']), visitante=equipo(e['visitante']))
    return e


class ContextoTests(unittest.TestCase):
    def test_faltan_datos_nota_basica(self):
        e = evento()
        self.assertEqual(valorar_contexto(e)['ajuste'],0)
        self.assertEqual(evaluar_evento(e)['desglose']['contexto'],0)
        self.assertEqual(evaluar_evento(e)['score'],5.2)

    def test_excepcional_no_acumula_posicion_racha_e_invicto(self):
        e = contextual()
        e['contexto']['visitante'] = equipo('Equipo B',2,'WWWWW',8,7,0)
        r = valorar_contexto(e)
        self.assertEqual(r['ajuste'],1.2)
        self.assertEqual(len(r['motivos']),1)

    def test_zona_alta_y_racha_limitados(self):
        e = contextual()
        e['contexto']['local']['posicion'] = 3
        e['contexto']['visitante'].update(posicion=2, forma='WWWLW')
        self.assertEqual(valorar_contexto(e)['ajuste'],1.3)

    def test_racha_de_ambos(self):
        e = contextual()
        for k in ('local','visitante'): e['contexto'][k]['forma']='WWWDL'
        self.assertEqual(valorar_contexto(e)['ajuste'],1)

    def test_muestra_temporada_frescura_e_identidad(self):
        for campo, valor in [('temporada',2025),('consultado','2026-10-24T10:00:00+01:00'),
                             ('consultado','2026-10-27T21:00:00+01:00')]:
            e = contextual();e['contexto'][campo]=valor
            self.assertEqual(valorar_contexto(e)['ajuste'],0)
        e=contextual();e['contexto']['local']=equipo('Otro equipo',1,'WWWWW',8,8,0)
        self.assertEqual(valorar_contexto(e)['ajuste'],0)
        e=contextual();e['contexto']['local']=equipo('Equipo A',1,'WWWWW',4,4,0)
        self.assertEqual(valorar_contexto(e)['ajuste'],0)

    def test_otro_torneo_y_datos_invalidos_no_se_aplican(self):
        e=contextual();e['contexto']['competicion']='esp.1'
        self.assertEqual(valorar_contexto(e)['ajuste'],0)
        e=contextual();e['contexto']['local']['posicion']=True
        self.assertEqual(valorar_contexto(e)['ajuste'],0)
        e=contextual();e['contexto']['local']['forma']='WW?'
        self.assertEqual(valorar_contexto(e)['ajuste'],0)

    def test_horario_acceso_no_modifican_contexto_ni_nota(self):
        e=contextual();e['contexto']['visitante']=equipo('Equipo B',2,'WWWWW',8,7,0)
        a=evaluar_evento(e);b=evaluar_evento({**e,'canales':['DAZN'],'vision_parcial':True})
        self.assertEqual(a['score'],b['score'])
        self.assertNotEqual(a['prioridad'],b['prioridad'])
        self.assertAlmostEqual(a['score'],round(a['desglose']['deportivo']+a['desglose']['afinidad'],1))

    def test_contexto_se_conserva_internamente_sin_desglose_visible(self):
        e=contextual();e['contexto']['visitante']=equipo('Equipo B',2,'WWWWW',8,7,0)
        r=demostracion('eventos');r['eventos']=recomendar_eventos([e],fecha=datetime(2026,10,27).date())
        informe=generar_informe(r)
        from resumen.diagnostico import preparar_diagnostico
        import json
        interno=json.dumps(preparar_diagnostico(r['eventos'],datetime(2026,10,27)))
        self.assertIn('example.org/tabla',interno)
        self.assertIn('2026-10-27',interno)
        for k in ('html','texto','listado_html'):
            self.assertNotIn('Interés deportivo',informe[k])
            self.assertNotIn('Por qué te lo proponemos',informe[k])
            self.assertNotIn('Nota final redondeada',informe[k])
            self.assertNotIn('En Google Calendar, elige',informe[k])

    @patch('resumen.contexto_fuentes.tabla_futbol',side_effect=ErrorContexto('Fallo'))
    def test_fuente_caida_y_evento_iniciado_conservan_base(self,fuente):
        e=evento();e['contexto']={'dato_viejo':True}
        avisos=enriquecer_eventos([e],datetime(2026,10,27,10,tzinfo=MADRID_TZ))
        self.assertNotIn('contexto',e)
        self.assertIn('0/1',avisos[0])
        e=evento()
        enriquecer_eventos([e],datetime(2026,10,27,21,tzinfo=MADRID_TZ))
        self.assertEqual(fuente.call_count,1)

    @patch('resumen.contexto_fuentes.requests.get',side_effect=requests.Timeout())
    def test_timeout_sanitizado(self,get):
        with self.assertRaises(ErrorContexto):descargar_json('https://example.org')

    def test_copa_bonus_solo_si_contraste_confirmado(self):
        e=contextual();e['competicion']='Copa del Rey 1ª Ronda'
        e['contexto'].update(tipo='copa',competicion='esp.copa_del_rey',
                            copa=dict(partido_unico=True,contraste_primera=True,fuentes=['https://example.org/regla']))
        self.assertEqual(valorar_contexto(e)['ajuste'],.6)
        e['contexto']['copa']['contraste_primera']=False
        self.assertEqual(valorar_contexto(e)['ajuste'],0)

    def test_temporada_no_es_anio_natural(self):
        self.assertEqual(temporada(datetime(2027,1,5)),2026)

    def test_historico_excluye_futuro_otro_torneo_y_duplicados(self):
        def partido(id,fecha,liga='ita.1'):
            return dict(id=id,date=fecha,league={'slug':liga},season={'year':2026},competitions=[
                dict(status={'type':{'completed':True}},competitors=[
                    {'id':'1','score':{'value':2}}, {'id':'2','score':{'value':0}}])])
        viejo=partido('a','2026-10-20T18:00Z')
        datos=dict(season={'year':2026},team={'id':'1'},events=[viejo,viejo,
                    partido('b','2026-10-27T12:00Z'),partido('c','2026-10-18T12:00Z','eng.1')])
        hist=historial_futbol(datos,'1','ita.1',2026,datetime(2026,10,27,10,tzinfo=MADRID_TZ))
        self.assertEqual(len(hist),1)
        self.assertEqual(hist[0][1],'W')

    @patch('resumen.contexto_fuentes.descargar_json')
    def test_tabla_futbol_contrasta_historico_y_rechaza_inconsistencia(self,descarga):
        entries=[]
        for i in range(20):
            stats=[{'name':k,'value':v} for k,v in dict(gamesPlayed=5,wins=5,ties=0,losses=0,rank=i+1).items()]
            entries.append({'team':{'id':str(i),'displayName':f'Equipo {i}'},'stats':stats})
        tabla=dict(season={'year':2026},children=[{'standings':{'entries':entries}}])
        hist=dict(season={'year':2026},team={'id':'0'},events=[])
        for i in range(5):
            hist['events'].append(dict(id=str(i),date=f'2026-10-{10+i:02d}T18:00Z',league={'slug':'ita.1'},season={'year':2026},
                competitions=[dict(status={'type':{'completed':True}},competitors=[
                    {'id':'0','score':{'value':2}}, {'id':'1','score':{'value':0}}])]))
        descarga.side_effect=[tabla,hist]
        ahora=datetime(2026,10,27,10,tzinfo=MADRID_TZ)
        r=tabla_futbol('ita.1',['Equipo 0'],ahora)
        self.assertEqual(r['Equipo 0']['forma'],'WWWWW')
        entries[0]['stats'][0]['value']=6
        entries[0]['stats'][1]['value']=6
        descarga.side_effect=[tabla,hist]
        self.assertEqual(tabla_futbol('ita.1',['Equipo 0'],ahora),{})

    @patch('resumen.contexto_fuentes.descargar_json')
    def test_euroliga_rechaza_paginacion_incompleta(self,descarga):
        descarga.return_value={'total':380,'data':[{'id':'parcial'}]}
        with self.assertRaises(ErrorContexto):
            tabla_euroliga(['Barcelona'],datetime(2026,10,27,10,tzinfo=MADRID_TZ))

    @patch('resumen.contexto_fuentes.tabla_futbol')
    def test_una_consulta_por_liga_y_no_reevaluar_pasados(self,tabla):
        tabla.return_value={'Equipo A':equipo('Equipo A'),'Equipo B':equipo('Equipo B')}
        a,b=evento(),evento()
        b['hora']='21:00'
        enriquecer_eventos([a,b],datetime(2026,10,27,10,tzinfo=MADRID_TZ))
        self.assertEqual(tabla.call_count,1)
        self.assertIn('contexto',a)
        self.assertIn('contexto',b)

    @patch('resumen.contexto_fuentes.descargar_json')
    def test_copa_identidad_por_id_y_horario_verificados(self,descarga):
        tabla=dict(season={'year':2026},children=[{'standings':{'entries':[
            {'team':{'id':str(i)}} for i in range(20)]}}])
        p=dict(date='2026-10-27T19:00Z',competitions=[dict(status={'type':{'state':'pre'}},competitors=[
            {'id':'999','homeAway':'home','team':{'displayName':'Equipo A'}},
            {'id':'0','homeAway':'away','team':{'displayName':'Equipo B'}}])])
        descarga.side_effect=[tabla,{'events':[p]}]
        e=evento();e['competicion']='Copa del Rey 1ª Ronda'
        ahora=datetime(2026,10,27,10,tzinfo=MADRID_TZ)
        self.assertEqual(contextos_copa([e],ahora),1)
        self.assertEqual(valorar_contexto(e)['ajuste'],.6)
        e.pop('contexto');p['date']='2026-10-27T20:00Z'
        descarga.side_effect=[tabla,{'events':[p]}]
        self.assertEqual(contextos_copa([e],ahora),0)
        self.assertNotIn('contexto',e)

    def test_fallo_inesperado_del_contexto_no_pierde_la_agenda(self):
        from resumen.fuente_eventos import generar_resultado_eventos
        with patch('resumen.fuente_eventos.descargar_html',return_value='HTML'), \
             patch('resumen.fuente_eventos.extraer_jornada',return_value=([evento()],[])), \
             patch('resumen.fuente_eventos.enriquecer_eventos',side_effect=RuntimeError('detalle interno')):
            r=generar_resultado_eventos(datetime(2026,10,27,10,tzinfo=MADRID_TZ))
        self.assertEqual(len(r['filtrados']),1)
        self.assertEqual(r['filtrados'][0]['score'],5.2)
        self.assertIn('valoraciones básicas',str(r['avisos']))
        self.assertNotIn('detalle interno',str(r))

    def test_tenis_joven_top100_frente_top10_es_afinidad(self):
        e=contextual();e.update(deporte='Tenis',competicion='ATP 500')
        e['contexto'].update(tipo='tenis',competicion='atp',publicado='2026-10-26T07:00Z',fuentes=['https://example.org/atp'])
        e['contexto']['local']=dict(nombre=e['local'],ranking=67,edad=20,pais='ESP')
        e['contexto']['visitante']=dict(nombre=e['visitante'],ranking=2,edad=29,pais='GER')
        c=valorar_contexto(e)
        self.assertEqual(c['ajuste'],0)
        self.assertEqual(c['afinidad'],.6)
        self.assertEqual(evaluar_evento(e)['desglose']['afinidad'],.2)
        e['contexto']['publicado']='2026-10-01T07:00Z'
        self.assertEqual(valorar_contexto(e)['ajuste'],0)
        self.assertNotIn('afinidad',valorar_contexto(e))

    @patch('resumen.contexto_fuentes.descargar_json')
    def test_ranking_atp_publicado_y_alias_exacto(self,descarga):
        ranks=[]
        for i in range(1,68):
            ranks.append(dict(current=i,athlete=dict(id=str(i),displayName=f'Jugador {i}',shortname=f'J. {i}',age=25,citizenshipCountry='USA')))
        ranks[1]['athlete'].update(displayName='Alexander Zverev',shortname='A. Zverev',age=29,citizenshipCountry='GER')
        ranks[66]['athlete'].update(displayName='Martin Landaluce',shortname='M. Landaluce',age=20,citizenshipCountry='ESP')
        tabla=dict(type='atp',update='2026-10-26T07:00Z',ranks=ranks)
        descarga.return_value={'rankings':[tabla]}
        e=evento();e.update(local='A. Zverev',visitante='M. Landaluce',deporte='Tenis',competicion='ATP 500')
        ahora=datetime(2026,10,27,10,tzinfo=MADRID_TZ)
        self.assertEqual(contextos_tenis([e],ahora),1)
        self.assertEqual(valorar_contexto(e)['afinidad'],.6)
        e.pop('contexto');tabla['update']='2026-10-28T07:00Z'
        self.assertEqual(contextos_tenis([e],ahora),0)
        self.assertNotIn('contexto',e)
