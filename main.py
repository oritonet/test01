import os
import psycopg2
import flet as ft
from datetime import datetime
from flet import Icons, Colors
from dotenv import load_dotenv

load_dotenv()

DB_HOST = os.getenv("DB_HOST")
DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")

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
class Task(ft.Container):
    def __init__(self, task_name, task_status_change, task_delete,
                 created_at=None, updated_at=None):
        super().__init__()

        self.task_name = task_name
        self.task_status_change = task_status_change
        self.task_delete = task_delete
        self.completed = False
        now = datetime.now().strftime("%m月%d日")
        self.created_at = created_at or now
        self.updated_at = updated_at or now

        self.update_label = ft.Text(f"編集: {self.updated_at}", size=8, color=Colors.GREY)
        self.edit_name = ft.TextField(expand=1, multiline=True)
        self.show_delete = False
        self.highlighted = False  # ハイライト状態
        self.draggable = False    # 初期はドラッグ不可
        self.delete_button = ft.IconButton(icon=Icons.DELETE_OUTLINE, tooltip="削除", on_click=self.delete_clicked)

        self.task_label_button = ft.TextButton(
            content=ft.Text(self.task_name, max_lines=1, overflow="ellipsis", width=200),
            on_click=self.edit_clicked,
            on_long_press=self.toggle_delete_icon,
        )

        self.checkbox = ft.Checkbox(
            value=False,
            on_change=self.status_changed,
        )

        self.display_view = ft.Row(
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            controls=[
                ft.Row(spacing=10, controls=[self.checkbox, self.task_label_button]),
                ft.Row(spacing=5, controls=[
                    ft.AnimatedSwitcher(content=self.delete_button if self.show_delete else ft.Container()),
                    self.update_label,
                ])
            ]
        )

        self.edit_view = ft.Row(
            visible=False,
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            controls=[
                self.edit_name,
                ft.IconButton(icon=Icons.DONE_OUTLINE_OUTLINED, icon_color=Colors.GREEN, on_click=self.save_clicked),
            ]
        )

        self.content = ft.Column(controls=[self.display_view, self.edit_view])
        self.bgcolor = None
        self.padding = 5
        self.border_radius = 5

        self.draggable = True  # 並び替えを可能に
        self.data = ""  # 後でタスクリスト内indexを入れる

    def edit_clicked(self, e):
        self.edit_name.value = self.task_name
        self.display_view.visible = False
        self.edit_view.visible = True
        self.update()

    def save_clicked(self, e):
        new_name = self.edit_name.value
        if new_name:
            self.task_name = new_name
            self.task_label_button.content.value = new_name
            self.updated_at = datetime.now().strftime("%m月%d日")
            self.update_label.value = f"編集: {self.updated_at}"
        self.display_view.visible = True
        self.edit_view.visible = False
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
        self.draggable = self.highlighted

        # ここで親の DragTarget の draggable も切り替え
        if hasattr(self, "parent") and self.parent is not None:
            self.parent.draggable = self.draggable

        self.display_view.controls[1].controls[0] = (
            self.delete_button if self.show_delete else ft.Container()
        )
        self.update()


#──────────────────────────────
# Todo アプリ全体
#──────────────────────────────
class TodoApp(ft.Column):
    def __init__(self):
        super().__init__()

        self.new_task = ft.TextField(hint_text="ここに内容記入", on_submit=self.add_clicked, expand=True, multiline=True)
        self.tasks = ft.Column(spacing=10)

        self.filter = ft.Tabs(
            selected_index=0,
            on_change=self.tabs_changed,
            tabs=[ft.Tab(text="アクティブ"), ft.Tab(text="完了")],
        )

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
                        alignment=ft.MainAxisAlignment.END,
                        controls=[
                            ft.OutlinedButton(text="完了タスクを削除", on_click=self.clear_clicked),
                        ],
                    ),
                ],
            ),
        ]

        # タスクの読み込み
        for i, data in enumerate(load_tasks_from_db()):
            task = self.create_task_from_data(data, i)
            self.tasks.controls.append(self.create_drag_target(task))

    def create_task_from_data(self, data, index):
        task = Task(
            task_name=data["name"],
            task_status_change=self.task_status_change,
            task_delete=self.task_delete,
            created_at=data.get("created_at"),
            updated_at=data.get("updated_at"),
        )
        task.checkbox.value = data["completed"]
        task.completed = data["completed"]
        task.data = str(index)
        task.draggable = True
        return task

    def create_drag_target(self, task):
        return ft.DragTarget(
            group="tasks",
            data=id(task),  # 固有IDとして使用
            on_will_accept=self.highlight_dragged,
            on_accept=self.reorder_tasks,
            on_leave=self.clear_highlight,
            content=task
        )

    def add_clicked(self, e):
        name = self.new_task.value
        if name:
            task = Task(name, self.task_status_change, self.task_delete)
            task.data = str(len(self.tasks.controls))
            task.draggable = True
            self.tasks.controls.append(self.create_drag_target(task))
            self.new_task.value = ""
            self.new_task.focus()
            self.update()
            save_tasks_to_db([d.content for d in self.tasks.controls])

    def task_status_change(self, task):
        self.update()
        save_tasks_to_db([d.content for d in self.tasks.controls])

    def task_delete(self, task):
        for dt in self.tasks.controls[:]:
            if dt.content == task:
                self.tasks.controls.remove(dt)
                break
        self.update()
        save_tasks_to_db([d.content for d in self.tasks.controls])

    def tabs_changed(self, e):
        self.update()

    def clear_clicked(self, e):
        for dt in self.tasks.controls[:]:
            if dt.content.completed:
                self.task_delete(dt.content)
        save_tasks_to_db([d.content for d in self.tasks.controls])

    def highlight_dragged(self, e):
        for dt in self.tasks.controls:
            if dt.content.data == e.data:
                dt.content.bgcolor = Colors.AMBER_100
                dt.content.update()
        return True

    def clear_highlight(self, e):
        for dt in self.tasks.controls:
            dt.content.bgcolor = None
            dt.content.update()

    def reorder_tasks(self, e):
        from_index = None
        to_index = None

        for i, dt in enumerate(self.tasks.controls):
            if dt.content.data == e.data:
                from_index = i
            if dt.data == e.target:
                to_index = i

        if from_index is not None and to_index is not None and from_index != to_index:
            task = self.tasks.controls.pop(from_index)
            self.tasks.controls.insert(to_index, task)

        self.clear_highlight(e)
        self.update()
        save_tasks_to_db([d.content for d in self.tasks.controls])

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
