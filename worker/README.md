# On-demand Tradera test (development)

The website creates Spotters locally. Creating a Spotter invokes searchSpotter(), but live requests remain disabled until a Worker URL is configured. No Tradera credentials are ever sent to the browser.

1. Deploy worker/src/index.js to a Cloudflare Worker.
2. Set Worker secret TRADERA_APP_KEY to the Tradera App Key. Set TRADERA_APP_ID=7762 and ALLOWED_ORIGIN to the exact GitHub Pages origin, e.g. https://atomicnumber36.github.io (without trailing slash).
3. In index.html, set SEARCH_ENDPOINT to the deployed Worker URL.
4. Create a Spotter on the website to trigger a read-only search. Check that Tradera accepts the request and returns items.

Important: This development endpoint has no user authentication. CORS is not an access-control mechanism against non-browser clients. Do not treat it as production-secure; add server-side rate limiting and access controls before exposing it broadly. Tradera response field mappings are provisional until a successful live test.

No scheduled or hard-coded queries are used by the on-demand path.
