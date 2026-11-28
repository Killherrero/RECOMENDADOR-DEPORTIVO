import copy,json,unittest,tempfile
from datetime import date,datetime
from pathlib import Path
from unittest.mock import patch,Mock
from resumen.camisetas import interpretar_partidos,obtener_partidos_hoy,generar_resultado,ErrorCamisetas
from resumen.config import MADRID_TZ,ROOT
from resumen.eventos import evaluar_evento,recomendar_eventos
from resumen.estado_eventos import estado_evento,programable
from resumen.calendario import enlace_calendario
from resumen.horarios import duracion_evento
from resumen.informe import generar_informe,guardar_informe
from resumen.ejecucion import ejecutar

DIA=date(2026,11,28)
AHORA=datetime(2026,11,28,10,tzinfo=MADRID_TZ)
def partido(comp='LaLiga EA Sports',local='Equipo A',visitante='Equipo B',sport='Fútbol',hora='18:30'):
    return dict(fecha=DIA.isoformat(),hora=hora,local=local,visitante=visitante,deporte=sport,competicion=comp,canales=[])
def api():
    return dict(id=123,utcDate='2026-11-28T17:30:00Z',homeTeam=dict(name='Elche'),awayTeam=dict(name='Atletico Madrid'),competition=dict(name='LaLiga'))
def davis(n=1):
    return partido('Davis Cup Finals Semifinal 2 Partido '+str(n)+(' (Dobles)' if n==3 else ''),'Gran Bretaña','España','Tenis',str(10+2*n)+':00')

class Mejoras28Tests(unittest.TestCase):
    def test_partidos_validos_sobreviven_y_diagnostico_no_filtra_texto_arbitrario(self):
        mala=api();mala['awayTeam']['name']=None;mala['id']='credencial-secreta'
        r=interpretar_partidos({'matches':[mala,api()]},DIA)
        self.assertEqual(len(r),1)
        self.assertEqual(r.descartados,[dict(indice=0,campo='awayTeam.name',motivo='dato_incompleto_o_invalido')])
        self.assertNotIn('credencial-secreta',str(r.descartados))

    def test_identifica_id_y_fecha_invalida_sin_registro_crudo(self):
        mala=api();mala['utcDate']='secreto'
        r=interpretar_partidos({'matches':[mala,api()]},DIA)
        self.assertEqual(r.descartados[0]['partido_id'],123)
        self.assertEqual(r.descartados[0]['campo'],'utcDate')
        self.assertNotIn('secreto',str(r.descartados))
        with self.assertRaises(ErrorCamisetas):interpretar_partidos({'matches':[mala]},DIA)
        self.assertEqual(interpretar_partidos({'matches':[]},DIA),[])

    @patch('resumen.camisetas.requests.get')
    def test_cobertura_parcial_no_es_fallo_total_y_queda_archivada(self,get):
        get.return_value=Mock(status_code=200)
        get.return_value.json.return_value={'matches':[{},api()]}
        with patch('resumen.ejecucion.obtener_api_key',return_value='clave-no-imprimir'):
            r=ejecutar('camiseta',AHORA)
        self.assertEqual(r['errores'],{})
        self.assertEqual(len(r['camiseta']['partidos']),1)
        informe=generar_informe(r)
        self.assertIn('Cobertura parcial de camisetas',informe['texto'])
        self.assertNotIn('CON ERRORES',informe['asunto'])
        with tempfile.TemporaryDirectory() as carpeta:
            guardar_informe(informe,carpeta)
            guardado=json.loads((Path(carpeta)/'diagnostico_camisetas.json').read_text(encoding='utf-8'))
        self.assertEqual(guardado['validos'],1)
        self.assertEqual(len(guardado['descartados']),1)

    def test_davis_recupera_dos_individuales_y_muestra_dobles_condicional(self):
        es=[davis(n) for n in (1,2,3)]
        r=recomendar_eventos(es,fecha=DIA)
        self.assertEqual(len(r['filtrados']),3)
        self.assertTrue(all(e['categoria_reconocida']=='Copa Davis' for e in r['filtrados']))
        dobles=r['filtrados'][-1]
        self.assertEqual(estado_evento(dobles),'condicional')
        self.assertFalse(programable(dobles))
        self.assertFalse(enlace_calendario(dobles))
        self.assertNotIn(dobles,r['seleccionados'])
        self.assertNotIn(dobles,r['alternativas'])
        html=generar_informe(dict(fecha=DIA.isoformat(),errores={},camiseta=None,eventos=r))['html']
        self.assertIn('Si es necesario',html)

    def test_cancelacion_prevalece_sobre_dobles_y_confirmacion_permite_calendario(self):
        e=davis(3)
        self.assertEqual(estado_evento({**e,'estado':'cancelado'}),'cancelado')
        self.assertFalse(recomendar_eventos([{**e,'estado':'cancelado'}],fecha=DIA)['filtrados'])
        self.assertTrue(programable({**e,'confirmado':True}))
        self.assertTrue(programable({**e,'estado':'en curso'}))

    def test_davis_no_hereda_ranking_atp_y_fase_espanola_es_diferenciada(self):
        e=davis();r=evaluar_evento(e)
        self.assertEqual(r['score'],8.4)
        self.assertEqual(r['desglose']['cartel'],0)
        self.assertGreater(r['score'],evaluar_evento({**e,'visitante':'Italia'})['score'])
        for comp in ['Junior Davis Cup Finals Semifinal','Davis Cup Qualifying Semifinal']:
            self.assertFalse(recomendar_eventos([{**e,'competicion':comp}],fecha=DIA)['filtrados'])

    def test_davis_no_hace_consulta_de_ranking_individual(self):
        from resumen.contexto_fuentes import enriquecer_eventos
        e=davis()
        with patch('resumen.contexto_fuentes.contextos_tenis') as ranking:
            enriquecer_eventos([e],AHORA)
        ranking.assert_not_called()

    def test_f2_distingue_sesiones_y_no_imita_f1(self):
        for nombre,nota,duracion in [('Carrera 1',4.2,60),('Carrera 2',4.5,90),('Clasificación',3.5,45),('Libres',2.5,45)]:
            e=partido('FIA Fórmula 2',sport='Automovilismo');e['descripcion']='G.P. Catar '+nombre
            self.assertEqual(evaluar_evento(e)['score'],nota)
            self.assertEqual(duracion_evento(e),duracion)
        self.assertEqual(evaluar_evento(partido('FIA Fórmula 3',sport='Automovilismo'))['score'],3.5)

    def test_favorito_principal_exacto_y_sin_trasladarlo_a_otros_deportes(self):
        atleti=partido(local='At. Madrid');villa=partido(local='Aston Villa')
        self.assertEqual(evaluar_evento(atleti)['desglose']['afinidad'],2.5)
        self.assertEqual(evaluar_evento(villa)['desglose']['afinidad'],1.5)
        self.assertNotEqual(evaluar_evento({**atleti,'local':'Atlético Madrid B'})['desglose']['afinidad'],2.5)

    def test_final_continental_supera_techo_sin_premiar_semifinal_ni_juveniles(self):
        final=partido('Copa Libertadores Final','Palmeiras','Estudiantes LP')
        self.assertEqual(evaluar_evento(final)['score'],9.0)
        self.assertLess(evaluar_evento({**final,'competicion':'Copa Libertadores Semifinal'})['score'],9)
        self.assertLess(evaluar_evento({**final,'competicion':'Copa Libertadores Sub-20 Final'})['score'],9)
        self.assertLess(evaluar_evento({**final,'competicion':'AFC Champions League Final'})['score'],9)

    def test_argentina_reconoce_ambos_historicos_y_no_duplica_la_ronda(self):
        e=partido('Primera División Argentina 1/4 de Final','Vélez Sarsfield','Independiente')
        r=evaluar_evento(e)
        self.assertEqual(r['score'],6.9)
        self.assertEqual(r['desglose']['fase'],1.6)
        self.assertLess(evaluar_evento({**e,'visitante':'Independiente Rivadavia'})['score'],r['score'])
        self.assertEqual(r['score'],evaluar_evento({**e,'madrugada':True,'vision_parcial':True})['score'])

    def test_calidad_domestica_usa_datos_matinales_y_solo_completa(self):
        es=json.loads((ROOT/'tests/fixtures/contexto_2026-11-28.json').read_text(encoding='utf-8'))
        stuttgart=next(e for e in es if e['local']=='Stuttgart')
        r=evaluar_evento(stuttgart)
        self.assertEqual(r['score'],6.9)
        self.assertEqual(r['evaluacion_contexto']['estado'],'validado')
        sin=copy.deepcopy(stuttgart);sin.pop('contexto')
        self.assertLess(evaluar_evento(sin)['score'],r['score'])
        malo=copy.deepcopy(stuttgart);malo['contexto']['visitante']['temporada_fuente']=2025
        # Domestic validator uses the envelope season; stale envelope cannot be scored.
        malo['contexto']['temporada']=2025
        self.assertEqual(evaluar_evento(malo)['score'],evaluar_evento(sin)['score'])
        e=next(e for e in es if e['local']=='Elche')
        self.assertEqual(evaluar_evento(e)['score'],8.7)

    def test_rivalidad_hamburgo_bayern_exacta_y_sin_filiales(self):
        from resumen.rivalidades import valorar_rivalidad
        e=partido('Bundesliga','Hamburger SV','FC Bayern')
        self.assertEqual(valorar_rivalidad(e)['ajuste'],.5)
        self.assertEqual(valorar_rivalidad({**e,'local':'Hamburger SV B'})['ajuste'],0)

    def test_dobles_condicional_reproducible_sin_crear_calendario(self):
        from resumen.diagnostico import preparar_diagnostico,reproducir
        r=recomendar_eventos([davis(1),davis(3)],ahora=AHORA,fecha=DIA)
        snapshot=preparar_diagnostico(r,AHORA)
        repetido=reproducir(snapshot)
        self.assertEqual([e['score'] for e in r['filtrados']],[e['score'] for e in repetido['filtrados']])
        self.assertFalse(enlace_calendario(repetido['filtrados'][-1]))
