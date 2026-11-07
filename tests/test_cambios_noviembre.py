import copy,json,unittest
from datetime import date,datetime
from pathlib import Path
from resumen.config import MADRID_TZ
from resumen.estado_eventos import programable,estado_evento
from resumen.eventos import recomendar_eventos,evaluar_evento,build_daily_plan,event_key
from resumen.fuente_eventos import extraer_eventos
from resumen.calendario import enlace_calendario
from resumen.planning import crear_planning
from resumen.horarios import preparar_horario
from resumen.sesiones import final_padel_espana,sesion_motor
from resumen.informe import generar_informe
from resumen.diagnostico import preparar_diagnostico,html_diagnostico,reproducir
from resumen.rivalidades import valorar_rivalidad

DIA=date(2026,11,7)
CORTE=datetime(2026,11,7,8,tzinfo=MADRID_TZ)
def e(a='Equipo A',b='Equipo B',sport='Fútbol',comp='LaLiga EA Sports',**extra):
 return dict(local=a,visitante=b,deporte=sport,competicion=comp,hora='19:00',fecha='2026-11-07',canales=[],**extra)

class CambiosNoviembreTests(unittest.TestCase):
 def test_aplazado_no_tiene_boton_aunque_se_pase_tramo_explicito(self):
  x={**e('Granada CF','CD Tenerife'), 'canales':['APLAZADO']}
  self.assertFalse(programable(x));self.assertEqual(enlace_calendario(x),'')
  self.assertEqual(enlace_calendario(x,inicio=CORTE,fin=CORTE.replace(hour=9),tramo=True),'')
  r=recomendar_eventos([x],ahora=CORTE)
  self.assertFalse(r['filtrados']);self.assertIn('aplazado',r['excluidos'][0]['motivo'])
 def test_plan_y_planning_defensivos_ante_evento_no_programable(self):
  x={**e(),'estado':'cancelado','score':9,'prioridad':9}
  self.assertEqual(build_daily_plan([x]),({},[]))
  self.assertEqual(crear_planning([x],[x],event_key),[])
 def test_estado_schema_y_canal_desconocido_no_equivalen(self):
  for clave,valor in [('estado','aplazado'),('estado_fuente','https://schema.org/EventPostponed'),('descripcion','Partido SUSPENDIDO'),('canales',['CANCELADO'])]:
   self.assertFalse(programable({**e(),clave:valor}))
  self.assertTrue(programable({**e(),'canales':['Canal por confirmar']}))
  self.assertTrue(programable({**e(),'canales':['TBD']}))
  self.assertTrue(programable({**e(),'descripcion':'Emisión por confirmar'}))
 def test_fuente_real_conserva_aviso_y_recupera_solo_cobertura_elegida(self):
  html=(Path(__file__).parent/'fixtures/cobertura_2026-11-07.html').read_text(encoding='utf-8')
  raw=extraer_eventos(html,DIA)
  granada=next(x for x in raw if x['local']=='Granada CF')
  self.assertEqual(granada['estado'],'aplazado')
  r=recomendar_eventos(raw,ahora=CORTE)
  self.assertEqual(len(r['filtrados']),5)
  self.assertEqual(sum(x['deporte']=='Pádel' for x in r['filtrados']),2)
  self.assertEqual(sum(x['deporte']=='Motociclismo' for x in r['filtrados']),2)
  self.assertTrue(any(x['local']=='Real Zaragoza' for x in r['filtrados']))
 def test_contexto_no_crea_decimas_negativas_sin_datos(self):
  from resumen.preferencias_eventos import FOOTBALL_TEAM_AFFINITY
  for club in ['Espanyol','Deportivo','Valencia','Lecce',*list(FOOTBALL_TEAM_AFFINITY)]:
   r=evaluar_evento(e(club))
   self.assertEqual(r['desglose']['contexto'],0,club)
 def test_favoritos_identidad_exacta_y_deporte(self):
  x=e('GA Cantabria','Movistar Estudiantes','Baloncesto','Primera FEB')
  r=evaluar_evento(x)
  self.assertEqual(r['score'],4.9)
  self.assertEqual(r['desglose']['deportivo'],3.5)
  self.assertEqual(r['desglose']['afinidad'],1.4)
  for nombre in ['Estudiantes LP','Estudiantes de Río Cuarto','Estudiantes B']:
   self.assertIsNone(evaluar_evento(e(nombre))['favorito_declarado'])
  for nombre in ['Roma','Borussia Dortmund','Atlético de Madrid','Aston Villa']:
   self.assertEqual(evaluar_evento(e(nombre))['desglose']['afinidad'],1.5)
  self.assertEqual(evaluar_evento(e('AS Roma'))['score'],evaluar_evento(e('Roma'))['score'])
  self.assertEqual(evaluar_evento(e('BVB'))['score'],evaluar_evento(e('Borussia Dortmund'))['score'])
 def test_equipo_favorito_visible_sin_forzar_plan(self):
  r=recomendar_eventos([e('GA Cantabria','Movistar Estudiantes','Baloncesto','Primera FEB')],ahora=CORTE)
  self.assertFalse(r['plan'])
  informe=generar_informe(dict(fecha=DIA.isoformat(),eventos=r,camiseta=None,nba=None,errores={}))
  self.assertIn('Tus equipos · para seguir',informe['html'])
  self.assertIn('Interés deportivo 3.50',informe['html'])
 def test_reconocimiento_argentino_no_es_premio_global(self):
  comp='Primera División Argentina Torneo Clausura'
  self.assertEqual(evaluar_evento(e('Club sin perfil','Otro','Fútbol',comp))['score'],3.5)
  self.assertGreater(evaluar_evento(e('Boca Juniors','Otro','Fútbol',comp))['score'],3.5)
  self.assertIsNone(evaluar_evento(e('Estudiantes LP','Otro','Fútbol',comp))['favorito_declarado'])
  self.assertEqual(evaluar_evento(e('Racing','Otro','Fútbol',comp))['perfiles_futbol'],[])
  from resumen.diseno_correo import desglose_html
  basket=evaluar_evento(e('Anadolu Efes','Partizan','Baloncesto','Euroliga'))
  self.assertEqual(basket['perfiles_futbol'],[])
  self.assertTrue(desglose_html(basket))
 def test_derbis_y_excepcion_inferior_solo_documentados(self):
  for a,b in [('Osasuna','Athletic Club'),('Parma','Bologna'),('Gimnasia Mendoza','Independiente Rivadavia')]:
   self.assertGreater(valorar_rivalidad(e(a,b))['ajuste'],0)
  comp='Primera Federación Grupo 2'
  for a,b,aceptado in [('Real Zaragoza','Huesca',True),('Real Zaragoza B','Huesca',False),('Club A','Club B',False)]:
   self.assertEqual(bool(recomendar_eventos([e(a,b,'Fútbol',comp)],ahora=CORTE)['filtrados']),aceptado)
  self.assertFalse(recomendar_eventos([e('Real Zaragoza','Huesca','Fútbol','Primera Federación Sub-19')],ahora=CORTE)['filtrados'])
 def test_padel_acotado_sin_cambiar_filtro_femenino_general(self):
  x=e('España','Argentina','Pádel','Campeonato del Mundo Final')
  self.assertTrue(final_padel_espana(x));self.assertAlmostEqual(evaluar_evento(x)['score'],8.8)
  for comp in ['Mundial Semifinal','Mundial 1/2 de Final','Mundial Semifinales','Mundial Cuartos de Final','Premier Padel Final','Mundial Sub-17 Final']:
   self.assertFalse(recomendar_eventos([{**x,'competicion':comp}],ahora=CORTE)['filtrados'])
  self.assertFalse(recomendar_eventos([{**x,'local':'Francia'}],ahora=CORTE)['filtrados'])
  self.assertFalse(recomendar_eventos([e('Athletic Femenino','Real Madrid Femenino','Fútbol','Liga F')],ahora=CORTE)['filtrados'])
  self.assertFalse(recomendar_eventos([e('Celtics','Rival','Baloncesto','WNBA')],ahora=CORTE)['filtrados'])
  iniciado={**x,'hora':'12:00'}
  tarde=CORTE.replace(hour=14)
  self.assertFalse(recomendar_eventos([iniciado],ahora=tarde)['filtrados'])
  self.assertTrue(recomendar_eventos([{**iniciado,'estado':'en curso'}],ahora=tarde)['filtrados'])
 def test_motor_sesion_duracion_y_motogp_sin_libres(self):
  notas=[]
  for sesion,minutos in [('Libres 3',75),('Clasificación',75),('Sprint',45),('Carrera',150)]:
   x={**e('','','Automovilismo','Fórmula 1 Brasil'),'descripcion':sesion}
   r=evaluar_evento(x);notas.append(r['score']);preparar_horario(x,DIA,CORTE)
   self.assertEqual(x['duracion_estimada'],minutos)
  self.assertEqual(notas,sorted(set(notas)))
  for comp,desc,aceptado in [('MotoGP','Sprint',True),('MotoGP','Libres 2',False),('Moto2','Sprint',False),('Moto3','Carrera',False),('MotoGP','Gran Premio',False)]:
   x={**e('','','Motociclismo',comp),'descripcion':desc}
   self.assertEqual(bool(recomendar_eventos([x],ahora=CORTE)['filtrados']),aceptado)
 def test_auditoria_y_reproduccion_guardan_motivo_sin_calendario(self):
  eventos=[e('Boca Juniors','Rival','Fútbol','Primera División Argentina'),{**e('Granada','Tenerife'),'estado':'aplazado'}]
  r=recomendar_eventos(eventos,ahora=CORTE);s=preparar_diagnostico(r,CORTE)
  self.assertIn('aplazado',json.dumps(s['excluidos']))
  self.assertIn('Eventos que no entraron',html_diagnostico(s))
  self.assertEqual([x['score'] for x in reproducir(s)['filtrados']],[x['score'] for x in r['filtrados']])
  self.assertEqual(reproducir(s)['excluidos'],s['excluidos'])
