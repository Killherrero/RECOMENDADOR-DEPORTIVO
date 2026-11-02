import os
import smtplib
import ssl
import tempfile
import unittest
from unittest.mock import patch

from resumen.__main__ import demostracion, main
from resumen.config import ErrorConfiguracion, obtener_config_correo
from resumen.correo import ErrorCorreo, crear_mensaje, enviar_informe
from resumen.informe import generar_informe

ENV = {'SMTP_USERNAME':'remitente@example.com', 'SMTP_PASSWORD':'abcd efgh ijkl mnop',
       'EMAIL_TO':'destino@example.com'}

class CorreoTests(unittest.TestCase):
    def setUp(self):
        self.report = generar_informe(demostracion('ambos'))

    def test_config_obligatoria_y_password_oculta(self):
        with patch.dict(os.environ, ENV, clear=True):
            config = obtener_config_correo()
            self.assertEqual(config.password, 'abcdefghijklmnop')
            self.assertNotIn(config.password, repr(config))
            self.assertEqual(config.remitente, ENV['SMTP_USERNAME'])
        for name in ENV:
            env = dict(ENV)
            env.pop(name)
            with patch.dict(os.environ, env, clear=True):
                with self.assertRaises(ErrorConfiguracion):
                    obtener_config_correo()

    def test_rechaza_cabeceras_y_direcciones_invalidas(self):
        for value in ('a@example.com\nBcc: x@example.com', 'a@example.com,b@example.com', 'sin-arroba', '<a@example.com>'):
            with patch.dict(os.environ, {**ENV,'EMAIL_TO':value}, clear=True):
                with self.assertRaises(ErrorConfiguracion):
                    obtener_config_correo()
        with patch.dict(os.environ, {**ENV,'EMAIL_FROM':'otro@example.com'}, clear=True):
            with self.assertRaises(ErrorConfiguracion):
                obtener_config_correo()

    def test_mensaje_multipart_utf8(self):
        with patch.dict(os.environ, ENV, clear=True):
            message = crear_mensaje(self.report, obtener_config_correo())
        self.assertEqual(message.get_content_type(),'multipart/mixed')
        adjuntos = list(message.iter_attachments())
        self.assertEqual(len(adjuntos),1)
        self.assertEqual(adjuntos[0].get_filename(),'todos_eventos.html')
        self.assertEqual(adjuntos[0].get_content().strip(),self.report['listado_html'].strip())
        self.assertEqual(message.get_body(preferencelist=('plain',)).get_content().strip(), self.report['texto'].strip())
        self.assertEqual(message.get_body(preferencelist=('html',)).get_content().strip(), self.report['html'].strip())
        self.assertEqual(str(message['To']), ENV['EMAIL_TO'])
        self.assertTrue(message['Message-ID'])

    @patch('resumen.correo.smtplib.SMTP_SSL')
    def test_envio_seguro_una_sola_vez(self, smtp_class):
        smtp = smtp_class.return_value.__enter__.return_value
        smtp.send_message.return_value = {}
        with patch.dict(os.environ, ENV, clear=True):
            enviar_informe(self.report)
        args = smtp_class.call_args
        self.assertEqual(args.args,('smtp.gmail.com',465))
        self.assertEqual(args.kwargs['timeout'],30)
        self.assertEqual(args.kwargs['context'].verify_mode, ssl.CERT_REQUIRED)
        self.assertTrue(args.kwargs['context'].check_hostname)
        smtp.login.assert_called_once_with(ENV['SMTP_USERNAME'],'abcdefghijklmnop')
        smtp.send_message.assert_called_once()

    @patch('resumen.correo.time.sleep')
    @patch('resumen.correo.smtplib.SMTP_SSL')
    def test_fallos_sanitizados_y_reintento_previo_seguro(self, smtp_class, sleep):
        for error in (smtplib.SMTPAuthenticationError(535,b'PASSWORD_SECRETA'),
                      smtplib.SMTPDataError(554,b'PASSWORD_SECRETA'), OSError('PASSWORD_SECRETA')):
            smtp_class.reset_mock()
            smtp_class.side_effect=error
            with patch.dict(os.environ, ENV, clear=True):
                with self.assertRaises(ErrorCorreo) as raised:
                    enviar_informe(self.report)
            self.assertNotIn('PASSWORD_SECRETA',str(raised.exception))
            self.assertEqual(smtp_class.call_count,3 if type(error) is OSError else 1)

    @patch('resumen.correo.smtplib.SMTP_SSL')
    def test_destinatario_rechazado_y_quit_tras_aceptacion(self, smtp_class):
        smtp = smtp_class.return_value.__enter__.return_value
        smtp.send_message.return_value = {ENV['EMAIL_TO']:(550,b'No')}
        with patch.dict(os.environ, ENV, clear=True):
            with self.assertRaises(ErrorCorreo):
                enviar_informe(self.report)
            smtp.send_message.return_value = {}
            smtp_class.return_value.__exit__.side_effect=smtplib.SMTPServerDisconnected('QUIT')
            enviar_informe(self.report)  # Ya aceptado: no se declara fallido ni se duplica.

    @patch('resumen.__main__.enviar_informe')
    def test_cli_envio_explicito_y_fallo_de_envio(self, send):
        with patch('sys.argv',['resumen','--sin-conexion']), patch('builtins.print'):
            self.assertEqual(main(),0)
            send.assert_not_called()
        with patch.dict(os.environ, ENV, clear=True), patch('builtins.print'):
            with patch('sys.argv',['resumen','--sin-conexion','--enviar']):
                self.assertEqual(main(),0)
                send.assert_called_once()
                send.side_effect=ErrorCorreo('Error de prueba')
                self.assertEqual(main(),1)

    @patch('resumen.__main__.ejecutar')
    @patch('resumen.__main__.enviar_informe')
    def test_cli_envia_parcial_y_conserva_estado_error(self, send, execute):
        partial=demostracion('eventos')
        partial['errores']={'camiseta':'API HTTP 503'}
        execute.return_value=partial
        with patch.dict(os.environ, ENV, clear=True), patch('builtins.print'), patch('sys.argv',['resumen','--enviar']):
            self.assertEqual(main(),1)
        self.assertIn('[CON ERRORES]',send.call_args.args[0]['asunto'])

if __name__ == '__main__':
    unittest.main()
