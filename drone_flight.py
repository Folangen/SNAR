import pygame
import sys
import os
import random

# Размер одной клетки в пикселях
CELL_SIZE = 50

# Цвета клеток (используются, если нет спрайта)
COLORS = {
    'sand': (244, 164, 96),
    'grass': (124, 252, 0),
    'tree': (0, 100, 0),
    'water': (30, 144, 255),
    'base': (128, 128, 128)      # серый для базы
}

# Папка со спрайтами
SPRITE_DIR = "sprites"

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
    # Клетки (включая base)
    for cell_type in COLORS:
        path = os.path.join(SPRITE_DIR, f"{cell_type}.png")
        sprites[cell_type] = load_sprite(path, CELL_SIZE)

    # Робот по направлениям: 0 - вверх, 1 - вправо, 2 - вниз, 3 - влево
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

    def get_forward_offset(self):
        """Возвращает смещение (dx, dy) для движения вперёд."""
        if self.direction == 0: return (0, -1)
        elif self.direction == 1: return (1, 0)
        elif self.direction == 2: return (0, 1)
        else: return (-1, 0)

    def get_backward_offset(self):
        """Смещение назад (противоположно направлению)."""
        dx, dy = self.get_forward_offset()
        return (-dx, -dy)

    def get_left_offset(self):
        """Смещение влево относительно направления."""
        # Поворот вектора направления на -90 градусов: (dx, dy) -> (dy, -dx)
        dx, dy = self.get_forward_offset()
        return (dy, -dx)

    def get_right_offset(self):
        """Смещение вправо относительно направления."""
        # Поворот на +90 градусов: (dx, dy) -> (-dy, dx)
        dx, dy = self.get_forward_offset()
        return (-dy, dx)

    def try_move(self, offset, width, height):
        """Пытается переместиться на заданное смещение, если новая позиция в пределах карты."""
        new_x = self.x + offset[0]
        new_y = self.y + offset[1]
        if 0 <= new_x < width and 0 <= new_y < height:
            self.x = new_x
            self.y = new_y
            return True
        return False

    def rotate_cw(self):
        """Поворот по часовой стрелке."""
        self.direction = (self.direction + 1) % 4

    def rotate_ccw(self):
        """Поворот против часовой стрелки."""
        self.direction = (self.direction - 1) % 4

def draw_cell(screen, x, y, cell_type, sprites):
    """Отрисовывает одну клетку: спрайт или цветной прямоугольник."""
    rect = pygame.Rect(x * CELL_SIZE, y * CELL_SIZE, CELL_SIZE, CELL_SIZE)
    sprite = sprites.get(cell_type)
    if sprite:
        screen.blit(sprite, rect.topleft)
    else:
        color = COLORS.get(cell_type, (200, 200, 200))
        pygame.draw.rect(screen, color, rect)
    # Рамка вокруг клетки
    pygame.draw.rect(screen, (0, 0, 0), rect, 1)

def draw_robot(screen, player, robot_sprites):
    """Отрисовывает робота с учётом направления."""
    rect = pygame.Rect(player.x * CELL_SIZE, player.y * CELL_SIZE, CELL_SIZE, CELL_SIZE)
    sprite = robot_sprites[player.direction]
    if sprite:
        screen.blit(sprite, rect.topleft)
    else:
        # Простой робот, если спрайт не загружен
        center = rect.center
        radius = CELL_SIZE // 3
        pygame.draw.circle(screen, (255, 255, 255), center, radius)
        # Линия направления
        dir_len = radius
        if player.direction == 0:      # вверх
            end = (center[0], center[1] - dir_len)
        elif player.direction == 1:    # вправо
            end = (center[0] + dir_len, center[1])
        elif player.direction == 2:    # вниз
            end = (center[0], center[1] + dir_len)
        else:                          # влево
            end = (center[0] - dir_len, center[1])
        pygame.draw.line(screen, (0, 0, 0), center, end, 3)

def choose_start_position(width, height, grid):
    """Интерактивный выбор начальной позиции дрона."""
    print("\nВыберите способ размещения дрона:")
    print("1 - Случайное место")
    print("2 - Конкретные координаты")
    print("3 - На базе (если есть)")
    choice = input("Ваш выбор (1/2/3): ").strip()

    if choice == '1':
        x = random.randint(0, width - 1)
        y = random.randint(0, height - 1)
        print(f"Дрон размещён случайно: ({x}, {y})")
        return x, y

    elif choice == '2':
        while True:
            try:
                x = int(input(f"Введите X (0..{width-1}): "))
                y = int(input(f"Введите Y (0..{height-1}): "))
                if 0 <= x < width and 0 <= y < height:
                    print(f"Дрон размещён в ({x}, {y})")
                    return x, y
                else:
                    print("Координаты вне диапазона! Попробуйте снова.")
            except ValueError:
                print("Ошибка ввода. Введите целые числа.")

    elif choice == '3':
        # Ищем все клетки с типом 'base'
        base_positions = []
        for y in range(height):
            for x in range(width):
                if grid[y][x] == 'base':
                    base_positions.append((x, y))
        if base_positions:
            # Берём первую найденную базу (можно изменить на случайную)
            x, y = base_positions[0]
            print(f"Дрон размещён на базе: ({x}, {y})")
            return x, y
        else:
            print("На карте нет базы! Размещаем случайно.")
            x = random.randint(0, width - 1)
            y = random.randint(0, height - 1)
            print(f"Дрон размещён случайно: ({x}, {y})")
            return x, y
    else:
        print("Неверный выбор. Размещаем случайно.")
        x = random.randint(0, width - 1)
        y = random.randint(0, height - 1)
        print(f"Дрон размещён случайно: ({x}, {y})")
        return x, y

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
    start_x, start_y = choose_start_position(width, height, grid)

    pygame.init()
    screen = pygame.display.set_mode((width * CELL_SIZE, height * CELL_SIZE))
    pygame.display.set_caption("Карта и дрон")
    clock = pygame.time.Clock()

    # Загрузка спрайтов
    sprites, robot_sprites = load_all_sprites()

    # Информируем пользователя, если спрайты не найдены
    if all(s is None for s in sprites.values()):
        print("Спрайты клеток не найдены в папке 'sprites'. Используются цвета.")
    if all(s is None for s in robot_sprites):
        print("Спрайты дрона не найдены в папке 'sprites'. Используется простой дрон.")

    player = Player(start_x, start_y, direction=0)  # начальное направление вверх

    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_o:      # выход
                    running = False
                # Движение относительно направления
                elif event.key in (pygame.K_UP, pygame.K_w):
                    player.try_move(player.get_forward_offset(), width, height)
                elif event.key in (pygame.K_DOWN, pygame.K_s):
                    player.try_move(player.get_backward_offset(), width, height)
                elif event.key in (pygame.K_LEFT, pygame.K_a):
                    player.try_move(player.get_left_offset(), width, height)
                elif event.key in (pygame.K_RIGHT, pygame.K_d):
                    player.try_move(player.get_right_offset(), width, height)
                # Повороты
                elif event.key == pygame.K_e:    # по часовой
                    player.rotate_cw()
                elif event.key == pygame.K_q:    # против часовой
                    player.rotate_ccw()

        # Отрисовка
        screen.fill((0, 0, 0))
        for y in range(height):
            for x in range(width):
                draw_cell(screen, x, y, grid[y][x], sprites)
        draw_robot(screen, player, robot_sprites)

        pygame.display.flip()
        clock.tick(30)

    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()
