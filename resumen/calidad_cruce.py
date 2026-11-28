"""Calidad conjunta: complemento mínimo, nunca suma de señales equivalentes."""


def valorar_cruce(evento, contexto, cartel, eliminatoria_argentina=None):
    resultado = {'ajuste': 0.0, 'objetivo': 0.0, 'motivos': []}
    if eliminatoria_argentina:
        from .reconocimiento import perfiles_futbol
        perfiles = perfiles_futbol(evento)
        if len({p['lado'] for p in perfiles if p['puntos'] >= .35}) == 2:
            objetivo = 1.8 if all(p['puntos'] >= .65 for p in perfiles) else 1.3
            return dict(ajuste=round(max(0,objetivo-cartel),2), objetivo=objetivo,
                        motivos=['Calidad editorial conjunta en eliminatoria argentina; no implica forma actual'])
    if contexto.get('estado') != 'validado':
        return resultado
    datos = evento['contexto']
    objetivo = 0.0
    motivo = ''
    if evento['deporte'] == 'Fútbol' and datos.get('competicion') in ('esp.1','eng.1','ita.1','ger.1','fra.1'):
        equipos = [datos[k] for k in ('local','visitante')]
        if all(e['jugados'] >= 8 for e in equipos):
            fuerte,debil = sorted(equipos,key=lambda e:e['posicion'])
            if (debil['posicion']-fuerte['posicion'] >= 10 and fuerte['victorias']/fuerte['jugados'] >= .65
                    and debil['victorias']/debil['jugados'] <= .2):
                ajuste=round(min(0,1.2-cartel-contexto['ajuste']),2)
                return dict(ajuste=ajuste,objetivo=1.2,motivos=['Extra moderado por desequilibrio doméstico validado'] if ajuste else [])
            if all(e['posicion'] <= 8 and e['victorias']/e['jugados'] >= .35 for e in equipos):
                objetivo = 1.8 if all(e['posicion'] <= 6 and e['victorias']/e['jugados'] >= .5 for e in equipos) else 1.2
        motivo = 'Calidad conjunta de liga doméstica contrastada; catálogo y forma no se duplican'
    elif datos.get('tipo') == 'europa':
        equipos = [datos[k] for k in ('local', 'visitante')]
        # Solo moderar si hay evidencia de ambos; un rival desconocido no se castiga.
        if contexto.get('moderacion_champions'):
            ajuste = round(min(0, .5 - cartel), 2)
            return {'ajuste':ajuste, 'objetivo':.5,
                    'motivos':['Reconocimiento moderado por contraste europeo validado'] if ajuste else []}
        if all(e['jugados'] >= 3 and e['victorias']/e['jugados'] >= .5 for e in equipos):
            peor = max(e['posicion'] for e in equipos)
            objetivo = 2.2 if peor <= 8 else 1.8 if peor <= 12 else 0
        motivo = 'Calidad conjunta europea: rendimiento contrastado de ambos clubes'
    elif datos.get('tipo') == 'tenis':
        mejor, peor = sorted(datos[k]['ranking'] for k in ('local', 'visitante'))
        # Cuenta el nivel de ambos. Un top-10 frente al 150 no activa el cruce.
        objetivo = (2.8 if peor <= 10 else 2.5 if peor <= 20 else
                    2.2 if mejor <= 10 and peor <= 30 else 1.8 if peor <= 30 else 0)
        motivo = f'Calidad conjunta: ranking ATP {mejor} y {peor}; se valora a ambos jugadores'
    elif evento['deporte'] == 'Baloncesto' and datos.get('competicion') == 'euro':
        posiciones = [datos[k]['posicion'] for k in ('local', 'visitante')]
        objetivo = 2.0 if max(posiciones) <= 5 else 1.2 if max(posiciones) <= 8 else 0
        equipos = [datos[k] for k in ('local', 'visitante')]
        muestra = all(e.get('jugados',0) >= 10 and e.get('victorias',0)/e['jugados'] >= .6 for e in equipos)
        if muestra and max(posiciones) <= 8:
            objetivo = 2.6 if max(posiciones) <= 5 else 2.4
        motivo = 'Calidad conjunta: nivel actual de ambos equipos de Euroliga contrastado'
    elif datos.get('tipo') == 'nba' and contexto.get('forma_nba', {}).get('estado') == 'validado':
        objetivo = contexto['forma_nba']['objetivo_cartel']
        motivo = 'Calidad conjunta NBA: nivel actual de ambos equipos contrastado'
    # Catálogo y contexto ya pueden reconocer el mismo atractivo: solo completar.
    contexto_equivalente = contexto.get('ajuste_forma_nba', contexto['ajuste'])
    ajuste = round(max(0.0, objetivo - cartel - contexto_equivalente), 2)
    return {'ajuste': ajuste, 'objetivo': objetivo,
            'motivos': [motivo] if ajuste else []}
