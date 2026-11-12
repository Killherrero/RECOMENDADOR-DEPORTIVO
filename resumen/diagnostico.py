"""Instantáneas reproducibles de la agenda, sin correo, claves ni resultados NBA."""
import hashlib
import json
from datetime import datetime, date
from pathlib import Path

from .config import ROOT

VERSION_DIAGNOSTICO = 1


class ResultadoContexto(dict):
    def __init__(self):
        super().__init__()
        self.fallos = {}

    def fallo(self, nombre, motivo):
        self.fallos[nombre] = motivo


def marcar(evento, estado, motivo, **detalle):
    evento['diagnostico_contexto'] = dict(estado=estado, motivo=motivo, **detalle)


def version_modelo():
    h = hashlib.sha256()
    for nombre in ('puntuacion.py', 'calidad_cruce.py', 'rivalidades.py', 'calendario.py', 'planning.py', 'contexto.py', 'perfiles.py', 'preferencias_eventos.py',
                   'contexto_fuentes.py', 'fuente_eventos.py', 'eventos.py', 'horarios.py', 'categorias.py', 'canales.py',
                   'estado_eventos.py','sesiones.py','favoritos.py','reconocimiento.py','ligas.py','ncaa.py','selecciones.py'):
        h.update(nombre.encode())
        h.update((ROOT/'resumen'/nombre).read_bytes().replace(b'\r\n', b'\n'))
    for p in sorted((ROOT/'data').glob('*.json')):
        h.update(p.name.encode())
        h.update(p.read_bytes().replace(b'\r\n', b'\n'))
    return h.hexdigest()[:16]


def serializar(valor):
    if isinstance(valor, (datetime, date)):
        return valor.isoformat()
    raise TypeError(type(valor).__name__)


def preparar_diagnostico(eventos, ahora):
    campos = ('hora','fecha','deporte','competicion','local','visitante','descripcion','canales','estado','estado_fuente',
              'contexto','diagnostico_contexto','score','prioridad','desglose','evaluacion_contexto','evaluacion_rivalidad','evaluacion_fase','evaluacion_selecciones',
              'motivos','inicio','fin_estimado','inicio_vision','fin_vision','vision_parcial')
    registros = [{k:e[k] for k in campos if k in e} for e in eventos.get('filtrados', [])]
    for e in registros:
        evaluacion = e.get('evaluacion_contexto', {})
        if evaluacion.get('estado') == 'validado':
            e['diagnostico_contexto'] = {**e.get('diagnostico_contexto', {}), 'estado':'validado', 'motivo':'con_ajuste' if e.get('desglose',{}).get('contexto') else 'validado_sin_ajuste'}
        elif evaluacion.get('estado') == 'parcial':
            e['diagnostico_contexto'] = {**e.get('diagnostico_contexto',{}), 'estado':'parcial', 'motivo':'participante_sin_datos'}
        elif e.get('contexto'):
            e['diagnostico_contexto'] = {**e.get('diagnostico_contexto', {}), 'estado':'sin_datos', 'motivo':evaluacion.get('estado','contexto_no_valido')}
    cubiertos = sum(e.get('evaluacion_contexto',{}).get('estado') == 'validado' for e in registros)
    parciales = sum(e.get('diagnostico_contexto',{}).get('estado') == 'parcial' for e in registros)
    resumen = {'relevantes':len(registros), 'validados':cubiertos, 'parciales':parciales,
               'con_ajuste':sum(bool(e.get('desglose',{}).get('contexto')) for e in registros)}
    por_deporte = {}
    for e in registros:
        d = por_deporte.setdefault(e['deporte'], {'total':0,'validados':0,'motivos':{}})
        d['total'] += 1
        d['validados'] += e.get('evaluacion_contexto',{}).get('estado') == 'validado'
        motivo = e.get('diagnostico_contexto',{}).get('motivo','sin_diagnostico')
        d['motivos'][motivo] = d['motivos'].get(motivo,0)+1
    snapshot = dict(version=VERSION_DIAGNOSTICO, modelo=version_modelo(), corte=ahora.isoformat(), excluidos=eventos.get('excluidos',[]),
                    cobertura=resumen, por_deporte=por_deporte, eventos=registros,
                    plan={k:f"{e['local']} — {e['visitante']}" for k,e in eventos.get('plan',{}).items()})
    return limpiar(json.loads(json.dumps(snapshot, default=serializar, ensure_ascii=False)))


def limpiar(valor):
    if isinstance(valor,dict):
        return {k:limpiar(v) for k,v in valor.items()
                if not any(s in k.casefold() for s in ('password','token','secret','api_key','smtp','email','authorization'))}
    if isinstance(valor,list): return [limpiar(v) for v in valor]
    return valor


def reproducir(snapshot):
    from .eventos import recomendar_eventos
    if snapshot['modelo'] != version_modelo():
        raise ValueError('La instantánea corresponde a otra versión del modelo.')
    entradas = []
    campos = ('hora','fecha','deporte','competicion','local','visitante','descripcion','canales','estado','estado_fuente',
              'contexto','diagnostico_contexto')
    for e in snapshot['eventos']:
        entradas.append({k:e[k] for k in campos if k in e})
    resultado = recomendar_eventos(entradas, ahora=datetime.fromisoformat(snapshot['corte']))
    if snapshot.get('excluidos'):
        resultado['excluidos'] = snapshot['excluidos']
    return resultado


def html_diagnostico(snapshot):
    from html import escape
    def t(x): return escape(str(x), quote=True)
    r=snapshot['cobertura']
    etiquetas={'con_ajuste':'Datos validados, con ajuste','validado_sin_ajuste':'Datos validados, sin bonus','participante_sin_datos':'Solo un participante tiene datos','identidad_no_resuelta':'Nombre no reconocido','identidad_ambigua':'Nombre ambiguo','fuente_no_disponible':'Fuente no disponible','otra_temporada':'Temporada incorrecta','historico_y_tabla_no_coinciden':'Histórico y tabla no coinciden','competicion_no_cubierta':'Competición sin fuente de contexto','evento_iniciado':'El evento ya había empezado','tiempo_agotado':'Se agotó el tiempo de consulta','horario_no_coincide':'Los horarios no coinciden','partido_no_identificado':'Partido no identificado en la fuente','ranking_fuera_de_fecha':'Ranking desactualizado o futuro'}
    etiquetas.update({'liga_austriaca_sin_cobertura':'Liga austriaca identificada; sin fuente de contexto local',
                      'liga_sin_cobertura':'Liga identificada; sin clasificación/forma validada'})
    body=f'<h1>Cobertura del contexto</h1><p>Corte: {t(snapshot["corte"])} · Modelo: {t(snapshot["modelo"])}</p>'
    body+='<div style="display:flex;flex-wrap:wrap;gap:12px">'
    for k in ('relevantes','validados','parciales','con_ajuste'):
        body+=f'<div style="padding:20px;background:#e1f0e8;border-radius:12px"><strong style="font-size:30px">{r[k]}</strong><br>{t(k.replace("_"," "))}</div>'
    body+='</div><p>Validado sin ajuste significa que se consultaron datos, pero ninguna regla añadió puntos. Parcial significa que solo se pudo validar un participante; esta entrega conserva la nota básica.</p><table width="100%" cellspacing="0"><tr><th>Evento</th><th>Estado y motivo</th><th>Nota</th></tr>'
    for e in snapshot['eventos']:
        d=e.get('diagnostico_contexto',{})
        color='#e1f0e8' if d.get('estado')=='validado' else '#fff0d9' if d.get('estado')=='parcial' else '#edf1f6'
        detalle=' · '.join(f'{k}: {v}' for k,v in d.get('participantes',{}).items())
        nombre = f"{e['local']} — {e['visitante']}" if e.get('local') else e.get('descripcion') or e['competicion']
        body+=f'<tr style="background:{color}"><td style="padding:12px;border-bottom:1px solid white">{t(e["hora"])} · {t(nombre)}</td><td style="padding:12px">{t(d.get("estado","sin datos"))}<br><strong>{t(etiquetas.get(d.get("motivo"), d.get("motivo","Sin diagnóstico")))}</strong><br>{t(detalle)}</td><td style="padding:12px">{e["score"]:.1f}</td></tr>'
    body+='</table><h2>Eventos que no entraron en tu agenda</h2>'
    for e in snapshot.get('excluidos',[]):
        nombre = f"{e.get('local','')} — {e.get('visitante','')}" if e.get('local') else e.get('descripcion') or e.get('competicion','')
        body+=f'<p>{t(e.get("hora",""))} · {t(nombre)} · <strong>{t(e.get("motivo",""))}</strong></p>'
    body+='<p>Instantánea de la agenda y datos usados. No incluye correo personal, claves ni marcadores NBA.</p>'
    return '<!doctype html><html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Cobertura deportiva</title></head><body style="margin:0;background:#f2f5f8;font:14px/1.6 Arial;color:#172b43"><main style="max-width:1000px;margin:auto;padding:20px;overflow-wrap:anywhere">'+body+'</main></body></html>'
