import os
import flet as ft

async def main(page: ft.Page):
    page.title = "Happy!!"
    page.vertical_alignment = ft.MainAxisAlignment.CENTER
    txt = ft.Text(value="Hello Render!", size=30)
    page.add(txt)

# ポートとホストを Render 向けに設定
ft.app_async(
    target=main,
    port=int(os.environ.get("PORT", 8000)),
    host="0.0.0.0"
)
