"""
Sube los archivos del proyecto al repositorio GitHub usando la API REST.
Requiere la variable de entorno GITHUB_TOKEN.
"""
import base64
import os
import sys
import urllib.request
import urllib.error
import json

REPO   = "karenpbq-bot/CLINICA-TMTR"
BRANCH = "main"
TOKEN  = os.environ.get("GITHUB_TOKEN", "")

ARCHIVOS = [
    "main.py",
    "database.py",
    "modulo_pacientes.py",
    "modulo_tratamientos.py",
    "modulo_usuarios.py",
    "modulo_agenda.py",
    "modulo_pagos.py",
    "especialistas.py",
    "schema.sql",
    "replit.md",
    "pyproject.toml",
]


def _api(path: str, data: dict | None = None, method: str = "GET") -> dict:
    url = f"https://api.github.com/repos/{REPO}/{path}"
    body = json.dumps(data).encode() if data else None
    req  = urllib.request.Request(
        url, data=body, method=method,
        headers={
            "Authorization": f"Bearer {TOKEN}",
            "Accept":        "application/vnd.github+json",
            "Content-Type":  "application/json",
            "X-GitHub-Api-Version": "2022-11-28",
        },
    )
    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        body_err = e.read().decode()
        raise RuntimeError(f"HTTP {e.code} {e.reason}: {body_err}") from e


def push_file(ruta_local: str):
    with open(ruta_local, "rb") as f:
        contenido = f.read()
    contenido_b64 = base64.b64encode(contenido).decode()

    sha = None
    try:
        info = _api(f"contents/{ruta_local}?ref={BRANCH}")
        sha  = info.get("sha")
    except RuntimeError as e:
        if "HTTP 404" not in str(e):
            raise

    payload: dict = {
        "message": f"chore: actualizar {ruta_local}",
        "content": contenido_b64,
        "branch":  BRANCH,
    }
    if sha:
        payload["sha"] = sha

    _api(f"contents/{ruta_local}", data=payload, method="PUT")
    accion = "actualizado" if sha else "creado"
    print(f"  ✓ {ruta_local} ({accion})")


def main():
    if not TOKEN:
        print("ERROR: GITHUB_TOKEN no está configurado.", file=sys.stderr)
        sys.exit(1)

    print(f"Subiendo archivos a {REPO} ({BRANCH})…")
    errores = []
    for archivo in ARCHIVOS:
        if not os.path.exists(archivo):
            print(f"  – {archivo} (no encontrado, omitido)")
            continue
        try:
            push_file(archivo)
        except Exception as ex:
            print(f"  ✗ {archivo}: {ex}")
            errores.append(archivo)

    print()
    if errores:
        print(f"Completado con errores en: {', '.join(errores)}")
        sys.exit(1)
    else:
        print("Todos los archivos subidos correctamente.")


if __name__ == "__main__":
    main()
