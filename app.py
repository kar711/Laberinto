import csv
import os
from pathlib import Path

from flask import Flask, abort, redirect, render_template, session, url_for

app = Flask(__name__)

# En Codespaces, puedes configurar FLASK_SECRET_KEY en las variables de entorno.
app.secret_key = os.environ.get(
    "FLASK_SECRET_KEY",
    "clave-de-desarrollo-cambia-esto",
)

BASE_DIR = Path(__file__).resolve().parent
CSV_PATH = BASE_DIR / "laberinto.csv"

VIDAS_INICIALES = 3
TIPOS_FINALES = {"tesoro", "muerte", "salida"}

# Todos estos archivos deben estar dentro de static/sonidos/.
SONIDOS = {
    "inicio": "startgame.mp3",
    "abrir_puerta": "abrirpuertas.mp3",
    "despues": "despues de abrir.mp3",
    "antes": "antes de abrir.mp3",
    "victoria": "win.mp3",
}


def cargar_escenas():
    """Lee laberinto.csv y devuelve un diccionario {id: fila}."""
    escenas = {}

    with CSV_PATH.open(newline="", encoding="utf-8-sig") as archivo:
        lector = csv.DictReader(archivo)

        for fila in lector:
            escenas[int(fila["id"])] = fila

    if 1 not in escenas:
        raise ValueError("El CSV debe tener una escena con id=1.")

    return escenas


ESCENAS = cargar_escenas()


def num(valor):
    """Convierte un campo del CSV a entero; vacío equivale a 0."""
    if not valor:
        return 0

    valor = valor.strip()
    return int(valor) if valor else 0


def nuevo_estado():
    """Reinicia el estado de juego guardado en la sesión."""
    session["puntos"] = 0
    session["vidas"] = VIDAS_INICIALES
    session["inventario"] = []
    session["actual"] = None


def puertas_de(escena):
    """
    Devuelve las puertas definidas en la fila del CSV.

    Sonido opcional por puerta:
    sonido_puerta1, sonido_puerta2, sonido_puerta3.
    Si la celda está vacía, usa abrirpuertas.mp3.
    """
    puertas = []

    for indice in (1, 2, 3):
        destino = (escena.get(f"destino{indice}") or "").strip()

        if not destino:
            continue

        sonido_personalizado = (
            escena.get(f"sonido_puerta{indice}") or ""
        ).strip()

        puertas.append({
            "texto": (escena.get(f"texto_puerta{indice}") or "").strip(),
            "imagen": (escena.get(f"imagen_puerta{indice}") or "").strip(),
            "destino": int(destino),
            "sonido": sonido_personalizado or SONIDOS["abrir_puerta"],
        })

    return puertas


@app.context_processor
def inyectar_sonidos():
    """Hace que el mapa de sonidos esté disponible en las plantillas."""
    return {"sonidos": SONIDOS}


@app.route("/")
def inicio():
    """Muestra el botón de inicio a pantalla completa."""
    nuevo_estado()

    escena_inicial = ESCENAS[1]

    return render_template(
        "escena.html",
        e=escena_inicial,
        tipo="inicio",
        puertas=puertas_de(escena_inicial),
        aviso=None,
        final=False,
        estado=session,
        pantalla_inicio=True,
    )


@app.route("/sala/<int:id>")
def escena(id):
    if id not in ESCENAS:
        abort(404)

    if "vidas" not in session:
        nuevo_estado()

    e = ESCENAS[id]
    aviso = None

    # Si la escena requiere un objeto que el jugador no tiene,
    # se queda en la escena anterior.
    requiere = (e.get("requiere") or "").strip()

    if requiere and requiere not in session["inventario"]:
        aviso = f"La puerta está cerrada. Necesitas: {requiere}."
        anterior = ESCENAS.get(session.get("actual"), ESCENAS[1])

        return render_template(
            "escena.html",
            e=anterior,
            tipo=anterior.get("tipo", "sala"),
            puertas=puertas_de(anterior),
            aviso=aviso,
            final=False,
            estado=session,
            pantalla_inicio=False,
        )

    # Cambiar puntos, vidas e inventario solo la primera vez que
    # se entra en una escena, no al recargarla.
    if session.get("actual") != id:
        session["puntos"] += num(e.get("puntos", ""))
        session["vidas"] = max(
            0,
            session["vidas"] + num(e.get("vidas", "")),
        )

        objeto = (e.get("objeto") or "").strip()

        if objeto and objeto not in session["inventario"]:
            session["inventario"] = session["inventario"] + [objeto]

        session["actual"] = id

    tipo = (e.get("tipo") or "sala").strip()

    if session["vidas"] <= 0:
        tipo = "muerte"

    final = tipo in TIPOS_FINALES
    puertas = [] if final else puertas_de(e)

    return render_template(
        "escena.html",
        e=e,
        tipo=tipo,
        puertas=puertas,
        aviso=aviso,
        final=final,
        estado=session,
        pantalla_inicio=False,
    )


if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 5000)),
        debug=True,
    )
