from flet.fastapi import FastAPI
import flet as ft

def main(page: ft.Page):
    page.title = "Flet Render Web App"
    txt = ft.Text("Hello from Flet on Render!")
    page.add(txt)

app = FastAPI(target=main)
