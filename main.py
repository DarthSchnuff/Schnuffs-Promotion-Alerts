import sys
import os

def resource_path(relative_path):
    """
    Liefert korrekten Pfad – egal ob Script oder PyInstaller-EXE
    """
    if hasattr(sys, "_MEIPASS"):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)

CONFIG_PATH = resource_path("config/config.json")


from fastapi import FastAPI
from app.database import engine
from app.models import Base
from app.worker import start
from app.api import streamers

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Schnuffs Promotion Alerts")

app.include_router(streamers.router)

@app.on_event("startup")
def startup():
    start()
