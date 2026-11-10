# Client statements generator

Creates Support at Home monthly statements as PDFs, one per client, from two CSV files.
Runs on Windows, entirely on your own PC. No client data is sent anywhere.

## Quick start

1. Install Python 3.10 or later from python.org, then run `py -m pip install reportlab`.
2. Put your logo in `branding/logo.png` and your business details in `branding/provider.csv`.
3. Double-click `launch.pyw`, choose your clients and line items CSVs, and click **Create statements**.

PDFs are saved to `statements/`, named like `AC12345_Mary_Smith_2026-11_10-224527.pdf`.
See [SETUP.md](SETUP.md) for step-by-step instructions and troubleshooting.

## Files

| File | What it is |
|---|---|
| `launch.pyw` | Double-click to start the app |
| `app/sah_statement.py` | Builds the PDFs (also usable from the command line) |
| `app/sah_gui.py` | The app window |
| `branding/provider.csv` | Provider name, address, contacts and header colours |
| `branding/logo.png` | Provider logo, square, at least 300 x 300 pixels (not stored in the repo) |
| `tests/make_test_data.py` | Makes made-up test clients |

## Your data

Client CSVs and generated statements are deliberately **not** stored in this repo (see `.gitignore`).
You need two CSV files:

- **clients**: one row per client (ID, name, address, statement period, budgets)
- **line items**: one row per service, linked to a client by `client_id`

Dates can be written `DD-MM-YYYY` or `D/MM/YYYY`. Rows with problems are skipped and listed in `statements/errors.log`.
To see the exact columns, run `py tests/make_test_data.py` and open the files it creates in `tests/data/`.

## Command line

```
py app\sah_statement.py clients.csv line_items.csv statements
```

## Requirements

Python 3.10+, ReportLab and Pillow. Pillow is installed automatically with ReportLab.
