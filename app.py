# app.py
import asyncio
import flet as ft
from fastapi import FastAPI
from starlette.responses import RedirectResponse

app = FastAPI()

@app.get("/")
async def redirect():
    return RedirectResponse("/index.html")

@app.on_event("startup")
async def start_flet():
    from main import main  # main.py にある main 関数を使う
    asyncio.create_task(ft.app(main, view=ft.WEB_BROWSER, port=8000))