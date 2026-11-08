import unittest
from datetime import datetime,date
from unittest.mock import patch
from resumen.config import MADRID_TZ
from resumen.contexto_fuentes import liga_evento,enriquecer_eventos
from resumen.puntuacion import base_futbol
from resumen.eventos import recomendar_eventos,evaluar_evento
from resumen.ncaa import universidad_relevante
from resumen.perfiles import identidad_basket
from resumen.sesiones import sesion_motor
from resumen.calendario import enlace_calendario
from resumen.reconocimiento import PERFILES,PERFILES_ACB

DIA=date(2026,11,8)
def evento(local='Equipo A',visitante='Equipo B',deporte='Fútbol',comp='Bundesliga'):
 return dict(local=local,visitante=visitante,deporte=deporte,competicion=comp,hora='19:00',fecha='2026-11-08',canales=[])

class IdentidadesNoviembreTests(unittest.TestCase):
 def test_austria_nunca_consulta_tabla_alemana(self):
  for comp in ['Admiral Bundesliga','Bundesliga Austria','Tipico Bundesliga']:
   e=evento('Sturm Graz','Red Bull Salzburg',comp=comp)
   self.assertIsNone(liga_evento(e))
   self.assertEqual(base_futbol(comp.lower())[0],4.3)
   with patch('resumen.contexto_fuentes.descargar_json') as red:
    enriquecer_eventos([e],datetime(2026,11,8,9,tzinfo=MADRID_TZ));red.assert_not_called()
   self.assertEqual(e['diagnostico_contexto']['motivo'],'liga_austriaca_sin_cobertura')
 def test_alemania_segunda_y_nombres_ambiguos(self):
  for comp in ['Bundesliga','Bundesliga Alemana','Bundesliga Jornada 11']:
   self.assertEqual(liga_evento(evento(comp=comp)),'ger.1')
  for comp in ['2. Bundesliga','Admiral Bundesliga','Swiss Bundesliga']:
   self.assertIsNone(liga_evento(evento(comp=comp)))
  self.assertEqual(base_futbol('2. bundesliga')[0],4.3)
 def test_ncaa_no_admite_universidades_parecidas(self):
  for equipo in ['Arkansas','Arkansas Razorbacks','Kansas State','Kansas State Wildcats','Michigan State','North Carolina State','NC State']:
   self.assertFalse(universidad_relevante(equipo),equipo)
   self.assertFalse(recomendar_eventos([evento('Virginia',equipo,'Baloncesto','NCAA')],fecha=DIA)['filtrados'])
 def test_ncaa_admite_solo_alias_de_los_programas_elegidos(self):
  for equipo in ['Kansas Jayhawks','Duke Blue Devils','North Carolina Tar Heels','Michigan Wolverines','UCLA Bruins']:
   self.assertTrue(universidad_relevante(equipo))
   self.assertTrue(recomendar_eventos([evento(equipo,'Rival','Baloncesto','NCAA')],fecha=DIA)['filtrados'])
  self.assertFalse(recomendar_eventos([evento('Kansas Jayhawks','Rival','Baloncesto','Liga inventada')],fecha=DIA)['filtrados'])
 def test_alias_acb_equivalentes_sin_confundir_cantera(self):
  for a,b in [('Joventut Badalona','Joventut'),('La Laguna Tenerife','Tenerife'),('Unicaja Málaga','Unicaja'),('UCAM Murcia CB','UCAM Murcia')]:
   self.assertEqual(identidad_basket(a),identidad_basket(b))
   x=evento(a,'Real Madrid','Baloncesto','Liga Endesa')
   self.assertEqual(evaluar_evento(x)['score'],evaluar_evento({**x,'local':b})['score'])
  self.assertNotEqual(identidad_basket('Joventut Badalona B'),'joventut')
 def test_acb_graduada_y_sin_traslado_a_euroliga(self):
  x=evento('La Laguna Tenerife','Joventut Badalona','Baloncesto','Liga Endesa')
  self.assertEqual(evaluar_evento(x)['score'],6.1)
  medio=evaluar_evento(evento('Real Madrid','UCAM Murcia CB','Baloncesto','Liga Endesa'))
  self.assertAlmostEqual(medio['desglose']['cartel'],1.15)
  self.assertFalse(evaluar_evento({**x,'competicion':'Euroleague'})['perfiles_acb'])
  self.assertEqual(evaluar_evento(evento('Básquet Coruña','MoraBanc Andorra','Baloncesto','Liga Endesa'))['score'],4.6)
 def test_dos_referentes_nuevos_sin_doble_pago_de_perfiles(self):
  r=evaluar_evento(evento('Club Brugge','Anderlecht',comp='Jupiler Pro League'))
  self.assertEqual(r['desglose']['cartel'],2)
  self.assertEqual(r['desglose']['rivalidad'],.6)
  self.assertEqual(r['score'],6.8)
  control=evaluar_evento(evento('Sint-Truiden','Zulte Waregem',comp='Jupiler Pro League'))
  self.assertEqual(control['score'],4.2)
 def test_paises_bajos_no_premia_a_cualquier_rival_por_igual(self):
  a=evaluar_evento(evento('Twente','Ajax',comp='Eredivisie'))['desglose']['cartel']
  b=evaluar_evento(evento('Equipo A','Ajax',comp='Eredivisie'))['desglose']['cartel']
  self.assertGreater(a,b)
  self.assertEqual(evaluar_evento(evento('Ajax B','Equipo B',comp='Eredivisie'))['perfiles_futbol'],[])
 def test_catalogos_sin_alias_repetidos_y_documentados(self):
  alias=[a for p in PERFILES for a in p['alias']]
  self.assertEqual(len(alias),len(set(alias)))
  for p in PERFILES+PERFILES_ACB:
   self.assertTrue(p['fuente'].startswith('https://'))
   self.assertLessEqual(p['puntos'],.8)
 def test_nascar_carrera_no_equivale_a_final_por_el_nombre(self):
  x={**evento('','','Automovilismo','NASCAR Cup Series'),'descripcion':'Championship Race Carrera'}
  s=sesion_motor(x);r=evaluar_evento(x)
  self.assertEqual(s['categoria'],'NASCAR Cup');self.assertEqual(s['duracion'],180)
  self.assertEqual(r['score'],5.2);self.assertEqual(r['desglose']['fase'],0)
  self.assertEqual(r['score'],evaluar_evento({**x,'descripcion':'Race Carrera'})['score'])
  self.assertIsNone(sesion_motor({**x,'competicion':'eNASCAR Cup Series'}))
  self.assertIn('20261108T210000Z',enlace_calendario(x))
 def test_ligas_sin_contexto_lo_explican_sin_consultas_erroneas(self):
  for comp in ['Eredivisie','Jupiler Pro League','Liga portuguesa']:
   x=evento(comp=comp)
   with patch('resumen.contexto_fuentes.descargar_json') as red:
    enriquecer_eventos([x],datetime(2026,11,8,9,tzinfo=MADRID_TZ));red.assert_not_called()
   self.assertEqual(x['diagnostico_contexto']['motivo'],'liga_sin_cobertura')
