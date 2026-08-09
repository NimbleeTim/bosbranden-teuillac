#!/usr/bin/env python3
"""Werkt de weercijfers in het vakantiedashboard bij.

Draait elke ochtend via .github/workflows/dagelijkse-update.yml, en is ook lokaal
te draaien met  python3 scripts/update-weer.py

Bronnen, in volgorde van voorrang voor de hoofdreeks:

  1. Foreca          - alleen als FORECA_USER en FORECA_PASSWORD gezet zijn.
  2. Open-Meteo      - altijd; ook de bron voor uurdata, lucht en de terugval.

Météo-France en Open-Meteo blijven er als controlelijn naast liggen, zodat je op de
pagina ziet wanneer de modellen het oneens zijn. Zonder Foreca-sleutel verandert er
niets aan het gedrag van vandaag: dan is Open-Meteo gewoon de hoofdreeks.

Het script schrijft niets als het geen verse cijfers kon ophalen. Liever een dag oude
data die als oud gelabeld staat dan verzonnen data.
"""

import json
import os
import re
import sys
import urllib.error
import urllib.request
from collections import defaultdict
from datetime import datetime, timedelta, timezone

LAT, LON = 45.09289, -0.54756
TZ = 'Europe/Paris'
PAGINA = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                      'vakantie-status-teuillac.html')

OM = 'https://api.open-meteo.com/v1/forecast'
OM_LUCHT = 'https://air-quality-api.open-meteo.com/v1/air-quality'
FORECA_TOKEN = 'https://pfa.foreca.com/authorize/token'
FORECA_DAILY = 'https://pfa.foreca.com/api/v1/forecast/daily'

CODE = {0: 'onbewolkt', 1: 'licht bewolkt', 2: 'wisselend bewolkt', 3: 'zwaarbewolkt',
        45: 'mist', 48: 'mist', 51: 'motregen', 53: 'motregen', 55: 'motregen',
        56: 'ijzelmotregen', 57: 'ijzelmotregen', 61: 'regen', 63: 'regen', 65: 'zware regen',
        66: 'ijzelregen', 67: 'ijzelregen', 71: 'sneeuw', 73: 'sneeuw', 75: 'sneeuw',
        77: 'sneeuwkorrels', 80: 'buien', 81: 'buien', 82: 'zware buien',
        85: 'sneeuwbuien', 86: 'sneeuwbuien', 95: 'onweer', 96: 'onweer met hagel',
        99: 'onweer met hagel'}
BINNEN_CODES = {61, 63, 65, 80, 81, 82, 95, 96, 99}

MAANDEN = ['januari', 'februari', 'maart', 'april', 'mei', 'juni', 'juli',
           'augustus', 'september', 'oktober', 'november', 'december']


def log(*a):
    print(*a, flush=True)


def haal(url, kop=None, data=None, timeout=30):
    req = urllib.request.Request(url, data=data, headers=kop or {})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode())


def nul(v, d=0.0):
    return d if v is None else v


# --------------------------------------------------------------------------
# Open-Meteo
# --------------------------------------------------------------------------

def haal_openmeteo():
    q = (f'{OM}?latitude={LAT}&longitude={LON}'
         '&hourly=temperature_2m,apparent_temperature,precipitation,precipitation_probability,'
         'wind_speed_10m,wind_gusts_10m'
         '&daily=temperature_2m_max,temperature_2m_min,precipitation_sum,'
         'precipitation_probability_max,wind_speed_10m_max,wind_gusts_10m_max,'
         'wind_direction_10m_dominant,sunrise,sunset,weather_code'
         f'&timezone={TZ.replace("/", "%2F")}&forecast_days=16')
    return haal(q)


def haal_meteofrance():
    q = (f'{OM}?latitude={LAT}&longitude={LON}&daily=temperature_2m_max'
         f'&timezone={TZ.replace("/", "%2F")}&forecast_days=16&models=meteofrance_seamless')
    d = haal(q)['daily']
    return [{'d': t, 'tmax': v} for t, v in zip(d['time'], d['temperature_2m_max']) if v is not None]


def haal_lucht():
    q = (f'{OM_LUCHT}?latitude={LAT}&longitude={LON}'
         '&hourly=pm10,pm2_5,european_aqi,ozone'
         f'&timezone={TZ.replace("/", "%2F")}&past_days=5&forecast_days=5')
    return haal(q)['hourly']


# --------------------------------------------------------------------------
# Foreca -- optioneel, alleen met sleutel
# --------------------------------------------------------------------------

def _pak(rij, *namen):
    """Foreca's veldnamen verschillen per pakket; probeer ze op volgorde."""
    for n in namen:
        if rij.get(n) is not None:
            return rij[n]
    return None


def haal_foreca(user, wachtwoord):
    body = json.dumps({'user': user, 'password': wachtwoord}).encode()
    tok = haal(FORECA_TOKEN, {'Content-Type': 'application/json'}, body)
    token = tok.get('access_token') or tok.get('accessToken')
    if not token:
        raise RuntimeError(f'geen access_token in antwoord: {sorted(tok)}')

    url = f'{FORECA_DAILY}/{LON},{LAT}?periods=14&dataset=full&tz={TZ}'
    rauw = haal(url, {'Authorization': f'Bearer {token}'})
    rijen = rauw.get('forecast') or rauw.get('data') or []
    if not rijen:
        raise RuntimeError(f'lege forecast; sleutels: {sorted(rauw)}')

    log(f'   Foreca gaf {len(rijen)} dagen, velden: {sorted(rijen[0])}')

    uit = []
    for r in rijen:
        datum = _pak(r, 'date', 'time')
        tmax = _pak(r, 'maxTemp', 'temperatureMax', 'maxTemperature')
        tmin = _pak(r, 'minTemp', 'temperatureMin', 'minTemperature')
        if datum is None or tmax is None or tmin is None:
            continue
        uit.append({
            'd': str(datum)[:10],
            'tmax': float(tmax),
            'tmin': float(tmin),
            'rain': float(nul(_pak(r, 'precipAccum', 'precipitation', 'precipAccumulation'))),
            'pop': int(nul(_pak(r, 'precipProb', 'precipitationProbability'))),
            'wind': float(nul(_pak(r, 'maxWindSpeed', 'windSpeed'))),
            'gust': int(round(nul(_pak(r, 'maxWindGust', 'windGust', 'maxWindSpeed', 'windSpeed')))),
            'dir': int(round(nul(_pak(r, 'windDir', 'windDirection')))),
        })
    if not uit:
        raise RuntimeError('geen bruikbare dagen na veldkoppeling')
    return uit


# --------------------------------------------------------------------------
# Afgeleiden: dagindeling en fietsvenster
# --------------------------------------------------------------------------

def uurreeksen(hourly):
    per_dag = defaultdict(dict)
    for i, t in enumerate(hourly['time']):
        per_dag[t[:10]][int(t[11:13])] = {
            't': hourly['temperature_2m'][i], 'a': hourly['apparent_temperature'][i],
            'r': hourly['precipitation'][i], 'p': hourly['precipitation_probability'][i],
            'w': hourly['wind_speed_10m'][i], 'g': hourly['wind_gusts_10m'][i]}
    return per_dag


def fietsvenster(uren, sr, ss):
    """Beste aaneengesloten blok van minstens twee uur, absoluut vergeleken.

    Vergelijk je met de vorige kandidaat in plaats van met de beste tot dan toe, dan
    zakt de keuze stap voor stap weg naar een lang maar matig venster. Dat was een
    echte bug op 4 augustus 2026; vandaar de expliciete vergelijking met `beste`.
    """
    score = {}
    for h in range(sr + 1, ss):
        x = uren.get(h)
        if not x:
            continue
        t, a, r = nul(x['t']), nul(x['a']), nul(x['r'])
        p, w, g = nul(x['p']), nul(x['w']), nul(x['g'])
        if r >= 0.3 or p >= 55 or g >= 55:
            score[h] = None
            continue
        s = 100.0
        if t < 15:
            s -= (15 - t) * 5
        if t > 23:
            s -= (t - 23) * 6.5
        if a > 30:
            s -= (a - 30) * 4
        if w > 12:
            s -= (w - 12) * 3
        if g > 32:
            s -= (g - 32) * 1.8
        s -= p * 0.35
        score[h] = s

    bruikbaar = sorted(h for h in score if score[h] is not None)
    beste = None
    for i in range(len(bruikbaar)):
        for j in range(i + 1, len(bruikbaar)):
            if bruikbaar[j] != bruikbaar[j - 1] + 1:
                break
            van, tot = bruikbaar[i], bruikbaar[j]
            lengte = tot - van + 1
            if lengte < 2:
                continue
            blok = [score[h] for h in range(van, tot + 1)]
            rang = sum(blok) / len(blok) + min(lengte, 5) * 1.2
            if beste is None or rang > beste[0]:
                temps = [nul(uren[h]['t']) for h in range(van, tot + 1)]
                winden = [nul(uren[h]['w']) for h in range(van, tot + 1)]
                beste = (rang, van, tot + 1, round(sum(blok) / len(blok)),
                         round(sum(temps) / len(temps), 1), round(sum(winden) / len(winden), 1))
    if not beste:
        return None
    return {'van': beste[1], 'tot': beste[2], 'score': beste[3], 't': beste[4], 'w': beste[5]}


def dagsoort(tmax, regen, code):
    if regen >= 3 or code in BINNEN_CODES:
        return 'binnen'
    if tmax >= 32:
        return 'water'
    if tmax >= 28:
        return 'warm'
    if tmax < 24:
        return 'fris'
    return 'uitstap'


# --------------------------------------------------------------------------
# JS-tekst opbouwen
# --------------------------------------------------------------------------

def getal(v, dec=1):
    return f'{v:.{dec}f}' if isinstance(v, float) else str(v)


def reeks(uren, sleutel, dec=1):
    out = []
    for h in range(24):
        v = uren.get(h, {}).get(sleutel)
        v = 0 if v is None else v
        out.append(round(v, dec) if dec else int(round(v)))
    return '[' + ','.join(getal(v, dec) for v in out) + ']'


def js_days(dagen):
    return ',\n'.join(
        "      {{ d:'{d}', tmax:{tmax:.1f}, tmin:{tmin:.1f}, rain:{rain:.1f}, pop:{pop}, "
        "wind:{wind:.1f}, gust:{gust}, dir:{dir} }}".format(**r) for r in dagen)


def js_mf(rijen):
    return ',\n'.join("      {{ d:'{d}', tmax:{tmax:.1f} }}".format(**r) for r in rijen)


def js_air(hourly, vandaag):
    piek = defaultdict(lambda: defaultdict(float))
    for i, t in enumerate(hourly['time']):
        for k in ('pm10', 'pm2_5', 'european_aqi', 'ozone'):
            v = hourly[k][i]
            if v is not None:
                piek[t[:10]][k] = max(piek[t[:10]][k], v)
    return ',\n'.join(
        "      {{ d:'{}', pm25:{:.1f}, pm10:{:.1f}, aqi:{}, o3:{:.1f}, past:{} }}".format(
            d, piek[d]['pm2_5'], piek[d]['pm10'], round(piek[d]['european_aqi']),
            piek[d]['ozone'], 'true' if d < vandaag else 'false')
        for d in sorted(piek))


def js_plan(daily, per_dag):
    regels = []
    for i, d in enumerate(daily['time']):
        tmax = daily['temperature_2m_max'][i]
        if tmax is None:
            continue
        regen = nul(daily['precipitation_sum'][i])
        code = int(nul(daily['weather_code'][i]))
        sr = int(daily['sunrise'][i][11:13])
        ss = int(daily['sunset'][i][11:13])
        uren = per_dag.get(d, {})
        b = fietsvenster(uren, sr, ss)
        bike = 'null' if not b else '{{van:{van},tot:{tot},score:{score},t:{t},w:{w}}}'.format(**b)
        regels.append(
            "    {{ d:'{}', sr:{}, ss:{}, kind:'{}', code:'{}', bike:{},\n"
            "      th:{}, ah:{}, wh:{}, rh:{} }}".format(
                d, sr, ss, dagsoort(tmax, regen, code), CODE.get(code, 'wisselend bewolkt'),
                bike, reeks(uren, 't'), reeks(uren, 'a'),
                reeks(uren, 'w', 0), reeks(uren, 'r')))
    return ',\n'.join(regels)


# --------------------------------------------------------------------------
# De pagina herschrijven
# --------------------------------------------------------------------------

def vervang(bron, aanhef, inhoud, inspring):
    """Vervangt de lijst achter `aanhef` door `inhoud`, door haakjes te tellen.

    Zo blijft dit werken als er records bij komen of als de opmaak verschuift --
    veiliger dan zoeken naar een vaste eindregel.
    """
    i = bron.index(aanhef) + len(aanhef)
    diepte, j = 1, i
    while diepte:
        if bron[j] == '[':
            diepte += 1
        elif bron[j] == ']':
            diepte -= 1
        j += 1
    return bron[:i] + '\n' + inhoud + '\n' + inspring + bron[j - 1:]


def main():
    nu = datetime.now(timezone.utc).astimezone(timezone(timedelta(hours=2)))
    vandaag = nu.strftime('%Y-%m-%d')
    log(f'== Weerupdate {nu:%Y-%m-%d %H:%M} ==')

    # Vakantie voorbij? Dan niets meer doen.
    if vandaag > '2026-08-22':
        log('De vakantie is voorbij (na 22 augustus 2026). Niets te doen.')
        return 0

    try:
        om = haal_openmeteo()
        lucht = haal_lucht()
    except (urllib.error.URLError, OSError, ValueError) as e:
        log(f'FOUT: Open-Meteo niet bereikbaar ({e}). Pagina ongewijzigd gelaten.')
        return 1
    log(f'   Open-Meteo: {len(om["daily"]["time"])} dagen')

    daily = om['daily']
    om_dagen = [{
        'd': t, 'tmax': daily['temperature_2m_max'][i], 'tmin': daily['temperature_2m_min'][i],
        'rain': nul(daily['precipitation_sum'][i]),
        'pop': int(nul(daily['precipitation_probability_max'][i])),
        'wind': daily['wind_speed_10m_max'][i],
        'gust': int(round(daily['wind_gusts_10m_max'][i])),
        'dir': int(round(daily['wind_direction_10m_dominant'][i]))}
        for i, t in enumerate(daily['time']) if daily['temperature_2m_max'][i] is not None]

    # Foreca als hoofdreeks, maar alleen als het echt lukt.
    bron, hoofd, foreca_dagen = 'open-meteo', om_dagen, []
    user, pw = os.environ.get('FORECA_USER'), os.environ.get('FORECA_PASSWORD')
    if user and pw:
        try:
            foreca_dagen = haal_foreca(user, pw)
            hoofd, bron = foreca_dagen, 'foreca'
            log(f'   Foreca is de hoofdreeks ({len(foreca_dagen)} dagen)')
        except Exception as e:                       # noqa: BLE001 - elke storing is terugval
            log(f'   LET OP: Foreca faalde ({e}). Open-Meteo blijft de hoofdreeks.')
    else:
        log('   Geen FORECA_USER/FORECA_PASSWORD gezet; Open-Meteo is de hoofdreeks.')

    try:
        mf = haal_meteofrance()
        log(f'   Météo-France: {len(mf)} dagen')
    except Exception as e:                           # noqa: BLE001 - controlelijn is optioneel
        log(f'   Météo-France overgeslagen ({e})')
        mf = []

    # Open-Meteo is nu een controlelijn zodra Foreca de hoofdreeks levert.
    om_lijn = [{'d': r['d'], 'tmax': r['tmax']} for r in om_dagen] if bron == 'foreca' else []

    pagina = open(PAGINA, encoding='utf-8').read()
    pagina = vervang(pagina, 'days: [', js_days(hoofd), '    ')
    pagina = vervang(pagina, 'mf: [', js_mf(mf), '    ')
    pagina = vervang(pagina, 'om: [', js_mf(om_lijn), '    ')
    pagina = vervang(pagina, 'air: [', js_air(lucht, vandaag), '    ')
    pagina = vervang(pagina, 'const PLAN = [', js_plan(daily, uurreeksen(om['hourly'])), '  ')

    stempel = f'{nu.day} {MAANDEN[nu.month - 1]}, {nu:%H:%M}'
    pagina = re.sub(r"fetchedAt: '[^']*'", f"fetchedAt: '{nu.isoformat(timespec='seconds')}'", pagina, count=1)
    pagina = re.sub(r"source: '[^']*'", f"source: '{bron}'", pagina, count=1)
    pagina = re.sub(r"const STAMP = '[^']*';", f"const STAMP = '{stempel}';", pagina, count=1)

    open(PAGINA, 'w', encoding='utf-8').write(pagina)

    warm = [r for r in hoofd if r['tmax'] >= 34]
    log(f'   Geschreven. Hoofdbron: {bron}. Dagen >= 34 graden: {len(warm)}'
        + (f", warmste {max(r['tmax'] for r in hoofd):.1f}" if hoofd else ''))
    return 0


if __name__ == '__main__':
    sys.exit(main())
