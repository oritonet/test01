import os  # 環境変数を扱うための標準ライブラリ
import psycopg2  # PostgreSQLとの接続に使うライブラリ
import flet as ft  # Flet UI ライブラリをftという名前でインポート
from datetime import datetime  # 日付・時間の操作用

# Fletから必要なUI部品・定数を個別にインポート
from flet import (
    Icons, Colors, Text, Row, Column, ElevatedButton,
    TextField, Tabs, Tab, AlertDialog, OutlinedButton, IconButton, Container
)
from dotenv import load_dotenv  # .envファイルから環境変数を読み込むライブラリ

load_dotenv()  # .envファイルから環境変数を読み込み

# 環境変数からDB接続情報を取得
DB_HOST = os.getenv("DB_HOST")  # ホスト名
DB_NAME = os.getenv("DB_NAME")  # データベース名
DB_USER = os.getenv("DB_USER")  # ユーザー名
DB_PASSWORD = os.getenv("DB_PASSWORD")  # パスワード

# デフォルトで使用するタグ一覧
DEFAULT_TAGS = ["仕事", "プライベート", "買い物"]

# PostgreSQLへの接続を返す関数
def get_conn():
    return psycopg2.connect(
        host=DB_HOST,
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
        port=5432
    )

# タスクリストをDBに保存する関数
def save_tasks_to_db(tasks):
    conn = get_conn()  # DB接続
    cur = conn.cursor()  # カーソル作成
    cur.execute("DELETE FROM todos")  # 既存タスクを全削除
    for t in tasks:
        cur.execute(
            "INSERT INTO todos (name, completed, created_at, updated_at, tag) VALUES (%s, %s, %s, %s, %s)",
            (t.task_name, t.completed, t.created_at, t.updated_at, t.tag)
        )
    conn.commit()  # コミットして反映
    cur.close()  # カーソルを閉じる
    conn.close()  # 接続を閉じる

# DBからタスクを読み込んで辞書形式で返す関数
def load_tasks_from_db():
    conn = get_conn()  # DB接続
    cur = conn.cursor()  # カーソル作成
    cur.execute("SELECT name, completed, created_at, updated_at, tag FROM todos")  # データ取得
    rows = cur.fetchall()  # 結果をすべて取得
    cur.close()  # カーソルを閉じる
    conn.close()  # 接続を閉じる
    # 各行を辞書形式に変換してリストで返す
    return [{
        "name": r[0],
        "completed": r[1],
        "created_at": r[2],
        "updated_at": r[3],
        "tag": r[4] or "その他"  # タグがNULLなら「その他」にする
    } for r in rows]

#──────────────────────────────
# タスク（1行分）
#──────────────────────────────
class Task(Container):  # タスクを表すコンポーネント（Containerを継承）
    def __init__(self, task_name, task_status_change, task_delete,
                 tag="その他", created_at=None, updated_at=None, page=None):
        super().__init__()  # 親クラスの初期化
        self.page = page  # ページ参照（編集時に必要）

        self.task_name = task_name  # タスク名
        self.task_status_change = task_status_change  # 状態変更時のコールバック
        self.task_delete = task_delete  # 削除時のコールバック
        self.completed = False  # 完了状態フラグ
        self.tag = tag  # タグ
        now = datetime.now().strftime("%m月%d日")  # 現在日時（MM月DD日形式）
        self.created_at = created_at or now  # 作成日時
        self.updated_at = updated_at or now  # 更新日時

        self.is_editing = False  # 編集モードかどうか

        self.update_label = Text(f"編集: {self.updated_at}", size=8, color=Colors.GREY)  # 編集日時ラベル
        self.edit_name = TextField(expand=1, multiline=True)  # 編集用テキストフィールド
        self.edit_tag = ft.Dropdown(  # 編集用のタグ選択ドロップダウン（未使用）
            options=[],
            value=self.tag,
            width=120
        )
        self.show_delete = False  # 削除ボタン表示フラグ
        self.highlighted = False  # ハイライト状態
        self.bgcolor = None  # 背景色
        self.padding = 5  # パディング
        self.border_radius = 5  # 角丸

        # 削除ボタン（初期状態では非表示）
        self.delete_button = IconButton(icon=Icons.DELETE_OUTLINE, tooltip="削除", on_click=self.delete_clicked)

        # タスク名ボタン（クリックで編集、長押しで削除ボタン表示）
        self.task_label_button = ft.TextButton(
            content=Text(self.task_name, max_lines=1, overflow="ellipsis", width=200),
            on_click=self.edit_clicked,
            on_long_press=self.toggle_delete_icon,
        )

        # チェックボックス（完了状態の切り替え）
        self.checkbox = ft.Checkbox(
            value=False,
            on_change=self.status_changed,
        )

        # 通常表示ビュー（表示中のラベルや削除ボタン）
        self.display_view = Row(
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            controls=[
                Row(spacing=10, controls=[self.checkbox, self.task_label_button]),  # 左側（チェック+名前）
                Row(spacing=5, controls=[  # 右側（削除ボタン・更新日ラベル）
                    ft.AnimatedSwitcher(content=self.delete_button if self.show_delete else ft.Container()),
                    self.update_label,
                ])
            ]
        )

        # 編集ビュー（非表示）
        self.edit_view = Row(
            visible=False,  # 初期は非表示
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            controls=[
                self.edit_name,  # 名前入力欄
                # self.edit_tag,  # タグ選択欄（使ってない）
                ft.IconButton(icon=Icons.DONE_OUTLINE_OUTLINED, icon_color=Colors.GREEN, on_click=self.save_clicked)  # 保存ボタン
            ]
        )

        self.content = Column(controls=[self.display_view, self.edit_view])  # 表示と編集ビューをまとめたColumn
        self.content.expand = True  # 自動で広がる
        self.content.padding = 0
        self.controls = [self.content]  # Containerに表示する中身として設定

    def set_tag_options(self, tag_list):  # タグ選択肢を更新
        self.edit_tag.options = [ft.dropdown.Option(t) for t in tag_list]  # 選択肢を設定
        if self.tag in tag_list:
            self.edit_tag.value = self.tag  # 現在のタグに合わせる
        else:
            self.edit_tag.value = tag_list[0] if tag_list else None  # 無効なら先頭タグを設定
        self.update()  # 表示更新

    def edit_clicked(self, e):  # 編集モードに入る処理
        self.is_editing = True  # 編集中フラグを立てる
        self.edit_name.value = self.task_name  # 現在の名前をセット
        self.display_view.visible = False  # 表示ビューを非表示
        self.edit_view.visible = True  # 編集ビューを表示
        self.set_tag_options(self.page.todo_app.tag_list)  # タグを更新
        self.update()  # 表示更新
        self.page.on_click = self.on_page_click  # 外側クリックで終了処理を設定

    def on_page_click(self, e):  # ページクリック時の処理
        if self.is_editing:
            if e.control in [self.edit_name, self.edit_tag]:  # 編集欄をクリックした場合は無視
                return
            self.save_clicked(None)  # 保存処理を呼び出し
            self.page.on_click = None  # イベント解除

    def save_clicked(self, e):  # 編集内容を保存
        new_name = self.edit_name.value.strip()  # 新しい名前
        new_tag = self.edit_tag.value  # 新しいタグ
        if new_name:  # 名前が空でなければ保存
            self.task_name = new_name
            self.tag = new_tag
            self.task_label_button.content.value = new_name  # 表示名更新
            self.updated_at = datetime.now().strftime("%m月%d日")  # 更新日を現在時刻に
            self.update_label.value = f"編集: {self.updated_at}"  # ラベル更新
        self.display_view.visible = True  # 表示ビューを表示
        self.edit_view.visible = False  # 編集ビューを非表示
        self.is_editing = False  # 編集フラグ解除
        self.update()
        self.task_status_change(self)  # 外部に通知（DB保存など）

    def status_changed(self, e):  # チェックボックスの状態が変わった時
        self.completed = self.checkbox.value  # 完了状態更新
        self.task_status_change(self)  # 外部に通知

    def delete_clicked(self, e):  # 削除ボタンがクリックされた時
        self.task_delete(self)  # 外部に通知

    def toggle_delete_icon(self, e):  # 長押しで削除ボタンの表示切り替え
        self.show_delete = not self.show_delete  # 表示フラグ切り替え
        self.highlighted = self.show_delete  # ハイライト状態も同時に切り替え
        self.bgcolor = Colors.AMBER_100 if self.highlighted else None  # 背景色を変更
        self.update()

#──────────────────────────────
# タグ管理ダイアログ
#──────────────────────────────
class TagManager(AlertDialog):  # Fletのダイアログを継承したクラス
    def __init__(self, tag_list, on_tags_updated):  # tag_list: 現在のタグ一覧, on_tags_updated: タグ更新時のコールバック関数
        super().__init__()  # 親クラスの初期化
        self.title = Text("タグ管理", size=20)  # ダイアログのタイトル
        self.on_tags_updated = on_tags_updated  # タグ更新通知用のコールバックを保存

        self.tag_list = tag_list.copy()  # 渡されたタグ一覧をコピーして保持（元を壊さない）

        self.tag_inputs = []  # テキスト入力欄を格納するリスト
        self.container = Column(spacing=5, scroll="auto", height=250)  # 入力欄の列（スクロール可能）

        self.new_tag_field = TextField(hint_text="新しいタグを追加")  # 新規タグ入力欄
        self.add_button = ElevatedButton(text="追加", icon=Icons.ADD, on_click=self.add_new_tag)  # 追加ボタン

        # ダイアログの中身（タグ一覧と追加行を縦に並べる）
        self.content = Column([
            self.container,  # 既存タグの編集欄
            Row([self.new_tag_field, self.add_button], alignment=ft.MainAxisAlignment.CENTER),  # 新規追加入力欄とボタン
        ])

        self.actions = [
            OutlinedButton("閉じる", on_click=self.close_dialog)  # 閉じるボタン（右下に表示される）
        ]

        self.update_tag_list()  # 初期のタグ入力欄を生成

    def update_tag_list(self):  # 入力欄の一覧を更新
        self.container.controls.clear()  # 一度すべての入力欄を消す
        self.tag_inputs.clear()  # 入力欄リストも空に

        for idx, tag in enumerate(self.tag_list):  # タグごとに処理
            tf = TextField(value=tag, width=200)  # 入力欄を作成（タグ名を初期値に）
            tf.tag_index = idx  # 入力欄にインデックスを付ける（後で変更・削除に使う）
            tf.on_change = self.tag_text_changed  # テキスト変更時の処理を設定

            del_btn = IconButton(icon=Icons.DELETE, tooltip="タグ削除", on_click=self.delete_tag)  # 削除ボタンを作成
            del_btn.tag_index = idx  # こちらにもインデックスを付ける

            row = Row([tf, del_btn], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)  # 入力欄＋削除ボタンを1行にまとめる
            self.tag_inputs.append(tf)  # 入力欄をリストに追加
            self.container.controls.append(row)  # UIに追加

    def tag_text_changed(self, e):  # テキスト変更時の処理
        idx = e.control.tag_index  # どの入力欄か取得
        new_val = e.control.value.strip()  # 入力値の前後の空白を除去
        if new_val:  # 空でなければ
            self.tag_list[idx] = new_val  # タグリストを更新

    def delete_tag(self, e):  # タグ削除ボタンが押されたときの処理
        idx = e.control.tag_index  # 押されたボタンのインデックス取得
        del self.tag_list[idx]  # 指定インデックスのタグを削除
        self.update_tag_list()  # 入力欄を更新して再描画

    def add_new_tag(self, e):  # 新しいタグを追加する処理
        new_tag = self.new_tag_field.value.strip()  # 入力されたタグ名
        if new_tag and new_tag not in self.tag_list:  # 空でなく重複もしていなければ
            self.tag_list.append(new_tag)  # タグを追加
            self.new_tag_field.value = ""  # 入力欄をクリア
            self.update_tag_list()  # 入力欄を更新

    def close_dialog(self, e):  # 閉じるボタン押下時の処理
        self.on_tags_updated(self.tag_list)  # 更新後のタグをコールバックで通知
        self.open = False  # ダイアログを閉じる
        self.update()  # 表示更新

#──────────────────────────────                          # 区切り線（視認性のための装飾）
# Todo アプリ全体                                         # アプリ本体を構成するクラス
#──────────────────────────────
class TodoApp(Column):                                    # Flet の Column を継承して UI を縦に並べる
    def __init__(self, page):                             # 初期化（page: Fletのページオブジェクト）
        super().__init__()                                # 親クラスの初期化

        self.page = page                                  # ページオブジェクトを保持
        self.tag_list = DEFAULT_TAGS.copy()               # デフォルトタグのコピーを保持

        self.tag_manager_button = ElevatedButton(text="タグ管理", icon=Icons.LABEL, on_click=self.open_tag_manager)  # タグ管理ダイアログ起動ボタン

        self.tag_tabs = Tabs(                             # タグ別フィルタ用タブ
            selected_index=0,                             # 最初に選ばれているタブ（先頭）
            on_change=self.filter_changed,                # タブ変更時の処理
            tabs=[Tab(text=t) for t in self.tag_list]     # タグ名からタブを作成
        )

        self.status_tabs = Tabs(                          # ステータス（アクティブ/完了）フィルタ用タブ
            selected_index=0,                             # 最初に「アクティブ」を選択
            on_change=self.filter_changed,                # タブ変更時の処理
            tabs=[Tab(text="アクティブ"), Tab(text="完了")]  # 2つの状態を切り替える
        )

        self.new_task = TextField(hint_text="ここに内容記入", on_submit=self.add_clicked, expand=True, multiline=True)  # 新規タスク入力欄

        self.all_tasks = []                               # 全タスクを保持するリスト
        self.tasks = Column(spacing=10, expand=True)      # フィルタ済みタスクを表示するColumn

        self.width = 700                                  # アプリ全体の幅

        self.controls = [                                 # UIに表示するコントロール群
            Row([Text("タグ付きToDoリスト", theme_style=ft.TextThemeStyle.HEADLINE_MEDIUM)],  # タイトル行
                alignment=ft.MainAxisAlignment.CENTER),
            Row([self.new_task, IconButton(icon=Icons.ADD, on_click=self.add_clicked)]),      # 入力欄と追加ボタン
            Row([self.tag_tabs, self.tag_manager_button]),                                     # タグフィルターとタグ管理ボタン
            self.status_tabs,                                                                  # ステータスタブ
            Column(                                                                            # メインの表示エリア
                spacing=25,
                expand=True,
                controls=[
                    self.tasks,                                                                # タスク一覧
                    Row(
                        alignment=ft.MainAxisAlignment.END,
                        controls=[
                            OutlinedButton(text="完了タスクを削除", on_click=self.clear_clicked),  # 一括削除ボタン
                        ],
                    ),
                ],
            ),
        ]

    def open_tag_manager(self, e):                         # タグ管理ボタンが押されたとき
        self.tag_manager = TagManager(self.tag_list, self.on_tags_updated)  # ダイアログ作成（現在のタグと更新コールバックを渡す）
        self.page.dialog = self.tag_manager                # ページにダイアログをセット
        self.tag_manager.open = True                       # ダイアログを開く
        self.page.update()                                 # UI更新

    def on_tags_updated(self, new_tags):                   # タグが更新されたときに呼ばれる
        if not new_tags:                                   # 空のタグリストなら
            new_tags = ["その他"]                           # デフォルトのタグを追加
        self.tag_list = new_tags                           # 新しいタグリストを保存

        # タブ再構築
        self.tag_tabs.tabs.clear()                         # 既存のタブをクリア
        for t in self.tag_list:                            # 新しいタグごとにタブを作る
            self.tag_tabs.tabs.append(Tab(text=t))
        self.tag_tabs.selected_index = 0                   # 先頭のタブを選択
        self.tag_tabs.update()                             # タブ更新

        # タスクタグが存在しないタグなら「その他」に変更
        for task in self.all_tasks:
            if task.tag not in self.tag_list:              # タグが無効になった場合
                task.tag = "その他"                         # タグを「その他」に変更
                task.update()                              # タスクUI更新

        self.filter_tasks()                                # フィルタを再適用
        self.page.update()                                 # ページ全体更新

    def reload_tasks_from_db(self):                        # DBからタスクを読み込む
        self.all_tasks.clear()                             # 現在のタスクリストをクリア
        for data in load_tasks_from_db():                  # DBからデータ取得
            task = self.create_task_from_data(data)        # 各データを Task に変換
            self.all_tasks.append(task)
        self.filter_tasks()                                # フィルタ適用して表示更新

    def create_task_from_data(self, data):                 # DBデータから Task インスタンスを生成
        task = Task(
            task_name=data["name"],
            task_status_change=self.task_status_change,
            task_delete=self.task_delete,
            tag=data.get("tag", "その他"),
            created_at=data.get("created_at"),
            updated_at=data.get("updated_at"),
            page=self.page
        )
        task.checkbox.value = data["completed"]            # チェック状態設定
        task.completed = data["completed"]
        return task

    def add_clicked(self, e):  # タスク追加ボタンがクリックされたときの処理
        name = self.new_task.value.strip()  # 入力されたタスク名を取得（前後の空白除去）
        if 0 <= self.tag_tabs.selected_index < len(self.tag_list):  # 選択されているタグのインデックスが有効か確認
            tag = self.tag_list[self.tag_tabs.selected_index]  # 選択されたタグを取得
        else:
            tag = "その他"  # 無効な場合は「その他」タグを使用

        if name:  # タスク名が空でない場合に処理を実行
            task = Task(name, self.task_status_change, self.task_delete, tag=tag, page=self.page)  # 新しいタスクを作成
            self.all_tasks.append(task)  # タスクリストに追加
            self.new_task.value = ""  # 入力フィールドをクリア
            self.new_task.focus()  # 入力フィールドにフォーカスを戻す
            self.filter_tasks()  # タスク表示をフィルターに基づいて更新
            save_tasks_to_db(self.all_tasks)  # 全タスクをデータベースに保存

    def task_status_change(self, task):  # タスクの完了状態が変更されたときの処理
        self.filter_tasks()  # タスク表示を更新
        save_tasks_to_db(self.all_tasks)  # タスクの状態をデータベースに保存

    def task_delete(self, task):  # タスクが削除されたときの処理
        if task in self.all_tasks:  # 指定されたタスクがリストに存在する場合
            self.all_tasks.remove(task)  # タスクをリストから削除
        self.filter_tasks()  # タスク表示を更新
        save_tasks_to_db(self.all_tasks)  # データベースを更新

    def filter_changed(self, e):  # ステータスやタグフィルターが変更されたときの処理
        self.filter_tasks()  # タスク表示を更新

    def clear_clicked(self, e):  # 「完了タスクをクリア」ボタンがクリックされたときの処理
        self.all_tasks = [t for t in self.all_tasks if not t.completed]  # 完了していないタスクだけを残す
        self.filter_tasks()  # タスク表示を更新
        save_tasks_to_db(self.all_tasks)  # データベースを更新

    def filter_tasks(self):  # 現在のフィルター条件に基づいてタスクを表示
        self.tasks.controls.clear()  # 現在のタスク表示をクリア

        if 0 <= self.tag_tabs.selected_index < len(self.tag_list):  # 有効なタグが選択されている場合
            selected_tag = self.tag_list[self.tag_tabs.selected_index]  # 選択されたタグを取得
        else:
            selected_tag = None  # 無効な場合はタグフィルターなし

        selected_status = self.status_tabs.tabs[self.status_tabs.selected_index].text  # 選択中のステータス（アクティブ／完了）を取得

        filtered = self.all_tasks  # フィルタリング対象の全タスク
        if selected_tag:  # タグフィルターが指定されている場合
            filtered = [t for t in filtered if t.tag == selected_tag]  # タグに一致するタスクのみ残す

        if selected_status == "アクティブ":  # ステータスがアクティブの場合
            visible_tasks = [t for t in filtered if not t.completed]  # 完了していないタスクだけ表示
        else:
            visible_tasks = [t for t in filtered if t.completed]  # 完了済みタスクのみ表示

        self.tasks.controls.extend(visible_tasks)  # フィルターされたタスクを表示用に追加
        self.update()  # 画面を更新


def main(page: ft.Page):  # アプリのエントリーポイント
    page.title = "ToDoリスト"  # アプリのタイトル設定
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER  # 水平方向の中央揃え
    page.scroll = ft.ScrollMode.ADAPTIVE  # スクロールモードを自動調整に設定

    todo_app = TodoApp(page)  # Todoアプリインスタンスを作成
    page.todo_app = todo_app  # ページにアプリを紐づけ（後で参照可能に）
    page.add(todo_app)  # アプリをページに追加して表示
    todo_app.reload_tasks_from_db()  # DBからタスクを読み込み
    todo_app.update()  # 画面を更新

if __name__ == "__main__":  # このファイルが直接実行された場合
    ft.app(target=main, port=int(os.environ.get("PORT", 8550)), host="0.0.0.0")  # Fletアプリを指定ポートで起動
