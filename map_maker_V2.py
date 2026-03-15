import tkinter as tk
from tkinter import filedialog, messagebox
import sys

class CellGrid(tk.Frame):
    """
    Редактор клеточного поля с типами: sand, grass, tree, water, base.
    Для tree рисуется ёлочка (два тёмно-зелёных треугольника на зелёном фоне).
    Для base действует ограничение: не более одной клетки на карте.
    """

    TYPE_COLORS = {
        'sand': '#F4A460',      # песочный
        'grass': '#7CFC00',      # ярко-зелёный (трава)
        'tree': '#006400',       # тёмно-зелёный для треугольников
        'water': '#1E90FF',      # синий
        'base': '#808080'        # серый
    }

    def __init__(self, master, width, height, cell_size=30, **kwargs):
        super().__init__(master, **kwargs)
        self.width = width
        self.height = height
        self.cell_size = cell_size

        self.current_type = 'sand'
        self.grid_data = [['sand' for _ in range(width)] for _ in range(height)]
        self.cell_objects = [[[] for _ in range(width)] for _ in range(height)]
        self.base_position = None  # координаты единственной базы (row, col) или None

        self.create_widgets()
        self.draw_grid()

    def create_widgets(self):
        top_frame = tk.Frame(self)
        top_frame.pack(side=tk.TOP, fill=tk.X, padx=5, pady=5)

        tk.Label(top_frame, text="Типы клеток:").pack(side=tk.LEFT, padx=5)

        # Кнопки палитры
        for type_name in ['sand', 'grass', 'tree', 'water', 'base']:
            if type_name in ['tree', 'base']:
                # Для tree и base делаем кнопки с текстом (чтобы было понятно)
                if type_name == 'tree':
                    bg_color = self.TYPE_COLORS['grass']
                else:  # base
                    bg_color = self.TYPE_COLORS['base']
                btn = tk.Button(
                    top_frame,
                    bg=bg_color,
                    text=type_name,
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
            text="Текущий: sand",
            bg=self.TYPE_COLORS['sand']
        )
        self.current_type_label.pack(side=tk.LEFT, padx=10)

        save_btn = tk.Button(top_frame, text="Сохранить", command=self.save_to_file)
        save_btn.pack(side=tk.RIGHT, padx=5)

        load_btn = tk.Button(top_frame, text="Загрузить", command=self.load_from_file)
        load_btn.pack(side=tk.RIGHT, padx=5)

        canvas_width = self.width * self.cell_size
        canvas_height = self.height * self.cell_size
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
        elif type_name == 'base':
            color = self.TYPE_COLORS['base']
        else:
            color = self.TYPE_COLORS[type_name]
        self.current_type_label.config(
            text=f"Текущий: {type_name}",
            bg=color
        )

    def draw_grid(self):
        for row in range(self.height):
            for col in range(self.width):
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

        if cell_type == 'sand':
            rect_id = self.canvas.create_rectangle(
                x1, y1, x2, y2,
                fill=self.TYPE_COLORS['sand'],
                outline='gray', width=1
            )
            self.cell_objects[row][col].append(rect_id)

        elif cell_type == 'grass':
            rect_id = self.canvas.create_rectangle(
                x1, y1, x2, y2,
                fill=self.TYPE_COLORS['grass'],
                outline='gray', width=1
            )
            self.cell_objects[row][col].append(rect_id)

        elif cell_type == 'water':
            rect_id = self.canvas.create_rectangle(
                x1, y1, x2, y2,
                fill=self.TYPE_COLORS['water'],
                outline='gray', width=1
            )
            self.cell_objects[row][col].append(rect_id)

        elif cell_type == 'tree':
            # Фон как у травы
            rect_id = self.canvas.create_rectangle(
                x1, y1, x2, y2,
                fill=self.TYPE_COLORS['grass'],
                outline='gray', width=1
            )
            self.cell_objects[row][col].append(rect_id)

            # Рисуем два тёмно-зелёных треугольника
            x_center = x1 + self.cell_size / 2
            y_center = y1 + self.cell_size / 2
            offset = self.cell_size / 4

            # Верхний треугольник
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

            # Нижний треугольник
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

        elif cell_type == 'base':
            rect_id = self.canvas.create_rectangle(
                x1, y1, x2, y2,
                fill=self.TYPE_COLORS['base'],
                outline='gray', width=1
            )
            self.cell_objects[row][col].append(rect_id)

        return self.cell_objects[row][col]

    def get_cell_from_coords(self, x, y):
        if 0 <= x < self.width * self.cell_size and 0 <= y < self.height * self.cell_size:
            col = x // self.cell_size
            row = y // self.cell_size
            return row, col
        return None, None

    def set_cell(self, row, col):
        if not (0 <= row < self.height and 0 <= col < self.width):
            return
        if self.grid_data[row][col] == self.current_type:
            return

        if self.current_type == 'base':
            # Если клетка уже является базой, ничего не делаем
            if self.base_position == (row, col):
                return

            # Если есть другая база, заменяем её на песок
            if self.base_position is not None:
                old_r, old_c = self.base_position
                self.grid_data[old_r][old_c] = 'sand'
                self.draw_cell(old_r, old_c)

            # Устанавливаем новую базу
            self.grid_data[row][col] = 'base'
            self.draw_cell(row, col)
            self.base_position = (row, col)

        else:
            # Если текущая клетка была базой, сбрасываем информацию о ней
            if self.base_position == (row, col):
                self.base_position = None

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
                f.write(f"{self.width},{self.height}\n")
                for row in self.grid_data:
                    row_str = ','.join(str(val) for val in row)
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

            if file_width != self.width or file_height != self.height:
                messagebox.showerror(
                    "Ошибка",
                    f"Размер карты в файле ({file_width}x{file_height}) "
                    f"не соответствует текущему ({self.width}x{self.height}).\n"
                    "Загрузка невозможна."
                )
                return

            if len(lines) - 1 != file_height:
                raise ValueError(
                    f"Количество строк данных ({len(lines)-1}) не соответствует высоте ({file_height})"
                )

            new_data = []
            for i, line in enumerate(lines[1:]):
                values = [v.strip() for v in line.split(',')]
                if len(values) != file_width:
                    raise ValueError(
                        f"Строка {i+1} содержит {len(values)} элементов, ожидалось {file_width}"
                    )
                for val in values:
                    if val not in self.TYPE_COLORS:
                        raise ValueError(f"Недопустимый тип клетки: {val}")
                new_data.append(values)

            # Проверка на количество баз
            base_positions = []
            for r in range(file_height):
                for c in range(file_width):
                    if new_data[r][c] == 'base':
                        base_positions.append((r, c))

            if len(base_positions) > 1:
                messagebox.showwarning(
                    "Предупреждение",
                    "Обнаружено несколько баз. Оставлена только первая, остальные заменены на 'sand'."
                )
                # Оставляем первую базу, остальные делаем песком
                for (r, c) in base_positions[1:]:
                    new_data[r][c] = 'sand'
                self.base_position = base_positions[0]
            elif len(base_positions) == 1:
                self.base_position = base_positions[0]
            else:
                self.base_position = None

            self.grid_data = new_data

            # Перерисовываем всё поле
            for row in range(self.height):
                for col in range(self.width):
                    self.draw_cell(row, col)

            messagebox.showinfo("Загрузка", "Карта успешно загружена")

        except Exception as e:
            messagebox.showerror("Ошибка загрузки", f"Не удалось загрузить файл:\n{e}")


def main():
    if len(sys.argv) < 3:
        print("Использование: python cell_editor.py <ширина> <высота> [размер_клетки]")
        print("Пример: python cell_editor.py 20 15 30")
        sys.exit(1)

    try:
        width = int(sys.argv[1])
        height = int(sys.argv[2])
        cell_size = int(sys.argv[3]) if len(sys.argv) > 3 else 30
    except ValueError:
        print("Ошибка: ширина, высота и размер клетки должны быть целыми числами.")
        sys.exit(1)

    root = tk.Tk()
    root.title("Клеточный редактор")
    root.update_idletasks()
    screen_width = root.winfo_screenwidth()
    screen_height = root.winfo_screenheight()
    window_width = width * cell_size + 50
    window_height = height * cell_size + 100
    x = (screen_width // 2) - (window_width // 2)
    y = (screen_height // 2) - (window_height // 2)
    root.geometry(f"{window_width}x{window_height}+{x}+{y}")

    app = CellGrid(root, width, height, cell_size)
    app.pack(fill=tk.BOTH, expand=True)

    root.mainloop()


if __name__ == "__main__":
    main()
