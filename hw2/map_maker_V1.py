import tkinter as tk
from tkinter import filedialog, messagebox
import sys

class CellGrid(tk.Frame):
    """
    Редактор клеточного поля с возможностью выбора типа клетки из палитры,
    сохранения и загрузки карты из файла.
    """

    TYPE_COLORS = {
        0: 'white',
        1: 'black',
        2: 'red',
        3: 'blue',
        4: 'green',
        5: 'yellow',
    }

    def __init__(self, master, width, height, cell_size=30, **kwargs):
        super().__init__(master, **kwargs)
        self.width = width
        self.height = height
        self.cell_size = cell_size

        self.current_type = 0
        self.grid_data = [[0 for _ in range(width)] for _ in range(height)]

        self.create_widgets()
        self.draw_grid()

    def create_widgets(self):
        """Создаёт палитру, поле и кнопки сохранения/загрузки."""
        top_frame = tk.Frame(self)
        top_frame.pack(side=tk.TOP, fill=tk.X, padx=5, pady=5)

        tk.Label(top_frame, text="Типы клеток:").pack(side=tk.LEFT, padx=5)

        for type_val, color in self.TYPE_COLORS.items():
            btn = tk.Button(
                top_frame,
                bg=color,
                width=2,
                height=1,
                command=lambda t=type_val: self.set_current_type(t)
            )
            btn.pack(side=tk.LEFT, padx=2)

        self.current_type_label = tk.Label(top_frame, text="Текущий: 0 (белый)")
        self.current_type_label.pack(side=tk.LEFT, padx=10)

        # Кнопки сохранения и загрузки
        save_btn = tk.Button(top_frame, text="Сохранить", command=self.save_to_file)
        save_btn.pack(side=tk.RIGHT, padx=5)

        load_btn = tk.Button(top_frame, text="Загрузить", command=self.load_from_file)
        load_btn.pack(side=tk.RIGHT, padx=5)

        # Поле (Canvas)
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

    def set_current_type(self, type_val):
        self.current_type = type_val
        color = self.TYPE_COLORS.get(type_val, 'white')
        self.current_type_label.config(
            text=f"Текущий: {type_val} ({color})",
            bg=color
        )

    def draw_grid(self):
        """Рисует все клетки на Canvas и сохраняет идентификаторы прямоугольников."""
        self.rect_ids = [[None for _ in range(self.width)] for _ in range(self.height)]
        for row in range(self.height):
            for col in range(self.width):
                x1 = col * self.cell_size
                y1 = row * self.cell_size
                x2 = x1 + self.cell_size
                y2 = y1 + self.cell_size
                color = self.TYPE_COLORS[self.grid_data[row][col]]
                rect_id = self.canvas.create_rectangle(
                    x1, y1, x2, y2,
                    fill=color,
                    outline='gray',
                    width=1
                )
                self.rect_ids[row][col] = rect_id

    def get_cell_from_coords(self, x, y):
        if 0 <= x < self.width * self.cell_size and 0 <= y < self.height * self.cell_size:
            col = x // self.cell_size
            row = y // self.cell_size
            return row, col
        return None, None

    def set_cell(self, row, col):
        if 0 <= row < self.height and 0 <= col < self.width:
            if self.grid_data[row][col] == self.current_type:
                return
            self.grid_data[row][col] = self.current_type
            rect_id = self.rect_ids[row][col]
            color = self.TYPE_COLORS[self.current_type]
            self.canvas.itemconfig(rect_id, fill=color)

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
        """Загружает карту из файла и обновляет отображение."""
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

            # Первая строка: ширина,высота
            first_line = lines[0].split(',')
            if len(first_line) != 2:
                raise ValueError("Первая строка должна содержать ширину и высоту через запятую")
            file_width, file_height = map(int, first_line)

            # Проверка соответствия размеров
            if file_width != self.width or file_height != self.height:
                messagebox.showerror(
                    "Ошибка",
                    f"Размер карты в файле ({file_width}x{file_height}) "
                    f"не соответствует текущему ({self.width}x{self.height}).\n"
                    "Загрузка невозможна."
                )
                return

            # Остальные строки — данные карты
            if len(lines) - 1 != file_height:
                raise ValueError(
                    f"Количество строк данных ({len(lines)-1}) не соответствует высоте ({file_height})"
                )

            new_data = []
            for i, line in enumerate(lines[1:]):
                values = line.split(',')
                if len(values) != file_width:
                    raise ValueError(
                        f"Строка {i+1} содержит {len(values)} элементов, ожидалось {file_width}"
                    )
                row = [int(v) for v in values]
                new_data.append(row)

            # Обновляем данные
            self.grid_data = new_data

            # Обновляем цвета на канвасе
            for row in range(self.height):
                for col in range(self.width):
                    rect_id = self.rect_ids[row][col]
                    color = self.TYPE_COLORS[self.grid_data[row][col]]
                    self.canvas.itemconfig(rect_id, fill=color)

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
