# La Sapinière — animatieprogramma

Zelfstandige repository. Geen afhankelijkheid van de review- of Quality-repository.

## Werking

- Recreatheek levert Nederlands en Frans. OpenAI vertaalt de Nederlandse tekst naar Engels en Duits.
- Een controle op minuut 17 van ieder uur haalt de planning op. Alleen nieuwe of gewijzigde teksten worden vertaald; dezelfde tekst op een andere datum wordt hergebruikt.
- Titel, uitleg en locatie worden vertaald. Activiteitcodes, afbeeldingen, leeftijden en tijden worden niet door AI gewijzigd.
- Voor bezoekers staan kleine, vooraf gemaakte JSON-bestanden op GitHub Pages. Er is geen AI-aanroep, vertaalserver of grote bibliotheek in hun browser.
- De browser laadt alleen de gekozen taal en maximaal gisteren tot zeven dagen vooruit. De server bewaart een extra bufferdag voor de datumwissel.
- Een lokale browsercache toont bij terugkeer de bewaarde planning direct; de nieuwste versie wordt op de achtergrond opgehaald.
- Bij een mislukte update blijft de vorige publicatie beschikbaar. Nieuwe of gewijzigde teksten krijgen nooit een oude, onjuiste vertaling. De browser meldt verouderde of offline gegevens.
- Gisteren wordt uit de vorige broncache behouden als de Recreatheek-feed die dag niet meer levert.
- GitHub kan geplande runs vertragen. Er is ook een handmatige knop bij Actions → Update cached animation programme → Run workflow. Bij 60 dagen zonder repository-activiteit kan GitHub openbare geplande workflows uitschakelen; controleer Actions bij een nieuw seizoen.

## Eenmalige inrichting

1. Voeg in **Settings → Secrets and variables → Actions** een repository secret `OPENAI_API_KEY` toe. Nooit in bestanden of BEX zetten.
2. Zet **Settings → Pages → Source** op **GitHub Actions**.
3. Start de workflow handmatig en controleer dat build en deploy slagen.
4. Vervang het volledige BEX-animatieblok door de inhoud van `docs/bex-code.txt`.

De code kiest automatisch de taal van de website (`html lang`). Optioneel kan op het div-element `data-language="nl"`, `"fr"`, `"en"` of `"de"` staan. De taalkeuze binnen het programma is altijd beschikbaar.

## Bestanden en kwaliteit

- `scripts/update_program.py`: bron importeren, gewijzigde teksten vertalen, compacte publicatie bouwen.
- `cache/translations.json`: permanent vertaalgeheugen, gekoppeld aan de exacte brontekst en woordenlijst.
- `cache/source.json`: recente brongegevens voor gisteren.
- `glossary.json`: vaste parktermen en herkenbare locatieaanduidingen.
- `overrides.json`: handmatig nagekeken vertalingen per tekstfingerprint en taal. Gebruik dezelfde velden als een vertaalgeheugenrecord; correcties blijven boven AI-uitvoer staan.
- `docs/data/*.json`: openbare taalbestanden.
- `docs/index.html`: werkend voorbeeld.
- `docs/bex-code.txt`: volledig BEX-codeblok.

Er worden maximaal 100 nieuwe tekstvarianten per run verwerkt, in groepen van 10, met maximaal drie pogingen per groep. Het model is configureerbaar via `OPENAI_MODEL`; de workflow gebruikt `gpt-5.4-mini`. API-gebruik kan kosten veroorzaken. Bij ongewijzigde tekst volgt geen nieuwe vertaaloproep.

De uitvoer wordt gecontroleerd op ontbrekende activiteiten, onverwachte velden, gewijzigde cijfers en leeftijdslabels. Dat garandeert geen perfecte taal: lees de eerste Engelse en Duitse reeks steekproefsgewijs na en bewaar gewenste correcties in `overrides.json`.

Deze repository bevat uitsluitend openbare activiteiten en broncode. Alleen `docs/` wordt gepubliceerd. Sleutels blijven in GitHub Secrets; providerantwoorden of sleutels worden nooit gelogd. Werkflows voor pull requests gebruiken geen sleutel en publiceren niet.

## Controle

```sh
python -m unittest discover -s tests -v
python -m py_compile scripts/update_program.py
```

Documentatie: [OpenAI Structured Outputs](https://developers.openai.com/api/docs/guides/structured-outputs), [GitHub Pages](https://docs.github.com/en/pages/getting-started-with-github-pages/using-custom-workflows-with-github-pages).

### Missing French source text

French titles and descriptions supplied by Recreatheek take priority. Blank fields are translated from the matching Dutch activity ahead of publication and saved in the existing translation memory. Only the missing fields are requested. Matching includes date, activity ID and start/end times. A changed Dutch field invalidates the cached repair; a later French source correction automatically replaces it. Raw imported French content remains unchanged in source history. Failed or unvalidated repairs leave the previous public feed available. No visitor request calls OpenAI and no BEX code change is needed.
