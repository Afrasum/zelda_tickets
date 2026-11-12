# zelda_tickets

En liten hjelper for billettslipp på **Konserthuset Stockholm** (billettsystemet er Tixly,
`biljetter.konserthuset.se`). Den kjøper **ikke** billetter for deg. Den gjør bare dette:

1. Overvåker konsertsiden og venter på at «Tickets»/«Buy»-knappen dukker opp ved slipp.
2. Åpner kjøpssiden i **ditt eget innloggede Chrome-vindu** i samme sekund.
3. Varsler med lyd + macOS-varsel + «Billetter!» (tale).

Deretter tar du over selv: velg dato, antall, sete og betal.

Laget for *The Legend of Zelda™ 40th Anniversary Concert*, 19. juni 2027 kl 15:00,
billettslipp **13. november 2026 kl 13:00**. Fungerer for alle konserter på konserthuset.se
(se `--url`).

> **Kun macOS.** Bruker Google Chrome, `afplay`, `osascript` og `caffeinate`.

## Hvordan det virker

- Konsertsiden (`konserthuset.se/en/programme/calendar/concert/...`) har ingen kjøpslenke før
  slipp. Ved slipp dukker det opp en lenke til
  `https://biljetter.konserthuset.se/en/buyingflow/tickets/<id>/`, som er hovedknappen med
  `data-track="buy-none"`. ID-en er ikke kjent på forhånd.
- `bot.py` henter konsertsidens HTML (vanlig HTTP, ingen nettleser). Den sjekker hvert 30.
  sekund frem til 10 sekunder før slipp, så **hvert 0,5 sekund** til 60 sekunder etter slipp
  (`--every` endrer dette), og deretter hvert 2. sekund. Svarer siden 403/429, pauser den i 5 sekunder. Når lenken finnes, styrer den den
  **eksisterende fanen** i bot-Chrome dit via Chrome DevTools Protocol (Playwright
  `connect_over_cdp`) og stopper.
- `start_chrome.sh` starter en **egen** Chrome med egen profil (`./chrome-profile`, gitignored)
  og `--remote-debugging-port=9222`. Din vanlige Chrome røres ikke, og innloggingen i
  bot-Chrome huskes mellom omstarter.
- Mens skriptet kjører, holder `caffeinate` Mac-en våken.

## Oppsett (gjør dette kvelden før)

Krever [uv](https://docs.astral.sh/uv/) og Google Chrome.

```sh
git clone <repo> zelda_tickets && cd zelda_tickets
uv sync                       # installerer playwright (ingen nettlesernedlasting trengs)
./start_chrome.sh             # åpner bot-Chrome på konsertsiden
```

1. **Lag konto / logg inn** på https://biljetter.konserthuset.se **i bot-Chrome-vinduet**.
   Innloggingen har reCAPTCHA, så det må gjøres for hånd og på forhånd.
2. **Tørrkjør** mot en konsert som er i salg nå:
   ```sh
   uv run python bot.py --test            # simulerer slipp om 20 sek
   ```
   Du skal se polling i terminalen, deretter hopper fanen til en kjøpsside og Mac-en sier
   «Billetter!». Ingenting reserveres, siden bare åpnes. Hvis testkonserten er over
   (`TEST` i `bot.py`), bytt den ut med en hvilken som helst konsert som har en «Buy ticket»-knapp.
3. Sjekk at klokka er riktig: `sntp time.apple.com` (avvik bør være < 0,1 s).

## På slippdagen

Rundt 12:30: lader i, lokket åpent, bot-Chrome åpen og innlogget.

```sh
uv run python bot.py                    # standard: Zelda 19. juni, slipp 13:00
```

Raskere eller roligere sjekking i slippvinduet (standard 0.5 s). Under ~0.3 s øker risikoen
for at Cloudflare struper deg akkurat når det gjelder:

```sh
uv run python bot.py --every 1
```

Andre konserter / tider:

```sh
uv run python bot.py --url "https://www.konserthuset.se/en/programme/calendar/concert/<...>/" --at 10:00
```

Når det ringer: gå til bot-Chrome, velg **riktig dato** (flere datoer kan dele samme kjøpsside),
antall, sete, og betal.

## Viktig

- **Ikke åpne kjøpssiden i en ny fane.** Tixly oppdager flere faner/vinduer, og da forsvinner
  setene du har valgt («It looks like you are using more than one window or tab…»).
- **Kø:** Tixly kan bruke Queue-it ved store slipp. Da får alle som venter når salget åpner
  vanligvis en tilfeldig plass i køen. Ingen bot kommer foran, og denne prøver heller ikke.
  Ser du en køside, la fanen være i fred og vent.
- Lukker du bot-Chrome-vinduet (rød knapp), kjører Chrome fortsatt i bakgrunnen uten vinduer.
  `bot.py` åpner da selv et nytt vindu på konsertsiden.
- **Reserveplan:** fungerer ikke skriptet, trykk «Tickets» på konsertsiden manuelt i
  bot-Chrome kl 13:00. Skriptet gir opp og varsler 30 min etter slipp hvis ingen knapp dukket opp.
- Tixlys vilkår kan forby automatiserte verktøy. Dette skriptet kjøper ikke, det bare
  åpner lenken. Bruk på eget ansvar, og kun for egne billetter.

## Filer

| Fil | Hva |
|-----|-----|
| `bot.py` | Overvåking, åpning av kjøpsside, varsling. `--test`, `--url`, `--at`, `--every`, `--in` |
| `start_chrome.sh` | Starter bot-Chrome (egen profil, debug-port 9222) |
| `chrome-profile/` | Bot-Chromes profil med innloggingen din (gitignored, ikke del den) |

## For Claude (hvis en venn setter dette opp med Claude Code)

- Kjør `uv sync`, deretter `./start_chrome.sh`. La brukeren logge inn selv (reCAPTCHA).
  Kjør så `uv run python bot.py --test` og bekreft med `curl -s localhost:9222/json/list` at
  fanen havnet på `biljetter.konserthuset.se/en/buyingflow/...`.
- Feilen `Browser context management is not supported` betyr at bot-Chrome kjører uten vinduer.
  `ensure_window()` i `bot.py` håndterer det. Hvis ikke: `./start_chrome.sh` på nytt.
- Port 9222 opptatt av noe annet? Endre port både i `start_chrome.sh` og `CDP` i `bot.py`.
- Ikke legg til automatisk kjøp, flere faner/sesjoner, ID-gjetting eller omgåelse av kø/CAPTCHA.
