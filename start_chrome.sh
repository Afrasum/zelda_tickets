#!/bin/sh
# Opens a separate Chrome window (own profile, so it does not touch your normal
# Chrome) that bot.py can control. Log in to biljetter.konserthuset.se in THIS
# window. The profile is kept in ./chrome-profile, so the login persists.
DIR="$(cd "$(dirname "$0")" && pwd)"
exec "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" \
  --user-data-dir="$DIR/chrome-profile" \
  --remote-debugging-port=9222 \
  --no-first-run --no-default-browser-check \
  "https://www.konserthuset.se/en/programme/calendar/concert/2027/the-legend-of-zelda-40th-anniversary-concert/20270619-1500/" \
  >/dev/null 2>&1 &
