# Retailer investigation — Phase 2

Investigation date: 2026-08-02 (Australia/Sydney). Only Umart is implemented.

## LG Australia — rejected

- `https://www.lg.com/au/robots.txt` could not be reliably retrieved by the
  investigation tooling.
- LG's current LGE Service Terms of Use say users must not collect data or
  information from the LGE Service or its system.
- LG's Australian legal notice restricts storing, copying, distributing, or
  transmitting site information without express written consent.
- Decision: do not collect. The terms evidence is prohibitive regardless of
  technical product-page availability.

Evidence:

- https://www.lg.com/au/lge-terms/
- https://www.lg.com/au/legal/
- https://www.lg.com/au/terms-and-conditions-of-sale/

## Computer Alliance — not selected

- `robots.txt` returned HTTP 200 and allows ordinary product URLs while blocking
  cart actions, administration, and WooCommerce operational paths.
- A candidate product page returned HTTP 200 static HTML (697,300 bytes) with
  two JSON-LD blocks and visible model, price, stock, and warranty.
- Its Terms of Service grant personal, non-commercial site use and prohibit all
  other uses without prior written consent. A public comparison dashboard is not
  clearly within that grant.
- Decision: do not infer permission; do not implement.

Evidence:

- https://www.computeralliance.com.au/robots.txt
- https://www.computeralliance.com.au/policies/terms-of-service/
- https://www.computeralliance.com.au/32-lg-ultragear-32gr93u-b-uhd-144hz-ips-gaming-monitor

## Centre Com — rejected technically

- Search-index evidence exposed relevant product and terms pages.
- Direct static requests to both `robots.txt` and a public catalog page returned
  an AWS WAF human-verification CAPTCHA.
- Decision: no bypass, CAPTCHA solving, browser automation, or collector.

Evidence:

- https://www.centrecom.com.au/robots.txt
- https://www.centrecom.com.au/terms

## Umart — selected

- `robots.txt` is plain text and permits clean `/product/...` URLs. It expressly
  disallows cart, checkout, login, search, affiliate, account-like, and numerous
  parameterized paths. The configured URL does not match a disallow rule.
- Published Terms and Conditions cover browsing and purchasing. Searches of the
  current terms found no prohibition using the terms robot, automated, scrape,
  or data mining. This is not treated as blanket permission: collection remains
  narrow, low-rate, read-only, and subject to future policy review.
- The clean U3225QE product URL returned HTTP 200, UTF-8 HTML, 552,874 bytes.
  It contains one schema.org `Product` JSON-LD object with exact `mpn`, AUD
  price, schema.org condition and availability, canonical offer URL, and an AU
  shipping destination. Visible static text provides the warranty period.
- The smoke command makes one product request, identifies itself, validates
  content type and size, uses a 15-second timeout, and permits at most one retry
  for 429/5xx only. It stops cleanly on access controls or malformed data.

Evidence:

- https://www.umart.com.au/robots.txt
- https://www.umart.com.au/corporate/help/terms-conditions-1076
- https://www.umart.com.au/product/dell-ultrasharp-32in-4k-ips-120hz-thunderbolt-hub-monitor-u3225qe-84809

## Maintenance risk

Robots rules, terms, HTML, structured data, stock wording, and access controls
can change without notice. Review this evidence before enabling automation and
disable the collector immediately if policy or access behavior becomes unclear.
