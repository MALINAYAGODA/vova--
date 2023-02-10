import telebot
import io
from PIL import Image
from main import find_contour_face
from dop_1 import create_white_portret_one

# bot
bot = telebot.TeleBot("5372525462:AAEd1HbGSDpYbIW-TuajxbvAgKrC6Qi4OKA")


# приветствие
@bot.message_handler(commands=['start'])
def start(message):
    # создаем клавиатуру помощника
    markup = telebot.types.ReplyKeyboardMarkup()
    markup.add(telebot.types.KeyboardButton('/help'))
    # отправляем html сообщение
    bot.send_message(message.chat.id,
                     f"Привет <b>{message.from_user.username}</b>! Меня зовут _. Я бот, который превращает"
                     " твои фотографии в наброски формата A4."
                     " С помощью них, ты сможешь нарисовать картину лучше"
                     " и точнее!\nЕсли что-то не понятно, напиши /help. Жду ваше фото для обработки!",
                     parse_mode='html',
                     reply_markup=markup)
    print('start')


# помощь
@bot.message_handler(commands=['help'])
def help_pl(message):
    s = f"Раскрываем карты! Самая главная моя цель - отдать вам то, что вы хотите," \
        f" а именно набросок портрета. <b>Портрет</b> - это выделение единственного" \
        f" лица на фото и вставка его точек в центр листа А4." \
        f" Если на фотографии будет <b>больше 1 лица</b> - я не смогу вам помочь." \
        f" После получения своего, вы можете кормить меня" \
        f" своими фотками дальше - я буду только рад!"
    # отправляем html сообщение
    bot.send_message(message.chat.id, s, parse_mode='html')
    print('help')


#  ответ на любой введенный текст
@bot.message_handler(content_types=['text'])
def answer(message):  # ответ на любой введенный текст
    bot.send_message(message.chat.id, 'Жду ваше фото:')
    print(message.text)


# когда отправляют фото
@bot.message_handler(content_types=['photo'])
def put_photo(message):
    print('фото принято')
    # отправляем сообщение
    bot.send_message(message.chat.id,
                     'Одну секунду...')
    # берем изображение
    fileID = message.photo[-1].file_id
    file_info = bot.get_file(fileID)
    downloaded_file = bot.download_file(file_info.file_path)  # возвращает в байтах
    img = Image.open(io.BytesIO(downloaded_file))  # преобразовываем байты в Image
    res = find_contour_face(img)  # берем координаты лиц
    people_id = message.chat.id  # берем id пользователя
    if len(res) != 0:  # если на картинке есть лица
        our_photo = res[-1]  # берем обработанное изображение со всеми лицами
        # Перевод из BGR to RGB
        for i in range(our_photo.shape[0]):
            for j in range(our_photo.shape[1]):
                our_photo[i][j][0], our_photo[i][j][1], our_photo[i][j][2] = our_photo[i][j][
                                                                                 2], \
                                                                             our_photo[i][j][
                                                                                 1], \
                                                                             our_photo[i][j][
                                                                                 0]
        photo = Image.fromarray(res[-1], 'RGB')  # из numpy в array
        bot.send_photo(people_id, photo)  # отправляем фото с необработанными лицами
        #  photo.show()  # показ на комп
        if len(res[0]) == 1:  # одно лицо
            # берем из первого лица все, кроме последнего элемента (картинки)
            purpose = [res[0][0][:-1]]
            size_photo = res[-1]  # размер фото
            # берем расстояние в мм и сам обработанный шаблон
            coordinates_in_mm, img = create_white_portret_one(purpose + [size_photo])
            # сохраняем картинку
            img.save(f'{people_id}' + ".jpg")  # , encoding="utf8"
            with open(f'{people_id}'".jpg", "rb") as file:  # открываем для отправки как файлом
                bot.send_document(people_id, document=file)
            # пишем отступы точек
            names_coord = ['righteye', 'lefteye', 'nose', 'rightmouth', 'leftmouth']
            str_coord = 'Объект Ширина Длина\n'  # все сохраняем в эту строку
            # перебираем координаты и выписываем
            for i in range(len(coordinates_in_mm)):
                x, y = coordinates_in_mm[i]
                name = names_coord[i]
                str_coord += f'{name}: {x} {y}\n'
            print(str_coord)
            bot.send_message(people_id, str_coord)  # отправляем расстояние
            bot.send_message(people_id,
                             'Вот ваш набросок! Думаю получиться отличная картина!'
                             ' Жду ваше новое фото:')
            print('фото отправлено')
        else:  # много лиц
            bot.send_message(people_id,
                             f'На фото {len(res[0])} лиц. Пока я не могу их всех обработать.'
                             f' Жду твое новое фото, для превращения:')
    else:
        bot.send_message(people_id,
                         'На фотографии не обнаружены лица. Жду твое новое фото, для превращения:')


bot.polling()  # заканчиваем сеанс
