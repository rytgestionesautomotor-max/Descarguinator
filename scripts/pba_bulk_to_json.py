# -*- coding: utf-8 -*-
"""Descarga PDFs de la web de PBA y genera JSONs base."""
from __future__ import annotations

import argparse
from pathlib import Path
from typing import List

import requests

import pdf_to_descargo


def cargar_urls(args: argparse.Namespace) -> List[str]:
    urls: List[str] = []
    if args.url:
        urls.extend(args.url)
    if args.from_file:
        with open(args.from_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    urls.append(line)
    return urls


def main() -> None:
    ap = argparse.ArgumentParser(
        description="Descarga PDFs de infracciones y genera JSONs usando pdf_to_descargo"
    )
    ap.add_argument("--url", action="append", help="URL directa al PDF (puede repetirse)")
    ap.add_argument("--from-file", help="Archivo con URLs, una por línea")
    ap.add_argument("--out", default="casos", help="Directorio de salida para JSONs y PDFs")
    args = ap.parse_args()

    urls = cargar_urls(args)
    if not urls:
        ap.error("Proporcioná al menos una URL con --url o --from-file")

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    for url in urls:
        try:
            resp = requests.get(url, timeout=10)
            resp.raise_for_status()
            ctx = pdf_to_descargo.parse_pdf(resp.content)
            acta = ctx.get("NRO_ACTA", "sin_acta")
            pdf_path = out_dir / f"{acta}.pdf"
            pdf_path.write_bytes(resp.content)
            json_path = out_dir / f"{acta}.json"
            pdf_to_descargo.save_json(ctx, json_path)
            print(f"OK {acta}")
        except Exception as e:
            print(f"Error con {url}: {e}")


if __name__ == "__main__":
    main()
