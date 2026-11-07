"""Fechas, disponibilidad y tiempos estimados de visionado en Madrid."""
from datetime import datetime, time, timedelta

from .config import MADRID_TZ

DURACIONES = {'Fútbol': 120, 'Baloncesto': 120, 'Tenis': 150,
              'Automovilismo': 180, 'Balonmano': 90}
MINIMO_VISION = 30


def duracion_evento(evento):
    from .sesiones import sesion_motor
    sesion = sesion_motor(evento)
    if sesion:
        return sesion['duracion']
    if evento.get('deporte') == 'Pádel':
        return 300  # Final por selecciones: varias eliminatorias, duración incierta.
    if evento.get('deporte') == 'Baloncesto' and 'nba' in evento.get('competicion','').lower():
        return 150
    return DURACIONES.get(evento.get('deporte'),120)

def preparar_horario(evento, fecha, ahora=None):
    """Devuelve si se pueden ver al menos 30 minutos; añade datos para la agenda.

    Las noches de viernes y sábado se amplían hasta las 01:00 del sábado/domingo.
    Se permite ver el comienzo de un evento largo, con aviso de visionado parcial.
    """
    try:
        h, m = map(int, evento['hora'].split(':'))
        hora = time(h, m)
        dia = datetime.strptime(evento.get('fecha', fecha.isoformat()), '%Y-%m-%d').date()
    except (ValueError, TypeError):
        return False
    inicio = datetime.combine(dia, hora, MADRID_TZ)
    manana = fecha + timedelta(days=1)
    if dia == fecha and hora >= time(6, 30):
        cierre = datetime.combine(manana, time(1 if manana.weekday() in (5, 6) else 0), MADRID_TZ)
    elif dia == manana and dia.weekday() in (5, 6) and hora < time(1):
        cierre = datetime.combine(dia, time(1), MADRID_TZ)
    elif dia == fecha and dia.weekday() in (5, 6) and hora < time(1):
        # Lanzamiento manual de madrugada: los eventos aún disponibles de hoy también cuentan.
        cierre = datetime.combine(dia, time(1), MADRID_TZ)
    else:
        return False
    duracion = duracion_evento(evento)
    fin = datetime.fromtimestamp(inicio.timestamp() + duracion * 60, MADRID_TZ)
    inicio_vision = max(inicio.timestamp(), ahora.timestamp()) if ahora else inicio.timestamp()
    fin_vision = min(fin.timestamp(), cierre.timestamp())
    if fin_vision - inicio_vision < MINIMO_VISION * 60:
        return False
    evento.update(fecha=dia.isoformat(), inicio=inicio, fin_estimado=fin,
                  inicio_vision=datetime.fromtimestamp(inicio_vision, MADRID_TZ),
                  fin_vision=datetime.fromtimestamp(fin_vision, MADRID_TZ),
                  duracion_estimada=duracion, en_curso=inicio_vision > inicio.timestamp(),
                  vision_parcial=fin.timestamp() > cierre.timestamp(),
                  madrugada=hora < time(6, 30))
    return True

def orden_inicio(evento):
    if 'inicio' in evento:
        return evento['inicio'].timestamp()
    hh, mm = map(int, evento['hora'].split(':'))
    return hh * 60 + mm

def intervalo(evento):
    if 'inicio_vision' in evento:
        return evento['inicio_vision'].timestamp() / 60, evento['fin_vision'].timestamp() / 60
    inicio = orden_inicio(evento)
    duracion = duracion_evento(evento)
    return inicio, inicio + duracion
