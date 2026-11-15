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

## Status
Flipit has a live GitHub Pages web app with Tradera listing synchronization and resale-profit tools. Some listing galleries and seller descriptions may still be incomplete; these paths require regression testing.

## Release checklist
- Confirm Tradera listing galleries and seller descriptions are preserved across sync runs.
- Check the deals view on narrow mobile screens and desktop.
- Verify profit and ROI calculations with purchase price, shipping, and selling fees.
- Test online refresh and offline fallback for the installed web app.
- Prefer small, reversible changes and verify the published site after deployment.

Development tracking: [Flipit quality issue #2](https://github.com/Atomicnumber36/marginspotter/issues/2).

## Website

The GitHub Pages deployment workflow runs on pushes to main. Public site: https://atomicnumber36.github.io/marginspotter/
