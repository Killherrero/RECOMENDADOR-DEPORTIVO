import unittest

from resumen.eventos import (knockout_bonus, calculate_score, football_match_quality_bonus,
                            build_daily_plan, recomendar_eventos)
from resumen.informe import generar_informe
from resumen.__main__ import demostracion

def evento(local='Equipo A', visitante='Equipo B', comp='LaLiga EA Sports', hora='18:00', deporte='Fútbol'):
    return {'hora':hora,'local':local,'visitante':visitante,'competicion':comp,
            'deporte':deporte,'canales':['Movistar+']}

class MejorasEventosTests(unittest.TestCase):
    def test_wnba_se_excluye_incluso_final_y_nba_se_conserva(self):
        from datetime import date
        w=evento('Atlanta Dream','Golden State Valkyries',comp='WNBA Final',deporte='Baloncesto')
        n=evento('Boston Celtics','Los Angeles Lakers',comp='NBA Liga Regular',deporte='Baloncesto')
        r=recomendar_eventos([w,n],fecha=date(2026,10,29))
        self.assertEqual([e['competicion'] for e in r['filtrados']],['NBA Liga Regular'])
        self.assertNotIn('Atlanta Dream',str(r['plan']))

    def test_fases_especificas_e_ida_vuelta(self):
        for fase, esperado in [('Final',2.5),('Semifinal',2),('Semi-final',2),
                                ('Cuartos de final',1.5),('Quarter-final',1.5),
                                ('Octavos de final',1),('1/16 de final',0.8),
                                ('Liga regular',0),('Liga dividida',0)]:
            with self.subTest(fase=fase):
                self.assertEqual(knockout_bonus({'competicion':fase}),esperado)
        self.assertEqual(knockout_bonus({'competicion':'Semifinal vuelta'}),2.7)
        self.assertEqual(knockout_bonus({'competicion':'Cuartos de final ida'}),1.8)

    def test_alias_atletico_tienen_mismo_bonus_y_derbi(self):
        scores=[calculate_score(evento(name,'Real Madrid')) for name in
                ['Atlético de Madrid','At. Madrid','Atlético Madrid','atletico madrid']]
        for score in scores:
            self.assertAlmostEqual(score,9.0)

    def test_alias_internacionales(self):
        for names in [('Manchester United','Manchester Utd.','Man Utd'),
                      ('FC Bayern','Bayern München','Bayern Munich'),
                      ('PSG','Paris Saint-Germain')]:
            values=[calculate_score(evento(name)) for name in names]
            self.assertEqual(values,[values[0]]*len(values))

    def test_calidad_cuenta_participantes_y_no_subcadenas(self):
        self.assertEqual(football_match_quality_bonus('Inter Milan','Fiorentina'),1)
        self.assertEqual(football_match_quality_bonus('Manchester United','Manchester City'),3)
        self.assertEqual(football_match_quality_bonus('Internacional','Equipo B'),0)

    def test_estudiantes_un_unico_bonus(self):
        base=calculate_score(evento('Equipo A','Equipo B','Primera FEB',deporte='Baloncesto'))
        est=calculate_score(evento('Estudiantes','Equipo B','Primera FEB',deporte='Baloncesto'))
        self.assertAlmostEqual(est-base,1.3)

    def test_competiciones_no_se_descartan_antes_de_puntuar(self):
        for comp in ['Eurocopa','Copa América','Copa del Mundo','World Cup','Eredivisie','La Liga EA Sports']:
            with self.subTest(comp=comp):
                self.assertEqual(len(recomendar_eventos([evento(comp=comp)])['filtrados']),1)
        self.assertEqual(calculate_score(evento(comp='La Liga EA Sports')),calculate_score(evento(comp='LaLiga EA Sports')))
        self.assertEqual(calculate_score(evento(comp='Eredivisie')),4.5)
        self.assertEqual(calculate_score(evento(comp='Serie A Brasil')),3.5)
        self.assertEqual(calculate_score(evento(comp='LaLiga Hypermotion')),4.5)

    def test_ningun_seleccionado_desaparece_del_plan_ni_del_correo(self):
        events=[{**evento(local=name,hora=hora),'score':score} for name,hora,score in
                [('Partido A','15:00',8),('Partido B','17:00',9),('Top','21:00',10)]]
        plan,selected=build_daily_plan(events)
        self.assertEqual(len(plan),3)
        self.assertEqual({id(e) for e in plan.values()},{id(e) for e in selected})
        result=demostracion('eventos')
        result['eventos']['plan']=plan
        result['eventos']['seleccionados']=selected
        text=generar_informe(result)['texto']
        self.assertIn('Partido A',text)
        self.assertIn('Partido B',text)

    def test_alternativas_mejores_ocho_antes_de_recortar(self):
        events=[evento(local=f'Equipo {i}',comp='Champions League Final',hora=f'{9+i:02d}:00') for i in range(13)]
        events[-1]['local']='Atlético de Madrid'
        # Todos coinciden para forzar que se seleccionen pocos y haya más de ocho alternativas.
        for e in events:
            e['hora']='18:00'
        events[0]['competicion']='FIFA Copa Mundial Final'
        events[0]['local']='Atlético de Madrid'
        result=recomendar_eventos(events)
        alternatives=result['alternativas']
        self.assertEqual(len(alternatives),8)
        self.assertEqual(alternatives[0]['local'],'Atlético de Madrid')
        self.assertEqual([e['prioridad'] for e in alternatives],sorted([e['prioridad'] for e in alternatives],reverse=True))

if __name__ == '__main__':
    unittest.main()
