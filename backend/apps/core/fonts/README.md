# Embedded PDF fonts

- **Inter** (400/500/600/700) — body text, tables, figures
- **Outfit** (600/700/800) — document titles and headings

Both are licensed under the SIL Open Font License 1.1 (https://openfontlicense.org),
which permits bundling and embedding in generated documents. Source: Google Fonts.

`apps/core/pdf.py` registers them with ReportLab at import time and falls back to
Helvetica if the files are missing.
