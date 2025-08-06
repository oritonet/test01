import os
import psycopg2
import flet as ft
from datetime import datetime
from flet import (
    Icons, Colors, Text, Row, Column, ElevatedButton,
    TextField, Tabs, Tab, AlertDialog, OutlinedButton, IconButton, Container
)
from dotenv import load_dotenv

load_dotenv()

DB_HOST = os.getenv("DB_HOST")
DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")

DEFAULT_TAGS = ["仕事", "プライベート", "買い物", "勉強", "その他"]

def get_conn():
    return psycopg2.connect(
        host=DB_HOST,
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
        port=5432
    )

def save_tasks_to_db(tasks):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("DELETE FROM todos")
    for t in tasks:
        cur.execute(
            "INSERT INTO todos (name, completed, created_at, updated_at, tag) VALUES (%s, %s, %s, %s, %s)",
            (t.task_name, t.completed, t.created_at, t.updated_at, t.tag)
        )
    conn.commit()
    cur.close()
    conn.close()

def load_tasks_from_db():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT name, completed, created_at, updated_at, tag FROM todos")
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return [{
        "name": r[0],
        "completed": r[1],
        "created_at": r[2],
        "updated_at": r[3],
        "tag": r[4] or "その他"
    } for r in rows]


#──────────────────────────────
# タスク（1行分）
#──────────────────────────────
class Task(Container):
    def __init__(self, task_name, task_status_change, task_delete,
                 tag="その他", created_at=None, updated_at=None, page=None):
        super().__init__()
        self.page = page

        self.task_name = task_name
        self.task_status_change = task_status_change
        self.task_delete = task_delete
        self.completed = False
        self.tag = tag
        now = datetime.now().strftime("%m月%d日")
        self.created_at = created_at or now
        self.updated_at = updated_at or now

        self.is_editing = False

        self.update_label = Text(f"編集: {self.updated_at}", size=8, color=Colors.GREY)
        self.edit_name = TextField(expand=1, multiline=True)
        self.edit_tag = ft.Dropdown(
            options=[],
            value=self.tag,
            width=120
        )
        self.show_delete = False
        self.highlighted = False
        self.bgcolor = None
        self.padding = 5
        self.border_radius = 5

        self.delete_button = IconButton(icon=Icons.DELETE_OUTLINE, tooltip="削除", on_click=self.delete_clicked)

        self.task_label_button = ft.TextButton(
            content=Text(self.task_name, max_lines=1, overflow="ellipsis", width=200),
            on_click=self.edit_clicked,
            on_long_press=self.toggle_delete_icon,
        )

        self.checkbox = ft.Checkbox(
            value=False,
            on_change=self.status_changed,
        )

        self.display_view = Row(
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            controls=[
                Row(spacing=10, controls=[self.checkbox, self.task_label_button, Text(f"[{self.tag}]", size=10)]),
                Row(spacing=5, controls=[
                    ft.AnimatedSwitcher(content=self.delete_button if self.show_delete else ft.Container()),
                    self.update_label,
                ])
            ]
        )

        self.edit_view = Row(
            visible=False,
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            controls=[
                self.edit_name,
                self.edit_tag,
                ft.IconButton(icon=Icons.DONE_OUTLINE_OUTLINED, icon_color=Colors.GREEN, on_click=self.save_clicked)
            ]
        )

        self.content = Column(controls=[self.display_view, self.edit_view])
        self.content.expand = True
        self.content.padding = 0
        self.controls = [self.content]

    def set_tag_options(self, tag_list):
        self.edit_tag.options = [ft.dropdown.Option(t) for t in tag_list]
        if self.tag in tag_list:
            self.edit_tag.value = self.tag
        else:
            self.edit_tag.value = tag_list[0] if tag_list else None
        self.update()

    def edit_clicked(self, e):
        self.is_editing = True
        self.edit_name.value = self.task_name
        self.display_view.visible = False
        self.edit_view.visible = True
        self.set_tag_options(self.page.todo_app.tag_list)
        self.update()
        # ページクリックで編集終了検知用イベントセット
        self.page.on_click = self.on_page_click

    def on_page_click(self, e):
        if self.is_editing:
            if e.control in [self.edit_name, self.edit_tag]:
                return
            self.save_clicked(None)
            self.page.on_click = None

    def save_clicked(self, e):
        new_name = self.edit_name.value.strip()
        new_tag = self.edit_tag.value
        if new_name:
            self.task_name = new_name
            self.tag = new_tag
            self.task_label_button.content.value = new_name
            self.updated_at = datetime.now().strftime("%m月%d日")
            self.update_label.value = f"編集: {self.updated_at}"
        self.display_view.visible = True
        self.edit_view.visible = False
        self.is_editing = False
        self.update()
        self.task_status_change(self)

    def status_changed(self, e):
        self.completed = self.checkbox.value
        self.task_status_change(self)

    def delete_clicked(self, e):
        self.task_delete(self)

    def toggle_delete_icon(self, e):
        self.show_delete = not self.show_delete
        self.highlighted = self.show_delete
        self.bgcolor = Colors.AMBER_100 if self.highlighted else None
        self.update()


#──────────────────────────────
# タグ管理ダイアログ
#──────────────────────────────
class TagManager(AlertDialog):
    def __init__(self, tag_list, on_tags_updated):
        super().__init__()
        self.title = Text("タグ管理", size=20)
        self.on_tags_updated = on_tags_updated

        self.tag_list = tag_list.copy()

        self.tag_inputs = []
        self.container = Column(spacing=5, scroll="auto", height=250)

        self.new_tag_field = TextField(hint_text="新しいタグを追加")
        self.add_button = ElevatedButton(text="追加", icon=Icons.ADD, on_click=self.add_new_tag)

        self.content = Column([
            self.container,
            Row([self.new_tag_field, self.add_button], alignment=ft.MainAxisAlignment.CENTER),
        ])

        self.actions = [
            OutlinedButton("閉じる", on_click=self.close_dialog)
        ]

        self.update_tag_list()

    def update_tag_list(self):
        self.container.controls.clear()
        self.tag_inputs.clear()
        for idx, tag in enumerate(self.tag_list):
            tf = TextField(value=tag, width=200)
            tf.tag_index = idx
            tf.on_change = self.tag_text_changed

            del_btn = IconButton(icon=Icons.DELETE, tooltip="タグ削除", on_click=self.delete_tag)
            del_btn.tag_index = idx

            row = Row([tf, del_btn], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)
            self.tag_inputs.append(tf)
            self.container.controls.append(row)

    def tag_text_changed(self, e):
        idx = e.control.tag_index
        new_val = e.control.value.strip()
        if new_val:
            self.tag_list[idx] = new_val

    def delete_tag(self, e):
        idx = e.control.tag_index
        del self.tag_list[idx]
        self.update_tag_list()

    def add_new_tag(self, e):
        new_tag = self.new_tag_field.value.strip()
        if new_tag and new_tag not in self.tag_list:
            self.tag_list.append(new_tag)
            self.new_tag_field.value = ""
            self.update_tag_list()

    def close_dialog(self, e):
        self.on_tags_updated(self.tag_list)
        self.open = False
        self.update()


#──────────────────────────────
# Todo アプリ全体
#──────────────────────────────
class TodoApp(Column):
    def __init__(self, page):
        super().__init__()

        self.page = page
        self.tag_list = DEFAULT_TAGS.copy()

        self.tag_manager_button = ElevatedButton(text="タグ管理", icon=Icons.LABEL, on_click=self.open_tag_manager)

        self.tag_tabs = Tabs(
            selected_index=0,
            on_change=self.filter_changed,
            tabs=[Tab(text=t) for t in self.tag_list]
        )

        self.status_tabs = Tabs(
            selected_index=0,
            on_change=self.filter_changed,
            tabs=[Tab(text="アクティブ"), Tab(text="完了")]
        )

        self.new_task = TextField(hint_text="ここに内容記入", on_submit=self.add_clicked, expand=True, multiline=True)

        self.all_tasks = []
        self.tasks = Column(spacing=10, expand=True)

        self.width = 700
        self.controls = [
            Row([Text("タグ付きToDoリスト", theme_style=ft.TextThemeStyle.HEADLINE_MEDIUM)],
                alignment=ft.MainAxisAlignment.CENTER),
            Row([self.new_task, IconButton(icon=Icons.ADD, on_click=self.add_clicked)]),
            Row([self.tag_tabs, self.tag_manager_button]),
            self.status_tabs,
            Column(
                spacing=25,
                expand=True,
                controls=[
                    self.tasks,
                    Row(
                        alignment=ft.MainAxisAlignment.END,
                        controls=[
                            OutlinedButton(text="完了タスクを削除", on_click=self.clear_clicked),
                        ],
                    ),
                ],
            ),
        ]

    def open_tag_manager(self, e):
        self.tag_manager = TagManager(self.tag_list, self.on_tags_updated)
        self.page.dialog = self.tag_manager
        self.tag_manager.open = True
        self.page.update()

    def on_tags_updated(self, new_tags):
        if not new_tags:
            new_tags = ["その他"]
        self.tag_list = new_tags
        # タブ再構築
        self.tag_tabs.tabs.clear()
        for t in self.tag_list:
            self.tag_tabs.tabs.append(Tab(text=t))
        self.tag_tabs.selected_index = 0
        self.tag_tabs.update()

        # タスクタグが存在しないタグなら「その他」に変更
        for task in self.all_tasks:
            if task.tag not in self.tag_list:
                task.tag = "その他"
                task.update()

        self.filter_tasks()
        self.page.update()

    def reload_tasks_from_db(self):
        self.all_tasks.clear()
        for data in load_tasks_from_db():
            task = self.create_task_from_data(data)
            self.all_tasks.append(task)
        self.filter_tasks()

    def create_task_from_data(self, data):
        task = Task(
            task_name=data["name"],
            task_status_change=self.task_status_change,
            task_delete=self.task_delete,
            tag=data.get("tag", "その他"),
            created_at=data.get("created_at"),
            updated_at=data.get("updated_at"),
            page=self.page
        )
        task.checkbox.value = data["completed"]
        task.completed = data["completed"]
        return task

    def add_clicked(self, e):
        name = self.new_task.value.strip()
        if 0 <= self.tag_tabs.selected_index < len(self.tag_list):
            tag = self.tag_list[self.tag_tabs.selected_index]
        else:
            tag = "その他"

        if name:
            task = Task(name, self.task_status_change, self.task_delete, tag=tag, page=self.page)
            self.all_tasks.append(task)
            self.new_task.value = ""
            self.new_task.focus()
            self.filter_tasks()
            save_tasks_to_db(self.all_tasks)

    def task_status_change(self, task):
        self.filter_tasks()
        save_tasks_to_db(self.all_tasks)

    def task_delete(self, task):
        if task in self.all_tasks:
            self.all_tasks.remove(task)
        self.filter_tasks()
        save_tasks_to_db(self.all_tasks)

    def filter_changed(self, e):
        self.filter_tasks()

    def clear_clicked(self, e):
        self.all_tasks = [t for t in self.all_tasks if not t.completed]
        self.filter_tasks()
        save_tasks_to_db(self.all_tasks)

    def filter_tasks(self):
        self.tasks.controls.clear()

        if 0 <= self.tag_tabs.selected_index < len(self.tag_list):
            selected_tag = self.tag_list[self.tag_tabs.selected_index]
        else:
            selected_tag = None

        selected_status = self.status_tabs.tabs[self.status_tabs.selected_index].text

        filtered = self.all_tasks
        if selected_tag:
            filtered = [t for t in filtered if t.tag == selected_tag]

        if selected_status == "アクティブ":
            visible_tasks = [t for t in filtered if not t.completed]
        else:
            visible_tasks = [t for t in filtered if t.completed]

        self.tasks.controls.extend(visible_tasks)
        self.update()


def main(page: ft.Page):
    page.title = "ToDoリスト"
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER
    page.scroll = ft.ScrollMode.ADAPTIVE

    todo_app = TodoApp(page)
    page.todo_app = todo_app
    page.add(todo_app)
    todo_app.reload_tasks_from_db()
    todo_app.update()

if __name__ == "__main__":
    ft.app(target=main, port=int(os.environ.get("PORT", 8550)), host="0.0.0.0")
