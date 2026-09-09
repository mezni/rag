"""Regenerate sample source documents into ``data/raw`` for development.

Creates a PDF, a DOCX, a TXT, an HTML page, and a SQLite database with a
``documents`` table so every wired connector (filesystem + database) has input.

Usage:
    uv run python scripts/generate_sample_docs.py
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

from reportlab.pdfgen import canvas as pdf_canvas

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data" / "raw"

REFUND_POLICY = """Weber Refund Policy

You can request a refund within 45 days of your purchase. Refunds are issued
to the original payment method within 5-7 business days of approval.

To request a refund, open a ticket with your order number and the reason for
the return. Physical products must be returned in their original condition
before the refund is processed.

Non-refundable items include digital gift cards and subscriptions that have
been active for more than 30 days.
"""

EMPLOYEE_HANDBOOK = """Acme Employee Handbook

Remote work is available for all software engineers on Fridays. Engineering
teams hold a weekly demo on Tuesday mornings where any engineer can present.

Annual leave accrues at 2.5 days per calendar month. The office is closed
between Christmas and New Year.

Open enrollment for health benefits runs every November.
"""

FAQS = """FAQ: Reimbursements

Q: What is the maximum reimbursement per expense claim?
A: 500 EUR per claim without manager approval.

Q: Which receipts are accepted?
A: PDF receipts and scanned copies. Photos of screenshots are not accepted.

Q: How long does reimbursement take?
A: Processing takes 3 business days after approval.
"""


def write_pdf(path: Path) -> None:
    canvas = pdf_canvas.Canvas(str(path))
    y = 760
    for line in REFUND_POLICY.splitlines():
        canvas.drawString(72, y, line)
        y -= 18
    canvas.save()


def write_docx(path: Path) -> None:
    from docx import Document

    document = Document()
    for line in EMPLOYEE_HANDBOOK.splitlines():
        document.add_paragraph(line)
    document.save(str(path))


def write_html(path: Path) -> None:
    body = "\n".join(f"<p>{line}</p>" for line in FAQS.splitlines())
    path.write_text(
        f"<!doctype html><html><head><title>Reimbursement FAQ</title></head>"
        f"<body><h1>Reimbursement FAQ</h1>{body}</body></html>",
        encoding="utf-8",
    )


def write_txt(path: Path) -> None:
    path.write_text(REFRESH_TOKEN_QA, encoding="utf-8")


def write_database(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(path) as connection:
        connection.execute(
            "CREATE TABLE IF NOT EXISTS documents ("
            "id INTEGER PRIMARY KEY, title TEXT, body TEXT)"
        )
        connection.executemany(
            "INSERT OR REPLACE INTO documents (id, title, body) VALUES (?, ?, ?)",
            [
                (1, "Backup Runbooks", "Nightly backups run at 02:00 UTC. "
                 "Retention is 14 daily, 8 weekly, and 12 monthly snapshots."),
                (2, "Incident Response", "P0 incidents are declared when the "
                 "checkout service is down for more than 5 minutes."),
            ],
        )


REFRESH_TOKEN_QA = """Question: Do access tokens expire?

Answer: Yes. Access tokens are valid for 15 minutes and refresh tokens for 90
days. Refresh tokens are rotating: each refresh invalidates the previous one.
"""


def main() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    write_pdf(DATA_DIR / "refund-policy.pdf")
    write_docx(DATA_DIR / "employee-handbook.docx")
    write_html(DATA_DIR / "reimbursement-faq.html")
    write_txt(DATA_DIR / "auth-qa.txt")
    write_database(DATA_DIR / "sample.db")
    for path in sorted(DATA_DIR.rglob("*")):
        if path.is_file():
            print(f"wrote {path.relative_to(PROJECT_ROOT)}")


if __name__ == "__main__":
    main()