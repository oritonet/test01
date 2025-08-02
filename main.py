import os
import flet as ft            # Flet 本体
from flet import Icons, Colors   # アイコンと色の定数

#────────────────────────────────────────
# 単一タスク（To-Do）を表すコンポーネント
#────────────────────────────────────────
class Task(ft.Column):
    def __init__(self, task_name, task_status_change, task_delete):
        super().__init__()                     # 親クラス(ft.Column) の初期化
        self.completed = False                 # 完了フラグ
        self.task_name = task_name             # 表示用タスク名
        self.task_status_change = task_status_change  # 状態変化コールバック
        self.task_delete = task_delete                 # 削除コールバック

        # チェックボックス（タスク名表示用）
        self.display_task = ft.Checkbox(
            value=False,                       # 既定は未完了
            label=self.task_name,              # ラベルにタスク名
            on_change=self.status_changed      # チェック変更時ハンドラ
        )

        self.edit_name = ft.TextField(expand=1)  # 編集用テキストフィールド

        # ── 通常表示ビュー（チェックボックス＋アイコンボタン×2）
        self.display_view = ft.Row(
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,     # 端と端に配置
            vertical_alignment=ft.CrossAxisAlignment.CENTER,  # 縦中央
            controls=[
                self.display_task,                            # 左：チェックボックス
                ft.Row(                                       # 右：アイコンボタン列
                    spacing=0,
                    controls=[
                        ft.IconButton(                        # 編集ボタン
                            icon=Icons.CREATE_OUTLINED,
                            tooltip="Edit To-Do",
                            on_click=self.edit_clicked,
                        ),
                        ft.IconButton(                        # 削除ボタン
                            icon=Icons.DELETE_OUTLINE,
                            tooltip="Delete To-Do",
                            on_click=self.delete_clicked,
                        ),
                    ],
                ),
            ],
        )

        # ── 編集ビュー（テキスト入力＋保存ボタン）
        self.edit_view = ft.Row(
            visible=False,                                    # 初期は非表示
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            controls=[
                self.edit_name,                               # 左：入力欄
                ft.IconButton(                                # 右：保存ボタン
                    icon=Icons.DONE_OUTLINE_OUTLINED,
                    icon_color=Colors.GREEN,
                    tooltip="Update To-Do",
                    on_click=self.save_clicked,
                ),
            ],
        )

        # Column の children に 2ビューを登録
        self.controls = [self.display_view, self.edit_view]

    #―― 編集アイコン押下：編集ビューを表示
    def edit_clicked(self, e):
        self.edit_name.value = self.display_task.label       # 現在のタスク名をセット
        self.display_view.visible = False                    # 通常ビュー非表示
        self.edit_view.visible = True                        # 編集ビュー表示
        self.update()                                        # 画面更新

    #―― 保存ボタン押下：名称更新して通常ビューへ戻す
    def save_clicked(self, e):
        self.display_task.label = self.edit_name.value       # ラベル更新
        self.display_view.visible = True
        self.edit_view.visible = False
        self.update()

    #―― チェック状態変更時：完了フラグ更新＆親へ通知
    def status_changed(self, e):
        self.completed = self.display_task.value
        self.task_status_change(self)                        # コールバック

    #―― 削除ボタン押下：親へ削除要求
    def delete_clicked(self, e):
        self.task_delete(self)

#────────────────────────────────────────
# To-Do アプリ全体を表すコンポーネント
#────────────────────────────────────────
class TodoApp(ft.Column):
    def __init__(self):
        super().__init__()

        #―― 新規タスク入力フィールド
        self.new_task = ft.TextField(
            hint_text="ここに内容記入",
            on_submit=self.add_clicked,  # Enter で追加
            expand=True                 # 幅いっぱい
        )

        self.tasks = ft.Column()        # 追加タスクを並べる列

        #―― タブ（フィルター：all / active / completed）
        self.filter = ft.Tabs(
            scrollable=False,
            selected_index=0,
            on_change=self.tabs_changed,
            tabs=[
                ft.Tab(text="全て"),
                ft.Tab(text="アクティブ"),
                ft.Tab(text="完了")
            ],
        )

        self.items_left = ft.Text("0 items left")  # 残件数表示

        self.width = 600               # アプリ幅

        # Column(child) 構築
        self.controls = [
            # タイトル
            ft.Row(
                [ft.Text(value="Todoリスト", theme_style=ft.TextThemeStyle.HEADLINE_MEDIUM)],
                alignment=ft.MainAxisAlignment.CENTER,
            ),
            # 入力行（テキスト＋追加ボタン）
            ft.Row(
                controls=[
                    self.new_task,
                    ft.FloatingActionButton(icon=Icons.ADD, on_click=self.add_clicked),
                ],
            ),
            # タスク一覧＋フッタ
            ft.Column(
                spacing=25,
                controls=[
                    self.filter,        # フィルタタブ
                    self.tasks,         # タスクリスト
                    # フッタ（残件数＋Clear button）
                    ft.Row(
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        controls=[
                            self.items_left,
                            ft.OutlinedButton(text="完了タスクを削除",
                                              on_click=self.clear_clicked),
                        ],
                    ),
                ],
            ),
        ]

    #―― タスク追加（Enter または ＋ボタン）
    def add_clicked(self, e):
        if self.new_task.value:                       # 入力が空でなければ
            task = Task(self.new_task.value,
                        self.task_status_change,
                        self.task_delete)
            self.tasks.controls.append(task)          # リストに追加
            self.new_task.value = ""                  # 入力欄クリア
            self.new_task.focus()                     # フォーカス戻す
            self.update()

    #―― タスクの完了状態変化時
    def task_status_change(self, task):
        self.update()

    #―― タスク削除
    def task_delete(self, task):
        self.tasks.controls.remove(task)
        self.update()

    #―― フィルタタブ切り替え
    def tabs_changed(self, e):
        self.update()

    #―― 「Clear completed」押下：完了タスク一括削除
    def clear_clicked(self, e):
        for task in self.tasks.controls[:]:           # コピーで安全に反復
            if task.completed:
                self.task_delete(task)

    #―― 更新前フック：可視状態と残件数を調整
    def before_update(self):
        status = self.filter.tabs[self.filter.selected_index].text  # 現在タブ
        count = 0
        for task in self.tasks.controls:
            # タブ状態に応じて表示／非表示
            task.visible = (
                status == "全て" or
                (status == "アクティブ" and not task.completed) or
                (status == "完了" and task.completed)
            )
            if not task.completed:
                count += 1
        self.items_left.value = f"アクティブ数:{count}"

#────────────────────────────────────────
# Flet アプリ エントリポイント
#────────────────────────────────────────
def main(page: ft.Page):
    page.title = "ToDoリスト"                 # ページタイトル
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER
    page.scroll = ft.ScrollMode.ADAPTIVE    # スクロール自動
    page.add(TodoApp())                     # TodoApp をページに配置

if __name__ == "__main__":
    ft.app(target=main, port=int(os.environ.get("PORT", 8550)), host="0.0.0.0")
