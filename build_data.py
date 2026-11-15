#!/usr/bin/env python3
"""Gaindegia datutegia (CSV zip) -> denbora-makina data.js + udal.js (prototype schema)."""
import csv, json, sys, os, re, collections, unicodedata

ZIP = sys.argv[1]      # unzipped folder
PROTO = sys.argv[2]    # folder with geo.js / old data.js
OUT = sys.argv[3]
Y0, Y1 = 2004, 2025
YEARS = list(range(Y0, Y1 + 1))

def R(f):
    with open(os.path.join(ZIP, f[0], f), encoding='utf-8-sig') as fh:
        return list(csv.DictReader(fh))

def num(s):
    try:
        v = float(str(s).replace(',', '.'))
        return v if v == v else None
    except Exception:
        return None

def load_js(p):
    s = open(p, encoding='utf-8').read()
    return json.loads(s[s.index('{'):s.rindex('}') + 1])

geo = load_js(os.path.join(PROTO, 'geo.js'))
old = load_js(os.path.join(PROTO, 'data.js'))
GEOM = geo['objects']['u']['geometries']
UIDS = [g['id'] for g in GEOM]
UIDX = {u: i for i, u in enumerate(UIDS)}
UH = [g['properties']['h'] for g in GEOM]
UNAMES = [g['properties']['n'] for g in GEOM]
UAREA = [g['properties']['a'] for g in GEOM]

# ---------------------------------------------------------------- territory names
AREA_NAMES = {
    'Euskal Herria': 'EH', 'Euskaraz, argitaletxea edonon': 'EH',
    'Euskal Herria*': 'HEH', 'Hego Euskal Herria': 'HEH',
    'Euskal Autonomia Erkidegoa': 'EAE', 'EAE': 'EAE', 'Euskal AE': 'EAE', 'Euskal Autonomi Erkidegoa': 'EAE',
    'Nafarroa Garaia': 'NG', 'Nafarroa': 'NG',
    'Ipar Euskal Herria': 'IEH', 'Iparraldea': 'IEH',
    'Araba': 'AR', 'Araba/Álava': 'AR', 'Bizkaia': 'BI', 'Gipuzkoa': 'GI',
    'Lapurdi': 'LA', 'Nafarroa Beherea': 'NB', 'Zuberoa': 'ZU',
    'Nafarroa Beherea eta Zuberoa': ('NB', 'ZU'),
    'EB guztira': 'EU27', 'EU-27': 'EU27',
}
HERR = {'Araba': 'AR', 'Bizkaia': 'BI', 'Gipuzkoa': 'GI', 'Nafarroa Garaia': 'NG',
        'Lapurdi': 'LA', 'Nafarroa Beherea': 'NB', 'Zuberoa': 'ZU'}

def norm(s):
    s = unicodedata.normalize('NFKD', s.lower()).encode('ascii', 'ignore').decode()
    return re.sub(r'[^a-z0-9]', '', s)

# municipality resolver
MUNI_ALIAS = {'untzitibar': 'E31237', 'getarialapurdi': 'F64249', 'biarritzmiarritze': 'F64122',
              'tebasmuruartederreta': 'E31163', 'goneerrigonibar': 'E31118', 'gonerrigonibar': 'E31118',
              'moreda': 'E01039', 'oltzazendea': 'E31193', 'ollaranolloibar': 'E31194',
              'jatabe': 'E48061'}
by_hn = {}
by_n = collections.defaultdict(set)
for g in GEOM:
    p = g['properties']
    for k in ('n', 'o'):
        for part in [p[k]] + p[k].split('/'):
            by_hn[(p['h'], norm(part))] = g['id']
            by_n[norm(part)].add(g['id'])
unmatched = collections.Counter()

def muni_id(name, herr=None, code=None):
    if code:
        c = str(code).strip()
        if c.isdigit():
            cid = 'E' + c.zfill(5)
            if cid in UIDX: return cid
    k = norm(name)
    if k in MUNI_ALIAS: return MUNI_ALIAS[k]
    h = HERR.get(herr) if herr else None
    if h and (h, k) in by_hn: return by_hn[(h, k)]
    if not h and len(by_n.get(k, ())) == 1: return next(iter(by_n[k]))
    if h:
        for part in re.split(r'[,/]| - ', name):
            if (h, norm(part)) in by_hn: return by_hn[(h, norm(part))]
    unmatched[(herr, name)] += 1
    return None

# ---------------------------------------------------------------- indicator specs
# sec: demo eko giz ing kul
S = []
def ind(**k): S.append(k)

ind(id='biztanleria', code='D1', sec='demo', f='D1_biztanleria__serie_1.csv', muni=True,
    eu='Biztanleriaren bilakaera', es='Evolución de la población', seu='Biztanleria', ses='Población', unit='', dec=0, better='neutral')
ind(id='dentsitatea', code='D2', sec='demo', f='D2_dentsitatea__serie_1.csv', muni=True, special='density',
    eu='Biztanleriaren dentsitatea', es='Densidad de población', seu='Dentsitatea', ses='Densidad', unit='biz/km²', dec=1, better='neutral')
ind(id='gazteak', code='D3', sec='demo', f='D3_piramidea__serie_1.csv', muni=True, special='young',
    eu='Adin egitura: 0-14 urtekoak', es='Estructura de edad: 0-14 años', seu='0-14 urte', ses='0-14 años', unit='%', dec=1, better='neutral')
ind(id='zahartzea', code='D4', sec='demo', f='D4_zahartze_tasa__serie_1.csv', muni=True,
    eu='Zahartze tasa', es='Tasa de envejecimiento', seu='Zahartzea', ses='Envejecimiento', unit='%', dec=1, better='neutral')
ind(id='jaiolekua', code='D5', sec='demo', f='D5_jaiolekuak__serie_1.csv', muni=True, special='born',
    eu='Euskal Herritik kanpo jaioak', es='Nacidos fuera de Euskal Herria', seu='Kanpoan jaioak', ses='Nacidos fuera', unit='%', dec=1, better='neutral')
ind(id='migrazioa', code='D6', sec='demo', f='D6_migrazio_saldoa__serie_1.csv', muni=True,
    eu='Migrazio saldoaren tasa', es='Tasa de saldo migratorio', seu='Migrazio saldoa', ses='Saldo migratorio', unit='‰', dec=1, better='neutral')
ind(id='jaiotzak', code='D7', sec='demo', f='D7_jaiotza_tasa__serie_1.csv', muni=True,
    eu='Jaiotza tasa', es='Tasa de natalidad', seu='Jaiotzak', ses='Natalidad', unit='‰', dec=1, better='up')
ind(id='heriotzak', code='D8', sec='demo', f='D8_heriotza_tasa__serie_1.csv', muni=True,
    eu='Heriotza tasa', es='Tasa de mortalidad', seu='Heriotzak', ses='Mortalidad', unit='‰', dec=1, better='down')
ind(id='hazkundea', code='D9', sec='demo', f='D9_berezko_hazkundea__serie_1.csv', muni=True,
    eu='Berezko hazkundea', es='Crecimiento vegetativo', seu='Berezko hazkundea', ses='Crec. vegetativo', unit='‰', dec=1, better='up')

ind(id='ind_tamaina', code='E1', sec='eko', f='E1_industria_establezimenduen_batez_besteko_tamaina__serie_1.csv',
    eu='Industria establezimenduen batez besteko tamaina', es='Tamaño medio de los establecimientos industriales', seu='Industria-tamaina', ses='Tamaño industrial', unit='langile', dec=1, better='neutral')
ind(id='ig', code='E2', sec='eko', f='E2_berrikuntza_IGko_gastua__serie_1__gastua.csv',
    eu='I+Gko gastua (BPGren %)', es='Gasto en I+D (% del PIB)', seu='I+G gastua', ses='Gasto I+D', unit='% BPG', dec=2, better='up')
ind(id='ig_langileak', code='E3', sec='eko', f='E3_IGko_langileak__serie_1__langileak.csv',
    eu='I+Gko langileak (enplegu osoaren %)', es='Personal de I+D (% del empleo)', seu='I+G langileak', ses='Personal I+D', unit='%', dec=2, better='up')
ind(id='zorra', code='E4', sec='eko', f='E4_tokiko_herri_administrazioen_zor_publikoa__serie_1__zorra_bpg.csv',
    eu='Tokiko herri-administrazioen zor publikoa (BPGren %)', es='Deuda pública de las administraciones locales (% PIB)', seu='Zor publikoa', ses='Deuda pública', unit='% BPG', dec=1, better='down')
ind(id='lansaria', code='E5', sec='eko', f='E5_lansaria_soldatapeko__serie_1__lansaria.csv',
    eu='Lansaria soldatapeko (€/urte)', es='Remuneración por asalariado (€/año)', seu='Lansaria', ses='Remuneración', unit='€', dec=0, better='up')
ind(id='zaintza', code='E6', sec='eko', f='E6_zaintzari_eskainitako_denbora__serie_1__zaintza.csv', filt={'Sexua': 'Guztira'},
    eu='Zaintzari eskainitako denbora (ordaindu gabea)', es='Tiempo dedicado a cuidados (no remunerado)', seu='Zaintza', ses='Cuidados', unit='min/egun', dec=0, better='neutral')
ind(id='kooperatibak', code='E7', sec='eko', f='E7_kooperatibetako_enplegua_landunen__serie_2.csv',
    eu='Kooperatibetako enplegua (landunen %)', es='Empleo en cooperativas (% de ocupados)', seu='Kooperatibak', ses='Cooperativas', unit='%', dec=1, better='up')
ind(id='bpg_biztanleko', code='E8', sec='eko', f='E8_BPG_biztanleko__serie_1__bpg.csv',
    eu='BPG biztanleko', es='PIB per cápita', seu='BPG biztanleko', ses='PIB per cápita', unit='€', dec=0, better='up')
ind(id='industria', code='E9', sec='eko', f='E9_industriaren_BE_pisua_balio_erantsi_gordinean__serie_1__ehunekoa.csv',
    eu='Industriaren (B-E) pisua balio erantsi gordinean', es='Peso de la industria (B-E) en el VAB', seu='Industria', ses='Industria', unit='%', dec=1, better='neutral')
ind(id='enpresa_saldoa', code='E10', sec='eko', f='E10_enpresa_demografia_saldo_garbia__serie_1__saldoa.csv',
    eu='Enpresa demografiaren saldo garbia', es='Saldo neto de la demografía empresarial', seu='Enpresa saldoa', ses='Saldo empresarial', unit='%', dec=1, better='up')
ind(id='esportazioak', code='E11', sec='eko', f='E11_esportazioak_ondasunak_BPGaren__serie_1__esportazioak.csv',
    eu='Esportazioak (ondasunak)', es='Exportaciones (bienes)', seu='Esportazioak', ses='Exportaciones', unit='M€', dec=0, better='up')
ind(id='balantza', code='E12', sec='eko', f='E12_merkataritza_balantza_ondasunak_zerbitzuak_BPG__serie_1__saldoa.csv', filt={'Eremua': 'GUZTIRA'},
    eu='Merkataritza-balantza (ondasunak eta zerbitzuak), BPGren %', es='Balanza comercial (bienes y servicios), % del PIB', seu='Merkat. balantza', ses='Balanza comercial', unit='% BPG', dec=1, better='up')
ind(id='produktibitatea', code='E13', sec='eko', f='E13_lanaren_produktibitatea__serie_1.csv',
    eu='Lanaren produktibitatea, lan egindako orduko', es='Productividad del trabajo por hora trabajada', seu='Produktibitatea', ses='Productividad', unit='€/ordu', dec=1, better='up')
ind(id='lan_kostua', code='E14', sec='eko', f='E14_lan_kostu_unitarioa_lan_egindako_orduko__serie_1.csv', filt={'Aldaera': 'A. Lan-kostua orduko (€/ordu)'},
    eu='Lan-kostua lan egindako orduko', es='Coste laboral por hora trabajada', seu='Lan-kostua', ses='Coste laboral', unit='€/ordu', dec=1, better='neutral')

ind(id='okupazioa', code='G1', sec='giz', f='G1_okupazio_tasa__serie_1.csv', dup='second',
    eu='Okupazio tasa (15-64)', es='Tasa de empleo (15-64)', seu='Okupazioa', ses='Empleo', unit='%', dec=1, better='up')
ind(id='kpi', code='G2', sec='giz', f='G2_kpi_tasa__serie_1.csv',
    eu='Kontsumo prezioen indizea (KPI)', es='Índice de precios al consumo (IPC)', seu='KPI', ses='IPC', unit='indizea', dec=1, better='down')
ind(id='babesa', code='G3', sec='giz', f='G3_gizarte_babesa__serie_1.csv',
    eu='Gizarte babeserako gastua (BPGren %)', es='Gasto en protección social (% del PIB)', seu='Gizarte babesa', ses='Protección social', unit='% BPG', dec=1, better='neutral')
ind(id='goi_hezkuntza', code='G4', sec='giz', f='G4_goi_hezkuntza__serie_1.csv', filt={'Adin tartea': ['25-64', '25-64 (IEH estimatua)']},
    eu='Goi-mailako ikasketak (25-64)', es='Estudios superiores (25-64)', seu='Goi hezkuntza', ses='Estudios superiores', unit='%', dec=1, better='up')
ind(id='gogobetetasuna', code='G5', sec='giz', f='G5_gogo_betetasuna__serie_1.csv',
    eu='Bizitzarekiko gogobetetasuna (0-10)', es='Satisfacción con la vida (0-10)', seu='Gogobetetasuna', ses='Satisfacción', unit='0-10', dec=1, better='up')
ind(id='berdintasuna', code='G6', sec='giz', f='G6_genero_berdintasuna__serie_1.csv',
    eu='Genero berdintasunaren indizea', es='Índice de igualdad de género', seu='Berdintasuna', ses='Igualdad', unit='indizea', dec=1, better='up')
ind(id='errenta', code='G7', sec='giz', f='G7_errenta__serie_1.csv',
    eu='Errenta erabilgarria biztanleko (EAP)', es='Renta disponible per cápita (PPA)', seu='Errenta', ses='Renta', unit='EAP', dec=0, better='up')
ind(id='arope', code='G8', sec='giz', f='G8_arope__serie_1.csv', filt={'Definizioa': 'EB2030'}, dup='first',
    eu='Pobrezia edo gizarte-bazterketa arriskua (AROPE)', es='Riesgo de pobreza o exclusión social (AROPE)', seu='AROPE', ses='AROPE', unit='%', dec=1, better='down')
ind(id='gini', code='G9', sec='giz', f='G9_gini__serie_1.csv', muni=True,
    eu='Gini indizea', es='Índice de Gini', seu='Gini', ses='Gini', unit='', dec=1, better='down')

ind(id='energia', code='I1', sec='ing', f='I1_Energia-intentsitatea__serie_1__marrak.csv',
    eu='Energia-intentsitatea', es='Intensidad energética', seu='Energia-intentsitatea', ses='Intensidad energética', unit='', dec=1, better='down')
ind(id='berriztagarriak', code='I2', sec='ing', f='I2_energia_berriztagarrien_kuota_azken_kontsumo_gordinean__serie_1.csv',
    eu='Energia berriztagarrien kuota azken kontsumo gordinean', es='Cuota de renovables en el consumo final bruto', seu='Berriztagarriak', ses='Renovables', unit='%', dec=1, better='up')
ind(id='ahalmena', code='I3', sec='ing', f='I3_elektrizitate_berriztagarria_sortzeko_ahalmen_instalatua__serie_1.csv',
    eu='Elektrizitate berriztagarria sortzeko ahalmen instalatua', es='Potencia renovable instalada', seu='Potentzia berriztag.', ses='Potencia renovable', unit='MW', dec=0, better='up')
ind(id='basoak', code='I4', sec='ing', f='I4_Bioaniztasuna_baso_naturalen_ehunekoa__serie_1.csv',
    eu='Bioaniztasuna: baso naturalen ehunekoa', es='Biodiversidad: porcentaje de bosques naturales', seu='Baso naturalak', ses='Bosques naturales', unit='%', dec=1, better='up')
ind(id='lurzorua', code='I5', sec='ing', f='I5_lurzorua_erabilera_artifizialerako_lurzoruaren_hazkundea__serie_1.csv', muni=True,
    eu='Lurzoru artifizializatua (azaleraren %)', es='Suelo artificializado (% de la superficie)', seu='Lurzoru artifiziala', ses='Suelo artificial', unit='%', dec=1, better='down')
ind(id='pm25', code='I6', sec='ing', f='I6_airearen_kutsadura_PM25__serie_1.csv', muni=True,
    eu='Airearen kutsadura: PM2.5 (urteko batez bestekoa)', es='Contaminación del aire: PM2.5 (media anual)', seu='PM2.5', ses='PM2.5', unit='µg/m³', dec=1, better='down')
ind(id='birziklatzea', code='I7', sec='ing', f='I7_hiri-hondakinen_birziklatze-tasa__serie_1.csv',
    eu='Hiri-hondakinen birziklatze-tasa', es='Tasa de reciclaje de residuos urbanos', seu='Birziklatzea', ses='Reciclaje', unit='%', dec=1, better='up')
ind(id='dmc', code='I8', sec='ing', f='I8_materialen_bertako_kontsumoa_per_capita__serie_1.csv',
    eu='Materialen bertako kontsumoa per capita (DMC)', es='Consumo nacional de materiales per cápita (DMC)', seu='Materialak (DMC)', ses='Materiales (DMC)', unit='t/biz', dec=1, better='down')
ind(id='kontserbazioa', code='I9', sec='ing', f='I9_bioaniztasuna_kontserbazio-egoera__serie_1.csv',
    eu='Bioaniztasuna: kontserbazio-egoera onean', es='Biodiversidad: estado de conservación favorable', seu='Kontserbazioa', ses='Conservación', unit='%', dec=1, better='up')
ind(id='ur_masak', code='I10', sec='ing', f='I10_egoera_ekologiko_onean_dauden_ur-masen_ehunekoa__serie_1.csv', filt={'Kategoria': 'Ibaiak'},
    eu='Egoera ekologiko onean dauden ibaiak', es='Ríos en buen estado ecológico', seu='Ur-masak', ses='Masas de agua', unit='%', dec=1, better='up')
ind(id='wenfi', code='I11', sec='ing', f='I11_WENFI_indizea__serie_1.csv', muni=True,
    eu='WENFI indizea (pertsona-baliokideak)', es='Índice WENFI (personas equivalentes)', seu='WENFI', ses='WENFI', unit='', dec=0, better='down')
ind(id='hondakinak', code='I12', sec='ing', f='I12_hondakin_guztien_sorkuntza__serie_1.csv',
    eu='Hondakin guztien sorkuntza', es='Generación total de residuos', seu='Hondakinak', ses='Residuos', unit='t/biz', dec=2, better='down')

ind(id='euskara_ezagutza', code='K1', sec='kul', f='K1_euskararen_ezagutza__serie_1__hartzaileak.csv', muni=True, special='k1',
    eu='Euskaldun hartzaileak (5 urte eta gehiago, %)', es='Bilingües pasivos (5 años y más, %)', seu='Euskaldun hartzaileak', ses='Bilingües pasivos', unit='%', dec=1, better='neutral')
ind(id='kale_erabilera', code='K2', sec='kul', f='K2_euskararen_kale_erabilera__serie_1.csv', filt={'Adina': 'Guztira'},
    eu='Euskararen kale erabilera', es='Uso del euskera en la calle', seu='Kale erabilera', ses='Uso en la calle', unit='%', dec=1, better='up')
ind(id='kultur_enplegua', code='K3', sec='kul', f='K3_kultur_enplegua__serie_1.csv',
    eu='Kultur enplegua (pertsonak)', es='Empleo cultural (personas)', seu='Kultur enplegua', ses='Empleo cultural', unit='', dec=0, better='up')
ind(id='kultur_gastua', code='K4', sec='kul', f='K4_kultur_gastua__serie_1.csv', filt={'Administrazioa': 'Guztira'},
    eu='Kultur gastu publikoa (mila €)', es='Gasto público en cultura (miles de €)', seu='Kultur gastua', ses='Gasto cultural', unit='', dec=0, better='up')
ind(id='tituluak', code='K5', sec='kul', f='K5_tituluak_euskaraz__serie_1__tituluak_euskaraz.csv',
    eu='Euskaraz argitaratutako tituluak', es='Títulos publicados en euskera', seu='Tituluak euskaraz', ses='Títulos en euskera', unit='', dec=0, better='up')
ind(id='lankideekin', code='K6', sec='kul', f='K6_euskeraren_erabilera_lankideekin__serie_1.csv', special='k6',
    eu='Lankideekin euskaraz (beti edo erdaraz baino gehiago)', es='Euskera con compañeros (siempre o más que castellano/francés)', seu='Lankideekin', ses='Con compañeros', unit='%', dec=1, better='up')

# ---------------------------------------------------------------- helpers
def valcol(rows):
    return list(rows[0].keys())[-1]

def passes(r, filt):
    for k, v in (filt or {}).items():
        vv = r.get(k)
        if isinstance(v, list):
            if vv not in v: return False
        elif vv != v: return False
    # generic defaults
    for k in ('Sexua', 'Adin tartea'):
        if k in r and not (filt and k in filt) and r[k] not in ('Guztira', '', '15-64', '25-64'):
            return False
    return True

def is_muni_row(r):
    return r.get('Maila') in ('Udalerria', 'Eskualdea') or ('Udalerria' in r and r.get('Maila') == 'Udalerria')

def area_ids(r):
    if r.get('Maila') in ('Udalerria', 'Eskualdea'): return ()
    a = AREA_NAMES.get(r.get('Lurraldea', ''))
    if a is None: return ()
    return a if isinstance(a, tuple) else (a,)

warnings = []

def series_from(rows, val, dup='warn', key=lambda r: None):
    """-> {area: {year: v}}"""
    out = collections.defaultdict(dict)
    groups = collections.defaultdict(list)
    for r in rows:
        y = r.get('Urtea', '')
        if not y.isdigit(): continue
        v = num(r[val])
        if v is None: continue
        for a in area_ids(r):
            groups[(a, int(y))].append(v)
    nd = 0
    for (a, y), vs in groups.items():
        if len(set(vs)) > 1: nd += 1
        out[a][y] = vs[1] if (dup == 'second' and len(vs) > 1) else vs[0]
    return out, nd

def muni_from(rows, val, code_col=None):
    m = {}
    for r in rows:
        name = r.get('Udalerria') or r.get('Lurraldea')
        if 'Maila' in r and r['Maila'] != 'Udalerria': continue
        if 'Maila' not in r and AREA_NAMES.get(name): continue
        y = r.get('Urtea', '')
        if not y.isdigit(): continue
        v = num(r[val])
        if v is None: continue
        uid = muni_id(name, r.get('Herrialdea'), r.get(code_col) if code_col else None)
        if uid is None: continue
        m.setdefault(uid, {})[int(y)] = v
    return m

# ---------------------------------------------------------------- build
pop_muni = None
indicators = {}
udal = {}
for sp in S:
    rows = R(sp['f'])
    val = valcol(rows)
    special = sp.get('special')
    ser = {}; muni = {}; nd = 0
    if special == 'young' or special == 'k1':
        pass
    if special == 'young':
        acc = collections.defaultdict(lambda: [0.0, 0.0])
        accm = collections.defaultdict(lambda: [0.0, 0.0])
        for r in rows:
            if r['Sexua'] != 'Guztira' or not r['Urtea'].isdigit(): continue
            t = r['Tartea']
            if t in ('Guztira', 'Total'): continue
            v = num(r[val]) or 0.0
            lo = int(re.match(r'\d+', t).group()) if re.match(r'\d+', t) else 99
            y = int(r['Urtea'])
            if r['Maila'] == 'Udalerria':
                uid = muni_id(r['Lurraldea'], r['Herrialdea'])
                if uid:
                    a = accm[(uid, y)]; a[1] += v; a[0] += v if lo < 15 else 0
            else:
                for ar in area_ids(r):
                    a = acc[(ar, y)]; a[1] += v; a[0] += v if lo < 15 else 0
        ser = collections.defaultdict(dict)
        for (ar, y), (a, b) in acc.items():
            if b: ser[ar][y] = round(a / b * 100, 2)
        for (u, y), (a, b) in accm.items():
            if b: muni.setdefault(u, {})[y] = round(a / b * 100, 2)
    elif special == 'born':
        acc = collections.defaultdict(lambda: [0.0, 0.0]); accm = collections.defaultdict(lambda: [0.0, 0.0])
        for r in rows:
            if not r['Urtea'].isdigit(): continue
            v = num(r[val]) or 0.0; y = int(r['Urtea']); out = r['Jaiolekua'] != 'Euskal Herrian jaioak'
            if r['Maila'] == 'Udalerria':
                uid = muni_id(r['Lurraldea'], r['Herrialdea'])
                if uid:
                    a = accm[(uid, y)]; a[1] += v; a[0] += v if out else 0
            else:
                for ar in area_ids(r):
                    a = acc[(ar, y)]; a[1] += v; a[0] += v if out else 0
        ser = collections.defaultdict(dict)
        for (ar, y), (a, b) in acc.items():
            if b: ser[ar][y] = round(a / b * 100, 2)
        for (u, y), (a, b) in accm.items():
            if b: muni.setdefault(u, {})[y] = round(a / b * 100, 2)
    elif special == 'k1':
        # population aged 5+ in 2021 from D3 pyramid
        d3 = R('D3_piramidea__serie_1.csv')
        p5 = collections.defaultdict(float); p5m = collections.defaultdict(float)
        for r in d3:
            if r['Urtea'] != '2021' or r['Sexua'] != 'Guztira': continue
            t = r['Tartea']; m = re.match(r'\d+', t)
            if not m or int(m.group()) < 5: continue
            v = num(r['Biztanleria']) or 0
            if r['Maila'] == 'Udalerria':
                u = muni_id(r['Lurraldea'], r['Herrialdea'])
                if u: p5m[u] += v
            else:
                for ar in area_ids(r): p5[ar] += v
        cnt = collections.defaultdict(float); cntm = collections.defaultdict(float)
        for r in rows:
            v = num(r[val]) or 0
            ids = area_ids(r)
            if ids:
                for ar in ids: cnt[ar] += v
            else:
                u = muni_id(r['Lurraldea'])
                if u: cntm[u] += v
        ser = collections.defaultdict(dict)
        for ar, c in cnt.items():
            if p5.get(ar): ser[ar][2021] = round(c / p5[ar] * 100, 2)
        for u, c in cntm.items():
            if p5m.get(u): muni.setdefault(u, {})[2021] = round(c / p5m[u] * 100, 2)
    elif special == 'k6':
        rows2 = [r for r in rows if r['Kategoria'] in ('Beti euskaraz', 'Euskaraz erdaraz baino gehiago')]
        acc = collections.defaultdict(float)
        for r in rows2:
            for ar in area_ids(r): acc[(ar, int(r['Urtea']))] += num(r[val]) or 0
        ser = collections.defaultdict(dict)
        for (ar, y), v in acc.items(): ser[ar][y] = round(v, 2)
    elif special == 'density':
        muni = muni_from(rows, val)
        # territory density = population / summed municipal area (geo.js)
        area_h = collections.defaultdict(float)
        for i, h in enumerate(UH): area_h[h] += UAREA[i] or 0
        area_h['EH'] = sum(area_h[h] for h in HERR.values())
        area_h['EAE'] = area_h['AR'] + area_h['BI'] + area_h['GI']
        area_h['IEH'] = area_h['LA'] + area_h['NB'] + area_h['ZU']
        area_h['HEH'] = area_h['EAE'] + area_h['NG']
        pop = indicators['biztanleria']['series']
        ser = {a: {int(y): round(v / area_h[a], 2) for y, v in s.items()} for a, s in pop.items() if area_h.get(a)}
    else:
        rows = [r for r in rows if passes(r, sp.get('filt'))]
        ser, nd = series_from(rows, val, dup=sp.get('dup', 'first'))
        if sp.get('muni'):
            muni = muni_from(rows, val, code_col='Udal kodea' if 'Udal kodea' in rows[0] else None)
    if nd and not sp.get('dup'):
        warnings.append(f"{sp['code']}: {nd} urte/lurralde bikoiztuak (lehenengoa hartuta)")
    # EU27 from estatuak table if present
    try:
        base = sp['f'].split('__')[0]
        for fn in os.listdir(os.path.join(ZIP, base[0])):
            if fn.startswith(base + '__serie_2'):
                rr = R(fn); vc = valcol(rr)
                for r in rr:
                    nmx = r.get('Lurraldea') or r.get('Herrialdea') or ''
                    if AREA_NAMES.get(nmx) == 'EU27' and r.get('Urtea', '').isdigit() and num(r[vc]) is not None:
                        if r.get('Sexua', 'Guztira') != 'Guztira': continue
                        ser.setdefault('EU27', {})[int(r['Urtea'])] = num(r[vc])
    except FileNotFoundError:
        pass
    # restrict to year window, round
    def clean(s):
        return {str(y): (round(v, 4) if abs(v) < 1000 else round(v, 1)) for y, v in sorted(s.items()) if Y0 <= y <= Y1}
    series = {a: clean(s) for a, s in ser.items()}
    series = {a: s for a, s in series.items() if s}
    main = 'EH' if 'EH' in series else 'HEH' if 'HEH' in series else 'EAE' if 'EAE' in series else (next(iter(series)) if series else None)
    if main == 'EH' and 'HEH' in series and len(series['HEH']) > 2 * len(series['EH']): main = 'HEH'
    if main is None:
        warnings.append(f"{sp['code']}: ez dago daturik {Y0}-{Y1} tartean — kanpoan utzita")
        continue
    indicators[sp['id']] = dict(code=sp['code'], section=sp['sec'], name={'eu': sp['eu'], 'es': sp['es']},
                                short={'eu': sp['seu'], 'es': sp['ses']}, unit=sp['unit'], decimals=sp['dec'],
                                better=sp['better'], main=main, series=series,
                                url=f"https://datutegia.gaindegia.eus/datuak-yaml?dataset={sp['f'].split('__')[0]}")
    if muni:
        arr = []
        for uid in UIDS:
            s = muni.get(uid, {})
            arr.append([(round(s[y], 3) if s.get(y) is not None else None) for y in YEARS])
        cover = sum(1 for a in arr if any(v is not None for v in a))
        if cover >= 50:
            udal[sp['id']] = arr
        indicators[sp['id']]['_mcover'] = cover

# ---------------------------------------------------------------- auto texts
def fmt(v, d):
    s = f"{v:,.{d}f}"
    return s.replace(',', 'X').replace('.', ',').replace('X', '.')
AN = {'EH': ('Euskal Herria', 'Euskal Herria'), 'HEH': ('Hego Euskal Herria', 'Hego Euskal Herria'), 'EAE': ('EAE', 'CAV')}
for k, d in indicators.items():
    s = d['series'][d['main']]; ys = sorted(s, key=int)
    a, b = ys[0], ys[-1]; va, vb = s[a], s[b]
    nmeu, nmes = AN.get(d['main'], (d['main'], d['main']))
    if a == b:
        teu = f"{nmeu}: {fmt(vb, d['decimals'])} ({b}). Urte bakarreko datua."
        tes = f"{nmes}: {fmt(vb, d['decimals'])} ({b}). Dato de un solo año."
    else:
        teu = f"{nmeu}: {fmt(va, d['decimals'])} ({a}) → {fmt(vb, d['decimals'])} ({b}). {len(ys)} urteko datuak."
        tes = f"{nmes}: {fmt(va, d['decimals'])} ({a}) → {fmt(vb, d['decimals'])} ({b}). Datos de {len(ys)} años."
    if d['main'] == 'HEH':
        teu += " Euskal Herria* = Hego Euskal Herria (EAE + Nafarroa Garaia)."
        tes += " Euskal Herria* = Hego Euskal Herria (CAV + Navarra)."
    d['text'] = {'eu': teu, 'es': tes}

# ---------------------------------------------------------------- package
areas = [
    {'id': 'AR', 'name': {'eu': 'Araba', 'es': 'Álava'}, 'p': 'EAE'},
    {'id': 'BI', 'name': {'eu': 'Bizkaia', 'es': 'Bizkaia'}, 'p': 'EAE'},
    {'id': 'GI', 'name': {'eu': 'Gipuzkoa', 'es': 'Gipuzkoa'}, 'p': 'EAE'},
    {'id': 'NG', 'name': {'eu': 'Nafarroa Garaia', 'es': 'Navarra'}, 'p': 'NG'},
    {'id': 'LA', 'name': {'eu': 'Lapurdi', 'es': 'Lapurdi'}, 'p': 'IEH'},
    {'id': 'NB', 'name': {'eu': 'Nafarroa Beherea', 'es': 'Baja Navarra'}, 'p': 'IEH'},
    {'id': 'ZU', 'name': {'eu': 'Zuberoa', 'es': 'Zuberoa'}, 'p': 'IEH'},
]
regions = [
    {'id': 'EAE', 'name': {'eu': 'Euskal AE', 'es': 'CA de Euskadi'}},
    {'id': 'NG', 'name': {'eu': 'Nafarroa Garaia', 'es': 'Navarra'}},
    {'id': 'IEH', 'name': {'eu': 'Ipar Euskal Herria', 'es': 'Iparralde'}},
    {'id': 'HEH', 'name': {'eu': 'Hego Euskal Herria', 'es': 'Hego Euskal Herria'}},
]
events = [
    {'year': 2008, 'name': {'eu': 'Finantza krisia', 'es': 'Crisis financiera'},
     'text': {'eu': 'Lehman Brothers erori eta krisi globala hasten da. Ikusi nola aldatzen den okupazio tasa.', 'es': 'Cae Lehman Brothers y empieza la crisis global. Mira cómo cambia la tasa de empleo.'}, 'ind': 'okupazioa'},
    {'year': 2013, 'name': {'eu': 'Krisiaren hondoa', 'es': 'Fondo de la crisis'},
     'text': {'eu': 'Enpleguaren urterik txarrenetakoa. Okupazio tasa serieko mailarik baxuenetan.', 'es': 'Uno de los peores años para el empleo: la tasa de ocupación, en mínimos de la serie.'}, 'ind': 'okupazioa'},
    {'year': 2020, 'name': {'eu': 'COVID-19 pandemia', 'es': 'Pandemia de COVID-19'},
     'text': {'eu': 'Itxialdiak eta gainheriotza: heriotza tasak gora egiten du.', 'es': 'Confinamientos y exceso de mortalidad: sube la tasa de mortalidad.'}, 'ind': 'heriotzak'},
    {'year': 2022, 'name': {'eu': 'Ukrainako gerra eta inflazioa', 'es': 'Guerra de Ucrania e inflación'},
     'text': {'eu': 'Energiaren prezioak gora; KPIak jauzi handia egiten du.', 'es': 'Se disparan los precios de la energía; el IPC da un gran salto.'}, 'ind': 'kpi'},
]
sections = [
    {'id': 'demo', 'code': 'D', 'name': {'eu': 'Demografia', 'es': 'Demografía'}},
    {'id': 'eko', 'code': 'E', 'name': {'eu': 'Ekonomia', 'es': 'Economía'}},
    {'id': 'giz', 'code': 'G', 'name': {'eu': 'Gizartea', 'es': 'Sociedad'}},
    {'id': 'ing', 'code': 'I', 'name': {'eu': 'Ingurumena', 'es': 'Medio ambiente'}},
    {'id': 'kul', 'code': 'K', 'name': {'eu': 'Kultura', 'es': 'Cultura'}},
]
for k, d in indicators.items(): d.pop('_mcover', None)
data = {'meta': {'fictitious': False, 'years': [Y0, Y1], 'downloaded': '2026-11-12',
                 'source': {'eu': 'Gaindegia · DatuAtaria (datutegia.gaindegia.eus)', 'es': 'Gaindegia · DatuAtaria (datutegia.gaindegia.eus)'}},
        'sections': sections, 'areas': areas, 'regions': regions, 'events': events, 'indicators': indicators}
os.makedirs(OUT, exist_ok=True)
with open(os.path.join(OUT, 'data.js'), 'w', encoding='utf-8') as fh:
    fh.write("/* GAINDEGIA · datu-geruza / capa de datos — DATU ERREALAK / DATOS REALES\n"
             "   Iturria: datutegia.gaindegia.eus (deskarga 2026-11-12). Sortzailea: build.py\n"
             "   indicators.<id>.series.<area>[\"<urtea>\"] = balioa\n"
             "   area: EH, HEH (Euskal Herria* = Hego EH), EAE, NG, IEH, AR, BI, GI, LA, NB, ZU, EU27\n"
             "   indicators.<id>.main = goiburuko lurraldea (EH, bestela HEH edo EAE) */\n")
    fh.write('window.GAINDEGIA_DATA = ' + json.dumps(data, ensure_ascii=False, separators=(',', ':')) + ';\n')
ud = {'note': {'eu': 'Udalerriak: Gaindegiaren DatuAtariko udal datuak (datutegia.gaindegia.eus).', 'es': 'Municipios: datos municipales de DatuAtaria de Gaindegia (datutegia.gaindegia.eus).'},
      'years': [Y0, Y1], 'ids': UIDS, 'names': UNAMES, 'h': UH, 'area': UAREA, 'ind': udal}
with open(os.path.join(OUT, 'udal.js'), 'w', encoding='utf-8') as fh:
    fh.write("/* Udalerri-datuak / datos municipales (ERREALAK) · ids = geo.js u.geometries ids · ind[id][udalerria][urtea-%d] (null = daturik ez) */\n" % Y0)
    fh.write('window.GAINDEGIA_UDAL = ' + json.dumps(ud, ensure_ascii=False, separators=(',', ':')) + ';\n')

# ---------------------------------------------------------------- report
print('indicators:', len(indicators), ' muni layers:', list(udal))
for k, d in indicators.items():
    s = d['series']
    ys = sorted({int(y) for a in s.values() for y in a})
    print(f"{d['code']:4} {k:18} main={d['main']:4} areas={','.join(sorted(s))} yrs={ys[0]}-{ys[-1]} ({len(ys)}) "
          f"main {list(s[d['main']].items())[:1]}..{list(s[d['main']].items())[-1:]}" + (f"  MUNI" if k in udal else ''))
print('WARN', *warnings, sep='\n  ')
print('unmatched munis (top):', unmatched.most_common(25))
