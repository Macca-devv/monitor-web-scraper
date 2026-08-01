# PLE Computers collector review

- Status: approved for bounded static collection
- Reviewed at: 2026-08-02 (Australia/Sydney)
- Review due: 2026-11-02, or immediately after a policy/page change
- Robots: <https://www.ple.com.au/robots.txt> (`User-agent: *`, `Allow: /`)
- Terms: <https://www.ple.com.au/TermsConditions>
- Product evidence: <https://www.ple.com.au/products/661692/lg-ultragear-32gr93u-b-32-4k-144hz-ips-monitor>
- Permitted path used: the single configured `/products/...` page
- Prohibited paths: none stated in robots.txt; private, account, cart and undocumented API paths are out of scope regardless
- Method: one GET of a configured public product page; parse schema.org Product/Offer JSON-LD, with visible warranty text only

The public terms reviewed are sales, warranty, privacy and returns terms. No language
prohibiting low-rate access to public product pages was found. This is not treated as
permission beyond the explicit robots allowance. The collector identifies itself,
caps the response at 2 MB, validates HTML content type, uses a 15-second timeout and
allows one bounded retry only after 429/5xx. CAPTCHA or access-control responses stop
collection.

Risks: terms and markup can change; JSON-LD does not itself state delivery cost. The
Australian-stock indicator is derived only from the configured established Australian
retailer selling its own inventory. Unknown delivery remains unknown and therefore the
effective price does not qualify if policy later requires delivered cost.
