"""Ejecución manual, vista previa y envío explícito por Gmail."""
import argparse
import logging
import random
from datetime import datetime
from pathlib import Path

from .camisetas import cargar_coleccion, seleccionar_camiseta
from .config import ErrorConfiguracion, MADRID_TZ, obtener_config_correo
from .correo import ErrorCorreo, enviar_informe
from .ejecucion import ejecutar
from .eventos import recomendar_eventos
from .informe import generar_informe, guardar_informe
from .seleccion_camisetas import recomendar_camisetas

def demostracion(modo):
    ahora = datetime(2026, 10, 25, 9, tzinfo=MADRID_TZ)
    result = {'fecha': ahora.date().isoformat(), 'modo': modo, 'camiseta': None,
              'eventos': None, 'errores': {}, 'demostracion': True}
    if modo in ('ambos', 'camiseta'):
        matches = [{'home': 'Equipo de ejemplo', 'away': 'Rival de ejemplo',
                    'hora': ahora.replace(hour=18), 'competition': 'Competición ficticia'},
                   {'home':'At. Madrid', 'away':'Real Madrid', 'hora':ahora.replace(hour=21),
                    'competition':'LaLiga EA Sports (ejemplo ficticio)'}]
        shirt, matches = seleccionar_camiseta(cargar_coleccion(), matches, random.Random(42))
        result['camiseta'] = {'fecha': result['fecha'], 'camiseta': shirt, 'partidos': matches}
    if modo in ('ambos', 'eventos'):
        events = [{'hora': hora, 'deporte': 'Fútbol', 'competicion': competition,
                   'local': local, 'visitante': rival, 'canales': ['Movistar+']}
                  for hora, competition, local, rival in [
                      ('13:00', 'Premier League', 'Arsenal', 'Chelsea'),
                      ('18:00', 'LaLiga EA Sports', 'FC Barcelona', 'Valencia'),
                      ('18:30', 'Champions League', 'Liverpool', 'Arsenal')]]
        result['eventos'] = {'fecha': result['fecha'], 'extraidos': len(events), **recomendar_eventos(events, ahora=ahora)}
    if result['camiseta'] is not None:
        result['camiseta'].update(recomendar_camisetas(cargar_coleccion(), result['camiseta']['partidos'],
                                                     [], ahora, random.Random(42)))
    return result

def main():
    parser = argparse.ArgumentParser(description='Resumen deportivo en HTML y texto, con envío opcional por Gmail.')
    parser.add_argument('--modo', choices=['ambos', 'camiseta', 'eventos'], default='ambos')
    parser.add_argument('--sin-conexion', action='store_true', help='Ejemplo ficticio sin API ni credenciales.')
    parser.add_argument('--salida', type=Path, help='Carpeta donde guardar resumen.html y resumen.txt.')
    parser.add_argument('--nba', action='store_true', help='Añade NBA en diferido sin spoilers (solo con conexión).')
    parser.add_argument('--enviar', action='store_true', help='Envía un correo mediante Gmail; sin esta opción no se envía nada.')
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
    if args.enviar:
        try:
            obtener_config_correo()
        except ErrorConfiguracion as error:
            logging.error('%s', error)
            return 1
    result = demostracion(args.modo) if args.sin_conexion else ejecutar(args.modo, incluir_nba=args.nba)
    report = generar_informe(result)
    print(report['texto'])
    if args.salida:
        try:
            guardar_informe(report, args.salida)
        except OSError:
            logging.error('No se pudieron guardar los archivos del resumen; revisa la carpeta de salida.')
            return 1
        logging.info('Vista previa guardada en %s.', args.salida)
    if args.enviar:
        try:
            estado_envio = enviar_informe(report)
        except (ErrorConfiguracion, ErrorCorreo) as error:
            guardar_estado_envio(args.salida, getattr(error, 'diagnostico', {}) or {'estado':'fallido'})
            logging.error('%s', error)
            return 1
        if isinstance(estado_envio, dict):
            guardar_estado_envio(args.salida, estado_envio)
    return 1 if result['errores'] else 0


def guardar_estado_envio(carpeta, estado):
    if carpeta:
        import json
        try:
            (carpeta/'envio.json').write_text(json.dumps(estado, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
        except OSError:
            logging.warning('No se pudo guardar el diagnóstico del envío; el estado de entrega no cambia.')

if __name__ == '__main__':
    raise SystemExit(main())
