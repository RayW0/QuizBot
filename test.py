import requests
import random
from googletrans import Translator
from telebot import TeleBot
from telebot.types import ReplyKeyboardMarkup, KeyboardButton

# Telegram API токен
TOKEN = '6872700666:AAHJzqKx6H54fzFvr3oWCQxsehNfYLqTrn8'

# Константы для категорий и сложностей
CATEGORIES = {
    '32': 'Мультфильмы и анимация',
    '31': 'Аниме и манга',
    '15': 'Видео игры',
    '9': 'Общие знания'
}

DIFFICULTIES = {
    'easy': 'Легкий',
    'medium': 'Средний',
    'hard': 'Сложный',
}

# Инициализация бота
bot = TeleBot(TOKEN)


# Перевод текста на русский
def translate_text(text, translator):
    return translator.translate(text, src='en', dest='ru').text


# Получение вопросов из Open Trivia DB
def get_quiz_questions(amount, category, difficulty):
    url = 'https://opentdb.com/api.php'
    api_token = 'eed0422ca6d60108f848808abc8c1a97bb7a3e0f3834cd2165cf8382a4f2627a'
    params = {
        'amount': amount,
        'category': category,
        'difficulty': difficulty,
        'type': 'multiple',
        'token': api_token
    }
    response = requests.get(url, params=params).json()
    return response['results']


# Команда /startquiz
@bot.message_handler(commands=["startquiz"])
def send_welcome(message):
    bot.send_message(message.chat.id, "Вас приветствует бот по квизам для любителей хентайных мультиков и поиграть в доту!")
    markup = ReplyKeyboardMarkup(row_width=3)

    # Кнопки с категориями
    for category_id, category_name in CATEGORIES.items():
        item_button = KeyboardButton(category_name)
        markup.add(item_button)

    bot.send_message(message.chat.id, "Выберите категорию:", reply_markup=markup)


@bot.message_handler(commands=['clear'])
def clear_chat(message):
    # Получаем информацию о чате
    chat_id = message.chat.id
    bot.send_message(chat_id, "Очищаю последние сообщения...")

    # Начинаем с текущего сообщения и удаляем последние 100 сообщений
    message_id = message.message_id

    for i in range(100):
        try:
            bot.delete_message(chat_id, message_id - i)
        except Exception as e:
            print(f"Не удалось удалить сообщение {message_id - i}: {e}")

    bot.send_message(chat_id, "Чат очищен!")

# Обработка выбора категории
@bot.message_handler(func=lambda message: message.text in CATEGORIES.values())
def select_category(message):
    category_name = message.text
    category_id = [k for k, v in CATEGORIES.items() if v == category_name][0]

    markup = ReplyKeyboardMarkup(row_width=3)

    # Кнопки со сложностью
    for difficulty in DIFFICULTIES.values():
        item_button = KeyboardButton(difficulty)
        markup.add(item_button)

    # Сохраняем категорию и ждем выбора сложности
    bot.send_message(message.chat.id, f"Категория {category_name}. Выберите сложность:", reply_markup=markup)
    bot.register_next_step_handler(message, select_difficulty, category_id)


# Обработка выбора сложности
def select_difficulty(message, category_id):
    difficulty_russian = message.text.lower()

    # Найти соответствующий ключ на английском
    difficulty = [key for key, value in DIFFICULTIES.items() if value.lower() == difficulty_russian]
    if difficulty:
        difficulty = difficulty[0]  # Извлечь ключ (easy, medium, hard)
        bot.send_message(message.chat.id, "Сколько вопросов вы хотите?", reply_markup=None)
        bot.register_next_step_handler(message, start_quiz, category_id, difficulty)
    else:
        bot.send_message(message.chat.id, "Пожалуйста, выберите правильную сложность.")


# Начало квиза
def start_quiz(message, category_id, difficulty):
    try:
        amount = int(message.text)
    except ValueError:
        bot.send_message(message.chat.id, "Введите корректное количество вопросов.")
        return

    questions = get_quiz_questions(amount, category_id, difficulty)
    translator = Translator()

    # Создаем состояние викторины (список вопросов и текущий счёт)
    quiz_state = {
        'questions': questions,
        'current_question': 0,
        'score': 0,
        'translator': translator
    }

    send_next_question(message, quiz_state)


# Отправка следующего вопроса
def send_next_question(message, quiz_state):
    question_idx = quiz_state['current_question']
    if question_idx < len(quiz_state['questions']):
        question_data = quiz_state['questions'][question_idx]

        # Убираем запятую, чтобы вопрос был строкой
        question = (question_data['question'])
        correct_answer = (question_data['correct_answer'])
        incorrect_answers = [ans for ans in
                             question_data['incorrect_answers']]

        all_answers = incorrect_answers + [correct_answer]
        random.shuffle(all_answers)

        # Формируем сообщение с вопросом и вариантами ответов
        answers_str = "\n".join([f"{i + 1}. {a}" for i, a in enumerate(all_answers)])
        bot.send_message(message.chat.id, f"Вопрос {question_idx + 1}:\n{question}\n\n{answers_str}")

        # Сохраняем правильный ответ в состоянии и ждем ответа пользователя
        quiz_state['correct_answer'] = correct_answer
        quiz_state['all_answers'] = all_answers

        bot.register_next_step_handler(message, check_answer, quiz_state)
    else:
        # Викторина завершена, выводим результат
        bot.send_message(message.chat.id,
                         f"Викторина завершена! Ваш результат: {quiz_state['score']} из {len(quiz_state['questions'])}",
                         reply_markup=None)


# Проверка ответа пользователя
def check_answer(message, quiz_state):
    try:
        user_answer = int(message.text) - 1
        if quiz_state['all_answers'][user_answer] == quiz_state['correct_answer']:
            bot.send_message(message.chat.id, "Верно!")
            quiz_state['score'] += 1
        else:
            bot.send_message(message.chat.id, f"Неверно! Правильный ответ: {quiz_state['correct_answer']}")
    except (ValueError, IndexError):
        bot.send_message(message.chat.id, "Пожалуйста, выберите корректный ответ.")

    # Переходим к следующему вопросу
    quiz_state['current_question'] += 1
    send_next_question(message, quiz_state)


# Запуск бота
bot.infinity_polling()
