# Dagelijkse update van het vakantiedashboard

Dit bestand is de werkinstructie voor de geplande cloud-agent. Volg het letterlijk.

## Context

Tim en zijn gezin (2 kinderen, 3 en 4,5 jaar) verblijven **8 t.e.m. 22 augustus 2026**
in **La Vigne d'Or, 40 chemin de Peublanc, 33710 Teuillac** (Gironde, Frankrijk).
Coördinaten: **45.09289 N, -0.54756 O**. Arrondissement Blaye, rechteroever van het
Gironde-estuarium.

In juli 2026 woedde een megabrand in het Landes-de-Gascogne-massief west/zuidwest van
Bordeaux (42.000 ha). Het dashboard beantwoordt één vraag: **wat betekent dit voor deze
vakantie?**

Het dashboard is `vakantie-status-teuillac.html` in deze repo.

## Stop-conditie

**Doe niets meer na 22 augustus 2026.** Als de huidige datum later is dan 22 augustus 2026,
publiceer niets, commit niets, en meld enkel dat de vakantie voorbij is.

## Stappen

### 1. Haal verse meetdata op

```bash
curl -s "https://api.open-meteo.com/v1/forecast?latitude=45.09289&longitude=-0.54756&daily=temperature_2m_max,temperature_2m_min,precipitation_sum,precipitation_probability_max,wind_speed_10m_max,wind_gusts_10m_max,wind_direction_10m_dominant&timezone=Europe%2FParis&forecast_days=16"

curl -s "https://air-quality-api.open-meteo.com/v1/air-quality?latitude=45.09289&longitude=-0.54756&hourly=pm10,pm2_5,european_aqi,ozone&timezone=Europe%2FParis&past_days=7&forecast_days=5"
```

Voor luchtkwaliteit: neem per dag het **maximum** van elke uurreeks.

### 2. Zoek de actuele situatie op

Gebruik WebSearch/WebFetch. Controleer minstens:

| Wat | Bron |
|---|---|
| Brandstatus, evacuaties | `gironde.gouv.fr` → Communiqués de presse (nieuwste maand) |
| Vigilance-niveau brandrisico | `gironde.fr/actualites` — let op: noir(5) / rouge(4) / orange(3) |
| Luchtkwaliteit | `atmo-nouvelleaquitaine.org` |
| Toerisme, wat open/dicht is | `en-nouvelle-aquitaine.fr` |
| Lokale agenda Blaye/Bourg | `bbte.fr/agenda-manifestations/tout-lagenda/` |
| Dune du Pilat | `ladunedupilat.com` |

`gironde.gouv.fr` geeft geregeld time-outs. Probeer opnieuw of gebruik een tweede bron,
en **zet een expliciet voorbehoud in de pagina** als je iets niet kon verifiëren.

### 3. Werk het HTML-bestand bij

Alles wat verandert zit in het `<script>`-blok, behalve de lopende tekst.

- **`DATA.days`** — de 16 dagen uit de forecast-API. Velden: `d, tmax, tmin, rain, pop, wind, gust, dir`.
- **`DATA.air`** — dagelijkse maxima. Velden: `d, pm25, pm10, aqi, o3, past`.
  `past: true` voor dagen vóór vandaag.
- **`DATA.fetchedAt`** — ISO-tijdstip van deze update.
- **`const STAMP`** — leesbare stempel, bv. `'7 augustus, 07:30'`. Komt in de statusregel
  en in de fallback-melding van de refresh-knop.
- De statusregel in de header (`id="liveTxt"`) — zelfde datum als STAMP.
- **`RULES`** — als het vigilance-niveau of een besluit wijzigde.
- **`SCENARIOS`** — herweeg de percentages. **Ze moeten samen exact 100 zijn.**
- **`ATTRACTIONS`** — status `ok` / `part` / `chk` / `shut`; `stx` is het label.
  Gebruik `chk` + "Nabellen" als je géén recente bron vond. Verzin geen open-status.
- **`NEWS`** — vervang door de meest recente berichten met werkende URL's.
- De verdict-tekst (`id="verdictBody"`) en de tegels erin, als het verhaal wezenlijk wijzigde.

**De rookmeetkunde staat vast en mag je niet aanpassen:** Teuillac ligt op peiling **55°**
vanaf het brandzwaartepunt (44.88 N, -0.98 O), 41 km. Rook bereikt Teuillac alleen bij wind
**uit ± 235°**. De pagina rekent dat zelf uit uit `dir`; niet hardcoderen.

### 4. Controleer voor je publiceert

```bash
node -e '
const s=require("fs").readFileSync("vakantie-status-teuillac.html","utf8");
if(/<!doctype|<html[\s>]|<body[\s>]/i.test(s)) throw new Error("doctype/html/body mag niet");
for(const t of ["style","script","svg","div","table","section"]){
  const o=(s.match(new RegExp("<"+t+"[\\s>]","g"))||[]).length;
  const c=(s.match(new RegExp("</"+t+">","g"))||[]).length;
  if(o!==c) throw new Error("tag-onbalans: "+t+" "+o+"/"+c);
}
console.log("structuur ok,",s.length,"bytes");'
```

Controleer daarnaast met de hand:
- Scenario-percentages tellen op tot 100.
- Geen enkele externe subresource (`<link>`, `<script src>`, remote `<img>`, `@import`).
  De artifact-CSP blokkeert die en de pagina breekt stil.
- Geen `<!doctype>`, `<html>` of `<body>` — het publicatieplatform wikkelt dat er zelf omheen.

### 5. Publiceer naar dezelfde URL

Gebruik de Artifact-tool met **exact** deze parameters:

- `file_path`: `vakantie-status-teuillac.html`
- `url`: `https://claude.ai/code/artifact/a6032651-57d4-47ac-844f-0a5cb063b697`
- `favicon`: `🔥🧭`

De `url` is verplicht — zonder die parameter maak je een nieuwe link aan en dan raakt Tim
het dashboard kwijt dat hij op zijn gsm heeft staan.

### 6. Commit terug

```bash
git add -A
git commit -m "Dagelijkse update: <datum>"
git push
```

## Toon

Nederlands, direct, geen marketingtaal. Tim wil weten wat er echt aan de hand is, inclusief
wat je níét kon verifiëren. Als de situatie verbetert, zeg dat; als ze verslechtert, ook.
Vermeld expliciet wanneer iets sinds de vorige update is veranderd — dat is de reden dat
deze pagina dagelijks herbouwd wordt.
