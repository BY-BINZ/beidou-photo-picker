"""Free desktop entry point; standard library UI, no PyQt/model dependency."""
import queue
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from .core import export_files, match_files


class App:
    def __init__(self, root):
        self.root, self.plan, self.busy = root, None, False
        self.events = queue.Queue()
        root.title('摄影师一键选图 · 北斗 免费版 0.1.0')
        root.geometry('1020x680')
        root.minsize(760, 540)
        root.protocol('WM_DELETE_WINDOW', self.close)
        style = ttk.Style(root)
        style.configure('TButton', padding=8)
        style.configure('TLabel', font=('Microsoft YaHei UI', 10))
        self.frame = ttk.Frame(root, padding=22)
        self.frame.pack(fill='both', expand=True)
        ttk.Label(self.frame, text='摄影师一键选图 · 北斗', font=('Microsoft YaHei UI', 22, 'bold')).pack(anchor='w')
        ttk.Label(self.frame, text='免费社区版：小图找原图 · 保留分类目录 · 复制校验与导出清单').pack(anchor='w', pady=(6, 18))
        self.variables, self.controls = {}, []
        for key, label in [('selected', '选好的小图'), ('originals', '高清图 / RAW'), ('output', '导出到新目录')]:
            row = ttk.Frame(self.frame)
            row.pack(fill='x', pady=5)
            ttk.Label(row, text=label, width=17).pack(side='left')
            variable = tk.StringVar()
            variable.trace_add('write', self.invalidate)
            self.variables[key] = variable
            entry = ttk.Entry(row, textvariable=variable)
            entry.pack(side='left', fill='x', expand=True, padx=8)
            button = ttk.Button(row, text='选择文件夹', command=lambda k=key: self.browse(k))
            button.pack(side='left')
            self.controls.extend([entry, button])
        actions = ttk.Frame(self.frame)
        actions.pack(fill='x', pady=14)
        self.scan = ttk.Button(actions, text='① 查找并预览', command=self.match)
        self.scan.pack(side='left', padx=(0, 12))
        self.copy = ttk.Button(actions, text='② 保留目录导出', command=self.export, state='disabled')
        self.copy.pack(side='left')
        self.controls.append(self.scan)
        self.status = tk.StringVar(value='请选择小图、原图和独立输出目录。原文件不会移动或删除。')
        ttk.Label(self.frame, textvariable=self.status, wraplength=930).pack(anchor='w', pady=8)
        columns = ('selected', 'status', 'original')
        self.table = ttk.Treeview(self.frame, columns=columns, show='headings')
        for name, label, width in [('selected', '小图相对路径', 310), ('status', '匹配结果', 120), ('original', '原图 / 冲突说明', 440)]:
            self.table.heading(name, text=label)
            self.table.column(name, width=width)
        self.table.pack(fill='both', expand=True)
        self.table.bind('<<TreeviewSelect>>', self.details)
        ttk.Label(self.frame, text='相同编号有多个候选时会标记“需核对”，不会自动选第一张；免费版不包含 AI 筛选、分款或命名。', wraplength=930).pack(anchor='w', pady=(12, 0))
        root.after(120, self.poll)

    def invalidate(self, *_):
        self.plan = None
        if hasattr(self, 'copy'):
            self.copy.configure(state='disabled')

    def browse(self, key):
        path = filedialog.askdirectory(parent=self.root, mustexist=key != 'output')
        if path:
            self.variables[key].set(path)

    def run(self, function):
        if self.busy:
            return
        self.busy = True
        self.copy.configure(state='disabled')
        for control in self.controls:
            control.configure(state='disabled')
        def work():
            try:
                self.events.put(('result', function()))
            except Exception as error:
                self.events.put(('error', str(error)))
        threading.Thread(target=work, daemon=True).start()

    def match(self):
        selected, originals = (self.variables[k].get().strip() for k in ('selected', 'originals'))
        if not selected or not originals:
            messagebox.showinfo('选择文件夹', '请先选择小图和原图目录。', parent=self.root)
            return
        self.plan = None
        self.table.delete(*self.table.get_children())
        self.status.set('正在扫描文件名，请稍候……')
        self.run(lambda: ('plan', match_files(selected, originals)))

    def export(self):
        if not self.plan:
            return
        output = self.variables['output'].get().strip()
        if not output:
            messagebox.showinfo('选择文件夹', '请选择独立输出目录。', parent=self.root)
            return
        plan = self.plan
        self.status.set('正在复制并校验；请勿断开存储设备。')
        self.run(lambda: ('export', export_files(plan, output,
                 lambda current, total: self.events.put(('progress', f'正在复制并校验：{current}/{total}')))))

    def details(self, _):
        if self.plan and self.table.selection():
            row = self.plan.rows[int(self.table.selection()[0])]
            self.status.set('候选：' + '；'.join(row.candidates) if row.candidates else '未找到对应原图，请核对原图目录。')

    def poll(self):
        try:
            while True:
                event, data = self.events.get_nowait()
                if event == 'progress':
                    self.status.set(data)
                    continue
                self.busy = False
                for control in self.controls:
                    control.configure(state='normal')
                if event == 'error':
                    self.status.set('任务失败：' + data)
                    messagebox.showerror('任务失败', data, parent=self.root)
                else:
                    kind, value = data
                    if kind == 'plan':
                        self.plan = value
                        labels = {'matched': '已匹配', 'missing': '未找到', 'ambiguous': '需核对'}
                        for i, row in enumerate(value.rows):
                            self.table.insert('', 'end', iid=str(i), values=(row.relative, labels[row.status], row.original or f'{len(row.candidates)} 个候选'))
                        count = value.summary()
                        self.status.set(f'共 {len(value.rows)} 张：已匹配 {count["matched"]}，未找到 {count["missing"]}，需核对 {count["ambiguous"]}。只导出已匹配文件。')
                    else:
                        self.status.set(f'导出完成：成功 {value["copied"]}，待核对 {value["unresolved"]}，失败 {value["failed"]}。清单：{value["log"]}')
                        messagebox.showinfo('导出结果', self.status.get(), parent=self.root)
                self.copy.configure(state='normal' if self.plan and self.plan.summary()['matched'] else 'disabled')
        except queue.Empty:
            pass
        self.root.after(120, self.poll)

    def close(self):
        if self.busy:
            messagebox.showinfo('任务进行中', '请等待当前任务结束后关闭，避免复制中断。', parent=self.root)
        else:
            self.root.destroy()


def main():
    root = tk.Tk()
    App(root)
    root.mainloop()
