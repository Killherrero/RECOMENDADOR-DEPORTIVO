"""Catálogos editoriales de reconocimiento; no representan rankings actuales."""
import re
import unicodedata


def normalizar(nombre):
    nombre = ''.join(c for c in unicodedata.normalize('NFD', nombre.casefold())
                     if not unicodedata.combining(c))
    return ' '.join(re.sub(r'[^a-z0-9 ]', ' ', nombre).split())


CODIGOS_EUROLIGA = {'IST':'efes', 'HTA':'hapoel tel aviv', 'ASV':'asvel',
                     'PAR':'partizan', 'VIR':'virtus', 'ZAL':'zalgiris'}

ALIAS_BASKET = {
    'joventut badalona':'joventut', 'asisa joventut':'joventut', 'club joventut badalona':'joventut',
    'la laguna tenerife':'tenerife', 'lenovo tenerife':'tenerife', 'iberostar tenerife':'tenerife', 'cb canarias':'tenerife',
    'unicaja malaga':'unicaja', 'unicaja baloncesto':'unicaja', 'cb malaga':'unicaja',
    'ucam murcia cb':'ucam murcia', 'ucam murcia club de baloncesto':'ucam murcia',
    'casademont zaragoza':'zaragoza', 'basket zaragoza':'zaragoza',
    'anadolu efes istanbul':'efes', 'anadolu efes':'efes',
    'hapoel tel aviv bc':'hapoel tel aviv', 'hapoel ibi tel aviv':'hapoel tel aviv',
    'asvel lyon villeurbanne':'asvel', 'ldlc asvel villeurbanne':'asvel',
    'bc partizan beograd':'partizan', 'partizan mozzart bet belgrade':'partizan',
    'virtus bologna':'virtus', 'virtus segafredo bologna':'virtus',
    'zalgiris kaunas':'zalgiris',
    'barca basket': 'barcelona', 'barca': 'barcelona', 'fc barcelona': 'barcelona',
    'fc barcelona basket': 'barcelona', 'barcelona basketball': 'barcelona',
    'real madrid baloncesto': 'real madrid', 'real madrid basketball': 'real madrid',
    'valencia basket': 'valencia', 'valencia basket club': 'valencia',
    'fc bayern basketball': 'bayern', 'bayern munich': 'bayern', 'bayern munchen': 'bayern',
    'fenerbahce istanbul': 'fenerbahce', 'fenerbahce beko istanbul': 'fenerbahce',
    'panathinaikos bc': 'panathinaikos', 'panathinaikos aktor athens': 'panathinaikos',
    'armani olimpia milan': 'milano', 'milan': 'milano',
    'ax olimpia milano': 'milano', 'ea7 emporio armani milan': 'milano', 'olimpia milano': 'milano',
    'crvena zvezda mts belgrade': 'estrella roja', 'crvena zvezda': 'estrella roja',
    'crvena zvezda meridianbet belgrade': 'estrella roja',
    'maccabi tel aviv bc': 'maccabi', 'maccabi tel aviv': 'maccabi',
    'olympiacos piraeus': 'olympiacos', 'olympiacos bc': 'olympiacos',
}
REFERENTES_EUROLIGA = {'barcelona', 'real madrid', 'valencia', 'baskonia', 'fenerbahce',
                       'panathinaikos', 'milano', 'estrella roja', 'maccabi', 'bayern', 'olympiacos'}
FIGURAS_TENIS = {'djokovic', 'alcaraz', 'sinner', 'zverev', 'medvedev'}
# Reconocimiento histórico moderado; no equivale a ranking o forma actuales.
RECONOCIDOS_EUROLIGA = {'efes', 'partizan', 'zalgiris', 'virtus'}
RECONOCIDOS_TENIS = {'shapovalov', 'griekspoor', 'struff', 'berrettini'}
REFERENTES_TENIS = FIGURAS_TENIS | {'rublev', 'hurkacz', 'fritz', 'tsitsipas', 'rune',
                                  'ruud', 'de minaur', 'paul', 'khachanov', 'shelton',
                                  'tiafoe', 'musetti'}


def identidad_basket(nombre):
    normal = normalizar(nombre)
    return ALIAS_BASKET.get(normal, normal)


def perfil_tenis(nombre):
    normal = normalizar(nombre)
    if any(re.search(r'(?<!\w)' + re.escape(p) + r'(?!\w)', normal) for p in FIGURAS_TENIS):
        return 'figura'
    if any(re.search(r'(?<!\w)' + re.escape(p) + r'(?!\w)', normal) for p in REFERENTES_TENIS):
        return 'referente'
    if any(re.search(r'(?<!\w)' + re.escape(p) + r'(?!\w)', normal) for p in RECONOCIDOS_TENIS):
        return 'reconocido'
    return None
