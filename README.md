# Flipit

A mobile-first app for spotting resale opportunities across marketplaces.

## MVP
- Add and manage products (name, platform, region, condition).
- Manually enter reference prices for loose and complete-in-box (CIB), with last-updated date.
- Calculate maximum purchase price and expected return after shipping and selling fees.
- Flag listings with at least 20% expected return on total invested cost.
- Start with manual listing entry; integrate Tradera only after confirming permitted, reliable access.

## Profit formula
Expected profit = expected resale price - selling costs - purchase price - inbound shipping.
ROI = expected profit / (purchase price + inbound shipping).

PriceCharting figures are reference estimates, not guaranteed Danish resale prices. Use conservative estimates and verify region, authenticity and condition.

## Current development status
Flipit has an implemented GitHub Pages website and Tradera synchronization work. The earlier MVP-only status text was outdated. Reliability of complete listing descriptions, image galleries, and responsive layout remains under review; do not assume these are fully verified.

## Quality checklist before deployment
- Verify Tradera listing details: seller description and full image gallery, including listings initially seen with one image.
- Confirm subsequent sync runs preserve previously fetched rich details rather than replacing them with empty or partial search-result fields.
- Check gallery navigation and image centering on narrow mobile and desktop screens.
- Verify purchase price, market value, fees, expected profit, and ROI remain unchanged after UI edits.
- Keep visual changes small and reversible, with review before merging into `main`.

Track work in [issue #2](https://github.com/Atomicnumber36/marginspotter/issues/2).

## Website

The GitHub Pages deployment workflow runs on pushes to main. Public site: https://atomicnumber36.github.io/marginspotter/
