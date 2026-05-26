import os
import shutil
import tkinter as tk
from tkinter import filedialog, messagebox, colorchooser
import pygame
import json

# Событие окончания трека для автоматического перехода
SONG_END = pygame.USEREVENT + 1

class GOR_Music_Prime:
    def __init__(self, root):
        self.root = root
        self.root.title("GOR Music Prime - V3 Ultra Pro Max SPEED EDITION")
        self.root.geometry("1000x900")
        self.root.configure(bg="#0f0f17")

        # Инициализация звукового движка с увеличенным буфером для скорости
        try:
            pygame.init()
            # Буфер 4096 убирает задержки при воспроизведении
            pygame.mixer.pre_init(44100, -16, 2, 4096)
            pygame.mixer.init()
            pygame.mixer.music.set_endevent(SONG_END)
        except Exception as e:
            print(f"Системная ошибка звука: {e}")

        # Плавность прокрутки категорий
        self.target_scroll_pos = 0.0
        self.scroll_speed = 0.1 

        # Данные и кэш
        self.config_file = "gmp_config.json"
        self.settings = self.load_settings()
        self.source_dir = self.settings.get("last_folder", "")
        self.buttons_data = self.settings.get("buttons", [])
        
        self.playlist = []
        self.current_index = 0
        self.is_paused = False
        self.song_length = 0
        self.current_pos_offset = 0 # Точка отсчета для быстрой перемотки

        # Инициализация интерфейса
        self.setup_ui()
        self.setup_keyboard_controls()
        self.check_event()
        self.render_buttons()
        self.update_smooth_scroll()
        self.refresh_progress_bar()
        
        # Быстрый старт последней папки
        if self.source_dir and os.path.exists(self.source_dir):
            self.root.after(300, lambda: self.load_playlist(self.source_dir))

    def load_settings(self):
        """Загрузка настроек с проверкой ошибок"""
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except: return {}
        return {}

    def save_all(self):
        """Сохранение состояния"""
        data = {"last_folder": self.source_dir, "buttons": self.buttons_data}
        try:
            with open(self.config_file, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=4)
        except Exception as e:
            print(f"Ошибка сохранения: {e}")

    def setup_keyboard_controls(self):
        """Горячие клавиши для управления"""
        self.root.bind("<space>", lambda e: self.toggle_pause())
        self.root.bind("<Right>", lambda e: self.next_song())
        self.root.bind("<Left>", lambda e: self.prev_song())
        self.root.bind("<Up>", lambda e: self.volume_scale.set(self.volume_scale.get() + 5))
        self.root.bind("<Down>", lambda e: self.volume_scale.set(self.volume_scale.get() - 5))

    def setup_ui(self):
        # HEADER (Верхняя панель)
        header = tk.Frame(self.root, bg="#1a1b26", pady=12)
        header.pack(side=tk.TOP, fill=tk.X)
        
        tk.Label(header, text="GOR Music Prime", fg="#7aa2f7", bg="#1a1b26", 
                 font=("Arial", 13, "bold")).pack(side=tk.LEFT, padx=25)

        tk.Button(header, text="📁 ПАПКА", command=self.select_folder, 
                  bg="#3b4261", fg="#c0caf5", relief=tk.FLAT, font=("Arial", 9, "bold"),
                  padx=15, cursor="hand2").pack(side=tk.LEFT, padx=10)
        
        tk.Button(header, text="➕ КАТЕГОРИЯ", command=self.open_editor, 
                  bg="#9ece6a", fg="#1a1b26", relief=tk.FLAT, font=("Arial", 9, "bold"),
                  padx=15, cursor="hand2").pack(side=tk.RIGHT, padx=25)

        # MAIN DISPLAY (Экран плеера)
        self.main_display = tk.Frame(self.root, bg="#0f0f17")
        self.main_display.pack(expand=True, fill=tk.BOTH)

        self.label_progress = tk.Label(self.main_display, text="0 / 0", 
                                      fg="#7aa2f7", bg="#0f0f17", font=("Consolas", 48, "bold"))
        self.label_progress.pack(pady=(40, 0))

        self.label_song = tk.Label(self.main_display, text="ВЫБЕРИТЕ МУЗЫКУ", 
                                   fg="#c0caf5", bg="#0f0f17", wraplength=850, 
                                   font=("Arial", 22, "bold"), justify="center")
        self.label_song.pack(pady=10)

        # PROGRESS BAR AREA (Интерактивная полоска перемотки)
        self.progress_container = tk.Frame(self.main_display, bg="#0f0f17")
        self.progress_container.pack(fill=tk.X, padx=100, pady=20)

        self.progress_canvas = tk.Canvas(self.progress_container, bg="#1a1b26", height=12, 
                                         highlightthickness=0, cursor="hand2")
        self.progress_canvas.pack(fill=tk.X)
        
        # Отрисовка элементов таймлайна
        self.progress_bar_fill = self.progress_canvas.create_rectangle(0, 4, 0, 8, fill="#f7768e", outline="")
        self.progress_handle = self.progress_canvas.create_oval(-6, 0, 6, 12, fill="white", outline="#f7768e")
        
        # События клика и перетаскивания для перемотки
        self.progress_canvas.bind("<Button-1>", self.seek_audio)
        self.progress_canvas.bind("<B1-Motion>", self.seek_audio)

        self.time_label = tk.Label(self.progress_container, text="00:00 / 00:00", 
                                   fg="#565f89", bg="#0f0f17", font=("Consolas", 10))
        self.time_label.pack(pady=5)

        # CONTROLS (Кнопки управления)
        controls = tk.Frame(self.root, bg="#16161e", pady=20)
        controls.pack(fill=tk.X)

        vol_frame = tk.Frame(controls, bg="#16161e")
        vol_frame.pack(fill=tk.X, padx=250)
        self.volume_scale = tk.Scale(vol_frame, from_=0, to=100, orient=tk.HORIZONTAL, 
                                     bg="#16161e", fg="#bb9af7", highlightthickness=0, 
                                     troughcolor="#1a1b26", command=self.set_volume)
        self.volume_scale.set(75)
        self.volume_scale.pack(fill=tk.X)

        btn_row = tk.Frame(controls, bg="#16161e", pady=10)
        btn_row.pack()
        
        tk.Button(btn_row, text="⏮", command=self.prev_song, bg="#24283b", fg="white", 
                  font=("Arial", 22), relief=tk.FLAT, width=4, cursor="hand2").grid(row=0, column=0, padx=15)
        
        self.btn_pause = tk.Button(btn_row, text="⏸ ПАУЗА", command=self.toggle_pause, 
                                   bg="#e0af68", fg="#1a1b26", font=("Arial", 12, "bold"), 
                                   relief=tk.FLAT, width=15, cursor="hand2")
        self.btn_pause.grid(row=0, column=1, padx=15)

        tk.Button(btn_row, text="⏭", command=self.next_song, bg="#24283b", fg="white", 
                  font=("Arial", 22), relief=tk.FLAT, width=4, cursor="hand2").grid(row=0, column=2, padx=15)

        # CATEGORY BUTTONS (Нижняя лента)
        scroll_container = tk.Frame(self.root, bg="#0f0f17", pady=20)
        scroll_container.pack(side=tk.BOTTOM, fill=tk.X)

        self.canvas = tk.Canvas(scroll_container, bg="#0f0f17", height=140, highlightthickness=0)
        self.canvas.pack(fill=tk.X, padx=20)

        self.btn_holder = tk.Frame(self.canvas, bg="#0f0f17")
        self.canvas.create_window((0, 0), window=self.btn_holder, anchor="nw")
        self.btn_holder.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.root.bind_all("<MouseWheel>", self._on_smooth_mousewheel)

    def refresh_progress_bar(self):
        """Оптимизированное обновление прогресса без тормозов"""
        if pygame.mixer.music.get_busy() and not self.is_paused:
            # Считаем текущее время: позиция в текущем куске + оффсет перемотки
            current_time = (pygame.mixer.music.get_pos() / 1000) + self.current_pos_offset
            
            if self.song_length > 0:
                width = self.progress_canvas.winfo_width()
                if width > 1:
                    ratio = min(current_time / self.song_length, 1.0)
                    px = ratio * width
                    
                    # Синхронное обновление полоски и кружка
                    self.progress_canvas.coords(self.progress_bar_fill, 0, 4, px, 8)
                    self.progress_canvas.coords(self.progress_handle, px-6, 0, px+6, 12)
                    
                    self.time_label.config(text=f"{self.format_time(current_time)} / {self.format_time(self.song_length)}")

        # Интервал 300мс идеален для экономии ресурсов
        self.root.after(300, self.refresh_progress_bar)

    def seek_audio(self, event):
        """Мгновенная перемотка при взаимодействии"""
        if self.playlist and self.song_length > 0:
            width = self.progress_canvas.winfo_width()
            # Ограничиваем координаты границами полоски
            ratio = max(0, min(event.x / width, 1))
            target_time = self.song_length * ratio
            
            # Сохраняем новую точку отсчета для корректного отображения времени
            self.current_pos_offset = target_time 
            
            # Перезапуск с нужной секунды
            pygame.mixer.music.play(start=target_time)
            if self.is_paused:
                self.is_paused = False
                self.btn_pause.config(text="⏸ ПАУЗА", bg="#e0af68")

    def format_time(self, seconds):
        """Преобразование секунд в формат 00:00"""
        m, s = divmod(int(seconds), 60)
        return f"{m:02}:{s:02}"

    def _on_smooth_mousewheel(self, event):
        """Логика для плавной прокрутки ленты"""
        delta = -(event.delta / 120) * 0.08
        self.target_scroll_pos = max(0, min(1, self.canvas.xview()[0] + delta))

    def update_smooth_scroll(self):
        """Цикл плавной анимации прокрутки"""
        curr = self.canvas.xview()[0]
        diff = self.target_scroll_pos - curr
        if abs(diff) > 0.0001:
            self.canvas.xview_moveto(curr + diff * self.scroll_speed)
        self.root.after(10, self.update_smooth_scroll)

    def render_buttons(self):
        """Отрисовка всех кнопок категорий"""
        for w in self.btn_holder.winfo_children(): w.destroy()
        
        if not self.buttons_data:
            tk.Label(self.btn_holder, text="Добавьте категории через [+]", 
                     fg="#565f89", bg="#0f0f17").pack(pady=45, padx=350)

        for i, b in enumerate(self.buttons_data):
            btn = tk.Button(self.btn_holder, text=b['name'].upper(), bg=b['color'], 
                            fg="#1a1b26", font=("Arial", 11, "bold"), height=3, width=20, 
                            relief=tk.FLAT, cursor="hand2", command=lambda d=b: self.handle_sort(d))
            btn.pack(side=tk.LEFT, padx=12, pady=15)
            
            # Привязка меню редактирования на ПКМ
            m = tk.Menu(self.root, tearoff=0, bg="#1a1b26", fg="white")
            m.add_command(label="📝 Изменить", command=lambda idx=i: self.open_editor(idx))
            m.add_command(label="🗑 Удалить", command=lambda idx=i: self.delete_button(idx))
            btn.bind("<Button-3>", lambda e, menu=m: menu.post(e.x_root, e.y_root))

    def handle_sort(self, data):
        """Копирование файла в выбранную категорию"""
        if not self.playlist: return
        full_path = self.playlist[self.current_index]
        target = os.path.join(self.source_dir, data['name']) if data['auto'] else data['path']
        
        try:
            os.makedirs(target, exist_ok=True)
            shutil.copy2(full_path, os.path.join(target, os.path.basename(full_path)))
            
            # Визуальный отклик (мигание названием)
            self.label_song.config(fg=data['color'])
            self.root.after(150, lambda: [self.label_song.config(fg="#c0caf5"), self.next_song()])
        except Exception as e:
            messagebox.showerror("Ошибка", str(e))

    def load_playlist(self, folder):
        """Сканирование папки на наличие музыки"""
        valid = ('.mp3', '.wav', '.ogg', '.opus', '.flac', '.m4a')
        self.playlist = []
        
        for r_dir, dirs, files in os.walk(folder):
            for f in files:
                if f.lower().endswith(valid):
                    self.playlist.append(os.path.join(r_dir, f))
        
        if self.playlist:
            self.current_index = 0
            self.play_song()
        else:
            self.label_song.config(text="МУЗЫКА НЕ НАЙДЕНА")

    def select_folder(self):
        """Диалог выбора папки"""
        folder = filedialog.askdirectory()
        if folder:
            self.source_dir = folder
            self.save_all()
            self.load_playlist(folder)

    def play_song(self):
        """Загрузка и запуск трека"""
        if not self.playlist: return
        path = self.playlist[self.current_index]
        try:
            # Очищаем память от предыдущего трека
            pygame.mixer.music.unload()
            pygame.mixer.music.load(path)
            
            # Быстрое получение длины трека через Sound
            snd = pygame.mixer.Sound(path)
            self.song_length = snd.get_length()
            self.current_pos_offset = 0
            
            pygame.mixer.music.play()
            self.is_paused = False
            self.btn_pause.config(text="⏸ ПАУЗА", bg="#e0af68")
            self.update_ui()
        except: 
            # Если файл поврежден, переходим к следующему
            self.next_song()

    def update_ui(self):
        """Обновление текстовых данных плеера"""
        self.label_progress.config(text=f"{self.current_index + 1} / {len(self.playlist)}")
        name = os.path.basename(self.playlist[self.current_index]).rsplit('.', 1)[0]
        self.label_song.config(text=name)

    def toggle_pause(self):
        """Пауза / Воспроизведение"""
        if not self.playlist: return
        self.is_paused = not self.is_paused
        if self.is_paused:
            pygame.mixer.music.pause()
            self.btn_pause.config(text="▶ ИГРАТЬ", bg="#bb9af7")
        else:
            pygame.mixer.music.unpause()
            self.btn_pause.config(text="⏸ ПАУЗА", bg="#e0af68")

    def next_song(self):
        """Следующий трек"""
        if self.playlist:
            self.current_index = (self.current_index + 1) % len(self.playlist)
            self.play_song()

    def prev_song(self):
        """Предыдущий трек"""
        if self.playlist:
            self.current_index = (self.current_index - 1) % len(self.playlist)
            self.play_song()

    def set_volume(self, val):
        """Изменение громкости"""
        pygame.mixer.music.set_volume(int(val) / 100)

    def check_event(self):
        """Проверка системных событий (конец трека)"""
        for event in pygame.event.get():
            if event.type == SONG_END: self.next_song()
        self.root.after(100, self.check_event)

    def open_editor(self, edit_idx=None):
        """Окно создания/редактирования категории"""
        win = tk.Toplevel(self.root)
        win.title("Категория")
        win.geometry("400x550")
        win.configure(bg="#1a1b26")
        win.grab_set()

        curr = self.buttons_data[edit_idx] if edit_idx is not None else {"name": "Новая", "color": "#7aa2f7", "path": "", "auto": True}
        
        tk.Label(win, text="ИМЯ КАТЕГОРИИ", bg="#1a1b26", fg="#565f89", font=("Arial", 8, "bold")).pack(pady=10)
        e_name = tk.Entry(win, font=("Arial", 12), bg="#24283b", fg="white", relief=tk.FLAT)
        e_name.insert(0, curr['name']); e_name.pack(padx=40, fill=tk.X)

        c_val = [curr['color']]
        c_btn = tk.Button(win, text="ВЫБРАТЬ ЦВЕТ", bg=c_val[0], command=lambda: [c_val.clear(), c_val.append(colorchooser.askcolor()[1] or c_val[0]), c_btn.config(bg=c_val[0])])
        c_btn.pack(pady=20, fill=tk.X, padx=40)

        tk.Label(win, text="ПУТЬ (ЕСЛИ НЕ АВТО)", bg="#1a1b26", fg="#565f89", font=("Arial", 8, "bold")).pack()
        e_path = tk.Entry(win, bg="#24283b", fg="white", relief=tk.FLAT)
        e_path.insert(0, curr['path']); e_path.pack(padx=40, fill=tk.X, pady=5)
        tk.Button(win, text="ВЫБРАТЬ ПАПКУ", command=lambda: [e_path.delete(0, tk.END), e_path.insert(0, filedialog.askdirectory())]).pack()

        auto_v = tk.BooleanVar(value=curr.get('auto', True))
        tk.Checkbutton(win, text="Создавать папку автоматически", variable=auto_v, 
                       bg="#1a1b26", fg="white", selectcolor="#1a1b26").pack(pady=15)

        def save():
            if not e_name.get(): return
            new_b = {"name": e_name.get(), "color": c_val[0], "path": e_path.get(), "auto": auto_v.get()}
            if edit_idx is not None: self.buttons_data[edit_idx] = new_b
            else: self.buttons_data.append(new_b)
            self.save_all(); self.render_buttons(); win.destroy()

        tk.Button(win, text="СОХРАНИТЬ", bg="#9ece6a", command=save, height=2, font=("Arial", 10, "bold")).pack(side=tk.BOTTOM, fill=tk.X, padx=40, pady=20)

    def delete_button(self, idx):
        """Удаление категории"""
        if messagebox.askyesno("Удалить?", "Удалить эту категорию?"):
            self.buttons_data.pop(idx); self.save_all(); self.render_buttons()

if __name__ == "__main__":
    root = tk.Tk()
    # Поверх всех окон при запуске
    root.lift()
    root.attributes('-topmost', True)
    root.after_idle(root.attributes, '-topmost', False)
    
    app = GOR_Music_Prime(root)
    root.mainloop()