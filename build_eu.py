#!/usr/bin/env python3
"""Gaindegia serie_2 (Europa) CSVs + Europe topology -> europa.js for denbora-makina."""
import csv, json, os, re, sys, collections, glob

ZIP, TOPO, DATAJS, OUT = sys.argv[1:5]
Y0, Y1 = 2004, 2025

topo = json.load(open(TOPO, encoding='utf-8'))
S = {g['id']: g['properties'] for g in topo['objects']['s']['geometries']}
R = {g['id']: g['properties'] for g in topo['objects']['r']['geometries']}
nameS = {p['eu']: k for k, p in S.items()}
nameR = {p['eu']: k for k, p in R.items()}
REF = {'EH_izar': 'EH*', 'Euskal Herria*': 'EH*', 'EU27_2020': 'EU27', 'EU-27': 'EU27', 'EU': 'EU27', 'EB guztira': 'EU27'}

s = open(DATAJS, encoding='utf-8').read()
D = json.loads(s[s.index('{'):s.rindex('}') + 1])
code2id = {v['code']: k for k, v in D['indicators'].items()}

def num(x):
    try:
        v = float(str(x).replace(',', '.'))
        return v if v == v else None
    except Exception:
        return None

def rows(f):
    with open(f, encoding='utf-8-sig') as fh:
        return list(csv.DictReader(fh))

FILTERS = {
    'E14': {'Aldaera': 'A. Lan-kostua orduko (€/ordu)'},
    'G8': {'Definizioa': 'EB2030'},
}
PICK = {'G1': 5}   # index inside duplicate group (women/men/total × age bands): total 15-64

out = {}
report = []
for code, iid in sorted(code2id.items(), key=lambda kv: (kv[0][0], int(kv[0][1:]))):
    files = sorted(glob.glob(os.path.join(ZIP, code[0], f'{code}_*__serie_2*.csv')))
    if code in ('D3', 'D4'):
        files = sorted(glob.glob(os.path.join(ZIP, 'D', 'D3_*__serie_2*.csv')))
    if code == 'I10':
        files = [f for f in files if rows(f) and rows(f)[0].get('Kategoria') == 'Ibaiak']
    if not files:
        continue
    res = {'s': {}, 'r': {}, 'ref': {}}
    label = None
    for f in files:
        rr = rows(f)
        if not rr:
            continue
        cols = list(rr[0].keys())
        val = cols[-1]
        label = label or val
        level = 'r' if 'erregioak' in f else 's' if 'estatuak' in f else None
        gcol = next((c for c in cols if c.lower().startswith('geo')), None)
        ncol = 'Lurraldea' if 'Lurraldea' in cols else 'Herrialdea' if 'Herrialdea' in cols else None
        groups = collections.defaultdict(list)
        acc = collections.defaultdict(lambda: [0.0, 0.0])  # D3/D4 pyramid shares
        for x in rr:
            if any(x.get(k) != v for k, v in FILTERS.get(code, {}).items()):
                continue
            if code not in ('D3', 'D4') and 'Sexua' in x and x['Sexua'] not in ('Guztira', ''):
                continue
            y = x.get('Urtea', '')
            if not y.isdigit() or not (Y0 <= int(y) <= Y1):
                continue
            c = (x.get(gcol) or '').strip() if gcol else ''
            n = (x.get(ncol) or '').strip() if ncol else ''
            key = None
            if c in REF or n in REF:
                key = ('ref', REF.get(c) or REF.get(n))
            elif level == 'r':
                if c in R: key = ('r', c)
                elif n in nameR: key = ('r', nameR[n])
                elif c in S: key = ('s', c)
                elif n in nameS: key = ('s', nameS[n])
            elif level == 's':
                if c in S: key = ('s', c)
                elif n in nameS: key = ('s', nameS[n])
            else:
                if c in S: key = ('s', c)
                elif c in R: key = ('r', c)
                elif n in nameS: key = ('s', nameS[n])
                elif n in nameR: key = ('r', nameR[n])
            if not key:
                continue
            if code in ('D3', 'D4'):
                m = re.match(r'\d+', x.get('Tartea', ''))
                v = num(x[val]) or 0.0
                sx = 'G' if x.get('Sexua') == 'Guztira' else 'S'
                a = acc[(key, int(y), sx)]; a[1] += v
                lo = int(m.group()) if m else -1
                if (code == 'D3' and 0 <= lo < 15) or (code == 'D4' and lo >= 65): a[0] += v
                continue
            v = num(x[val])
            if v is None:
                continue
            groups[(key, int(y))].append(v)
        if code in ('D3', 'D4'):
            for (key, y, sx), (a, b) in acc.items():
                if sx == 'S' and acc.get((key, y, 'G'), [0, 0])[1]: continue
                if b: groups[(key, y)] = [round(a / b * 100, 2)]
        for (key, y), vs in groups.items():
            if code in PICK:
                if len(vs) not in (9, 12): continue
                v = vs[PICK[code]]
            else:
                v = vs[0]
            lvl, k = key
            # a file-level 'estatuak' file must not overwrite region-level and vice versa
            res[lvl].setdefault(k, {}).setdefault(str(y), round(v, 4))
    # EH must exist in both levels if present in either (same shape)
    for a, b in (('s', 'r'), ('r', 's')):
        if 'EH' in res[a] and 'EH' not in res[b] and res[b]:
            res[b]['EH'] = dict(res[a]['EH'])
    for lvl in ('s', 'r'):
        if len(res[lvl]) < 5:
            res[lvl] = {}
    if not res['s'] and not res['r']:
        continue
    res['label'] = label
    L = label.lower()
    res['unit'] = '‰' if '‰' in L else '%' if ('%' in L or 'ehuneko' in L or 'tasa' == L.strip() or code in ('D3','D4','G1','G8')) else 'PPS' if 'pps' in L else 'EAP' if 'eap' in L else '€/urte' if '€/urte' in L else '€/ordu' if code in ('E13','E14') else ''
    if code in ('D3', 'D4'): res['label'] = {'D3': '0-14 urtekoen ehunekoa', 'D4': '65 urte eta gehiagokoen ehunekoa'}[code]
    out[iid] = res
    report.append(f"{code:4} {iid:18} s={len(res['s']):3} r={len(res['r']):3} ref={list(res['ref'])} EH={'EH' in res['s'] or 'EH' in res['r']} label={label[:45]}")

# make geometry lighter for the page: keep only what we draw
EU = {'topo': topo, 'ind': out}
with open(OUT, 'w', encoding='utf-8') as fh:
    fh.write('/* Europako konparazioa / comparación europea · Gaindegia DatuAtaria (serie_2), 2026-11-12.\n'
             '   Geometria: DatuAtariko Europa_estatuak eta Europa_erregioak mapak (sinplifikatuak).\n'
             '   ind.<id>.s|r.<KODEA>["urtea"] = balioa · ref: EU27, EH* (Hego EH) */\n')
    fh.write('window.GAINDEGIA_EUROPA = ' + json.dumps(EU, ensure_ascii=False, separators=(',', ':')) + ';\n')
print('\n'.join(report))
print('indicators with Europe data:', len(out), ' size', os.path.getsize(OUT))
