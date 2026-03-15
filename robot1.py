import numpy as np
import random as rd

class Robot:
    def __init__(self, real, orientation):
        self.real = real
        self.orientation = orientation

    def turn_right(self):
        keys = list(rOrientation.keys())
        i = keys.index(self.orientation)
        self.orientation = keys[(i + 1) % len(keys)]

    def turn_left(self):
        keys = list(rOrientation.keys())
        i = keys.index(self.orientation)
        self.orientation = keys[(i - 1) % len(keys)]

    def orient(self):
        return rOrientation[self.orientation]
    
    def str_orientation(self):
        return self.orientation
    
    def position(self):
        return self.real
    
    def sense_under(self, p, Z):
        return sense(p, Z)
    
    def sense_front(self, p, Z):
        sensor_pos = rOrientation[self.orientation]
        return sense(p, Z, sensor_pos)
    
    def sense_front_right(self, p, Z):
        front = rOrientation[self.orientation]
        right = [front[1], -front[0]]
        sensor_pos = [
            front[0] + right[0],
            front[1] + right[1]
        ]
        return sense(p, Z, sensor_pos)
    
    def sense_front_left(self, p, Z):
        front = rOrientation[self.orientation]
        left = [-front[1], front[0]]
        sensor_pos = [
            front[0] + left[0],
            front[1] + left[1]
        ]
        return sense(p, Z, sensor_pos)      
     
    def side_move(self, p, U):
        high, width = p.shape
        front = self.orient()
        side = [abs(front[1]), abs(front[0])]
        self.real[0] = (self.real[0] + side[0] * U) % high
        self.real[1] = (self.real[1] + side[1] * U) % width

        p_new = np.zeros((high, width))

        for i in range(high):
            for j in range(width):
                i_dop = (i - side[0] * U) % high
                j_dop = (j - side[1] * U) % width
                s = pExact['side'] * p[i_dop, j_dop]

                i_dop = (i - side[0] * (U + 1)) % high
                j_dop = (j - side[1] * (U + 1)) % width
                s += pOvershoot['side'] * p[i_dop, j_dop]

                i_dop = (i - side[0] * (U - 1)) % high
                j_dop = (j - side[1] * (U - 1)) % width
                s += pUndershoot['side'] * p[i_dop, j_dop]
                p_new[i, j] = s
    
        return p_new
        
    def dir_move(self, p, U):
        high, width = p.shape

        front = self.orient()
        direction = [front[0], front[1]]
        self.real[0] = (self.real[0] + direction[0] * U) % high
        self.real[1] = (self.real[1] + direction[1] * U) % width

        p_new = np.zeros((high, width))

        for i in range(high):
            for j in range(width):
                i_dop = (i - direction[0] * U) % high
                j_dop = (j - direction[1] * U) % width
                s = pExact['dir'] * p[i_dop, j_dop]

                i_dop = (i - direction[0] * (U + 1)) % high
                j_dop = (j - direction[1] * (U + 1)) % width
                s += pOvershoot['dir'] * p[i_dop, j_dop]

                i_dop = (i - direction[0] * (U - 1)) % high
                j_dop = (j - direction[1] * (U - 1)) % width
                s += pUndershoot['dir'] * p[i_dop, j_dop]
                p_new[i, j] = s
    
        return p_new      


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

world = map_read('map_fine.txt')
high, width = world.shape
ground = np.array(['sand', 'grass', 'tree', 'water'])

def ground_False(Z):
    ground_False = [gr for gr in ground if gr != Z]
    return rd.choice(ground_False)

def init_pos(high, width):
    p = np.zeros((high, width))
    i = rd.randint(0, high - 1)
    j = rd.randint(0, width - 1)
    p[i, j] = 1.0
    return p, [i, j]

p, real = init_pos(high, width)
print(p)

pHit = 0.8
pMiss = (1 - pHit) / (ground.shape[0] - 1)

pSensor = np.full((ground.shape[0], ground.shape[0]), pMiss)
np.fill_diagonal(pSensor, pHit)

rOrientation_keys = ['up', 'right', 'down', 'left']
rOrientation_values = [[-1, 0], [0, 1], [1, 0], [0, -1]]
rOrientation = {keys : values
          for keys, values in zip(rOrientation_keys, rOrientation_values)}

pExact_keys = ['side', 'dir']
pExact_values = [0.8, 0.8]
pExact = {keys : values
          for keys, values in zip(pExact_keys, pExact_values)}

pOvershoot_keys = ['side', 'dir']
pOvershoot_values = [0.1, 0.1]
pOvershoot = {keys : values
          for keys, values in zip(pOvershoot_keys, pOvershoot_values)}

pUndershoot_keys = ['side', 'dir']
pUndershoot_values = [0.1, 0.1]
pUndershoot = {keys : values
          for keys, values in zip(pUndershoot_keys, pUndershoot_values)}

prediction = np.zeros(2)
false_count = 0
realSensorError = 0.9

def argmax(values):
    i, j = np.unravel_index(np.argmax(values), values.shape)
    return [int(i), int(j)]


def sense(p, Z, sensor_pos = [0, 0]):
    high, width = p.shape
    p_new = np.zeros((high, width))
    index_Z = np.where(ground == Z)[0][0]
    for i in range(high):
        for j in range(width):
            pos_i = (i + sensor_pos[0]) % high
            pos_j = (j + sensor_pos[1]) % width            
            index_True = np.where(ground == world[pos_i, pos_j])[0][0]
            p_new[i, j] = p[i, j] * pSensor[index_True, index_Z]

    s = np.sum(p_new)
    p_new = p_new / s

    return p_new


if __name__ == "__main__":
    robot = Robot(real, 'right')
    for k in range(10):
        #1
        flag = rd.random() < realSensorError
        i, j = robot.position()
        if flag:
            p = robot.sense_under(p, world[i, j])
        else:
            p = robot.sense_under(p, ground_False(world[i, j]))     

        #2
        flag = rd.random() < realSensorError
        i, j = robot.position()
        sensor_pos = robot.orient()
        pos_i = (i + sensor_pos[0]) % high
        pos_j = (j + sensor_pos[1]) % width
        if flag:
            p = robot.sense_front(p, world[pos_i, pos_j])
        else:
            p = robot.sense_front(p, ground_False(world[pos_i, pos_j]))
    
        #3
        flag = rd.random() < realSensorError
        i, j = robot.position()
        front = robot.orient()
        right = [front[1], -front[0]]
        pos_i = (i + front[0] + right[0]) % high
        pos_j = (j + front[1] + right[1]) % width
        if flag:
            p = robot.sense_front_right(p, world[pos_i, pos_j])
        else:
            p = robot.sense_front_right(p, ground_False(world[pos_i, pos_j]))

        #4
        flag = rd.random() < realSensorError
        i, j = robot.position()
        front = robot.orient()
        left = [-front[1], front[0]]
        pos_i = (i + front[0] + left[0]) % high
        pos_j = (j + front[1] + left[1]) % width
        if flag:
            p = robot.sense_front_left(p, world[pos_i, pos_j])
        else:
            p = robot.sense_front_left(p, ground_False(world[pos_i, pos_j]))

        prediction = argmax(p)
        print('sense: ', end = '')
        print(p)
        print(f'real={robot.position()}, {prediction=}')

        if k % 2:
            p = robot.side_move(p, 1)
        else:
            p = robot.dir_move(p, 1)

        prediction = argmax(p)
        print('move:  ', end = '')
        print(p)
        print(f'real={robot.position()}, {prediction=}\n')

        if not np.array_equal(robot.position(), prediction):
            false_count += 1
        
    print(f'{false_count=}')
