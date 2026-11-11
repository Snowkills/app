#!/usr/bin/env python3
"""Aggiorna apps.json con dimensione, impronta SHA-256 e data di ogni file scaricabile.

Uso, dopo aver aggiunto o sostituito un file in downloads/:
    python3 aggiorna.py
Segnala anche i file elencati che mancano e quelli presenti ma non elencati.
"""
import hashlib
import json
import sys
from datetime import date
from pathlib import Path

QUI = Path(__file__).resolve().parent
INDICE = QUI / "apps.json"
LIMITE_GITHUB = 100 * 1024 * 1024  # GitHub rifiuta i file oltre 100 MB


def sha256(percorso: Path) -> str:
    h = hashlib.sha256()
    with percorso.open("rb") as f:
        for blocco in iter(lambda: f.read(1 << 20), b""):
            h.update(blocco)
    return h.hexdigest()


def main() -> int:
    app = json.loads(INDICE.read_text(encoding="utf-8"))
    elencati, errori = set(), 0
    for a in app:
        for d in a.get("download", []):
            f = QUI / d["file"]
            elencati.add(f)
            if not f.is_file():
                print(f"MANCA   {d['file']}  ({a['nome']})")
                errori += 1
                continue
            impronta = sha256(f)
            if d.get("sha256") != impronta:
                d["aggiornato"] = date.fromtimestamp(f.stat().st_mtime).isoformat()
            d["dimensione"] = f.stat().st_size
            d["sha256"] = impronta
            if d["dimensione"] > LIMITE_GITHUB:
                print(f"TROPPO GRANDE (oltre 100 MB)  {d['file']}")
                errori += 1
            print(f"ok      {d['file']}  {d['dimensione'] / 1e6:.1f} MB")
    for f in sorted((QUI / "downloads").rglob("*")):
        if f.is_file() and f not in elencati:
            print(f"NON ELENCATO in apps.json: {f.relative_to(QUI)}")
    INDICE.write_text(json.dumps(app, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return 1 if errori else 0


if __name__ == "__main__":
    sys.exit(main())
