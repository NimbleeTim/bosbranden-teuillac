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

Probeer eerst `curl` vanuit Bash:

```bash
curl -s --max-time 25 "https://api.open-meteo.com/v1/forecast?latitude=45.09289&longitude=-0.54756&daily=temperature_2m_max,temperature_2m_min,precipitation_sum,precipitation_probability_max,wind_speed_10m_max,wind_gusts_10m_max,wind_direction_10m_dominant&timezone=Europe%2FParis&forecast_days=16"

curl -s --max-time 25 "https://air-quality-api.open-meteo.com/v1/air-quality?latitude=45.09289&longitude=-0.54756&hourly=pm10,pm2_5,european_aqi,ozone&timezone=Europe%2FParis&past_days=7&forecast_days=5"
```

> **Let op — dit faalde op 3 én 4 augustus.** De cloud-sandbox blokkeert uitgaand
> verkeer vanuit Bash naar `api.open-meteo.com`. Krijg je een timeout of een leeg
> antwoord, ga dan **niet** verder met verouderde cijfers, maar val terug op
> **WebFetch** met exact dezelfde URL. Dat is op 4 augustus getest en het **werkt** —
> WebFetch loopt langs een andere route dan de sandbox. Sla die stap niet over. Vraag in de prompt om de dagreeksen letterlijk terug te geven, bijvoorbeeld:
> *"Give me the complete `daily` arrays as JSON: time, temperature_2m_max,
> temperature_2m_min, precipitation_sum, precipitation_probability_max,
> wind_speed_10m_max, wind_gusts_10m_max, wind_direction_10m_dominant. Return raw
> numbers, all 16 days, no commentary."*
>
> Lukt ook dat niet, laat `DATA.days` en `DATA.air` dan ongemoeid en **zeg
> uitdrukkelijk in de statusregel én in je samenvatting dat de meetcijfers van een
> eerdere datum zijn.** Nooit stilzwijgend oude cijfers als nieuw presenteren.

Voor luchtkwaliteit: neem per dag het **maximum** van elke uurreeks.

Haal daarnaast de **uurdata** op — die voedt de dagindeling en de fietsvensters:

```bash
curl -s --max-time 25 "https://api.open-meteo.com/v1/forecast?latitude=45.09289&longitude=-0.54756&hourly=temperature_2m,apparent_temperature,precipitation,precipitation_probability,wind_speed_10m,wind_gusts_10m&daily=temperature_2m_max,temperature_2m_min,precipitation_sum,precipitation_probability_max,wind_speed_10m_max,wind_gusts_10m_max,wind_direction_10m_dominant,sunrise,sunset,weather_code&timezone=Europe%2FParis&forecast_days=16"
```

Gebruik **deze ene call** voor zowel `DATA.days` als `PLAN`, zodat dag- en uurcijfers
uit dezelfde modelrun komen. Velden kunnen `null` zijn in de laatste dagen — vang dat af.

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

- **`PLAN`** — één record per dag, voedt de dagindeling en het uurdetail. Velden:
  `d`, `sr`/`ss` (uur van zonop/onder), `kind`, `code` (weertype in het Nederlands),
  `bike`, en de uurreeksen `th` (temperatuur), `wh` (wind), `rh` (regen), elk 24 lang.

  `kind` bepaal je zo, in deze volgorde: `binnen` als regen ≥ 3 mm of weather_code in
  61/63/65/80/81/82/95/96/99; anders `water` bij tmax ≥ 32; `warm` bij ≥ 28;
  `fris` bij < 24; anders `uitstap`.

  `bike` is het beste aaneengesloten blok van **minstens twee uur** tussen
  zonsopgang + 1 u en zonsondergang − 1 u. Score per uur: start op 100, en
  onberijdbaar (`null`) bij regen ≥ 0,3 mm, buienkans ≥ 55 % of stoten ≥ 55 km/h.
  Aftrek: `(15 − t) × 5` onder 15 °C, `(t − 23) × 6,5` boven 23 °C,
  `(gevoelstemp − 30) × 4` boven 30, `(wind − 12) × 3` boven 12 km/h,
  `(stoten − 32) × 1,8` boven 32, en `buienkans × 0,35`.
  Kies het venster met de hoogste **`gemiddelde score + min(lengte, 5) × 1,2`**.
  Vergelijk altijd absoluut tegen het beste tot dan toe — vergelijk je met de vórige
  kandidaat, dan zakt de keuze stap voor stap weg naar een lang, matig venster.
  Dat was een echte bug op 4 augustus.

**De planner niet vereenvoudigen.** Het tabblad *Planning* deelt activiteiten uit over
de verblijfsdagen. Regels die moeten blijven gelden:

- Alleen dagen van **8 t.e.m. 22 augustus**, en alleen vanaf vandaag.
- Op de **aankomstdag (8 aug)** en de **terugreisdag (22 aug)** wordt niets ingepland.
  Dat is een expliciete wens van Tim, geen omissie.
- Dagen waarvoor het model nog niet reikt, tonen "Nog geen verwachting" — geen
  verzonnen invulling.
- Elke activiteit komt **maximaal één keer** in de hele planning voor.
- Afgevinkte activiteiten (`localStorage`-sleutel `teuillac-gedaan`) vallen weg uit de
  planning. Raak die sleutel niet aan; die is van Tim.
- De knop **Andere planning** verhoogt `planSeed` en deelt opnieuw uit.

Wil je activiteiten toevoegen, doe dat in de `ACTIVITIES`-pool met een `past`-lijst van
dagtypes waarvoor ze deugen. Voeg niets toe dat je niet in een bron hebt gezien.

**Het toonvenster mag je niet weghalen.** De grafieken, de windtabel en de dagbalk
tonen bewust alleen dagen vanaf vandaag tot en met 22 augustus (`windowed()` in het
script). Gepasseerde dagen vallen weg, zodat er vanaf 8 augustus vanzelf enkel nog de
vakantieperiode overblijft. Vul `DATA.days` en `DATA.air` dus gewoon met de volledige
reeks uit de API — het filteren gebeurt bij het renderen. Let er wel op dat teksten
over "hete dagen" of "regen in 16 dagen" over de **volledige** reeks gaan; herbereken
die uit `DATA`, niet uit wat je op het scherm ziet.

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

**Over het delen: raak het Share-menu niet aan.** Een publiek gedeeld artifact wordt
vastgepind op de versie van het moment van delen; `Latest` kiezen is geblokkeerd zolang de
toegang publiek staat, en de Artifact-tool heeft geen parameter om dat recht te zetten. Het
artifact is daarom alleen nog Tims eigen weergave — hij is eigenaar en ziet altijd de
nieuwste versie. **De publieke link loopt via GitHub Pages** (stap 6), en die is de reden
dat de push nu wél moet lukken.

### 6. Push — dit is de publieke link

```bash
git add -A
git commit -m "Dagelijkse update: <datum>"
git push
```

**Deze stap mag niet stilzwijgend mislukken.** De repo staat op GitHub Pages:

- Publieke link: <https://nimbleetim.github.io/bosbranden-teuillac/>
- Bron: branch `main`, map `/` van `NimbleeTim/bosbranden-teuillac`

`index.html` is een vaste laadschil die `vakantie-status-teuillac.html` ophaalt en
uitvoert. **Jij hoeft `index.html` niet aan te raken** — één bronbestand, geen tweede
kopie die uit de pas kan lopen. Alleen jouw push maakt de publieke pagina vers; zonder
push blijft iedereen die de link opent op de vorige dag hangen.

Bij de testruns van 3 en 4 augustus faalde de push — de cloud-sessie had de repo
alleen-lezen. Lukt het nu weer niet, probeer dan in deze volgorde:

```bash
git push          # eerst gewoon dit
gh auth status    # geen push? kijk of de sessie überhaupt een token heeft
```

Heeft `gh` wél een token maar git niet, schrijf het bestand dan via de contents-API.
Niet met `base64` op de commandoregel — dat loopt stuk op de lengte, en de `-i`-vlag
betekent iets anders op Linux dan op macOS. Bouw de payload met `node`:

```bash
REPO=NimbleeTim/bosbranden-teuillac
PAD=vakantie-status-teuillac.html
node -e '
const fs = require("fs");
process.stdout.write(JSON.stringify({
  message: "Dagelijkse update: " + process.argv[1],
  branch: "main",
  sha: process.argv[2],
  content: fs.readFileSync(process.argv[3]).toString("base64"),
}));' "<datum>" "$(gh api repos/$REPO/contents/$PAD --jq .sha)" "$PAD" > payload.json
gh api -X PUT "repos/$REPO/contents/$PAD" --input payload.json
```

Lukt geen van beide, **zeg dan in je samenvatting met zoveel woorden dat de publieke
pagina op de oude dag is blijven staan** en waarom. Dat is geen detail: dan klopt wat
anderen zien niet met wat jij gepubliceerd hebt. Ga niet forceren en probeer geen
andere remote.

## Toon

Nederlands, direct, geen marketingtaal. Tim wil weten wat er echt aan de hand is, inclusief
wat je níét kon verifiëren. Als de situatie verbetert, zeg dat; als ze verslechtert, ook.
Vermeld expliciet wanneer iets sinds de vorige update is veranderd — dat is de reden dat
deze pagina dagelijks herbouwd wordt.
