import os
import flet as ft

def main (page: ft.Page):
    page.title = "My App
    page.add(ft. Text("Hello from Flet on Render!") )
if -_name__ =="
    ft. app(target=main, port=int(os.environ.get ("PORT"
8550)), host="0.0.0.0")