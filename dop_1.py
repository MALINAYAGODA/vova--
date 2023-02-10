from PIL import Image, ImageDraw


# переводим пиксели в систему координат [0; 1] + сжатие
def normalize(s: list, koef=0, is_up=False):
    if is_up:
        min_value = min(s) + koef
        max_value = max(s) - koef
    else:
        min_value = min(s) - koef
        max_value = max(s) + koef
    dif = max_value - min_value
    for i in range(len(s)):
        s[i] = (s[i] - min_value) / dif
    return s


# создание портрета
def create_white_portret_one(inp):
    color = '#000000'  # цвет
    choice = 5  # кол-во точек на портрете
    coef_aligning = 0.2  # коэф сжатия
    k = 4  # радиус точки на рисунке
    vertically = True  # рисовать горизонтально или вертикально
    # точки, цвет, вид, коэф сжатия, радиуса круга, поворот камеры (0 (True) | 90 (False))
    # размер выдаваемой картинки
    if vertically:
        real_height, real_width = 3508, 2480
    else:
        real_height, real_width = 2480, 3508
    points_all = inp[0][1]  # все точки 68 точек
    points_crop = [list(i) for i in inp[0][0]]  # unique 5 точек
    if choice == 5:
        points = points_crop
    else:
        points = points_all
    # переведем в квадрат
    x1, y1, x2, y2 = inp[0][2]  # берем крайний левый и нижний правый угол координаты
    max_y = max([j[1] for j in points])  # ищем самую max 'y' точку
    if max_y > y2:  # если квадрат за границей (берет не все лицо)
        y1, y2 = y1 + (max_y - y2), max_y  # сдвигаем область лицо вниз
    # переведем все точки в новую систему координат (квадрат) где x0 = 0
    df_x, df_y = x1, y1
    for i in range(len(points)):
        x, y = points[i]
        points[i] = [x - df_x, y - df_y]
    size = min(real_height, real_width)  # найдем минимальный размер
    # переводим в новую систему относительно размера картинки
    x_p = [i / (x2 - x1) for i in [j[0] for j in points]]
    y_p = [i / (y2 - y1) for i in [j[1] for j in points]]
    # уменьшаем размер, если coef_aligning не пуст
    if coef_aligning is not None:
        x_p = normalize(x_p, coef_aligning)
        y_p = normalize(y_p, coef_aligning)
    for i in range(len(points)):  # преобразование в формат A4 (точки в относительной системе коорд)
        points[i] = [x_p[i] * size,
                     y_p[i] * size]
    # сдвиг к центру
    df_x = (real_width // 2) - ((max([j[0] for j in points]) + min([j[0] for j in points])) // 2)
    df_y = (real_height // 2) - ((max([j[1] for j in points]) + min([j[1] for j in points])) // 2)
    for i in range(len(points)):  # сдвиг к центру
        points[i] = [points[i][0] + df_x,
                     points[i][1] + df_y]
    # выписываем сдвиг + переводим в мм
    coordinates_in_mm = []
    for i in range(len(points)):  # перебираем точки и пишем их: длину, ширину на А4
        x, y = points[i]
        coordinates_in_mm.append([round((x / real_width) * 2100), round((y / real_height) * 2100)])
    # создаем холст
    image = Image.new('RGB', (real_width, real_height), "WHITE")
    # разрешаем рисовать
    draw = ImageDraw.Draw(image)
    for i in points:  # перебираем точки и рисуем их на холсте
        x, y = i
        draw.ellipse((x - k, y - k, x + k, y + k), fill=color)
    # отправляем координаты в мм и сам изрисованный холст
    return coordinates_in_mm, image
