import flet as ft

def main(page: ft.Page):
    page.title = "Hello Flet Web"
    page.add(ft.Text("Hello from Flet Web!"))

if __name__ == "__main__":
    ft.app(target=main)
