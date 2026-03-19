import tkinter as tk
from tkinter import filedialog, messagebox
import sys
import os
from PIL import Image, ImageTk

class CellGrid(tk.Frame):
    """
    Редактор клеточного поля с рамкой из нередактируемых клеток 'wall'.
    Внутренняя область размером width x height содержит типы: sand, grass, tree, water.
    Для отображения используются спрайты из папки sprites/ (PNG, 32x32).
    """

    # Цвета для резервной отрисовки (если спрайт не найден)
    TYPE_COLORS = {
        'wall': '#808080',      # серый (рамка)
        'sand': '#F4A460',      # песочный
        'grass': '#7CFC00',     # ярко-зелёный
        'tree': '#006400',      # тёмно-зелёный
        'water': '#1E90FF'      # синий
    }

    def __init__(self, master, inner_width, inner_height, cell_size=32, **kwargs):
        """
        :param inner_width:  ширина внутренней редактируемой области (в клетках)
        :param inner_height: высота внутренней редактируемой области
        :param cell_size:    размер стороны клетки в пикселях (рекомендуется 32)
        """
        super().__init__(master, **kwargs)
        self.inner_width = inner_width
        self.inner_height = inner_height
        self.cell_size = cell_size

        self.total_width = inner_width + 2
        self.total_height = inner_height + 2

        self.current_type = 'sand'

        self.grid_data = self._create_initial_grid()
        self.cell_objects = [[[] for _ in range(self.total_width)] for _ in range(self.total_height)]

        # Загружаем спрайты
        self.sprites = {}
        self.load_sprites()

        self.create_widgets()
        self.draw_grid()

    def _create_initial_grid(self):
        grid = []
        for r in range(self.total_height):
            row = []
            for c in range(self.total_width):
                if r == 0 or r == self.total_height - 1 or c == 0 or c == self.total_width - 1:
                    row.append('wall')
                else:
                    row.append('sand')
            grid.append(row)
        return grid

    def load_sprites(self):
        """Загружает спрайты из папки sprites/ и масштабирует под cell_size."""
        sprite_dir = "sprites"
        if not os.path.exists(sprite_dir):
            print(f"Предупреждение: папка {sprite_dir} не найдена. Будут использованы цвета.")
            return

        for type_name in ['sand', 'grass', 'tree', 'water', 'wall']:
            path = os.path.join(sprite_dir, f"{type_name}.png")
            if os.path.isfile(path):
                try:
                    img = Image.open(path)
                    # Масштабируем до cell_size x cell_size
                    img = img.resize((self.cell_size, self.cell_size), Image.Resampling.LANCZOS)
                    self.sprites[type_name] = ImageTk.PhotoImage(img)
                except Exception as e:
                    print(f"Не удалось загрузить {path}: {e}")
                    self.sprites[type_name] = None
            else:
                self.sprites[type_name] = None

    def create_widgets(self):
        top_frame = tk.Frame(self)
        top_frame.pack(side=tk.TOP, fill=tk.X, padx=5, pady=5)

        tk.Label(top_frame, text="Типы клеток:").pack(side=tk.LEFT, padx=5)

        for type_name in ['sand', 'grass', 'tree', 'water']:
            # Для кнопок используем цвета (так проще, чем миниатюры)
            if type_name == 'tree':
                btn = tk.Button(
                    top_frame,
                    bg=self.TYPE_COLORS['grass'],
                    text='tree',
                    width=4,
                    height=1,
                    command=lambda t=type_name: self.set_current_type(t)
                )
            else:
                btn = tk.Button(
                    top_frame,
                    bg=self.TYPE_COLORS[type_name],
                    width=2,
                    height=1,
                    command=lambda t=type_name: self.set_current_type(t)
                )
            btn.pack(side=tk.LEFT, padx=2)

        self.current_type_label = tk.Label(
            top_frame,
            text=f"Текущий: sand",
            bg=self.TYPE_COLORS['sand']
        )
        self.current_type_label.pack(side=tk.LEFT, padx=10)

        save_btn = tk.Button(top_frame, text="Сохранить", command=self.save_to_file)
        save_btn.pack(side=tk.RIGHT, padx=5)

        load_btn = tk.Button(top_frame, text="Загрузить", command=self.load_from_file)
        load_btn.pack(side=tk.RIGHT, padx=5)

        canvas_width = self.total_width * self.cell_size
        canvas_height = self.total_height * self.cell_size
        self.canvas = tk.Canvas(
            self,
            width=canvas_width,
            height=canvas_height,
            bg='white',
            highlightthickness=1,
            highlightbackground='gray'
        )
        self.canvas.pack(side=tk.TOP, padx=5, pady=5)

        self.canvas.bind("<Button-1>", self.on_cell_click)
        self.canvas.bind("<B1-Motion>", self.on_cell_drag)

    def set_current_type(self, type_name):
        self.current_type = type_name
        if type_name == 'tree':
            color = self.TYPE_COLORS['grass']
        else:
            color = self.TYPE_COLORS[type_name]
        self.current_type_label.config(
            text=f"Текущий: {type_name}",
            bg=color
        )

    def draw_grid(self):
        for row in range(self.total_height):
            for col in range(self.total_width):
                self.draw_cell(row, col)

    def draw_cell(self, row, col):
        # Удаляем старые объекты клетки
        for obj_id in self.cell_objects[row][col]:
            self.canvas.delete(obj_id)
        self.cell_objects[row][col] = []

        x1 = col * self.cell_size
        y1 = row * self.cell_size
        x2 = x1 + self.cell_size
        y2 = y1 + self.cell_size

        cell_type = self.grid_data[row][col]

        # Для wall всегда используем прямоугольник (рамку)
        if cell_type == 'wall':
            rect_id = self.canvas.create_rectangle(
                x1, y1, x2, y2,
                fill=self.TYPE_COLORS['wall'],
                outline='gray',
                width=1
            )
            self.cell_objects[row][col].append(rect_id)
            return

        # Для остальных типов пытаемся использовать спрайт
        sprite = self.sprites.get(cell_type)
        if sprite:
            # Размещаем спрайт по центру клетки
            img_id = self.canvas.create_image(
                x1 + self.cell_size/2,
                y1 + self.cell_size/2,
                image=sprite
            )
            self.cell_objects[row][col].append(img_id)
        else:
            # Резервный вариант – цветная заливка
            rect_id = self.canvas.create_rectangle(
                x1, y1, x2, y2,
                fill=self.TYPE_COLORS.get(cell_type, 'white'),
                outline='gray',
                width=1
            )
            self.cell_objects[row][col].append(rect_id)

            # Для tree, если спрайта нет, рисуем треугольники (как раньше)
            if cell_type == 'tree' and cell_type not in self.sprites:
                x_center = x1 + self.cell_size / 2
                y_center = y1 + self.cell_size / 2
                offset = self.cell_size / 4

                top_triangle = [
                    x_center, y1 + offset,
                    x1 + offset, y_center,
                    x2 - offset, y_center
                ]
                top_id = self.canvas.create_polygon(
                    top_triangle,
                    fill=self.TYPE_COLORS['tree'],
                    outline=''
                )
                self.cell_objects[row][col].append(top_id)

                bottom_triangle = [
                    x_center, y1 + offset * 1.5,
                    x1 + offset, y_center + offset,
                    x2 - offset, y_center + offset
                ]
                bottom_id = self.canvas.create_polygon(
                    bottom_triangle,
                    fill=self.TYPE_COLORS['tree'],
                    outline=''
                )
                self.cell_objects[row][col].append(bottom_id)

    def get_cell_from_coords(self, x, y):
        if 0 <= x < self.total_width * self.cell_size and 0 <= y < self.total_height * self.cell_size:
            col = x // self.cell_size
            row = y // self.cell_size
            return row, col
        return None, None

    def is_inside(self, row, col):
        return (1 <= row <= self.inner_height and 1 <= col <= self.inner_width)

    def set_cell(self, row, col):
        if self.is_inside(row, col):
            if self.grid_data[row][col] == self.current_type:
                return
            self.grid_data[row][col] = self.current_type
            self.draw_cell(row, col)

    def on_cell_click(self, event):
        row, col = self.get_cell_from_coords(event.x, event.y)
        if row is not None:
            self.set_cell(row, col)

    def on_cell_drag(self, event):
        row, col = self.get_cell_from_coords(event.x, event.y)
        if row is not None:
            self.set_cell(row, col)

    def save_to_file(self):
        file_path = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
        )
        if not file_path:
            return

        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(f"{self.inner_width},{self.inner_height}\n")
                for r in range(1, self.inner_height + 1):
                    row_data = self.grid_data[r][1:self.inner_width + 1]
                    row_str = ','.join(str(val) for val in row_data)
                    f.write(row_str + '\n')
            messagebox.showinfo("Сохранение", f"Карта успешно сохранена в {file_path}")
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось сохранить файл:\n{e}")

    def load_from_file(self):
        file_path = filedialog.askopenfilename(
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
        )
        if not file_path:
            return

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = [line.strip() for line in f if line.strip()]

            if not lines:
                raise ValueError("Файл пуст")

            first_line = lines[0].split(',')
            if len(first_line) != 2:
                raise ValueError("Первая строка должна содержать ширину и высоту через запятую")
            file_width, file_height = map(int, first_line)

            if file_width != self.inner_width or file_height != self.inner_height:
                messagebox.showerror(
                    "Ошибка",
                    f"Размер карты в файле ({file_width}x{file_height}) "
                    f"не соответствует текущему ({self.inner_width}x{self.inner_height}).\n"
                    "Загрузка невозможна."
                )
                return

            if len(lines) - 1 != file_height:
                raise ValueError(
                    f"Количество строк данных ({len(lines)-1}) не соответствует высоте ({file_height})"
                )

            new_inner_data = []
            for i, line in enumerate(lines[1:]):
                values = [v.strip() for v in line.split(',')]
                if len(values) != file_width:
                    raise ValueError(
                        f"Строка {i+1} содержит {len(values)} элементов, ожидалось {file_width}"
                    )
                for val in values:
                    if val not in ['sand', 'grass', 'tree', 'water']:
                        raise ValueError(f"Недопустимый тип клетки: {val}")
                new_inner_data.append(values)

            for r in range(1, self.inner_height + 1):
                for c in range(1, self.inner_width + 1):
                    self.grid_data[r][c] = new_inner_data[r-1][c-1]

            for row in range(self.total_height):
                for col in range(self.total_width):
                    self.draw_cell(row, col)

            messagebox.showinfo("Загрузка", "Карта успешно загружена")

        except Exception as e:
            messagebox.showerror("Ошибка загрузки", f"Не удалось загрузить файл:\n{e}")


def main():
    if len(sys.argv) < 3:
        print("Использование: python map_maker_V2.py <ширина> <высота> [размер_клетки]")
        print("Пример: python map_maker_V2.py 10 8 32")
        sys.exit(1)

    try:
        inner_width = int(sys.argv[1])
        inner_height = int(sys.argv[2])
        cell_size = int(sys.argv[3]) if len(sys.argv) > 3 else 32
    except ValueError:
        print("Ошибка: ширина, высота и размер клетки должны быть целыми числами.")
        sys.exit(1)

    root = tk.Tk()
    root.title("Клеточный редактор со спрайтами")

    total_width = inner_width + 2
    total_height = inner_height + 2
    window_width = total_width * cell_size + 50
    window_height = total_height * cell_size + 100

    screen_width = root.winfo_screenwidth()
    screen_height = root.winfo_screenheight()
    x = (screen_width // 2) - (window_width // 2)
    y = (screen_height // 2) - (window_height // 2)
    root.geometry(f"{window_width}x{window_height}+{x}+{y}")

    app = CellGrid(root, inner_width, inner_height, cell_size)
    app.pack(fill=tk.BOTH, expand=True)

    root.mainloop()


if __name__ == "__main__":
    main()
