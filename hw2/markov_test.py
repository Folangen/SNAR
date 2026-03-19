import pygame
import sys
import os
import random
import numpy as np

# Размер одной клетки в пикселях
CELL_SIZE = 50

# Высота области для заголовков
TITLE_HEIGHT = 30

# Цвета клеток (используются, если нет спрайта)
COLORS = {
    'sand': (244, 164, 96),
    'grass': (124, 252, 0),
    'tree': (0, 100, 0),
    'water': (30, 144, 255),
    'base': (128, 128, 128)
}

# Папка со спрайтами
SPRITE_DIR = "sprites"

# Параметры шума движения
MOTION_PROBS = {
    'main': 0.9,    # движение в желаемом направлении
    'side_left': 0.02,
    'side_right': 0.02,
    'back': 0.02,
    'stay': 0.02
}
# Параметры шума сенсора
SENSOR_CORRECT = 0.9      # вероятность верного определения типа клетки
SENSOR_ERROR = 0.1        # вероятность ошибки (распределяется равномерно по остальным типам)

# Список всех возможных типов клеток
CELL_TYPES = list(COLORS.keys())

def load_map(filename):
    """Загружает карту из файла. Возвращает (width, height, grid)."""
    with open(filename, 'r', encoding='utf-8') as f:
        lines = [line.strip() for line in f if line.strip()]

    width, height = map(int, lines[0].split(','))
    grid = []
    for i in range(1, height + 1):
        row = lines[i].split(',')
        row = [cell.strip() for cell in row]
        if len(row) != width:
            raise ValueError(f"Строка {i} содержит {len(row)} клеток, ожидалось {width}")
        grid.append(row)
    return width, height, grid

def load_sprite(filename, size):
    """Загружает спрайт и масштабирует его."""
    try:
        image = pygame.image.load(filename)
        return pygame.transform.scale(image, (size, size))
    except (pygame.error, FileNotFoundError):
        return None

def load_all_sprites():
    """Загружает спрайты для всех типов клеток и робота."""
    sprites = {}
    for cell_type in COLORS:
        path = os.path.join(SPRITE_DIR, f"{cell_type}.png")
        sprites[cell_type] = load_sprite(path, CELL_SIZE)

    robot_sprites = [None, None, None, None]
    directions = ['up', 'right', 'down', 'left']
    for i, d in enumerate(directions):
        path = os.path.join(SPRITE_DIR, f"robot_{d}.png")
        robot_sprites[i] = load_sprite(path, CELL_SIZE)

    return sprites, robot_sprites

class Player:
    def __init__(self, x, y, direction=0):
        self.x = x
        self.y = y
        self.direction = direction   # 0=вверх, 1=вправо, 2=вниз, 3=влево

    def get_offset_for_direction(self, direction):
        """Возвращает смещение (dx, dy) для абсолютного направления."""
        if direction == 0: return (0, -1)
        elif direction == 1: return (1, 0)
        elif direction == 2: return (0, 1)
        else: return (-1, 0)

    def apply_noisy_move(self, command, width, height):
        """
        Выполняет шумное движение в соответствии с командой (0..3).
        Обновляет координаты игрока и возвращает фактическое направление перемещения (int 0..3) или None, если остался.
        """
        # Определяем возможные исходы в зависимости от команды
        # Для команды dir_cmd возможные перемещения (abs_dir, prob)
        # abs_dir = абсолютное направление (0..3)
        options = []

        # главное направление (команда)
        options.append((command, MOTION_PROBS['main']))
        # влево (команда - 1)
        options.append(((command - 1) % 4, MOTION_PROBS['side_left']))
        # вправо (команда + 1)
        options.append(((command + 1) % 4, MOTION_PROBS['side_right']))
        # назад (команда + 2)
        options.append(((command + 2) % 4, MOTION_PROBS['back']))
        # остаться
        options.append((None, MOTION_PROBS['stay']))  # None означает остаться

        # Случайный выбор согласно вероятностям
        dirs, probs = zip(*options)
        chosen = random.choices(dirs, weights=probs, k=1)[0]

        if chosen is None:
            return None  # остался на месте

        dx, dy = self.get_offset_for_direction(chosen)
        new_x = self.x + dx
        new_y = self.y + dy
        if 0 <= new_x < width and 0 <= new_y < height:
            self.x = new_x
            self.y = new_y
            return chosen
        else:
            # Если перемещение выходит за границы, остаёмся на месте
            return None

    def rotate_cw(self):
        self.direction = (self.direction + 1) % 4

    def rotate_ccw(self):
        self.direction = (self.direction - 1) % 4

def motion_update(belief, command, width, height):
    """
    Обновляет распределение вероятностей на основе модели движения.
    command: желаемое направление (0..3)
    """
    new_belief = np.zeros_like(belief, dtype=float)
    # Для каждой клетки-источника
    for y in range(height):
        for x in range(width):
            prob = belief[y, x]
            if prob == 0:
                continue

            # Рассматриваем все возможные исходы движения из этой клетки
            # главное направление
            dx, dy = (0, -1) if command == 0 else (1, 0) if command == 1 else (0, 1) if command == 2 else (-1, 0)
            nx, ny = x + dx, y + dy
            if 0 <= nx < width and 0 <= ny < height:
                new_belief[ny, nx] += prob * MOTION_PROBS['main']
            else:
                new_belief[y, x] += prob * MOTION_PROBS['main']  # остаётся

            # влево (command - 1)
            left_cmd = (command - 1) % 4
            dx, dy = (0, -1) if left_cmd == 0 else (1, 0) if left_cmd == 1 else (0, 1) if left_cmd == 2 else (-1, 0)
            nx, ny = x + dx, y + dy
            if 0 <= nx < width and 0 <= ny < height:
                new_belief[ny, nx] += prob * MOTION_PROBS['side_left']
            else:
                new_belief[y, x] += prob * MOTION_PROBS['side_left']

            # вправо (command + 1)
            right_cmd = (command + 1) % 4
            dx, dy = (0, -1) if right_cmd == 0 else (1, 0) if right_cmd == 1 else (0, 1) if right_cmd == 2 else (-1, 0)
            nx, ny = x + dx, y + dy
            if 0 <= nx < width and 0 <= ny < height:
                new_belief[ny, nx] += prob * MOTION_PROBS['side_right']
            else:
                new_belief[y, x] += prob * MOTION_PROBS['side_right']

            # назад (command + 2)
            back_cmd = (command + 2) % 4
            dx, dy = (0, -1) if back_cmd == 0 else (1, 0) if back_cmd == 1 else (0, 1) if back_cmd == 2 else (-1, 0)
            nx, ny = x + dx, y + dy
            if 0 <= nx < width and 0 <= ny < height:
                new_belief[ny, nx] += prob * MOTION_PROBS['back']
            else:
                new_belief[y, x] += prob * MOTION_PROBS['back']

            # остаться
            new_belief[y, x] += prob * MOTION_PROBS['stay']

    # Нормализация (на случай численных ошибок)
    total = np.sum(new_belief)
    if total > 0:
        new_belief /= total
    else:
        # Если всё обнулилось, возвращаем равномерное
        new_belief.fill(1.0 / (width * height))
    return new_belief

def sensor_update(belief, observation, grid):
    """
    Обновляет belief на основе наблюдения (тип клетки).
    observation: строка с типом, который увидел дрон.
    """
    height, width = belief.shape
    likelihood = np.zeros_like(belief, dtype=float)
    for y in range(height):
        for x in range(width):
            true_type = grid[y][x]
            if observation == true_type:
                likelihood[y, x] = SENSOR_CORRECT
            else:
                # Ошибка: равномерно распределяем SENSOR_ERROR между остальными типами
                other_types = [t for t in CELL_TYPES if t != true_type]
                # Если observation среди других типов
                if observation in other_types:
                    likelihood[y, x] = SENSOR_ERROR / len(other_types)
                else:
                    likelihood[y, x] = 0.0  # такого не должно быть, но на всякий случай

    new_belief = belief * likelihood
    total = np.sum(new_belief)
    if total > 0:
        new_belief /= total
    else:
        # Если всё обнулилось, возвращаем равномерное
        new_belief.fill(1.0 / (width * height))
    return new_belief

def draw_cell(screen, x, y, cell_type, sprites, rect=None):
    """Отрисовывает одну клетку в заданном прямоугольнике."""
    if rect is None:
        rect = pygame.Rect(x * CELL_SIZE, y * CELL_SIZE, CELL_SIZE, CELL_SIZE)
    sprite = sprites.get(cell_type)
    if sprite:
        screen.blit(sprite, rect.topleft)
    else:
        color = COLORS.get(cell_type, (200, 200, 200))
        pygame.draw.rect(screen, color, rect)
    pygame.draw.rect(screen, (0, 0, 0), rect, 1)

def draw_robot(screen, x, y, direction, robot_sprites, color_offset=(0,0), marker_color=(255,255,255)):
    """
    Рисует робота в клетке (x,y) с заданным направлением.
    Если спрайты не загружены, рисует круг с линией.
    color_offset - смещение для рисования (используется для разных областей).
    """
    rect = pygame.Rect(x * CELL_SIZE + color_offset[0], y * CELL_SIZE + color_offset[1], CELL_SIZE, CELL_SIZE)
    sprite = robot_sprites[direction]
    if sprite:
        screen.blit(sprite, rect.topleft)
    else:
        center = rect.center
        radius = CELL_SIZE // 3
        pygame.draw.circle(screen, marker_color, center, radius)
        # Линия направления
        dir_len = radius
        if direction == 0:      # вверх
            end = (center[0], center[1] - dir_len)
        elif direction == 1:    # вправо
            end = (center[0] + dir_len, center[1])
        elif direction == 2:    # вниз
            end = (center[0], center[1] + dir_len)
        else:                   # влево
            end = (center[0] - dir_len, center[1])
        pygame.draw.line(screen, (0, 0, 0), center, end, 3)

def draw_heatmap_cell(screen, x, y, prob, max_prob, font, color_offset=(0,0)):
    """Рисует клетку тепловой карты с цветом и текстом вероятности."""
    rect = pygame.Rect(x * CELL_SIZE + color_offset[0], y * CELL_SIZE + color_offset[1], CELL_SIZE, CELL_SIZE)
    if max_prob > 0:
        intensity = prob / max_prob
        # от синего (0,0,255) до красного (255,0,0)
        r = int(255 * intensity)
        b = int(255 * (1 - intensity))
        color = (r, 0, b)
    else:
        color = (0, 0, 255)
    pygame.draw.rect(screen, color, rect)
    pygame.draw.rect(screen, (0, 0, 0), rect, 1)

    # Текст вероятности
    text = f"{prob:.2f}" if prob >= 0.01 else "<0.01"
    text_surf = font.render(text, True, (255, 255, 255) if prob < 0.5 else (0, 0, 0))
    text_rect = text_surf.get_rect(center=rect.center)
    screen.blit(text_surf, text_rect)

def choose_start_position(width, height, grid):
    """Интерактивный выбор начальной позиции дрона. Возвращает (x, y, belief_type)."""
    print("\nВыберите способ размещения дрона:")
    print("1 - Случайное место")
    print("2 - Конкретные координаты")
    print("3 - На базе (если есть)")
    choice = input("Ваш выбор (1/2/3): ").strip()

    if choice == '1':
        x = random.randint(0, width - 1)
        y = random.randint(0, height - 1)
        print(f"Дрон размещён случайно: ({x}, {y})")
        return x, y, 'uniform'

    elif choice == '2':
        while True:
            try:
                x = int(input(f"Введите X (0..{width-1}): "))
                y = int(input(f"Введите Y (0..{height-1}): "))
                if 0 <= x < width and 0 <= y < height:
                    print(f"Дрон размещён в ({x}, {y})")
                    return x, y, 'exact'
                else:
                    print("Координаты вне диапазона! Попробуйте снова.")
            except ValueError:
                print("Ошибка ввода. Введите целые числа.")

    elif choice == '3':
        base_positions = []
        for y in range(height):
            for x in range(width):
                if grid[y][x] == 'base':
                    base_positions.append((x, y))
        if base_positions:
            # Берём первую базу для реального размещения
            x, y = base_positions[0]
            print(f"Дрон размещён на базе: ({x}, {y})")
            return x, y, 'bases'  # равномерно по всем базам для фильтра
        else:
            print("На карте нет базы! Размещаем случайно.")
            x = random.randint(0, width - 1)
            y = random.randint(0, height - 1)
            print(f"Дрон размещён случайно: ({x}, {y})")
            return x, y, 'uniform'
    else:
        print("Неверный выбор. Размещаем случайно.")
        x = random.randint(0, width - 1)
        y = random.randint(0, height - 1)
        print(f"Дрон размещён случайно: ({x}, {y})")
        return x, y, 'uniform'

def initialize_belief(width, height, grid, belief_type, exact_x=None, exact_y=None):
    """Создаёт начальное распределение вероятностей."""
    belief = np.zeros((height, width), dtype=float)
    if belief_type == 'exact' and exact_x is not None and exact_y is not None:
        belief[exact_y, exact_x] = 1.0
    elif belief_type == 'bases':
        base_positions = []
        for y in range(height):
            for x in range(width):
                if grid[y][x] == 'base':
                    base_positions.append((x, y))
        if base_positions:
            prob = 1.0 / len(base_positions)
            for (x, y) in base_positions:
                belief[y, x] = prob
        else:
            # Если баз нет, равномерно
            belief.fill(1.0 / (width * height))
    else:  # uniform
        belief.fill(1.0 / (width * height))
    return belief

def main():
    # Запрос файла карты
    filename = input("Введите имя файла карты (по умолчанию map_fine.txt): ").strip()
    if not filename:
        filename = 'map_fine.txt'

    try:
        width, height, grid = load_map(filename)
    except FileNotFoundError:
        print(f"Файл {filename} не найден.")
        return
    except Exception as e:
        print(f"Ошибка при загрузке карты: {e}")
        return

    # Выбор начальной позиции
    start_x, start_y, belief_type = choose_start_position(width, height, grid)

    pygame.init()
    # Создаём окно для трёх карт (горизонтально) с местом для заголовков
    screen_width = 3 * width * CELL_SIZE
    screen_height = height * CELL_SIZE + TITLE_HEIGHT
    screen = pygame.display.set_mode((screen_width, screen_height))
    pygame.display.set_caption("Марковская локализация дрона")
    clock = pygame.time.Clock()
    font = pygame.font.SysFont(None, 20)          # для текста вероятностей
    title_font = pygame.font.SysFont(None, 28)    # для заголовков

    # Загрузка спрайтов
    sprites, robot_sprites = load_all_sprites()
    if all(s is None for s in sprites.values()):
        print("Спрайты клеток не найдены в папке 'sprites'. Используются цвета.")
    if all(s is None for s in robot_sprites):
        print("Спрайты дрона не найдены в папке 'sprites'. Используется простой дрон.")

    # Создание игрока (реальная позиция)
    player = Player(start_x, start_y, direction=0)

    # Инициализация распределения вероятностей
    belief = initialize_belief(width, height, grid, belief_type, exact_x=start_x, exact_y=start_y)

    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_o:      # выход
                    running = False

                # Движение (относительно текущего направления игрока)
                command = None
                if event.key in (pygame.K_UP, pygame.K_w):
                    command = player.direction  # вперёд
                elif event.key in (pygame.K_DOWN, pygame.K_s):
                    command = (player.direction + 2) % 4  # назад
                elif event.key in (pygame.K_LEFT, pygame.K_a):
                    command = (player.direction - 1) % 4  # влево
                elif event.key in (pygame.K_RIGHT, pygame.K_d):
                    command = (player.direction + 1) % 4  # вправо
                elif event.key == pygame.K_e:    # поворот по часовой
                    player.rotate_cw()
                elif event.key == pygame.K_q:    # поворот против часовой
                    player.rotate_ccw()

                if command is not None:
                    # 1. Реальное движение с шумом
                    player.apply_noisy_move(command, width, height)

                    # 2. Получаем наблюдение (тип клетки под реальным дроном)
                    obs = grid[player.y][player.x]

                    # 3. Обновляем belief: предсказание движения
                    belief = motion_update(belief, command, width, height)

                    # 4. Обновление по наблюдению
                    belief = sensor_update(belief, obs, grid)

        # Отрисовка
        screen.fill((0, 0, 0))

        # Смещение по Y для карт (ниже заголовков)
        map_y_offset = TITLE_HEIGHT

        # Левая карта: реальное положение дрона
        left_offset = (0, map_y_offset)
        for y in range(height):
            for x in range(width):
                draw_cell(screen, x, y, grid[y][x], sprites,
                          rect=pygame.Rect(x * CELL_SIZE + left_offset[0], y * CELL_SIZE + left_offset[1], CELL_SIZE, CELL_SIZE))
        draw_robot(screen, player.x, player.y, player.direction, robot_sprites,
                   color_offset=left_offset, marker_color=(255,255,255))

        # Средняя карта: наиболее вероятное положение
        mid_offset = (width * CELL_SIZE, map_y_offset)
        max_prob = np.max(belief)
        if max_prob > 0:
            # Находим клетку с максимальной вероятностью (первую)
            indices = np.where(belief == max_prob)
            best_y, best_x = indices[0][0], indices[1][0]
        else:
            best_x, best_y = 0, 0

        for y in range(height):
            for x in range(width):
                draw_cell(screen, x, y, grid[y][x], sprites,
                          rect=pygame.Rect(x * CELL_SIZE + mid_offset[0], y * CELL_SIZE + mid_offset[1], CELL_SIZE, CELL_SIZE))
        # Рисуем синий круг для наиболее вероятной позиции
        draw_robot(screen, best_x, best_y, player.direction, robot_sprites,
                   color_offset=mid_offset, marker_color=(0, 0, 255))

        # Правая карта: тепловая карта вероятностей
        right_offset = (2 * width * CELL_SIZE, map_y_offset)
        max_belief = np.max(belief)
        for y in range(height):
            for x in range(width):
                prob = belief[y, x]
                draw_heatmap_cell(screen, x, y, prob, max_belief, font, color_offset=right_offset)

        # Рисуем подписи к картам
        titles = [
            "Реальная позиция",
            "Наиболее вероятная",
            "Тепловая карта"
        ]
        for i, title in enumerate(titles):
            text = title_font.render(title, True, (255, 255, 255))
            # Центрируем заголовок над каждой картой
            x_pos = i * width * CELL_SIZE + (width * CELL_SIZE - text.get_width()) // 2
            y_pos = 5  # отступ сверху
            screen.blit(text, (x_pos, y_pos))

        # Разделительные линии между картами
        line_color = (100, 100, 100)
        for i in range(1, 3):
            x_line = i * width * CELL_SIZE
            pygame.draw.line(screen, line_color, (x_line, 0), (x_line, screen_height), 2)

        # Горизонтальная линия под заголовками
        pygame.draw.line(screen, line_color, (0, TITLE_HEIGHT-2), (screen_width, TITLE_HEIGHT-2), 2)

        pygame.display.flip()
        clock.tick(30)

    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()
