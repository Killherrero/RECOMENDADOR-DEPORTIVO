import json
import os
import smtplib
import ssl
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, call
from resumen.correo import enviar_informe, ErrorCorreo
from resumen.__main__ import main, demostracion
from resumen.informe import generar_informe
from test_correo import ENV


class RecuperacionCorreoTests(unittest.TestCase):
    def setUp(self):
        self.informe=generar_informe(demostracion('eventos'))

    @patch('resumen.correo.time.sleep')
    @patch('resumen.correo.smtplib.SMTP_SSL')
    def test_rechazo_temporal_reintenta_mismo_mensaje_y_registra_recuperacion(self, clase, dormir):
        smtp=clase.return_value.__enter__.return_value
        smtp.send_message.side_effect=[smtplib.SMTPDataError(451,b'4.7.0 CLAVE_PRIVADA'),{}]
        with patch.dict(os.environ,ENV,clear=True):
            r=enviar_informe(self.informe)
        self.assertEqual(r['estado'],'aceptado')
        self.assertEqual(len(r['intentos']),2)
        self.assertEqual(r['intentos'][0]['codigos'],[451])
        self.assertEqual(r['intentos'][0]['codigos_ampliados'],['4.7.0'])
        self.assertIs(smtp.send_message.call_args_list[0].args[0],smtp.send_message.call_args_list[1].args[0])
        self.assertNotIn('CLAVE_PRIVADA',json.dumps(r))
        dormir.assert_called_once_with(5)

    @patch('resumen.correo.time.sleep')
    @patch('resumen.correo.smtplib.SMTP_SSL')
    def test_corte_durante_entrega_es_incierto_y_no_duplica(self,clase,dormir):
        smtp=clase.return_value.__enter__.return_value
        for error in [smtplib.SMTPServerDisconnected('CLAVE_PRIVADA'),OSError('CLAVE_PRIVADA')]:
            smtp.send_message.reset_mock();smtp.send_message.side_effect=error
            with patch.dict(os.environ,ENV,clear=True),self.assertRaises(ErrorCorreo) as r:
                enviar_informe(self.informe)
            self.assertEqual(r.exception.diagnostico['estado'],'incierto')
            self.assertNotIn('CLAVE_PRIVADA',str(r.exception))
            smtp.send_message.assert_called_once();dormir.assert_not_called()

    @patch('resumen.correo.time.sleep')
    @patch('resumen.correo.smtplib.SMTP_SSL')
    def test_error_permanente_muestra_codigo_pero_no_respuesta(self,clase,dormir):
        smtp=clase.return_value.__enter__.return_value
        smtp.send_message.side_effect=smtplib.SMTPDataError(552,b'5.7.0 CLAVE_PRIVADA remitente@example.com')
        with patch.dict(os.environ,ENV,clear=True),self.assertRaises(ErrorCorreo) as r:
            enviar_informe(self.informe)
        for esperado in ['552','5.7.0','entrega','contenido rechazado']:
            self.assertIn(esperado,str(r.exception))
        for privado in ['CLAVE_PRIVADA','remitente@example.com']:
            self.assertNotIn(privado,str(r.exception));self.assertNotIn(privado,json.dumps(r.exception.diagnostico))
        self.assertEqual(r.exception.diagnostico['estado'],'rechazado')
        dormir.assert_not_called()

    @patch('resumen.correo.time.sleep')
    @patch('resumen.correo.smtplib.SMTP_SSL')
    def test_autenticacion_temporal_se_recupera_sin_duplicar_data(self,clase,dormir):
        smtp=clase.return_value.__enter__.return_value
        smtp.login.side_effect=[smtplib.SMTPAuthenticationError(454,b'4.7.0 TEMPORAL'),None]
        smtp.send_message.return_value={}
        with patch.dict(os.environ,ENV,clear=True):
            self.assertEqual(enviar_informe(self.informe)['estado'],'aceptado')
        smtp.send_message.assert_called_once()
        dormir.assert_called_once_with(5)

    @patch('resumen.correo.time.sleep')
    @patch('resumen.correo.smtplib.SMTP_SSL')
    def test_rechazos_de_destinatario_temporales_limitados(self,clase,dormir):
        smtp=clase.return_value.__enter__.return_value
        smtp.send_message.side_effect=smtplib.SMTPRecipientsRefused({'privado@example.com':(450,b'4.2.0 PRIVADO')})
        with patch.dict(os.environ,ENV,clear=True),self.assertRaises(ErrorCorreo) as r:
            enviar_informe(self.informe)
        self.assertEqual(clase.call_count,3)
        self.assertEqual(dormir.call_args_list,[call(5),call(15)])
        self.assertEqual(len(r.exception.diagnostico['intentos']),3)
        self.assertNotIn('privado@example.com',json.dumps(r.exception.diagnostico))

    @patch('resumen.__main__.enviar_informe')
    def test_cli_guarda_error_y_aceptacion_en_archivo(self,enviar):
        with tempfile.TemporaryDirectory() as d,patch.dict(os.environ,ENV,clear=True),patch('builtins.print'):
            carpeta=Path(d)
            with patch('sys.argv',['resumen','--sin-conexion','--enviar','--salida',d]):
                enviar.side_effect=ErrorCorreo('Fallo de entrega',{'estado':'incierto','intentos':[]})
                self.assertEqual(main(),1)
                self.assertEqual(json.loads((carpeta/'envio.json').read_text(encoding='utf-8'))['estado'],'incierto')
                self.assertTrue((carpeta/'resumen.html').exists())
                enviar.side_effect=None;enviar.return_value={'estado':'aceptado','intentos':[]}
                self.assertEqual(main(),0)
                self.assertEqual(json.loads((carpeta/'envio.json').read_text(encoding='utf-8'))['estado'],'aceptado')

    @patch('resumen.correo.time.sleep')
    @patch('resumen.correo.smtplib.SMTP_SSL')
    def test_certificado_y_password_permanentes_no_se_reintentan(self,clase,dormir):
        clase.side_effect=ssl.SSLCertVerificationError('PRIVADO')
        with patch.dict(os.environ,ENV,clear=True),self.assertRaises(ErrorCorreo):
            enviar_informe(self.informe)
        clase.assert_called_once();dormir.assert_not_called()
        clase.reset_mock();clase.side_effect=None
        smtp=clase.return_value.__enter__.return_value
        smtp.login.side_effect=smtplib.SMTPAuthenticationError(535,b'5.7.8 PRIVADO')
        with patch.dict(os.environ,ENV,clear=True),self.assertRaises(ErrorCorreo) as r:
            enviar_informe(self.informe)
        self.assertEqual(r.exception.diagnostico['estado'],'rechazado')
        self.assertIn('autenticacion',str(r.exception))
        smtp.send_message.assert_not_called();dormir.assert_not_called()
