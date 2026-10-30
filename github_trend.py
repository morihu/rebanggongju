import customtkinter as ctk
import tkinter as tk
from tkinter import ttk
import webbrowser
import requests
from bs4 import BeautifulSoup
import re
import threading

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

class GitHubTrendApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("GitHub 热榜工具")
        self.geometry("1350x700")
        self.minsize(1050, 500)

        self.time_range = "daily"

        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }

        self.setup_styles()
        self.create_widgets()
        
        # 启动时自动加载
        self.start_loading_thread()

    def setup_styles(self):
        self.style = ttk.Style()
        self.style.theme_use("default")
        self.style.configure("Treeview", background="#2b2b2b", foreground="#e0e0e0",
                             rowheight=35, fieldbackground="#2b2b2b", borderwidth=0,
                             font=("Microsoft YaHei", 10))
        self.style.map("Treeview", background=[('selected', '#1f538d')], foreground=[('selected', 'white')])
        self.style.configure("Treeview.Heading", background="#1e1e1e", foreground="#ffffff",
                             relief="flat", font=("Microsoft YaHei", 11, "bold"))
        self.style.map("Treeview.Heading", background=[('active', '#333333')])

    def create_widgets(self):
        # ================= 顶部控制区 =================
        self.top_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.top_frame.pack(fill="x", padx=15, pady=(15, 5))

        # 时间范围切换
        self.seg_button = ctk.CTkSegmentedButton(
            self.top_frame, values=["今日", "本周", "本月"],
            command=self.switch_range, font=("Microsoft YaHei", 12)
        )
        self.seg_button.set("今日")
        self.seg_button.pack(side="left", padx=(0, 15))

        # 刷新按钮
        self.btn_refresh = ctk.CTkButton(
            self.top_frame, text="🔄 刷新", width=100, 
            command=self.start_loading_thread, font=("Microsoft YaHei", 12)
        )
        self.btn_refresh.pack(side="left", padx=5)

        # 状态信息 (右侧)
        self.status_label = ctk.CTkLabel(
            self.top_frame, text="就绪", text_color="#aaaaaa", font=("Microsoft YaHei", 12)
        )
        self.status_label.pack(side="right", padx=10)

        # ================= 表格区 =================
        self.table_frame = ctk.CTkFrame(self, fg_color="#2b2b2b", corner_radius=8)
        self.table_frame.pack(fill="both", expand=True, padx=15, pady=(5, 15))

        columns = ("rank", "name", "star", "desc", "url")
        self.tree = ttk.Treeview(self.table_frame, columns=columns, show="headings", style="Treeview")

        self.tree.heading("rank", text="排名")
        self.tree.heading("name", text="项目名称")
        self.tree.heading("star", text="星标")
        self.tree.heading("desc", text="描述")
        self.tree.heading("url", text="链接")

        self.tree.column("rank", width=60, anchor="center")
        self.tree.column("name", width=250, anchor="w")
        self.tree.column("star", width=100, anchor="center")
        self.tree.column("desc", width=700, anchor="w")
        self.tree.column("url", width=100, anchor="center")

        scroll_y = ctk.CTkScrollbar(self.table_frame, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scroll_y.set)
        scroll_y.pack(side="right", fill="y", padx=(0, 5), pady=5)
        
        self.tree.pack(fill="both", expand=True, padx=5, pady=5)

        self.tree.tag_configure("oddrow", background="#2b2b2b")
        self.tree.tag_configure("evenrow", background="#242424")
        self.tree.tag_configure("hover", background="#3a4757")

        # ================= 事件绑定区 =================
        self.hover_row = None
        self.tree.bind("<Motion>", self.on_mouse_move)
        self.tree.bind("<Leave>", self.on_mouse_leave)
        self.tree.bind("<Button-1>", self.on_single_click) 
        self.tree.bind("<Motion>", self.change_cursor, add="+")

    def change_cursor(self, event):
        """鼠标在链接列时变成手型"""
        region = self.tree.identify("region", event.x, event.y)
        column = self.tree.identify_column(event.x)
        if region == "cell" and column == "#5":
            self.tree.configure(cursor="hand2")
        else:
            self.tree.configure(cursor="")

    def parse_star(self, star_str):
        if not star_str:
            return 0
        s = star_str.strip().replace(",", "")
        match = re.search(r"([0-9.]+)(k?)", s, re.IGNORECASE)
        if not match:
            return 0
        num = float(match.group(1))
        unit = match.group(2).lower()
        if unit == "k":
            return int(num * 1000)
        return int(num)

    def switch_range(self, value):
        mapping = {"今日": "daily", "本周": "weekly", "本月": "monthly"}
        self.time_range = mapping[value]
        self.start_loading_thread()

    def start_loading_thread(self):
        """启动线程，防止网络请求卡死界面"""
        self.btn_refresh.configure(state="disabled")
        self.seg_button.configure(state="disabled")
        self.status_label.configure(text="⏳ 正在加载...", text_color="#ffcc44")
        self.btn_refresh.configure(text="加载中...")
        
        # 清空表格
        self.tree.delete(*self.tree.get_children())
        
        threading.Thread(target=self.load_data, daemon=True).start()

    def load_data(self):
        try:
            url = f"https://github.com/trending?since={self.time_range}"
            # 直接请求，不带代理
            resp = requests.get(url, headers=self.headers, timeout=15)
            soup = BeautifulSoup(resp.text, "html.parser")
            items = soup.select("article.Box-row")

            repo_list = []
            for item in items:
                name_tag = item.select_one("h2 a")
                full_name = name_tag.get_text(strip=True).replace("\n", "").replace(" ", "")
                link = "https://github.com" + name_tag["href"]
                desc_tag = item.select_one("p")
                desc = desc_tag.get_text(strip=True) if desc_tag else "暂无描述"
                star_tag = item.select_one('a[href$="/stargazers"]')
                star_text = star_tag.get_text(strip=True) if star_tag else "0"
                star_num = self.parse_star(star_text)
                repo_list.append({
                    "name": full_name,
                    "star_text": star_text,
                    "star_num": star_num,
                    "desc": desc,
                    "url": link
                })

            repo_list.sort(key=lambda x: x["star_num"], reverse=True)

            # 使用 after 更新主线程 UI
            def update_tree():
                for index, repo in enumerate(repo_list):
                    tag = "evenrow" if index % 2 == 0 else "oddrow"
                    self.tree.insert("", tk.END, values=(
                        index + 1, repo["name"], repo["star_text"], repo["desc"], "🔗 点击打开"
                    ), tags=(tag,), iid=repo["url"])
                self.status_label.configure(text=f"✔️ 成功获取 {len(repo_list)} 条", text_color="#55ff55")
            
            self.after(0, update_tree)
            
        except requests.exceptions.Timeout:
            self.after(0, lambda: self.status_label.configure(text="❌ 请求超时，请检查网络", text_color="#ff5555"))
        except requests.exceptions.ConnectionError:
            self.after(0, lambda: self.status_label.configure(text="❌ 连接失败，请检查网络", text_color="#ff5555"))
        except Exception as e:
            print(f"详细错误: {e}") 
            self.after(0, lambda: self.status_label.configure(text="❌ 数据解析异常", text_color="#ff5555"))
        finally:
            # 恢复按钮状态
            self.after(0, lambda: self.btn_refresh.configure(state="normal", text="🔄 刷新"))
            self.after(0, lambda: self.seg_button.configure(state="normal"))

    def on_mouse_move(self, event):
        row = self.tree.identify_row(event.y)
        if row != self.hover_row:
            if self.hover_row:
                children = self.tree.get_children()
                if self.hover_row in children:
                    idx = children.index(self.hover_row)
                    tag = "evenrow" if idx % 2 == 0 else "oddrow"
                    self.tree.item(self.hover_row, tags=(tag,))
            
            self.hover_row = row
            if row:
                self.tree.item(row, tags=("hover",))

    def on_mouse_leave(self, event):
        if self.hover_row:
            children = self.tree.get_children()
            if self.hover_row in children:
                idx = children.index(self.hover_row)
                tag = "evenrow" if idx % 2 == 0 else "oddrow"
                self.tree.item(self.hover_row, tags=(tag,))
            self.hover_row = None

    def on_single_click(self, event):
        region = self.tree.identify("region", event.x, event.y)
        column = self.tree.identify_column(event.x)
        if region == "cell" and column == "#5":
            row_id = self.tree.identify_row(event.y)
            if row_id and row_id.startswith("https://"):
                webbrowser.open(row_id)


if __name__ == "__main__":
    app = GitHubTrendApp()
    app.mainloop()