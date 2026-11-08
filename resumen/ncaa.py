"""Programas universitarios exactos; Kansas no es Arkansas ni Kansas State."""
from .perfiles import normalizar

ALIAS = {
    'kansas':{'kansas','kansas jayhawks','university of kansas'},
    'duke':{'duke','duke blue devils','duke university'},
    'kentucky':{'kentucky','kentucky wildcats','university of kentucky'},
    'north carolina':{'north carolina','north carolina tar heels','unc tar heels'},
    'michigan':{'michigan','michigan wolverines','university of michigan'},
    'purdue':{'purdue','purdue boilermakers','purdue university'},
    'wisconsin':{'wisconsin','wisconsin badgers','university of wisconsin'},
    'ucla':{'ucla','ucla bruins'},
}


def universidad_relevante(nombre):
    from .preferencias_eventos import TOP_NCAA
    return any(normalizar(nombre) in ALIAS.get(c,{c}) for c in TOP_NCAA)
