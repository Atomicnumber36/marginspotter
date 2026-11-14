# Connect Tradera to MarginSpotter

The frontend, public JSON feed, scheduled read-only fetcher, and GitHub workflow are committed. **No live data has been fetched or verified.**

1. Register at https://api.tradera.com/register and create an app.
2. In GitHub repository Settings → Secrets and variables → Actions, create two repository secrets named `TRADERA_APP_ID` and `TRADERA_APP_KEY`. Never paste keys into source or public issues.
3. Edit `config/tradera-watchlist.json` to contain a few shared searches, e.g. `{"queries":["Pokémon Blue","iPhone 13"]}`. **This is a public shared watchlist**, not yet automatically synchronized from personal Spotters in browser localStorage.
4. Run the `Sync Tradera listings` workflow manually under Actions, inspect the run and generated feed. The workflow is also scheduled every six hours.
5. Verify API search parameter and response normalization against live v4 responses, which may change because v4 is beta. In particular, `scripts/tradera_sync.py` currently uses a provisional `query` parameter and conservative response field mapping; adapt to official OpenAPI schema before treating the connector as production-ready.
6. The frontend currently lists fetched results; automatic matching to each private Spotter, SEK→DKK conversion, shipping verification, ROI qualification and notifications remain to implement. Never assume an auction's current bid is its final purchase price.

The GitHub Actions workflow needs permission to write repository contents for automatic feed commits; check Settings → Actions → General → Workflow permissions if push is denied. This repository is public, so all feed data and shared searches are public. No secrets are written into the feed.
