"""Identidad visual: equipos por delante de competición, sin inferir resultados."""
import unicodedata
import re


def normalizar(texto):
    return ' '.join(''.join(c for c in unicodedata.normalize('NFD', texto.casefold())
                           if not unicodedata.combining(c)).split())


def favorito_visual(e):
    """Identidad visual exacta; no altera afinidades ni puntuaciones."""
    equipos = {normalizar(e.get(k, '')) for k in ('local','visitante')}
    deporte = normalizar(e.get('deporte',''))
    catalogo = [
        ('baloncesto', {'estudiantes','movistar estudiantes','estudiantes baloncesto'}, '#103e70', '#176a91', 'Estudiantes', '#ffffff'),
        ('futbol', {'atletico de madrid','atletico madrid','at. madrid','at madrid','club atletico de madrid'}, '#861526', '#b51c2b', 'Atlético de Madrid', '#ffffff'),
        ('futbol', {'aston villa','aston villa fc'}, '#551b38', '#760d35', 'Aston Villa', '#ffffff'),
        ('futbol', {'roma','as roma','as roma fc'}, '#681c2b', '#c69229', 'Roma', '#ffffff'),
        ('futbol', {'borussia dortmund','dortmund','bvb','bvb dortmund'}, '#d4b000', '#161616', 'Borussia Dortmund', '#161616'),
        (deporte, {'espana','seleccion espanola','spain'}, '#a31524', '#b51c2b', 'España', '#ffffff'),
        ('baloncesto', {'celtics','boston celtics'}, '#064c2d', '#007a33', 'Boston Celtics', '#ffffff'),
    ]
    for sport, aliases, fondo, acento, nombre, tinta in catalogo:
        if deporte == sport and equipos & aliases:
            return dict(fondo=fondo, acento=acento, nombre=nombre, tinta=tinta,
                        secundaria='#edeff3' if tinta == '#ffffff' else '#302900', borde='#c4cbd4')
    return None


def tema_evento(e):
    favorito = favorito_visual(e)
    if favorito:
        return favorito['fondo'], favorito['acento'], favorito['nombre']
    equipos = {normalizar(e.get(k, '')) for k in ('local', 'visitante')}
    deporte = normalizar(e.get('deporte', ''))
    comp = normalizar(e.get('competicion', ''))
    if deporte == 'baloncesto' and equipos & {'celtics', 'boston celtics'}:
        return '#e2f3e8', '#007a33', 'Boston Celtics'
    if deporte == 'futbol':
        if equipos & {'atletico de madrid', 'atletico madrid', 'at. madrid', 'at madrid', 'espana', 'seleccion espanola'}:
            return '#ffe5e5', '#b51c2b', 'Atleti / España'
        if 'aston villa' in equipos:
            return '#f4e3ea', '#760d35', 'Aston Villa'
        if 'conference' in comp:
            return '#e7f4df', '#39751c', 'Conference League'
        if 'europa league' in comp or 'liga europa' in comp:
            return '#ffecd9', '#aa4b08', 'Europa League'
        if 'champions' in comp or 'liga de campeones' in comp:
            return '#e4ebff', '#183d96', 'Champions League'
        if 'libertadores' in comp:
            return '#f9e4f2', '#91316e', 'Copa Libertadores'
        if re.search(r'\b(copa|cup|pokal|coupe|coppa|taca)\b', comp):
            return '#f9e4f2', '#91316e', 'Copa'
        return '#e2f1f0', '#286c69', 'Liga / fútbol'
    if deporte == 'tenis':
        return '#f1f7b5', '#566400', 'Tenis'
    if deporte == 'padel':
        return '#e1f2d8', '#47742c', 'Pádel'
    if deporte == 'motociclismo':
        return '#dbe8f3', '#285674', 'MotoGP'
    if deporte == 'automovilismo':
        return '#f5e3d5', '#a05224', 'Motor'
    if deporte == 'baloncesto':
        if 'nba' in comp:
            return '#ffdfc1', '#b45309', 'NBA'
        if 'euroliga' in comp or 'euroleague' in comp:
            return '#d7b9f3', '#502080', 'Euroliga'
        if re.search(r'\b(copa|cup)\b', comp):
            return '#f9e4f2', '#91316e', 'Copa de baloncesto'
        if any(s in comp for s in ('acb', 'endesa')):
            return '#dff0ff', '#176a91', 'ACB'
        return '#fff0df', '#955717', 'Baloncesto'
    return '#edf2f7', '#52647a', e.get('deporte', 'Deporte')
