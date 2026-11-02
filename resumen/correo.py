"""Envío Gmail por SMTP_SSL, con texto y HTML en un único mensaje."""
import logging
import smtplib
import ssl
import re
import time
from email.message import EmailMessage
from email.utils import formatdate, make_msgid

from .config import obtener_config_correo

logger = logging.getLogger(__name__)

class ErrorCorreo(Exception):
    def __init__(self, mensaje, diagnostico=None):
        super().__init__(mensaje)
        self.diagnostico = diagnostico or {}

def crear_mensaje(informe, config):
    mensaje = EmailMessage()
    mensaje['Subject'] = informe['asunto']
    mensaje['From'] = config.remitente
    mensaje['To'] = config.destinatario
    mensaje['Date'] = formatdate(localtime=False)
    mensaje['Message-ID'] = make_msgid()
    mensaje.set_content(informe['texto'], charset='utf-8')
    mensaje.add_alternative(informe['html'], subtype='html', charset='utf-8')
    if informe.get('listado_html'):
        mensaje.add_attachment(informe['listado_html'], subtype='html', charset='utf-8',
                               filename='todos_eventos.html')
    return mensaje

def enviar_informe(informe):
    config = obtener_config_correo()
    mensaje = crear_mensaje(informe, config)
    historial = []
    # Mismo mensaje e ID en cada intento. Reintentar solo antes de DATA o ante rechazo explícito 4xx.
    for intento in range(1, 4):
        fase = 'conexion'
        aceptado = False
        try:
            with smtplib.SMTP_SSL('smtp.gmail.com', 465, timeout=30,
                                  context=ssl.create_default_context()) as smtp:
                fase = 'autenticacion'
                smtp.login(config.usuario, config.password)
                fase = 'entrega'
                rechazados = smtp.send_message(mensaje, from_addr=config.remitente,
                                                to_addrs=[config.destinatario])
                if rechazados:
                    raise smtplib.SMTPRecipientsRefused(rechazados)
                aceptado = True
                fase = 'cierre'
        except (smtplib.SMTPException, OSError) as error:
            # Un fallo al cerrar no invalida el 250 de aceptación anterior.
            if aceptado:
                logger.info('Gmail aceptó el mensaje; el fallo de cierre no requiere repetirlo.')
            else:
                detalle = clasificar_error(error, fase)
                historial.append({'intento':intento, **detalle})
                if detalle['reintentable'] and intento < 3:
                    espera = 5 if intento == 1 else 15
                    logger.warning('Envío temporalmente interrumpido (%s; SMTP %s); reintento seguro %s/3 en %ss.',
                                   fase, detalle['codigos'] or 'sin código', intento+1, espera)
                    time.sleep(espera)
                    continue
                diagnostico = {'estado':detalle['estado'], 'intentos':historial}
                codigo = ', '.join(str(c) for c in detalle['codigos']) or 'sin código'
                ampliado = ', '.join(detalle['codigos_ampliados'])
                mensaje_error = f'Fallo de correo en {fase}: {detalle["tipo"]}; SMTP {codigo}'
                if ampliado:
                    mensaje_error += f' ({ampliado})'
                mensaje_error += f'. Intentos: {intento}. '
                if isinstance(error, smtplib.SMTPAuthenticationError):
                    mensaje_error += 'Gmail rechazó la autenticación; revisa usuario y contraseña de aplicación. '
                elif detalle['estado'] == 'rechazado':
                    mensaje_error += 'Gmail rechazó explícitamente el envío. '
                if detalle['estado'] == 'incierto':
                    mensaje_error += 'La entrega es incierta: no se repite para evitar duplicados. Comprueba la bandeja antes de volver a ejecutar.'
                else:
                    mensaje_error += 'No hay aceptación confirmada del mensaje. Consulta envio.json para el diagnóstico.'
                raise ErrorCorreo(mensaje_error, diagnostico) from None
        logger.info('Gmail ha aceptado el correo para su entrega.')
        return {'estado':'aceptado', 'intentos':historial + [{'intento':intento, 'fase':fase, 'estado':'aceptado'}]}


def clasificar_error(error, fase):
    """Lista cerrada de campos públicos: nunca copiar respuestas, direcciones o claves."""
    respuestas = list(error.recipients.values()) if isinstance(error, smtplib.SMTPRecipientsRefused) else [
        (getattr(error, 'smtp_code', None), getattr(error, 'smtp_error', b''))]
    codigos = sorted({c for c, _ in respuestas if type(c) is int and 100 <= c <= 599})
    ampliados = set()
    for _, texto in respuestas:
        texto = texto.decode('ascii', errors='ignore') if isinstance(texto, bytes) else str(texto)
        ampliados.update(re.findall(r'(?<![\w.])[245]\.\d{1,3}\.\d{1,3}(?![\w.])', texto))
    explicito = bool(codigos)
    temporal = explicito and len(codigos) == len({c for c, _ in respuestas}) and all(400 <= c < 500 for c in codigos)
    previo = fase in ('conexion', 'autenticacion')
    conexion_temporal = (isinstance(error, smtplib.SMTPServerDisconnected) or
                         isinstance(error, OSError) and not isinstance(error, (smtplib.SMTPException, ssl.SSLError)))
    tipos = [(smtplib.SMTPAuthenticationError,'autenticacion rechazada'),
             (smtplib.SMTPRecipientsRefused,'destinatario rechazado'),
             (smtplib.SMTPSenderRefused,'remitente rechazado'),
             (smtplib.SMTPDataError,'contenido rechazado'),
             (smtplib.SMTPConnectError,'conexion rechazada'),
             (smtplib.SMTPServerDisconnected,'conexion interrumpida'),
             (ssl.SSLError,'error de conexion cifrada'), (OSError,'error de red')]
    tipo = next((nombre for clase,nombre in tipos if isinstance(error,clase)), 'error de protocolo SMTP')
    return {'fase':fase, 'tipo':tipo, 'codigos':codigos, 'codigos_ampliados':sorted(ampliados),
            'estado':'rechazado' if explicito else 'no_enviado' if previo else 'incierto',
            'reintentable':temporal or (previo and not explicito and conexion_temporal)}
