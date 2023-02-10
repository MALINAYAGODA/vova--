from __future__ import division
import torch
import cv2
import numpy as np
from PIL import Image
import time

from common.utils import BBox, drawLandmark_multiple
from models.mobilefacenet import MobileFaceNet
from Retinaface import Retinaface
from utils.align_trans import get_reference_facial_points, warp_and_crop_face

mean = np.asarray([0.485, 0.456, 0.406])
std = np.asarray([0.229, 0.224, 0.225])

crop_size = 112
scale = crop_size / 112.
reference = get_reference_facial_points(default_square=True) * scale

# использование gpu или cpu
if torch.cuda.is_available():
    map_location = lambda storage, loc: storage.cuda()
else:
    map_location = 'cpu'


# загружаем модель
def load_model():
    # if args.backbone=='MobileFaceNet':
    model = MobileFaceNet([112, 112], 136)
    checkpoint = torch.load('checkpoint/mobilefacenet_model_best.pth.tar', map_location=map_location)
    print('Use MobileFaceNet as backbone')
    # end
    model.load_state_dict(checkpoint['state_dict'])  # загружаем модель (веса)
    return model


# главная функция по разметки лиц
def find_contour_face(pil_image):
    out_size = 112
    model = load_model()  # открыли модель
    model = model.eval()  # оценить модель, отключение вычисления градиентов
    open_cv_image = np.array(pil_image)  # перевод из Image -> numpy
    # Перевод из RGB to BGR
    img = open_cv_image[:, :, ::-1].copy()
    org_img = pil_image
    height, width, _ = img.shape  # размер фото
    retinaface = Retinaface.Retinaface()
    faces = retinaface(img)  # получаем координаты наших лиц
    if len(faces) == 0:  # если лица не найдены
        print('NO face is detected!')
        return []
    all_faces = []
    for k, face in enumerate(faces):  # перебирание [номер, лицо]
        if face[4] < 0.9:  # если лицо с маленьким шансом
            continue
        x1 = face[0]
        y1 = face[1]
        x2 = face[2]
        y2 = face[3]
        w = x2 - x1 + 1  # ширина
        h = y2 - y1 + 1  # длина
        size = int(min([w, h]) * 1.2)
        cx = x1 + w // 2  # середина по x
        cy = y1 + h // 2  # середина по y
        #  сдвигаем
        x1 = cx - size // 2
        x2 = x1 + size
        y1 = cy - size // 2
        y2 = y1 + size

        # чтобы не свалилась
        dx = max(0, -x1)
        dy = max(0, -y1)
        x1 = max(0, x1)
        y1 = max(0, y1)

        edx = max(0, x2 - width)
        edy = max(0, y2 - height)
        x2 = min(width, x2)
        y2 = min(height, y2)
        # end
        new_bbox = list(map(int, [x1, x2, y1, y2]))  # переводим из float -> int
        # преобразуем матрицу картинки для работы модели
        new_bbox = BBox(new_bbox)  # объект BBox
        cropped = img[new_bbox.top:new_bbox.bottom, new_bbox.left:new_bbox.right]
        if (dx > 0 or dy > 0 or edx > 0 or edy > 0):
            cropped = cv2.copyMakeBorder(cropped, int(dy), int(edy), int(dx), int(edx),
                                         cv2.BORDER_CONSTANT, 0)
        cropped_face = cv2.resize(cropped, (out_size, out_size))

        if cropped_face.shape[0] <= 0 or cropped_face.shape[1] <= 0:
            continue
        test_face = cropped_face.copy()
        test_face = test_face / 255.0
        test_face = test_face.transpose((2, 0, 1))
        test_face = test_face.reshape((1,) + test_face.shape)
        input = torch.from_numpy(test_face).float()
        input = torch.autograd.Variable(input)  # преобразованные входные данные
        start = time.time()
        # работа модели (на последнем слое выдает 136 эл, что значит 68 точек)
        landmark = model(input)[0].cpu().data.numpy()  # работа модели
        end = time.time()
        print('Time: {:.6f}s.'.format(end - start))
        landmark = landmark.reshape(-1, 2)  # группируем по точкам
        landmark = new_bbox.reprojectLandmark(landmark)  # возвращаем в нормальный вид
        img = drawLandmark_multiple(img, new_bbox, landmark)  # рисуем квадраты на лицах
        # находим целевые точки на лице
        lefteye_x = 0
        lefteye_y = 0
        for i in range(36, 42):
            lefteye_x += landmark[i][0]
            lefteye_y += landmark[i][1]
        lefteye_x = lefteye_x / 6
        lefteye_y = lefteye_y / 6
        lefteye = [lefteye_x, lefteye_y]

        righteye_x = 0
        righteye_y = 0
        for i in range(42, 48):
            righteye_x += landmark[i][0]
            righteye_y += landmark[i][1]
        righteye_x = righteye_x / 6
        righteye_y = righteye_y / 6
        righteye = [righteye_x, righteye_y]

        nose = landmark[33]
        leftmouth = landmark[48]
        rightmouth = landmark[54]
        # все 5 целевых точек на лице
        facial5points = [righteye, lefteye, nose, rightmouth, leftmouth]
        # добавляем на фото точки
        warped_face = warp_and_crop_face(np.array(org_img), facial5points, reference,
                                         crop_size=(crop_size, crop_size))
        # из array -> в картинку
        img_warped = Image.fromarray(warped_face)
        # сохраняем параметры лица (5 целевых точек на лице,
        all_faces.append([facial5points, landmark, [x1, y1, x2, y2], img_warped])
    # отдаем параметры лица + ширину и длину картинки + разрисованную картинку
    return [all_faces] + [[height, width]] + [img]
