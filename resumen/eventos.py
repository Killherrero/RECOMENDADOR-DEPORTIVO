"""Filtrado, valoración personal y agenda, sin consultas al importar."""
from .perfiles import perfil_tenis, normalizar as normalizar_perfil
from copy import deepcopy
from datetime import time
from datetime import datetime
import re
import unicodedata
from .config import MADRID_TZ
from .horarios import intervalo, orden_inicio, preparar_horario
from .categorias import categoria_tenis, bonus_categoria_tenis
from .puntuacion import valorar, UMBRAL_PLAN, UMBRAL_ALTERNATIVAS, umbral_plan
from .estado_eventos import programable, estado_evento
from .sesiones import final_padel_espana, sesion_motor

from .preferencias_eventos import (
    EVENT_DURATION,
    MAX_OVERLAP,
    DAY_START,
    DAY_END,
    TOP_ATP,
    TOP_ATP_20,
    TOP_NCAA,
    TOP_ACB,
    BIG_FOOTBALL_TEAMS,
    NBA_TOP_TEAMS,
    POSITIVE_CHANNELS,
    FREE_CHANNELS,
    NBA_TEAM_AFFINITY,
    FOOTBALL_TEAM_AFFINITY,
    FOOTBALL_DERBIES,
    TENNIS_PLAYER_AFFINITY,
    ALLOWED_FOOTBALL_COMPETITIONS,
    EXCLUDED_FOOTBALL_COMPETITIONS,
    MAX_OTHER_EVENTS
)

def hour_to_min(h):
    hh, mm = map(int, h.split(":"))
    return hh * 60 + mm

def is_female(e):
    text = f"{e['local']} {e['visitante']} {e['competicion']}".lower()
    return any(x in text for x in ["women", "femenino", "femenina", "ellas", "fsf"])

def valid_time(hora):
    try:
        h, m = map(int, hora.split(":"))
        time(h, m)
        return True  # La disponibilidad se evalúa con fecha y final estimado.
    except ValueError:
        # Handle cases where hora is not in 'HH:MM' format, e.g., 'PD'
        return False

def is_lower_division_football(e):
    comp = e["competicion"].lower()
    return any(x in comp for x in ["primera federación", "segunda federación", "tercera", "regional", "academy", "juvenil", "sub-19", "sub 19", "u19"])

def channel_score(canales):
    text = " ".join(canales).lower()
    score = 0
    if any(c in text for c in POSITIVE_CHANNELS):
        score += 2
    if any(c in text for c in FREE_CHANNELS):
        score += 1
    return score

def can_add_event(event, selected):
    start, end = intervalo(event)

    for e in selected:
        s, e_end = intervalo(e)
        overlap = min(end, e_end) - max(start, s)
        if overlap > MAX_OVERLAP:
            return False

    return True

def nba_affinity_score(local, visitante):
    score = 0
    for team, affinity in NBA_TEAM_AFFINITY.items():
        if team in local:
            score += affinity
        if team in visitante:
            score += affinity
    return score

def football_team_affinity(event):
    local = normalize_team_name(event["local"])
    visitante = normalize_team_name(event["visitante"])

    affinities = []

    for team, value in FOOTBALL_TEAM_AFFINITY.items():
        if team_matches(team, local):
            affinities.append(value)
        if team_matches(team, visitante):
            affinities.append(value)

    return max(affinities) if affinities else 0

def football_derby_bonus(event):
    # Compatibilidad con la antigua escala; la nota usa el registro documentado.
    from .rivalidades import valorar_rivalidad
    return valorar_rivalidad({**event, 'deporte': 'Fútbol'})['ajuste'] / .3

def knockout_bonus(event):
    comp = event["competicion"].lower()
    bonus = 0
    from .categorias import segunda_ronda_octavos
    if segunda_ronda_octavos(event):
        return 1.0

    if re.search(r'\bsemi[ -]?final|(?<!\d)1\s*/\s*2\b', comp):
        bonus = 2.0
    elif any(x in comp for x in ["cuartos", "quarter"]) or re.search(r'(?<!\d)1\s*/\s*4\b|\bqf\b', comp):
        bonus = 1.5
    elif any(x in comp for x in ["octavos", "round of 16"]) or re.search(r'(?<!\d)1\s*/\s*8\b', comp):
        bonus = 1.0
    elif 'round of 32' in comp or re.search(r'(?<!\d)1\s*/\s*16\b', comp):
        bonus = 0.8
    elif re.search(r'\bfinal(?:es)?\b', comp):
        bonus = 2.5
    elif 'playoff' in comp:
        bonus = 1.5

    # Ajuste por ida / vuelta
    if re.search(r'\bvuelta\b', comp):
        bonus += 0.7
    elif re.search(r'\bida\b', comp):
        bonus += 0.3

    return bonus

def stakes_bonus(event):
    comp = event["competicion"].lower()
    bonus = 0

    # Título claro
    if any(x in comp for x in [
        "supercopa", "playoff", "titulo", "campeón"
    ]):
        bonus += 2.0

    # Ascenso / descenso
    if any(x in comp for x in [
        "ascenso", "permanencia", "descenso", "playout"
    ]):
        bonus += 1.2

    return bonus

def tennis_affinity_bonus(event):
    nombres = [normalizar_perfil(event[k]) for k in ('local', 'visitante')]
    return max((bonus for player, bonus in TENNIS_PLAYER_AFFINITY.items()
                if any(re.search(r'(?<!\w)' + re.escape(player) + r'(?!\w)', n) for n in nombres)), default=0)


def event_key(e):
    return (
        e.get('fecha'),
        e["hora"],
        e["deporte"],
        e.get("competicion"),
        e.get("local"),
        e.get("visitante")
    )

def football_match_quality_bonus(local, visitante):
    # Cuenta equipos participantes, no cuántas etiquetas coinciden con un nombre.
    big_count = sum(any(team_matches(team, name) for team in BIG_FOOTBALL_TEAMS)
                    for name in (local, visitante))

    if big_count == 2:
        return 3.0 # Doubled from 1.5
    elif big_count == 1:
        return 1.0 # Doubled from 0.5
    return 0

def normalize_team_name(name):
    name = normalize_text(name)
    name = re.sub(r'[^\w\s]', ' ', name)
    name = ' '.join(name.split())
    return TEAM_ALIASES.get(name, name)

def normalize_text(text):
    return ''.join(c for c in unicodedata.normalize('NFD', text.casefold())
                   if unicodedata.category(c) != 'Mn')

TEAM_ALIASES = {
    'dortmund':'borussia dortmund', 'bvb':'borussia dortmund', 'bvb dortmund':'borussia dortmund',
    'as roma':'roma', 'as roma fc':'roma',
    'at madrid': 'atletico madrid', 'atletico de madrid': 'atletico madrid',
    'club atletico de madrid': 'atletico madrid',
    'barca': 'fc barcelona', 'barcelona': 'fc barcelona',
    'manchester utd': 'manchester united', 'man utd': 'manchester united',
    'fc bayern': 'bayern munich', 'fc bayern munchen': 'bayern munich',
    'bayern munchen': 'bayern munich', 'bayern': 'bayern munich',
    'paris saint germain': 'psg', 'paris saint germain fc': 'psg',
    'inter': 'inter milan', 'internazionale': 'inter milan',
    'milan': 'ac milan', 'napoles': 'napoli',
    'o lyonnais': 'lyon', 'olympique lyonnais': 'lyon', 'olympique lyon': 'lyon',
    'o marseille': 'olympique marsella', 'olympique de marseille': 'olympique marsella',
    'newcastle utd': 'newcastle united', 'newcastle united fc': 'newcastle united',
    'sl benfica': 'benfica', 'sport lisboa e benfica': 'benfica',
    'fc porto': 'porto', 'sporting cp': 'sporting lisboa',
    'sevilla': 'sevilla fc',
}

def team_matches(team, name):
    return re.search(r'(?<!\w)' + re.escape(normalize_team_name(team)) + r'(?!\w)',
                     normalize_team_name(name)) is not None

def normalize_competition(name):
    return re.sub(r'\bla\s+liga\b', 'laliga', normalize_text(name))

def select_preferred_channel(canales):
    """
    Devuelve UN solo canal favorito según prioridad:
    Movistar+ > DAZN > resto favoritos.
    Si no hay canal favorito, devuelve None.
    """
    if not canales:
        return None

    canales_norm = [c.lower() for c in canales]

    # 1️⃣ Movistar+
    for c in canales_norm:
        if "movistar" in c:
            return "Movistar+"

    # 2️⃣ DAZN
    for c in canales_norm:
        if "dazn" in c:
            return "DAZN"

    # 3️⃣ Resto favoritos
    for c in canales_norm:
        if any(x in c for x in ["teledeporte", "rtve", "youtube"]):
            # Normalizamos nombre bonito
            if "youtube" in c:
                return "YouTube"
            if "teledeporte" in c:
                return "Teledeporte"
            if "rtve" in c:
                return "RTVE Play"

    return None

def evaluar_evento(e):
    sport = e['deporte']
    local, visitante = normalize_team_name(e['local']), normalize_team_name(e['visitante'])
    afinidad = (football_team_affinity(e) if sport == 'Fútbol' else
                nba_affinity_score(local, visitante) if sport == 'Baloncesto' else
                tennis_affinity_bonus(e) if sport == 'Tenis' else 0)
    # El ajuste por ida/vuelta no equivale a una fase: se calcula sobre el texto de ronda.
    fase_evento = dict(e, competicion=re.sub(r'\b(?:ida|vuelta)\b', '', e['competicion'], flags=re.IGNORECASE))
    return valorar(e, local, visitante, normalize_competition(e['competicion']), afinidad,
                   football_derby_bonus(e) if sport == 'Fútbol' else 0,
                   knockout_bonus(fase_evento))

def calculate_score(e):
    return evaluar_evento(e)['score']

def build_daily_plan(events):
    # --------------------------------------------------
    # 1️⃣ Elegir IMPRESCINDIBLE (por score, no por hora)
    # --------------------------------------------------
    top_events = [
        e for e in events
        if programable(e) and e["score"] >= umbral_plan(e)
    ]

    if not top_events:
        return {}, []

    must_watch = max(top_events, key=lambda e: (e.get('prioridad',e['score']),e['score']))

    # --------------------------------------------------
    # 2️⃣ Construir selección respetando solapes
    # --------------------------------------------------
    selected = [must_watch]

    for e in sorted(top_events, key=lambda e: (-e.get('prioridad',e['score']),-e['score'], orden_inicio(e))):
        if e is must_watch:
            continue

        # Umbral mínimo
        if e["score"] < umbral_plan(e):
            continue

        # Solapamiento real
        if not can_add_event(e, selected):
            continue

        selected.append(e)

        # Límite suave
        if len(selected) == 4:
            break

    # --------------------------------------------------
    # 3️⃣ Orden cronológico para presentación
    # --------------------------------------------------
    selected.sort(key=orden_inicio)

    # --------------------------------------------------
    # 4️⃣ Construir plan visual
    # --------------------------------------------------
    plan = {"imprescindible": must_watch}

    for e in selected:
        if e is must_watch:
            continue

        h = hour_to_min(e["hora"])
        if h < 6 * 60 + 30:
            franja = "madrugada"
        elif h < 12 * 60:
            franja = "mañana"
        elif h < 15 * 60:
            franja = "mediodía"
        elif h < 20 * 60:
            franja = "tarde"
        else:
            franja = "noche"
        indice = 2
        clave = franja
        while clave in plan:
            clave = f'{franja} ({indice})'
            indice += 1
        plan[clave] = e

    return plan, selected

def recomendar_eventos(events, ahora=None, fecha=None, preseleccion_tenis=False):
    # La copia evita añadir score/channel a los datos de entrada del llamante.
    events = deepcopy(events)
    if ahora is not None and ahora.tzinfo is None:
        raise ValueError('La hora de ejecución debe incluir zona horaria.')
    fecha = fecha or (ahora or datetime.now(MADRID_TZ)).astimezone(MADRID_TZ).date()
    filtered_events = []
    excluidos = []
    def descartar(e, motivo):
        excluidos.append({**{k:e.get(k,'') for k in ('hora','fecha','deporte','competicion','local','visitante','descripcion')},
                          'estado':estado_evento(e), 'motivo':motivo})
    for e in events:
        deporte = e["deporte"]
        comp = normalize_competition(e["competicion"])
        local = e["local"].lower()
        visitante = e["visitante"].lower()
        canales = " ".join(e["canales"]).lower()
        local = normalize_team_name(local)
        visitante = normalize_team_name(visitante)
    
    
        # WNBA no es NBA: excluirla antes de cualquier filtro amplio de baloncesto.
        if not programable(e):
            descartar(e, 'Evento ' + estado_evento(e))
            continue
        padel = final_padel_espana(e)
        if 'wnba' in comp or (is_female(e) and not padel) or not valid_time(e["hora"]):
            descartar(e, 'Categoría excluida o sin hora válida')
            continue
        if not preparar_horario(e, fecha, ahora):
            descartar(e, 'Fuera de disponibilidad o ya terminado')
            continue
        if padel:
            if e.get('en_curso') and normalize_text(e.get('estado','')) not in ('en curso','live','in progress'):
                descartar(e, 'Final de pádel ya iniciada, sin directo confirmado')
                continue
            filtered_events.append(e)
            continue
        if deporte == 'Motociclismo':
            sesion = sesion_motor(e)
            if sesion and sesion['categoria'] == 'MotoGP' and sesion['tipo'] in ('clasificacion','sprint','carrera'):
                filtered_events.append(e)
            else:
                descartar(e, 'Solo MotoGP competitivo autorizado')
            continue
    
        if deporte in {"Fútbol Sala", "Waterpolo", "Hockey Patines", "Atletismo", "Rugby U", "Boxeo", "Ishockey", "Béisbol"}:
            descartar(e, 'Deporte no incluido en tus preferencias')
            continue
    
        if deporte == "Automovilismo":
            filtered_events.append(e)
            continue
    
        if deporte == "Fútbol":
            from .rivalidades import valorar_rivalidad
            rivalidad = valorar_rivalidad(e)
            excepcion_derbi = (rivalidad['estado'] == 'verificada' and
                               rivalidad.get('ambito','clubes') == 'clubes' and
                               any(x in comp for x in ('primera federacion','segunda federacion','tercera federacion','regional')))
            if "u23" in comp or (is_lower_division_football(e) and not excepcion_derbi):
                descartar(e, 'Categoría inferior sin derbi documentado')
                continue
            if not excepcion_derbi and not any(normalize_competition(x) in comp for x in ALLOWED_FOOTBALL_COMPETITIONS):
                descartar(e, 'Competición no autorizada')
                continue
            if any(normalize_competition(x) in comp for x in EXCLUDED_FOOTBALL_COMPETITIONS):
                descartar(e, 'Competición excluida')
                continue
            filtered_events.append(e)
            continue
    
        if deporte == "Baloncesto":
            is_relevant_baloncesto = False
            if "nba" in comp:
                is_relevant_baloncesto = True
            if "copa del rey" in comp:
                is_relevant_baloncesto = True
            if "endesa" in comp or "acb" in comp or "euroliga" in comp or "euroleague" in comp:
                is_relevant_baloncesto = True
            from .favoritos import favorito_declarado
            if favorito_declarado(e) == 'Estudiantes':
                is_relevant_baloncesto = True
            if "espana" in local or "espana" in visitante:
                is_relevant_baloncesto = True
            from .ncaa import universidad_relevante
            if 'ncaa' in comp and (universidad_relevante(local) or universidad_relevante(visitante)):
                is_relevant_baloncesto = True
    
            if is_relevant_baloncesto:
                filtered_events.append(e)
            else:
                descartar(e, 'Baloncesto fuera de tus competiciones y equipos')
            continue
    
        if deporte == "Balonmano":
            if local == "espana" or visitante == "espana":
                filtered_events.append(e)
            else:
                descartar(e, 'Balonmano sin España')
            continue
    
        if deporte == "Tenis":
            categoria, _ = categoria_tenis(e)
            from .contexto import valorar_contexto
            jugadores = valorar_contexto(e).get('jugadores', {})
            ranking_relevante = any(p['ranking'] <= 30 for p in jugadores.values())
            if (perfil_tenis(e['local']) or perfil_tenis(e['visitante'])
                or (categoria is not None and (preseleccion_tenis or ranking_relevante))
                or (categoria is not None and knockout_bonus(e) >= 2)):
                filtered_events.append(e)
            else:
                descartar(e, 'Tenis sin categoría o participantes relevantes')
            continue
        descartar(e, 'Deporte o competición no autorizados')
    for e in filtered_events:
        e.update(evaluar_evento(e))
        e['ajuste_horario'] = e['desglose']['horario']
        e['channel'] = select_preferred_channel(e['canales'])
        if e['deporte'] == 'Tenis':
            e['categoria_reconocida'], e['origen_categoria'] = categoria_tenis(e)
            e['avisos_datos'] = [] if e['categoria_reconocida'] else ['Categoría sin identificar; no se resta por falta de datos.']
    filtered_events.sort(key=orden_inicio)
    daily_plan, selected_events = build_daily_plan(filtered_events)
    visible_plan_keys = {event_key(e) for e in daily_plan.values()}
    other_top_events = [e for e in filtered_events
                        if event_key(e) not in visible_plan_keys and e['score'] >= UMBRAL_ALTERNATIVAS]
    other_top_events.sort(key=lambda e: (-e.get('prioridad',e['score']),-e['score'], orden_inicio(e)))
    from .explicaciones import explicar_agenda
    explicar_agenda(filtered_events, daily_plan, event_key)
    from .planning import crear_planning
    flexible = crear_planning(filtered_events, selected_events, event_key)
    return {**({'planning': flexible} if flexible else {}), **({'excluidos':excluidos} if excluidos else {}), 'filtrados': filtered_events, 'plan': daily_plan,
            'seleccionados': selected_events, 'alternativas': sorted(other_top_events[:MAX_OTHER_EVENTS], key=orden_inicio)}
