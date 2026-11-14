# Tradera integration plan

Status: researched; **not connected yet**. No Tradera credentials have been obtained or deployed.

## Verified API
- Developer registration: https://api.tradera.com/register.aspx
- REST v4 docs: https://api.tradera.com/documentation/rest-getting-started
- Search: GET /v4/search, POST /v4/search/advanced
- Item details: GET /v4/items/{itemId}
- All calls require X-App-Id and X-App-Key. Read-only searches need no user authorization.
- Tradera documents a default 10,000 calls / 24 hours / method (subject to change).
- Developer terms permit search, discovery, alerts, and analytics, but prohibit automated bidding and auction sniping.

## Architecture
1. User creates a generic Spotter with a query, expected resale price, and minimum ROI (20% default).
2. A scheduled server-side job calls Tradera v4 search using app credentials stored as GitHub Actions secrets (never in public repo or browser).
3. Normalize listings: id, title, URL, auction/fixed-price type, current price, shipping when available, end time, currency, image, seller, fetched timestamp.
4. Store snapshots as generated static JSON on a deployable branch/artifact, not secrets. De-duplicate by item ID.
5. Frontend loads JSON and filters by Spotter. Note that current Spotters live only in each browser's localStorage; server-side searches for personal Spotters require a sync mechanism or a fixed/shared watchlist. Choose sync design before implementation.
6. Convert SEK/DKK with dated rates; treat unknown shipping and auction final prices as uncertain. Compute total cost, expected profit, and ROI; only show qualifying listings when sufficient data exists.
7. Display source links and last updated time. No bidding, purchasing, or notifications until separately designed and approved.

## Next blocking step
Register a Tradera developer application and obtain App ID and App Key. Store them as GitHub repository Actions secrets; never commit or paste the key in public files. Once available, build a read-only proof of concept and test real listings.
