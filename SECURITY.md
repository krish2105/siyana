# Security

- **Reporting.** Open a private security advisory on GitHub (Security → Advisories → Report a vulnerability). Do not file public issues for vulnerabilities.
- **Secrets.** None are committed. Configuration comes from `.env` (see `.env.example`) and host environment variables. The Anthropic key is server-side only.
- **Authentication.** Set `SIYANA_API_KEY` on the API host and every mutating route (`/daleel/cards/*`, `/daleel/signatures/*/draft`, `/ajal/schedule/solve`, `/nazar/inspect`) requires the `X-SIYANA-KEY` header. Unset means an open demo deployment; `/health/ready` reports which mode is active.
- **Rate limits.** `/daleel/judge` (20/min) and `/nazar/inspect` (10/min) per client IP.
- **Data.** Snag text is de-identified (registrations, dates, work orders, names) before it is embedded or sent to the LLM judge. Raw text is retained in the database so auditors can trace a card to its source entry; treat the database as confidential in a customer deployment.
- **Approvals.** Licence numbers are stored with each decision by design; they are the audit trail.
