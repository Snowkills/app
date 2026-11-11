# Monty Apps

Pagina di download delle mie app Android e dei miei programmi per PC.

## Aggiungere o aggiornare un'app

1. Copia il file in `downloads/android`, `downloads/linux`, `downloads/windows` o `downloads/sorgenti` (massimo 100 MB per file).
2. Aggiungi o modifica la voce in `apps.json` (nome, versione, descrizione, percorso del file).
3. Esegui `python3 aggiorna.py`: calcola dimensione e impronta SHA-256 e segnala i file mancanti o non elencati.
4. `git add -A && git commit -m "Aggiorna ..." && git push`

Anteprima in locale: `python3 -m http.server` e apri <http://localhost:8000>.
