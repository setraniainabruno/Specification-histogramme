from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.routers import histogram, images, measurements, morphology

BASE_DIR = Path(__file__).resolve().parent

app = FastAPI(
    title="HistoSpec — Spécification d'histogramme",
    description=(
        "Application pédagogique de traitement d'image : spécification "
        "et égalisation d'histogramme, seuillage, morphologie "
        "mathématique et mesures granulométriques, sur la base du cours "
        "d'Analyse d'Image de l'Ecole des Mines de Saint-Etienne."
    ),
    version="1.0.0",
)

app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

app.include_router(images.router)
app.include_router(histogram.router)
app.include_router(morphology.router)
app.include_router(measurements.router)


@app.get("/", include_in_schema=False)
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/health", tags=["system"])
async def health():
    return {"status": "ok"}


@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    return RedirectResponse(url="/static/favicon.svg")
