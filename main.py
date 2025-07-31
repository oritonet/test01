import flet as ft

async def main(page: ft.Page):
    page.title = "Flet counter example"
    txt = ft.TextField(value="0", text_align=ft.TextAlign.RIGHT, width=100)

    def minus(e):
        txt.value = str(int(txt.value) - 1)
        page.update()

    def plus(e):
        txt.value = str(int(txt.value) + 1)
        page.update()

    page.add(
        ft.Row(
            [
                ft.IconButton(ft.icons.REMOVE, on_click=minus),
                txt,
                ft.IconButton(ft.icons.ADD, on_click=plus),
            ],
            alignment=ft.MainAxisAlignment.CENTER,
        )
    )

ft.app(target=main)
