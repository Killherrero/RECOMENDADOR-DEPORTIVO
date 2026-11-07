"""Favoritos declarados: identidad exacta y deporte, nunca subcadenas."""
from .perfiles import normalizar


def favorito_declarado(evento):
    equipos = {normalizar(evento.get(k,'')) for k in ('local','visitante')}
    if evento.get('deporte') == 'Fútbol':
        grupos = {
            'Atlético de Madrid':{'atletico madrid','atletico de madrid','at madrid','club atletico de madrid'},
            'Aston Villa':{'aston villa','aston villa fc'},
            'Roma':{'roma','as roma','as roma fc'},
            'Borussia Dortmund':{'borussia dortmund','dortmund','bvb dortmund','bvb'},
            'España':{'espana','spain','seleccion espanola'},
        }
    elif evento.get('deporte') == 'Baloncesto':
        grupos = {'Estudiantes':{'estudiantes','movistar estudiantes','estudiantes baloncesto'},
                  'Celtics':{'celtics','boston celtics'}}
    else:
        return None
    return next((nombre for nombre,alias in grupos.items() if equipos & alias),None)
