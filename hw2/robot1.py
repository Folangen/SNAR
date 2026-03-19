import numpy as np
import random as rd
import pygame
import sys
import os

# ================== Обработка аргументов командной строки ==================

def print_help():
    """Выводит справку по использованию программы."""
    help_text = """
Использование: python robot.py [файл_карты] [режим]

Параметры:
  файл_карты    - путь к текстовому файлу с картой (по умолчанию: map_fine.txt)
  режим         - режим работы: 'auto' (автоматический, по умолчанию) или 'manual' (ручной)

Управление в ручном режиме:
  W A S D       - движение вперёд, влево, назад, вправо (относительно ориентации робота)
  Q / E         - поворот налево / направо
  Пробел        - выполнить все четыре измерения (под собой, спереди, спереди-слева, спереди-справа)
  ESC           - выход

Примеры:
  python robot.py                     # автоматический режим с картой map_fine.txt
  python robot.py my_map.txt           # автоматический режим с картой my_map.txt
  python robot.py map.txt manual       # ручной режим с картой map.txt
  python robot.py --help               # вывод этой справки
"""
    print(help_text)
    sys.exit(0)

def parse_arguments():
    """Парсит аргументы командной строки, возвращает (map_file, manual_mode)."""
    if len(sys.argv) > 1 and sys.argv[1] in ('-h', '--help', '/h', '/?'):
        print_help()

    map_file = sys.argv[1] if len(sys.argv) > 1 else 'map_fine.txt'
    manual_mode = False
    if len(sys.argv) > 2:
        mode_arg = sys.argv[2].lower()
        if mode_arg == 'manual':
            manual_mode = True
        elif mode_arg == 'auto':
            manual_mode = False
        else:
            print(f"Ошибка: неизвестный режим '{sys.argv[2]}'. Допустимые значения: auto, manual")
            print_help()

    if len(sys.argv) > 3:
        print("Ошибка: слишком много аргументов.")
        print_help()

    return map_file, manual_mode

map_file, manual_mode = parse_arguments()

# ================== Загрузка карты и основные константы ==================

def map_read(file):
    with open(file, 'r') as f:
        line = f.readline()
        high = int(list(line.strip('\n').split(','))[0])
        width = int(list(line.strip('\n').split(','))[1])
        world = []
        for i in range(high):
            line = f.readline()
            line = list(line.strip('\n').split(','))
            world.append(line)
        return np.array(world)

try:
    world = map_read(map_file)
except FileNotFoundError:
    print(f"Ошибка: файл карты '{map_file}' не найден.")
    sys.exit(1)
except Exception as e:
    print(f"Ошибка при чтении файла карты: {e}")
    sys.exit(1)

high, width = world.shape
ground = np.array(['sand', 'grass', 'tree', 'water', 'wall'])

def ground_False(Z):
    ground_False = [gr for gr in ground if gr != Z]
    return rd.choice(ground_False)

def init_pos(high, width):
    p = np.zeros((high, width))
    free_cells = [(i, j) for i in range(high) for j in range(width) if world[i, j] != 'wall']
    if not free_cells:
        print("Ошибка: на карте нет свободных клеток (все стены)")
        sys.exit(1)
    i, j = rd.choice(free_cells)
    p[i, j] = 1.0
    return p, [i, j]

p, real = init_pos(high, width)
print("Начальное распределение вероятностей (сумма =", np.sum(p), "):")
print(p)

# ================== Модель сенсоров ==================

pHit = 0.8
pMiss = (1 - pHit) / (ground.shape[0] - 1)
pHitWall = 0.95
pMissWall = (1 - pHitWall) / (ground.shape[0] - 1)

pSensor = np.array([
    [pHit, 1.3 * pMiss, 1.3 * pMiss, 1.3 * pMiss, 0.1 * pMiss],
    [0.45 * pMiss, pHit, 2 * pMiss, 0.45 * pMiss, 0.1 * pMiss],
    [0.45 * pMiss, 2 * pMiss, pHit, 0.45 * pMiss, 0.1 * pMiss],
    [1.3 * pMiss, 1.3 * pMiss, 1.3 * pMiss, pHit, 0.1 * pMiss],
    [pMissWall, pMissWall, pMissWall, pMissWall, pHitWall]
])

for i in range(ground.shape[0] - 1):
    row_sum = np.sum(pSensor[i])
    if row_sum > 0:
        pSensor[i] = pSensor[i] / row_sum

# ================== Ориентация ==================

rOrientation_keys = ['up', 'right', 'down', 'left']
rOrientation_values = [[-1, 0], [0, 1], [1, 0], [0, -1]]
rOrientation = dict(zip(rOrientation_keys, rOrientation_values))

# ================== Параметры движения и поворотов ==================

forward_matrix = {
    (-2, 0): 0.1,
    (-1, -1): 0.05,
    (-1, 0): 0.7,
    (-1, 1): 0.05,
    (0, -1): 0.05,
    (0, 1): 0.05
}
assert abs(sum(forward_matrix.values()) - 1.0) < 1e-9

pTurnExact = 0.8
pTurnLeft = 0.1
pTurnRight = 0.1

# ================== Класс Robot ==================

class Robot:
    def __init__(self, real, orientation):
        self.real = real
        self.orientation = orientation
        self.last_scan_results = []  # результаты последнего сканирования

    def clear_scan_results(self):
        self.last_scan_results = []

    # ---------- Повороты ----------
    def turn_right(self):
        keys = list(rOrientation.keys())
        i = keys.index(self.orientation)
        new_orient = keys[(i + 1) % len(keys)]
        self.orientation = new_orient

        left_vec = self._left_from_orientation(new_orient)
        right_vec = self._right_from_orientation(new_orient)

        r = rd.random()
        if r < pTurnExact:
            move_vec = (0, 0)
        elif r < pTurnExact + pTurnLeft:
            move_vec = left_vec
        else:
            move_vec = right_vec

        new_i = self.real[0] + move_vec[0]
        new_j = self.real[1] + move_vec[1]
        if 0 <= new_i < high and 0 <= new_j < width and world[new_i, new_j] != 'wall':
            self.real[0] = new_i
            self.real[1] = new_j

        return self._apply_turn(p, move_vec)

    def turn_left(self):
        keys = list(rOrientation.keys())
        i = keys.index(self.orientation)
        new_orient = keys[(i - 1) % len(keys)]
        self.orientation = new_orient

        left_vec = self._left_from_orientation(new_orient)
        right_vec = self._right_from_orientation(new_orient)

        r = rd.random()
        if r < pTurnExact:
            move_vec = (0, 0)
        elif r < pTurnExact + pTurnLeft:
            move_vec = left_vec
        else:
            move_vec = right_vec

        new_i = self.real[0] + move_vec[0]
        new_j = self.real[1] + move_vec[1]
        if 0 <= new_i < high and 0 <= new_j < width and world[new_i, new_j] != 'wall':
            self.real[0] = new_i
            self.real[1] = new_j

        return self._apply_turn(p, move_vec)

    def _left_from_orientation(self, orient):
        if orient == 'up':
            return (0, -1)
        elif orient == 'right':
            return (-1, 0)
        elif orient == 'down':
            return (0, 1)
        elif orient == 'left':
            return (1, 0)

    def _right_from_orientation(self, orient):
        if orient == 'up':
            return (0, 1)
        elif orient == 'right':
            return (1, 0)
        elif orient == 'down':
            return (0, -1)
        elif orient == 'left':
            return (-1, 0)

    def _apply_turn(self, p, move_vec):
        turn_matrix = {
            (0, 0): pTurnExact,
            self._left_from_orientation(self.orientation): pTurnLeft,
            self._right_from_orientation(self.orientation): pTurnRight
        }
        return self._apply_motion(p, turn_matrix)

    def orient(self):
        return rOrientation[self.orientation]

    def str_orientation(self):
        return self.orientation

    def position(self):
        return list(self.real)

    # ---------- Сенсоры ----------
    def _sense(self, p, Z, sensor_pos=[0, 0], record_result=None):
        high, width = p.shape
        p_new = np.zeros((high, width))
        index_Z = np.where(ground == Z)[0][0]
        wall_index = np.where(ground == 'wall')[0][0]

        if record_result is not None:
            scan_i = self.real[0] + sensor_pos[0]
            scan_j = self.real[1] + sensor_pos[1]
            if 0 <= scan_i < high and 0 <= scan_j < width:
                self.last_scan_results.append(((scan_i, scan_j), record_result))

        for i in range(high):
            for j in range(width):
                pos_i = i + sensor_pos[0]
                pos_j = j + sensor_pos[1]
                if 0 <= pos_i < high and 0 <= pos_j < width:
                    index_True = np.where(ground == world[pos_i, pos_j])[0][0]
                else:
                    index_True = wall_index

                p_new[i, j] = p[i, j] * pSensor[index_True, index_Z]

        s = np.sum(p_new)
        if s > 0:
            return p_new / s
        else:
            return np.ones_like(p) / (high * width)

    def sense_under(self, p):
        flag = rd.random() < realSensorError['under']
        i, j = self.position()
        if flag:
            return self._sense(p, world[i, j], record_result=True)
        else:
            return self._sense(p, ground_False(world[i, j]), record_result=False)

    def sense_front(self, p):
        flag = rd.random() < realSensorError['front']
        i, j = self.position()
        sensor_pos = self.orient()
        pos_i = i + sensor_pos[0]
        pos_j = j + sensor_pos[1]
        if 0 <= pos_i < high and 0 <= pos_j < width:
            if flag:
                return self._sense(p, world[pos_i, pos_j], sensor_pos, record_result=True)
            else:
                return self._sense(p, ground_False(world[pos_i, pos_j]), sensor_pos, record_result=False)
        return self._sense(p, world[i, j] if flag else ground_False(world[i, j]), sensor_pos)

    def sense_front_right(self, p):
        flag = rd.random() < realSensorError['front_right']
        i, j = self.position()
        front = self.orient()
        right = [front[1], -front[0]]
        pos_i = i + front[0] + right[0]
        pos_j = j + front[1] + right[1]
        sensor_pos = [front[0] + right[0], front[1] + right[1]]
        if 0 <= pos_i < high and 0 <= pos_j < width:
            if flag:
                return self._sense(p, world[pos_i, pos_j], sensor_pos, record_result=True)
            else:
                return self._sense(p, ground_False(world[pos_i, pos_j]), sensor_pos, record_result=False)
        return self._sense(p, world[i, j] if flag else ground_False(world[i, j]), sensor_pos)

    def sense_front_left(self, p):
        flag = rd.random() < realSensorError['front_left']
        i, j = self.position()
        front = self.orient()
        left = [-front[1], front[0]]
        pos_i = i + front[0] + left[0]
        pos_j = j + front[1] + left[1]
        sensor_pos = [front[0] + left[0], front[1] + left[1]]
        if 0 <= pos_i < high and 0 <= pos_j < width:
            if flag:
                return self._sense(p, world[pos_i, pos_j], sensor_pos, record_result=True)
            else:
                return self._sense(p, ground_False(world[pos_i, pos_j]), sensor_pos, record_result=False)
        return self._sense(p, world[i, j] if flag else ground_False(world[i, j]), sensor_pos)

    # ---------- Движение ----------
    def _apply_motion(self, p, motion_dict):
        high, width = p.shape
        p_new = np.zeros((high, width))
        for i in range(high):
            for j in range(width):
                prob = p[i, j]
                if prob == 0:
                    continue
                for (di, dj), w in motion_dict.items():
                    ni = i + di
                    nj = j + dj
                    if 0 <= ni < high and 0 <= nj < width and world[ni, nj] != 'wall':
                        p_new[ni, nj] += prob * w
                    else:
                        p_new[i, j] += prob * w
        s = np.sum(p_new)
        if s > 0:
            return p_new / s
        else:
            return np.ones_like(p) / (high * width)

    def dir_move(self, p, direction):
        if direction == 1:
            motion = forward_matrix
        else:
            motion = {(-di, dj): w for (di, dj), w in forward_matrix.items()}
        oriented_motion = self._rotate_motion(motion, self.orientation)
        self._update_real_position(oriented_motion)
        return self._apply_motion(p, oriented_motion)

    def side_move(self, p, direction):
        if direction == 1:  # вправо
            rotated = {self._rotate_cw(di, dj): w for (di, dj), w in forward_matrix.items()}
        else:  # влево
            rotated = {self._rotate_ccw(di, dj): w for (di, dj), w in forward_matrix.items()}
        oriented_motion = self._rotate_motion(rotated, self.orientation)
        self._update_real_position(oriented_motion)
        return self._apply_motion(p, oriented_motion)

    def _rotate_motion(self, motion, orient):
        if orient == 'up':
            return motion
        rotated = {}
        for (di, dj), w in motion.items():
            if orient == 'right':
                new_di, new_dj = dj, -di
            elif orient == 'down':
                new_di, new_dj = -di, -dj
            elif orient == 'left':
                new_di, new_dj = -dj, di
            else:
                raise ValueError(f"Unknown orientation: {orient}")
            rotated[(new_di, new_dj)] = rotated.get((new_di, new_dj), 0) + w
        return rotated

    def _rotate_cw(self, di, dj):
        return (dj, -di)

    def _rotate_ccw(self, di, dj):
        return (-dj, di)

    def _update_real_position(self, motion_dict):
        items = list(motion_dict.items())
        displacements = [disp for disp, _ in items]
        weights = [w for _, w in items]
        chosen = rd.choices(displacements, weights=weights)[0]
        new_i = self.real[0] + chosen[0]
        new_j = self.real[1] + chosen[1]
        if 0 <= new_i < high and 0 <= new_j < width and world[new_i, new_j] != 'wall':
            self.real[0] = new_i
            self.real[1] = new_j

# ================== Параметры ошибок сенсоров ==================

realSensorError = {'under': 0.9, 'front': 0.8, 'front_right': 0.8, 'front_left': 0.8}
false_count = 0

def argmax(values):
    i, j = np.unravel_index(np.argmax(values), values.shape)
    return [int(i), int(j)]

# ================== Визуализация Pygame с двумя картами (поменяны местами) ==================

CELL_SIZE = 40
BORDER = 1
MAP_WIDTH = (width + 2 * BORDER) * CELL_SIZE
MAP_HEIGHT = (high + 2 * BORDER) * CELL_SIZE
GAP = 20  # промежуток между картами
WIN_WIDTH = MAP_WIDTH * 2 + GAP
WIN_HEIGHT = MAP_HEIGHT
FPS = 30

COLORS = {
    'wall': '#808080',
    'sand': '#F4A460',
    'grass': '#7CFC00',
    'tree': '#006400',
    'water': '#1E90FF'
}

def load_sprites(sprites_dir='sprites'):
    ground_sprites = {}
    drone_sprites = {}
    if os.path.exists(sprites_dir) and os.path.isdir(sprites_dir):
        for name in ground:
            path = os.path.join(sprites_dir, f"{name}.png")
            if os.path.isfile(path):
                try:
                    img = pygame.image.load(path).convert_alpha()
                    img = pygame.transform.scale(img, (CELL_SIZE, CELL_SIZE))
                    ground_sprites[name] = img
                except:
                    print(f"Не удалось загрузить спрайт {path}, используется цвет")
        drone_names = ['up', 'down', 'left', 'right']
        for orient in drone_names:
            path = os.path.join(sprites_dir, f"drone_{orient}.png")
            if os.path.isfile(path):
                try:
                    img = pygame.image.load(path).convert_alpha()
                    img = pygame.transform.scale(img, (CELL_SIZE, CELL_SIZE))
                    drone_sprites[orient] = img
                except:
                    print(f"Не удалось загрузить спрайт {path}, используется векторная отрисовка")
    return ground_sprites, drone_sprites

# ---------- Левая карта (основная) – теперь будет рисоваться слева ----------
def draw_main_map(screen, ground_sprites, drone_sprites, robot, prediction, offset_x):
    """Рисует основную карту с дроном, рамками и предсказанием."""
    # Область карты
    rect = pygame.Rect(offset_x, 0, MAP_WIDTH, MAP_HEIGHT)
    screen.fill((0, 0, 0), rect)

    # Рисуем внешние стены
    wall_color = pygame.Color(COLORS['wall'])
    # Верхняя и нижняя стены
    for x in range(width + 2 * BORDER):
        rect_top = pygame.Rect(offset_x + x * CELL_SIZE, 0, CELL_SIZE, CELL_SIZE)
        rect_bottom = pygame.Rect(offset_x + x * CELL_SIZE, (high + 2 * BORDER - 1) * CELL_SIZE, CELL_SIZE, CELL_SIZE)
        if 'wall' in ground_sprites:
            screen.blit(ground_sprites['wall'], rect_top)
            screen.blit(ground_sprites['wall'], rect_bottom)
        else:
            pygame.draw.rect(screen, wall_color, rect_top)
            pygame.draw.rect(screen, wall_color, rect_bottom)
    # Левая и правая стены
    for y in range(1, high + 2 * BORDER - 1):
        rect_left = pygame.Rect(offset_x + 0, y * CELL_SIZE, CELL_SIZE, CELL_SIZE)
        rect_right = pygame.Rect(offset_x + (width + 2 * BORDER - 1) * CELL_SIZE, y * CELL_SIZE, CELL_SIZE, CELL_SIZE)
        if 'wall' in ground_sprites:
            screen.blit(ground_sprites['wall'], rect_left)
            screen.blit(ground_sprites['wall'], rect_right)
        else:
            pygame.draw.rect(screen, wall_color, rect_left)
            pygame.draw.rect(screen, wall_color, rect_right)

    # Рисуем внутреннюю карту
    for i in range(high):
        for j in range(width):
            cell_type = world[i, j]
            x = offset_x + (j + BORDER) * CELL_SIZE
            y = (i + BORDER) * CELL_SIZE
            rect = pygame.Rect(x, y, CELL_SIZE, CELL_SIZE)
            if cell_type in ground_sprites:
                screen.blit(ground_sprites[cell_type], rect)
            else:
                color = COLORS.get(cell_type, (255, 255, 255))
                pygame.draw.rect(screen, pygame.Color(color), rect)
                pygame.draw.rect(screen, (0, 0, 0), rect, 1)

    # Рисуем результаты сканирования
    if robot.last_scan_results:
        for (i, j), success in robot.last_scan_results:
            x = offset_x + (j + BORDER) * CELL_SIZE
            y = (i + BORDER) * CELL_SIZE
            rect = pygame.Rect(x, y, CELL_SIZE, CELL_SIZE)
            color = (0, 255, 0) if success else (255, 0, 0)
            pygame.draw.rect(screen, color, rect, 3)

    # Рисуем дрона
    i, j = robot.position()
    orient = robot.str_orientation()
    center_x = offset_x + (j + BORDER) * CELL_SIZE + CELL_SIZE // 2
    center_y = (i + BORDER) * CELL_SIZE + CELL_SIZE // 2

    if orient in drone_sprites:
        rect = drone_sprites[orient].get_rect(center=(center_x, center_y))
        screen.blit(drone_sprites[orient], rect)
    else:
        center = (center_x, center_y)
        pygame.draw.circle(screen, (0, 255, 0), center, CELL_SIZE // 3, 2)
        orient_vec = robot.orient()
        arrow_end = (center_x + orient_vec[1] * CELL_SIZE // 3,
                     center_y + orient_vec[0] * CELL_SIZE // 3)
        pygame.draw.line(screen, (0, 255, 0), center, arrow_end, 2)

    # Предсказанное положение (красный крест)
    pi, pj = prediction
    pred_center_x = offset_x + (pj + BORDER) * CELL_SIZE + CELL_SIZE // 2
    pred_center_y = (pi + BORDER) * CELL_SIZE + CELL_SIZE // 2
    pred_center = (pred_center_x, pred_center_y)
    size = CELL_SIZE // 3
    pygame.draw.line(screen, (255, 0, 0),
                     (pred_center[0] - size, pred_center[1] - size),
                     (pred_center[0] + size, pred_center[1] + size), 2)
    pygame.draw.line(screen, (255, 0, 0),
                     (pred_center[0] + size, pred_center[1] - size),
                     (pred_center[0] - size, pred_center[1] + size), 2)

# ---------- Правая карта (вероятности) – теперь будет рисоваться справа ----------
def draw_prob_map(screen, p, prediction, offset_x):
    """Рисует карту вероятностей: красные оттенки и белые цифры, синий квадрат для предсказания."""
    # Область карты
    rect = pygame.Rect(offset_x, 0, MAP_WIDTH, MAP_HEIGHT)
    screen.fill((0, 0, 0), rect)

    # Рисуем стены по краям (серые)
    wall_color = pygame.Color(COLORS['wall'])
    # Верхняя и нижняя стены
    for x in range(width + 2 * BORDER):
        rect_top = pygame.Rect(offset_x + x * CELL_SIZE, 0, CELL_SIZE, CELL_SIZE)
        rect_bottom = pygame.Rect(offset_x + x * CELL_SIZE, (high + 2 * BORDER - 1) * CELL_SIZE, CELL_SIZE, CELL_SIZE)
        pygame.draw.rect(screen, wall_color, rect_top)
        pygame.draw.rect(screen, wall_color, rect_bottom)
    # Левая и правая стены
    for y in range(1, high + 2 * BORDER - 1):
        rect_left = pygame.Rect(offset_x + 0, y * CELL_SIZE, CELL_SIZE, CELL_SIZE)
        rect_right = pygame.Rect(offset_x + (width + 2 * BORDER - 1) * CELL_SIZE, y * CELL_SIZE, CELL_SIZE, CELL_SIZE)
        pygame.draw.rect(screen, wall_color, rect_left)
        pygame.draw.rect(screen, wall_color, rect_right)

    max_p = np.max(p) if np.max(p) > 0 else 1
    font = pygame.font.Font(None, 20)

    # Рисуем клетки внутренней области
    for i in range(high):
        for j in range(width):
            x = offset_x + (j + BORDER) * CELL_SIZE
            y = (i + BORDER) * CELL_SIZE
            rect = pygame.Rect(x, y, CELL_SIZE, CELL_SIZE)

            prob = p[i, j]
            if prob > 0:
                alpha = int(255 * prob / max_p)
                color = (255, 0, 0, alpha)
                # Создаём поверхность для заливки
                surf = pygame.Surface((CELL_SIZE, CELL_SIZE), pygame.SRCALPHA)
                surf.fill(color)
                screen.blit(surf, (x, y))
            else:
                # Чёрный фон
                pygame.draw.rect(screen, (0, 0, 0), rect)

            # Белая рамка для всех клеток
            pygame.draw.rect(screen, (50, 50, 50), rect, 1)

            # Текст вероятности
            if prob > 0:
                text = font.render(f"{prob:.2f}", True, (255, 255, 255))
                text_rect = text.get_rect(center=(x + CELL_SIZE//2, y + CELL_SIZE//2))
                screen.blit(text, text_rect)

    # Синий квадрат для предсказания (клетка с максимальной вероятностью)
    pi, pj = prediction
    if world[pi, pj] != 'wall':  # предсказание может быть в стене? но макс вероятность может быть в стене? В нашем распределении стены имеют нулевую вероятность, так что ок.
        x = offset_x + (pj + BORDER) * CELL_SIZE
        y = (pi + BORDER) * CELL_SIZE
        rect = pygame.Rect(x, y, CELL_SIZE, CELL_SIZE)
        pygame.draw.rect(screen, (0, 0, 255), rect, 3)  # синяя рамка толщиной 3

def draw_future_scan_targets(screen, robot, offset_x):
    """Рисует фиолетовые рамки для будущих целей сенсоров на основной карте."""
    i, j = robot.position()
    orient = robot.orient()
    positions = [
        (i, j),  # under
        (i + orient[0], j + orient[1]),  # front
        (i + orient[0] + orient[1], j + orient[1] - orient[0]),  # front_right
        (i + orient[0] - orient[1], j + orient[1] + orient[0])   # front_left
    ]
    for pi, pj in positions:
        if 0 <= pi < high and 0 <= pj < width:
            x = offset_x + (pj + BORDER) * CELL_SIZE
            y = (pi + BORDER) * CELL_SIZE
            rect = pygame.Rect(x, y, CELL_SIZE, CELL_SIZE)
            pygame.draw.rect(screen, (128, 0, 128), rect, 3)  # фиолетовый

def draw_info(screen, mode, false_count=None, step=None):
    font = pygame.font.Font(None, 24)
    y = 10
    if mode == "auto":
        if step is not None:
            text_step = font.render(f"Шаг: {step}", True, (255, 255, 255))
            screen.blit(text_step, (10, y))
            y += 20
        if false_count is not None:
            text_errors = font.render(f"Ошибки: {false_count}", True, (255, 255, 255))
            screen.blit(text_errors, (10, y))
            y += 20
    else:
        instructions = [
            "WASD: движение",
            "Q/E: поворот налево/направо",
            "Пробел: выполнить сенсоры",
            "Esc: выход"
        ]
        for line in instructions:
            text = font.render(line, True, (255, 255, 255))
            screen.blit(text, (10, y))
            y += 20

def draw_all(screen, ground_sprites, drone_sprites, robot, p, prediction, mode,
             false_count=None, step=None, show_future=False):
    # Левая карта (основная) - смещение 0
    draw_main_map(screen, ground_sprites, drone_sprites, robot, prediction, 0)
    # Правая карта (вероятности) - смещение MAP_WIDTH + GAP
    draw_prob_map(screen, p, prediction, MAP_WIDTH + GAP)
    # Если нужно, фиолетовые рамки на основной карте (слева)
    if show_future:
        draw_future_scan_targets(screen, robot, 0)
    # Информация (поверх всего, в левом верхнем углу)
    draw_info(screen, mode, false_count, step)
    pygame.display.flip()

# ================== Автоматический режим ==================

def run_auto_mode(screen, ground_sprites, drone_sprites, robot):
    global p, false_count
    clock = pygame.time.Clock()
    for k in range(10):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

        # --- Шаг сенсоров ---
        robot.clear_scan_results()
        p = robot.sense_under(p)
        p = robot.sense_front(p)
        p = robot.sense_front_right(p)
        p = robot.sense_front_left(p)

        prediction = argmax(p)
        print(f'Шаг {k} (сенсоры): реальное={robot.position()}, предсказание={prediction}')
        draw_all(screen, ground_sprites, drone_sprites, robot, p, prediction, "auto", false_count, k, show_future=False)
        clock.tick(2)

        if not np.array_equal(robot.position(), prediction):
            false_count += 1

        # --- Шаг движения ---
        if k % 2:
            p = robot.side_move(p, 1)   # движение вправо
        else:
            p = robot.dir_move(p, 1)    # движение вперёд

        prediction = argmax(p)
        print(f'Шаг {k} (движение): реальное={robot.position()}, предсказание={prediction}')
        draw_all(screen, ground_sprites, drone_sprites, robot, p, prediction, "auto", false_count, k, show_future=True)
        clock.tick(2)
        pygame.time.delay(500)

    print(f'Всего ошибок: {false_count}')

# ================== Ручной режим ==================

def run_manual_mode(screen, ground_sprites, drone_sprites, robot):
    global p
    clock = pygame.time.Clock()
    running = True
    show_future = True
    while running:
        prediction = argmax(p)
        draw_all(screen, ground_sprites, drone_sprites, robot, p, prediction, "manual", show_future=show_future)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                # Движение
                elif event.key == pygame.K_w:
                    robot.clear_scan_results()
                    p = robot.dir_move(p, 1)
                    show_future = True
                elif event.key == pygame.K_s:
                    robot.clear_scan_results()
                    p = robot.dir_move(p, -1)
                    show_future = True
                elif event.key == pygame.K_a:
                    robot.clear_scan_results()
                    p = robot.side_move(p, -1)
                    show_future = True
                elif event.key == pygame.K_d:
                    robot.clear_scan_results()
                    p = robot.side_move(p, 1)
                    show_future = True
                # Повороты
                elif event.key == pygame.K_q:
                    robot.clear_scan_results()
                    p = robot.turn_left()
                    show_future = True
                elif event.key == pygame.K_e:
                    robot.clear_scan_results()
                    p = robot.turn_right()
                    show_future = True
                # Сенсоры
                elif event.key == pygame.K_SPACE:
                    robot.clear_scan_results()
                    p = robot.sense_under(p)
                    p = robot.sense_front(p)
                    p = robot.sense_front_right(p)
                    p = robot.sense_front_left(p)
                    show_future = False

        clock.tick(FPS)

# ================== Запуск ==================

if __name__ == "__main__":
    pygame.init()
    screen = pygame.display.set_mode((WIN_WIDTH, WIN_HEIGHT))
    mode_str = "РУЧНОЙ" if manual_mode else "АВТО"
    pygame.display.set_caption(f"Марковская локализация ({map_file}) - режим {mode_str}")

    ground_sprites, drone_sprites = load_sprites()
    robot = Robot(real, 'right')

    if manual_mode:
        run_manual_mode(screen, ground_sprites, drone_sprites, robot)
    else:
        run_auto_mode(screen, ground_sprites, drone_sprites, robot)

    pygame.quit()
    sys.exit()
