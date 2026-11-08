import unittest
from datetime import datetime
from urllib.parse import urlparse, parse_qs

from resumen.calendario import enlace_calendario
from resumen.config import MADRID_TZ
from resumen.eventos import recomendar_eventos
from resumen.diseno_correo import tarjeta_evento, listado_completo, boton_calendario


def evento(fecha='2026-10-28', hora='21:00'):
    return dict(local='Atlético de Madrid',visitante='Real Madrid',deporte='Fútbol',
                competicion='La Liga EA Sports',fecha=fecha,hora=hora,canales=['DAZN'])


class CalendarioTests(unittest.TestCase):
    def parametros(self,e,**kwargs):
        url=enlace_calendario(e,**kwargs)
        self.assertEqual(urlparse(url).netloc,'calendar.google.com')
        return {k:v[0] for k,v in parse_qs(urlparse(url).query).items()}

    def test_utc_invierno_y_textos_codificados(self):
        p=self.parametros(evento())
        self.assertEqual(p['dates'],'20261028T200000Z/20261028T220000Z')
        self.assertIn('Atlético de Madrid',p['text'])
        self.assertIn('DAZN',p['details'])
        self.assertIn('Partidazos',p['details'])
        self.assertNotIn('add',p)  # No invita a nadie.
        self.assertEqual(p['ctz'],'Europe/Madrid')

    def test_verano_y_cruce_de_medianoche(self):
        self.assertEqual(self.parametros(evento('2026-07-01','23:30'))['dates'],
                         '20260701T213000Z/20260701T233000Z')

    def test_cambio_horario_conserva_duracion_real(self):
        self.assertEqual(self.parametros(evento('2026-10-25','01:30'))['dates'],
                         '20261024T233000Z/20261025T013000Z')

    def test_sin_fecha_o_intervalo_invalido_no_muestra_boton(self):
        self.assertEqual(enlace_calendario({}), '')
        self.assertEqual(boton_calendario({}), '')
        e=evento();a=datetime(2026,10,28,21,tzinfo=MADRID_TZ)
        self.assertEqual(enlace_calendario(e,inicio=a,fin=a), '')

    def test_tramo_no_equivale_a_partido_completo(self):
        e=evento();a=datetime(2026,10,28,21,tzinfo=MADRID_TZ);b=datetime(2026,10,28,21,45,tzinfo=MADRID_TZ)
        p=self.parametros(e,inicio=a,fin=b,tramo=True)
        self.assertEqual(p['dates'],'20261028T200000Z/20261028T204500Z')
        self.assertIn('no es el partido completo',p['details'])
        self.assertTrue(p['text'].startswith('Ver:'))

    def test_botones_en_tarjetas_lista_y_planning(self):
        r=recomendar_eventos([evento()],ahora=datetime(2026,10,28,10,tzinfo=MADRID_TZ))
        e=r['filtrados'][0]
        self.assertIn('calendar.google.com',tarjeta_evento(e,True))
        self.assertIn('calendar.google.com',listado_completo([e]))
        self.assertIn('calendario_url',r['planning'][0])
        self.assertNotIn('elige <strong>Partidazos',tarjeta_evento(e))
