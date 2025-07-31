import flet as ft # 1.

def main(page: ft.Page): # 2.
    page.title = "Flet counter example" # 3.
    page.vertical_alignment = ft.MainAxisAlignment.CENTER # 4.

    txt_number = ft.TextField(value="0", text_align=ft.TextAlign.RIGHT, width=100) # 5.

    def minus_click(e): # 6.
        txt_number.value = str(int(txt_number.value) - 1)
        page.update()

    def plus_click(e): # 6.
        txt_number.value = str(int(txt_number.value) + 1)
        page.update()

    page.add( # 7.
        ft.Row(
            [
                ft.IconButton(ft.Icons.REMOVE, on_click=minus_click),
                txt_number,
                ft.IconButton(ft.Icons.ADD, on_click=plus_click),
            ],
            alignment=ft.MainAxisAlignment.CENTER,
        )
    )

ft.app(target=main) # 8.
