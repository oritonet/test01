import os
import psycopg2
import flet as ft
from datetime import datetime
from flet import Icons, Colors

#──────────────────────────────
# DB 接続設定
#──────────────────────────────
def get_conn():
    return psycopg2.connect(
        host=os.environ["DB_HOST"],
        dbname=os.environ["DB_NAME"],
        user=os.environ["DB_USER"],
        password=os.environ["DB_PASSWORD"],
        port=5432
    )

def save_tasks_to_db(tasks):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("DELETE FROM todos")
    for t in tasks:
        cur.execute(
            "INSERT INTO todos (name, completed, created_at, updated_at) VALUES (%s, %s, %s, %s)",
            (t.task_name, t.completed, t.created_at, t.updated_at)
        )
    conn.commit()
    cur.close()
    conn.close()

def load_tasks_from_db():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT name, completed, created_at, updated_at FROM todos")
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return [{
        "name": r[0],
        "completed": r[1],
        "created_at": r[2],
        "updated_at": r[3],
    } for r in rows]

#──────────────────────────────
# タスク（1行分）
#──────────────────────────────
class Task(ft.Column):
    def __init__(self, task_name, task_status_change, task_delete,
                 created_at=None, updated_at=None):
        super().__init__()
        self.completed = False
        self.task_name = task_name
        self.task_status_change = task_status_change
        self.task_delete = task_delete
        now = datetime.now().strftime("%m月%d日")
        self.created_at = created_at or now
        self.updated_at = updated_at or now

        self.update_label = ft.Text(f"編集: {self.updated_at}", size=8, color=Colors.GREY)
        self.display_task = ft.Checkbox(
            value=False,
            label=ft.Text(self.task_name, max_lines=1, overflow="ellipsis", width=150),
            on_change=self.status_changed,
        )
        self.edit_name = ft.TextField(expand=1)
        self.display_view = ft.Row(
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            controls=[
                self.display_task,
                ft.Row(spacing=5, vertical_alignment=ft.CrossAxisAlignment.CENTER, controls=[
                    ft.IconButton(icon=Icons.CREATE_OUTLINED, tooltip="編集", on_click=self.edit_clicked),
                    ft.IconButton(icon=Icons.DELETE_OUTLINE, tooltip="削除", on_click=self.delete_clicked),
                    self.update_label
                ])
            ],
        )
        self.edit_view = ft.Row(
            visible=False,
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            controls=[
                self.edit_name,
                ft.IconButton(icon=Icons.DONE_OUTLINE_OUTLINED, icon_color=Colors.GREEN, tooltip="保存", on_click=self.save_clicked),
            ],
        )
        self.controls = [self.display_view, self.edit_view]

    def edit_clicked(self, e):
        self.edit_name.value = self.display_task.label.value
        self.display_view.visible = False
        self.edit_view.visible = True
        self.update()

    def save_clicked(self, e):
        new_name = self.edit_name.value
        if new_name:
            self.task_name = new_name
            self.display_task.label.value = new_name
            self.updated_at = datetime.now().strftime("%m月%d日")
            self.update_label.value = f"編集: {self.updated_at}"
        self.display_view.visible = True
        self.edit_view.visible = False
        self.update()
        self.task_status_change(self)

    def status_changed(self, e):
        self.completed = self.display_task.value
        self.task_status_change(self)

    def delete_clicked(self, e):
        self.task_delete(self)

#──────────────────────────────
# Todo アプリ全体
#──────────────────────────────
class TodoApp(ft.Column):
    def __init__(self):
        super().__init__()

        self.new_task = ft.TextField(hint_text="ここに内容記入", on_submit=self.add_clicked, expand=True)
        self.tasks = ft.Column()
        self.filter = ft.Tabs(
            scrollable=False,
            selected_index=0,
            on_change=self.tabs_changed,
            tabs=[ft.Tab(text="全て"), ft.Tab(text="アクティブ"), ft.Tab(text="完了")],
        )
        self.items_left = ft.Text("0 items left")

        self.width = 600
        self.controls = [
            ft.Row([ft.Text("Todoリスト", theme_style=ft.TextThemeStyle.HEADLINE_MEDIUM)],
                   alignment=ft.MainAxisAlignment.CENTER),
            ft.Row(controls=[self.new_task,
                             ft.FloatingActionButton(icon=Icons.ADD, on_click=self.add_clicked)]),
            ft.Column(
                spacing=25,
                controls=[
                    self.filter,
                    self.tasks,
                    ft.Row(
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        controls=[
                            self.items_left,
                            ft.OutlinedButton(text="完了タスクを削除", on_click=self.clear_clicked),
                        ],
                    ),
                ],
            ),
        ]

        for data in load_tasks_from_db():
            task = Task(
                task_name=data["name"],
                task_status_change=self.task_status_change,
                task_delete=self.task_delete,
                created_at=data.get("created_at"),
                updated_at=data.get("updated_at"),
            )
            task.display_task.value = data["completed"]
            task.completed = data["completed"]
            self.tasks.controls.append(task)

    def add_clicked(self, e):
        name = self.new_task.value
        if name:
            task = Task(name, self.task_status_change, self.task_delete)
            self.tasks.controls.append(task)
            self.new_task.value = ""
            self.new_task.focus()
            self.update()
            save_tasks_to_db(self.tasks.controls)

    def task_status_change(self, task):
        self.update()
        save_tasks_to_db(self.tasks.controls)

    def task_delete(self, task):
        self.tasks.controls.remove(task)
        self.update()
        save_tasks_to_db(self.tasks.controls)

    def tabs_changed(self, e):
        self.update()

    def clear_clicked(self, e):
        for task in self.tasks.controls[:]:
            if task.completed:
                self.task_delete(task)
        save_tasks_to_db(self.tasks.controls)

    def before_update(self):
        status = self.filter.tabs[self.filter.selected_index].text
        count = 0
        for task in self.tasks.controls:
            task.visible = (
                status == "全て"
                or (status == "アクティブ" and not task.completed)
                or (status == "完了" and task.completed)
            )
            if not task.completed:
                count += 1
        self.items_left.value = f"アクティブ数: {count}"

#──────────────────────────────
# エントリポイント
#──────────────────────────────
def main(page: ft.Page):
    page.title = "ToDoリスト"
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER
    page.scroll = ft.ScrollMode.ADAPTIVE
    page.add(TodoApp())

if __name__ == "__main__":
    ft.app(target=main, port=int(os.environ.get("PORT", 8550)), host="0.0.0.0")
