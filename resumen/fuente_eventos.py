"""Descarga y extracción HTML; la recomendación está en eventos.py."""
import logging
import re
import time
from datetime import datetime, timedelta

import requests
from bs4 import BeautifulSoup

from .config import MADRID_TZ
from .eventos import recomendar_eventos, event_key
from .contexto_fuentes import enriquecer_eventos
from .diagnostico import preparar_diagnostico, marcar

URL = 'https://www.futbolenlatv.es/deporte'
logger = logging.getLogger(__name__)

class ErrorEventos(Exception):
    pass

def descargar_html():
    for intento in range(3):
        try:
            response = requests.get(URL, headers={'User-Agent': 'Mozilla/5.0'}, timeout=(5,20))
        except (requests.Timeout, requests.ConnectionError):
            if intento < 2:
                logger.warning('Descarga de eventos interrumpida; reintento %s/2.', intento + 1)
                time.sleep(2 ** intento)
                continue
            raise ErrorEventos('No se pudo conectar con la web de eventos tras tres intentos.') from None
        except requests.RequestException:
            raise ErrorEventos('Fallo al descargar la web de eventos.') from None
        if 500 <= response.status_code <= 599 and intento < 2:
            logger.warning('Web de eventos HTTP %s; reintento %s/2.', response.status_code, intento + 1)
            time.sleep(2 ** intento)
            continue
        if response.status_code != 200:
            raise ErrorEventos(f'Web de eventos HTTP {response.status_code}.')
        # La web declara UTF-8. Evita la interpretación ISO-8859-1 por defecto de requests.
        response.encoding = 'utf-8'
        return response.text

def extraer_eventos(html, fecha):
    soup = BeautifulSoup(html, 'html.parser')
    table = soup.find('table', class_='tablaPrincipal')
    if table is None:
        raise ErrorEventos('No se encontró tablaPrincipal; puede haber cambiado la web o bloqueado el acceso.')
    header = table.find('tr', class_='cabeceraTabla')
    dates = re.findall(r'\b\d{2}/\d{2}/\d{4}\b', header.get_text(' ', strip=True) if header else '')
    try:
        published = datetime.strptime(dates[0], '%d/%m/%Y').date()
    except (IndexError, ValueError):
        raise ErrorEventos('No se pudo comprobar la fecha de la tabla de eventos.') from None
    if published != fecha:
        raise ErrorEventos(f'La web muestra {published.isoformat()}, pero se esperaba {fecha.isoformat()}.')
    events = []
    for row in table.find_all('tr'):
        if 'cabeceraTabla' in row.get('class', []):
            continue
        hora_td = row.find('td', class_='hora')
        if hora_td is None:
            continue
        detalles_td = row.find('td', class_='detalles')
        local_td = row.find('td', class_='local')
        visitante_td = row.find('td', class_='visitante')
        canales_td = row.find('td', class_='canales')
        img = detalles_td.find('img') if detalles_td else None
        deporte = (img.get('title') or img.get('alt')) if img else None
        events.append({
            'hora': hora_td.get_text(strip=True),
            'deporte': deporte,
            'competicion': detalles_td.get_text(' ', strip=True) if detalles_td else '',
            'local': local_td.get_text(strip=True) if local_td else '',
            'visitante': visitante_td.get_text(strip=True) if visitante_td else '',
            'canales': [li.get_text(strip=True) for li in canales_td.find_all('li')] if canales_td else [],
        })
        descripcion_td = row.find('td', class_='eventoUnaColumna')
        if descripcion_td:
            events[-1]['descripcion'] = descripcion_td.get_text(' ', strip=True)
        from .estado_eventos import estado_evento
        metadato = row.find(attrs={'itemprop':'eventStatus'})
        if metadato:
            events[-1]['estado_fuente'] = metadato.get('content') or metadato.get_text(' ', strip=True)
        estado = estado_evento(events[-1])
        if estado != 'programado':
            events[-1]['estado'] = estado
    if not events or not any(e['deporte'] for e in events):
        raise ErrorEventos('La tabla no contiene eventos reconocibles; no se interpretará como un día sin recomendaciones.')
    logger.info('Extraídos %s eventos para %s de la primera tabla.', len(events), fecha)
    return events

def extraer_jornada(html, fecha):
    events = [{**e, 'fecha': fecha.isoformat()} for e in extraer_eventos(html, fecha)]
    avisos = []
    manana = fecha + timedelta(days=1)
    if manana.weekday() in (5, 6):
        soup = BeautifulSoup(html, 'html.parser')
        tabla_manana = None
        for table in soup.find_all('table', class_='tablaPrincipal'):
            header = table.find('tr', class_='cabeceraTabla')
            dates = re.findall(r'\b\d{2}/\d{2}/\d{4}\b', header.get_text(' ', strip=True) if header else '')
            if dates and dates[0] == manana.strftime('%d/%m/%Y'):
                tabla_manana = table
                break
        if tabla_manana is None:
            avisos.append('La web todavía no publica la tabla de mañana; no se ha podido comprobar la madrugada del fin de semana.')
        else:
            try:
                siguientes = extraer_eventos(str(tabla_manana), manana)
                # El filtrado posterior comprueba la hora y cuánto tiempo se puede ver.
                events.extend({**e, 'fecha': manana.isoformat()} for e in siguientes
                              if e['hora'].split(':')[0] == '00')
            except ErrorEventos:
                avisos.append('No se pudo interpretar la tabla de mañana; la cobertura de madrugada es incompleta.')
    for aviso in avisos:
        logger.warning('%s', aviso)
    return events, avisos

def generar_resultado_eventos(ahora=None):
    ahora = ahora or datetime.now(MADRID_TZ)
    if ahora.tzinfo is None:
        raise ErrorEventos('La fecha de consulta debe incluir zona horaria.')
    fecha = ahora.astimezone(MADRID_TZ).date()
    events, avisos = extraer_jornada(descargar_html(), fecha)
    relevantes = recomendar_eventos(events, ahora=ahora, fecha=fecha, preseleccion_tenis=True)['filtrados']
    hubo_contexto = False
    try:
        avisos_contexto = enriquecer_eventos(relevantes, ahora)
        hubo_contexto = bool(avisos_contexto)
        por_clave = {event_key(e):e for e in relevantes}
        for e in events:
            candidato = por_clave.get(event_key(e), {})
            for campo in ('contexto', 'diagnostico_contexto'):
                if campo in candidato: e[campo] = candidato[campo]
    except Exception:
        # El contexto es opcional: un fallo inesperado tampoco debe perder la agenda.
        for e in events:
            e.pop('contexto', None)
            marcar(e, 'sin_datos', 'fallo_contexto')
        avisos.append('Contexto deportivo no disponible; se conservan las valoraciones básicas.')
    result = recomendar_eventos(events, ahora=ahora, fecha=fecha)
    no_programables = [e for e in result.get('excluidos',[]) if e.get('estado') != 'programado']
    if no_programables:
        avisos.append('Sin programación ni calendario: ' + '; '.join(
            f"{e['local']} — {e['visitante']} ({e['estado']})" for e in no_programables))
    result['diagnostico'] = preparar_diagnostico(result, ahora)
    cobertura = result['diagnostico']['cobertura']
    if hubo_contexto:
        avisos.append(f"Contexto validado en {cobertura['validados']}/{cobertura['relevantes']} eventos relevantes; {cobertura['parciales']} con datos parciales. {cobertura['con_ajuste']} notas ajustadas. Los datos ausentes no restan.")
    logger.info('Eventos filtrados: %s; seleccionados: %s; alternativas: %s.',
                len(result['filtrados']), len(result['seleccionados']), len(result['alternativas']))
    return {'fecha': fecha.isoformat(), 'extraidos': len(events), 'avisos': avisos,
            'eventos_disponibles': events, **result}
