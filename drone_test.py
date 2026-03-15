import pygame
import sys
import os
import math

# Размер одной клетки в пикселях
CELL_SIZE = 50

# Цвета клеток (RGB)
COLORS = {
    'sand': (244, 164, 96),
    'grass': (124, 252, 0),
    'tree': (0, 100, 0),
    'water': (30, 144, 255)
}

# Параметры марковской локализации
P_MOVE = 0.9      # вероятность успешного движения
P_STAY = 0.1      # вероятность остаться на месте
P_CORRECT = 0.9   # вероятность правильного наблюдения
P_INCORRECT = 0.1 / 3   # вероятность ошибочного наблюдения (для 3 других типов)

# Направления: (dx, dy) для 0=вверх,1=вправо,2=вниз,3=влево
DIRECTIONS = [(0, -1), (1, 0), (0, 1), (-1, 0)]

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

class Player:
    """Реальный дрон."""
    def __init__(self, x, y, direction=0):
        self.x = x
        self.y = y
        self.direction = direction   # 0=вверх,1=вправо,2=вниз,3=влево

    def move(self, dx, dy):
        self.x += dx
        self.y += dy

    def rotate(self):
        self.direction = (self.direction + 1) % 4

class MarkovLocalization:
    """Дискретная марковская локализация."""
    def __init__(self, grid, width, height):
        self.grid = grid
        self.width = width
        self.height = height
        # равномерное начальное распределение
        self.belief = [[1.0 / (width * height) for _ in range(width)] for _ in range(height)]

    def predict(self, direction):
        """Предсказание на основе команды движения."""
        dx, dy = DIRECTIONS[direction]
        new_belief = [[0.0] * self.width for _ in range(self.height)]
        for y in range(self.height):
            for x in range(self.width):
                prob = self.belief[y][x]
                if prob == 0:
                    continue
                # движение в целевую клетку, если возможно
                nx, ny = x + dx, y + dy
                if 0 <= nx < self.width and 0 <= ny < self.height:
                    new_belief[ny][nx] += prob * P_MOVE
                    new_belief[y][x] += prob * P_STAY
                else:
                    # движение невозможно, вся масса остаётся
                    new_belief[y][x] += prob * (P_MOVE + P_STAY)
        self.belief = new_belief

    def update(self, observation):
        """Коррекция на основе наблюдения (тип клетки)."""
        total = 0.0
        for y in range(self.height):
            for x in range(self.width):
                cell_type = self.grid[y][x]
                if cell_type == observation:
                    self.belief[y][x] *= P_CORRECT
                else:
                    self.belief[y][x] *= P_INCORRECT
                total += self.belief[y][x]
        # нормализация
        if total > 0:
            for y in range(self.height):
                for x in range(self.width):
                    self.belief[y][x] /= total
        else:
            # аварийный случай – равномерное распределение
            inv = 1.0 / (self.width * self.height)
            for y in range(self.height):
                for x in range(self.width):
                    self.belief[y][x] = inv

def draw_grid(screen, offset_x, offset_y, width, height, grid):
    """Отрисовывает сетку клеток в заданной области."""
    for y in range(height):
        for x in range(width):
            rect = pygame.Rect(offset_x + x * CELL_SIZE, offset_y + y * CELL_SIZE, CELL_SIZE, CELL_SIZE)
            cell_type = grid[y][x]
            color = COLORS.get(cell_type, (200, 200, 200))
            pygame.draw.rect(screen, color, rect)
            pygame.draw.rect(screen, (0, 0, 0), rect, 1)

def draw_robot(screen, offset_x, offset_y, player):
    """Отрисовывает реального дрона на левой карте."""
    center_x = offset_x + player.x * CELL_SIZE + CELL_SIZE // 2
    center_y = offset_y + player.y * CELL_SIZE + CELL_SIZE // 2
    radius = CELL_SIZE // 3
    pygame.draw.circle(screen, (255, 255, 255), (center_x, center_y), radius)
    # линия направления
    dir_len = radius
    if player.direction == 0:      # вверх
        end = (center_x, center_y - dir_len)
    elif player.direction == 1:    # вправо
        end = (center_x + dir_len, center_y)
    elif player.direction == 2:    # вниз
        end = (center_x, center_y + dir_len)
    else:                          # влево
        end = (center_x - dir_len, center_y)
    pygame.draw.line(screen, (0, 0, 0), (center_x, center_y), end, 3)

def draw_belief(screen, offset_x, offset_y, width, height, grid, belief):
    """Отрисовывает карту вероятностей (правая половина)."""
    # сначала рисуем карту
    draw_grid(screen, offset_x, offset_y, width, height, grid)
    # находим максимальную вероятность
    max_bel = max(max(row) for row in belief)
    if max_bel == 0:
        max_bel = 1e-9
    # наложение белого полупрозрачного слоя
    for y in range(height):
        for x in range(width):
            prob = belief[y][x]
            alpha = int(255 * prob / max_bel)
            if alpha > 0:
                rect = pygame.Rect(offset_x + x * CELL_SIZE, offset_y + y * CELL_SIZE, CELL_SIZE, CELL_SIZE)
                s = pygame.Surface((CELL_SIZE, CELL_SIZE), pygame.SRCALPHA)
                s.fill((255, 255, 255, alpha))
                screen.blit(s, rect.topleft)
    # отметим наиболее вероятную позицию красным кружком
    max_prob = 0
    max_x, max_y = 0, 0
    for y in range(height):
        for x in range(width):
            if belief[y][x] > max_prob:
                max_prob = belief[y][x]
                max_x, max_y = x, y
    if max_prob > 0:
        center_x = offset_x + max_x * CELL_SIZE + CELL_SIZE // 2
        center_y = offset_y + max_y * CELL_SIZE + CELL_SIZE // 2
        pygame.draw.circle(screen, (255, 0, 0), (center_x, center_y), CELL_SIZE // 4, 2)

def draw_text(screen, text, x, y, color=(255,255,255)):
    """Рисует текст в указанной позиции."""
    font = pygame.font.Font(None, 24)
    img = font.render(text, True, color)
    screen.blit(img, (x, y))

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

    # Инициализация pygame
    pygame.init()
    screen_width = 2 * width * CELL_SIZE
    screen_height = height * CELL_SIZE
    screen = pygame.display.set_mode((screen_width, screen_height))
    pygame.display.set_caption("Марковская локализация дрона")
    clock = pygame.time.Clock()

    # Объекты
    player = Player(0, 0)
    loc = MarkovLocalization(grid, width, height)

    # Основной цикл
    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_q:
                    running = False
                elif event.key == pygame.K_r:
                    player.rotate()
                else:
                    # Определяем направление движения
                    dx = dy = 0
                    direction = None
                    if event.key in (pygame.K_UP, pygame.K_w):
                        dy = -1
                        direction = 0
                    elif event.key in (pygame.K_DOWN, pygame.K_s):
                        dy = 1
                        direction = 2
                    elif event.key in (pygame.K_LEFT, pygame.K_a):
                        dx = -1
                        direction = 3
                    elif event.key in (pygame.K_RIGHT, pygame.K_d):
                        dx = 1
                        direction = 1
                    if direction is not None:
                        # Проверка границ для реального дрона
                        new_x = player.x + dx
                        new_y = player.y + dy
                        if 0 <= new_x < width and 0 <= new_y < height:
                            # Реальное движение
                            player.move(dx, dy)
                            # Получаем наблюдение
                            obs = grid[player.y][player.x]
                            # Обновляем фильтр: предсказание и коррекция
                            loc.predict(direction)
                            loc.update(obs)
                        else:
                            # Попытка выйти за границу – игнорируем движение,
                            # но можно всё равно сделать предсказание и наблюдение?
                            # Реально дрон не двинулся, наблюдение не меняется.
                            # В локализации можно сделать предсказание, но наблюдение
                            # остаётся прежним (текущая клетка). Однако мы не будем
                            # усложнять – просто пропускаем.
                            pass

        # Отрисовка
        screen.fill((0, 0, 0))
        # Левая карта (реальная)
        draw_grid(screen, 0, 0, width, height, grid)
        draw_robot(screen, 0, 0, player)
        draw_text(screen, "Real", 10, 10)
        # Правая карта (вероятности)
        draw_belief(screen, width * CELL_SIZE, 0, width, height, grid, loc.belief)
        draw_text(screen, "Belief", width * CELL_SIZE + 10, 10)

        # Информация о реальной позиции
        info = f"Real: ({player.x}, {player.y})  Dir: {player.direction}"
        draw_text(screen, info, 10, screen_height - 30)

        pygame.display.flip()
        clock.tick(30)

    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()