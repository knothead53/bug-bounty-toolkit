# Recon Report — example.com

**Generated at (UTC):** 2025-09-22T20:58:29.162651Z

## Scope
- Main domain: `example.com`


---

## Passive: crt.sh subdomains (10)


Subdomains discovered via certificate transparency (crt.sh):

- `as207960 test intermediate - example.com`

- `dev.example.com`

- `example.com`

- `m.example.com`

- `m.testexample.com`

- `products.example.com`

- `subjectname@example.com`

- `support.example.com`

- `user@example.com`

- `www.example.com`



---

## Notes / Next steps (manual)
1. Validate the live hosts (HTTP/HTTPS) with `httpx` or `curl` (manual or safe automation).
2. For hosts in-scope, run non-invasive service enumeration (nmap -sV --version-light) with permission.
3. Import findings into Burp Suite for manual inspection and active testing (only with explicit permission).
4. Keep a strict timeline of every action including command used, date/time, and who authorized the test.

---

## Evidence
- Scope JSON and raw outputs are saved in the output directory.