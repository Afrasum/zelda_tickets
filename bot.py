"""Waits for the buy button on the Konserthuset concert page, then opens it in
the logged-in Chrome window (start_chrome.sh) and alerts you. It stops there:
you pick date/seats and pay yourself. It never opens extra tabs, never touches
a queue or captcha.

    uv run python bot.py                 # real run, release 13:00 today
    uv run python bot.py --test          # dry run against a concert on sale now
"""

import argparse
import datetime as dt
import os
import re
import subprocess
import sys
import time
import urllib.request

from playwright.sync_api import sync_playwright

ZELDA = ("https://www.konserthuset.se/en/programme/calendar/concert/2027/"
         "the-legend-of-zelda-40th-anniversary-concert/20270619-1500/")
TEST = ("https://www.konserthuset.se/en/programme/calendar/concert/2026/"
        "leonkoro-quartet/20261114-1600/")
CDP = "http://localhost:9222"
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/130 Safari/537.36")

FAST_FROM = 90        # seconds before release: switch to fast polling
FAST_EVERY = 1.5      # seconds between polls around release
SLOW_EVERY = 30       # seconds between polls before that (catches early release)
GIVE_UP_AFTER = 30    # minutes after release

A_TAG = re.compile(r"<a\b[^>]*>", re.I)
HREF = re.compile(r'href="(https://biljetter\.konserthuset\.se/[^"]*buyingflow/tickets/\d+/?)"', re.I)


def log(msg):
    print(f"[{dt.datetime.now():%H:%M:%S.%f}"[:-3] + f"] {msg}", flush=True)


def alert(title, msg, loud=True):
    subprocess.run(["osascript", "-e",
                    f'display notification "{msg}" with title "{title}" sound name "Glass"'])
    if loud:
        subprocess.Popen(["sh", "-c",
                          "for i in 1 2 3; do afplay /System/Library/Sounds/Glass.aiff; done; "
                          "say 'Billetter! Velg plass nå.'"])


def find_buy_link(html):
    """Main buy button for this date (data-track="buy-none"), else any buy link."""
    fallback = None
    for tag in A_TAG.findall(html):
        m = HREF.search(tag)
        if not m:
            continue
        if 'data-track="buy-none"' in tag:
            return m.group(1)
        fallback = fallback or m.group(1)
    return fallback


def fetch(url):
    sep = "&" if "?" in url else "?"
    req = urllib.request.Request(f"{url}{sep}_={int(time.time() * 1000)}",
                                 headers={"User-Agent": UA, "Cache-Control": "no-cache"})
    with urllib.request.urlopen(req, timeout=8) as r:
        return r.read().decode("utf-8", "replace")


def bot_page(p):
    """The existing tab in the bot Chrome (never opens a new one)."""
    browser = p.chromium.connect_over_cdp(CDP)
    pages = [pg for ctx in browser.contexts for pg in ctx.pages]
    if not pages:
        sys.exit("Chrome-vinduet har ingen faner. Åpne én og prøv igjen.")
    for pg in pages:
        if "konserthuset.se" in pg.url:
            return browser, pg
    return browser, pages[0]


def open_in_chrome(url):
    with sync_playwright() as p:
        browser, page = bot_page(p)
        page.bring_to_front()
        try:
            # 'commit' = return as soon as navigation starts; a queue page or a slow
            # site must not make us bail out. The tab keeps loading on its own.
            page.goto(url, wait_until="commit", timeout=20_000)
        except Exception as e:  # noqa: BLE001
            log(f"navigasjon rapporterte: {e!r} — siden laster sannsynligvis fortsatt")
        # No browser.close(): leaving the `with` block just drops the CDP
        # connection and leaves the user's Chrome (and the tab) as is.


def preflight():
    try:
        with sync_playwright() as p:
            browser, page = bot_page(p)
            log(f"Koblet til Chrome. Aktiv fane: {page.url}")
    except Exception as e:  # noqa: BLE001
        sys.exit(f"Får ikke kontakt med bot-Chrome på {CDP} ({e}).\n"
                 "Kjør ./start_chrome.sh først, og lukk andre Chrome-vinduer med samme profil.")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default=ZELDA, help="konsertsiden som skal overvåkes")
    ap.add_argument("--at", default="13:00", help="slipptid HH:MM (lokal tid)")
    ap.add_argument("--test", action="store_true",
                    help="tørrkjøring mot en konsert som er i salg nå, starter umiddelbart")
    a = ap.parse_args()

    url = TEST if a.test else a.url
    now = dt.datetime.now()
    if a.test:
        release = now
    else:
        h, m = map(int, a.at.split(":"))
        release = now.replace(hour=h, minute=m, second=0, microsecond=0)
        if release < now - dt.timedelta(minutes=GIVE_UP_AFTER):
            release += dt.timedelta(days=1)

    # Keep the Mac awake for as long as this script runs.
    subprocess.Popen(["caffeinate", "-dimsu", "-w", str(os.getpid())])

    preflight()
    log(f"Overvåker {url}")
    log(f"Slipp: {release:%Y-%m-%d %H:%M}. Rask polling fra {FAST_FROM}s før.")

    deadline = release + dt.timedelta(minutes=GIVE_UP_AFTER)
    last_note = None
    while dt.datetime.now() < deadline:
        left = (release - dt.datetime.now()).total_seconds()
        try:
            link = find_buy_link(fetch(url))
        except Exception as e:  # noqa: BLE001
            log(f"henting feilet: {e!r}")
            link = None

        if link:
            log(f"KJØPSLENKE FUNNET: {link}")
            open_in_chrome(link)
            alert("Zelda-billetter", "Kjøpssiden er åpen — velg dato/plass og betal!")
            log("Ferdig. Ta over i Chrome-vinduet: velg 19. juni, antall 1, plass, betal.")
            log("IKKE åpne en ny fane til billettsiden — Tixly kaster deg ut da.")
            return

        if left > FAST_FROM:
            minute = int(left // 60)
            if minute != last_note and (minute % 10 == 0 or minute <= 5):
                log(f"{minute} min igjen, ingen kjøpsknapp ennå")
                last_note = minute
            time.sleep(min(SLOW_EVERY, max(1, left - FAST_FROM)))
        else:
            time.sleep(FAST_EVERY)

    alert("Zelda-billetter", "Fant ingen kjøpsknapp — sjekk siden manuelt!")
    log("Ga opp etter fristen. Sjekk konsertsiden manuelt.")


if __name__ == "__main__":
    main()
