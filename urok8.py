import datetime
import telebot
from telebot import types
import requests

# ==========================================
# 1. КОНФИГУРАЦИЯ И ПЕРЕМЕННЫЕ
# ==========================================
TELEGRAM_TOKEN = ""
MISTRAL_API_KEY = ""
MISTRAL_MODEL = "open-mistral-7b"

MISTRAL_API_URL = "https://api.mistral.ai/v1/chat/completions"

# Инициализация бота
bot = telebot.TeleBot(TELEGRAM_TOKEN)


# ==========================================
# ВСПАМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ==========================================

def get_main_keyboard():
    """Создает постоянную нижнюю клавиатуру (ReplyKeyboardMarkup)"""
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    
    # Кнопки
    btn_time = types.KeyboardButton("🕒 Показать время")
    btn_date = types.KeyboardButton("📅 Показать дату")
    btn_ask = types.KeyboardButton("🤖 Спросить Mistral")
    btn_examples = types.KeyboardButton("❓ Примеры вопросов")
    btn_help = types.KeyboardButton("ℹ️ Помощь")
    
    # Размещение кнопок по рядам
    markup.add(btn_time, btn_date)
    markup.add(btn_ask)
    markup.add(btn_examples, btn_help)
    
    return markup


def send_long_message(chat_id, text, max_length=4000):
    """Разбивает и отправляет длинное сообщение частями (до 4000 символов)"""
    for i in range(0, len(text), max_length):
        bot.send_message(chat_id, text[i:i + max_length])


def ask_mistral_api(prompt):
    """
    Отправляет запрос к Mistral AI API с помощью библиотеки requests.
    Обрабатывает основные ошибки HTTP (включая 401 и 429).
    """
    headers = {
        "Authorization": f"Bearer {MISTRAL_API_KEY}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": MISTRAL_MODEL,
        "messages": [
            {"role": "user", "content": prompt}
        ]
    }
    
    try:
        response = requests.post(MISTRAL_API_URL, json=payload, headers=headers, timeout=60)
        
        # Проверка статусов ошибок API
        if response.status_code == 401:
            return "❌ Ошибка авторизации (401): Неверный MISTRAL_API_KEY."
        elif response.status_code == 429:
            return "⚠️ Превышен лимит запросов (429): Попробуйте позже."
        elif response.status_code != 200:
            return f"❌ Ошибка API ({response.status_code}): {response.text}"
            
        data = response.json()
        return data["choices"][0]["message"]["content"]
        
    except requests.exceptions.RequestException as e:
        return f"❌ Сетевая ошибка при обращении к Mistral API: {e}"


# ==========================================
# ОБРАБОТЧИКИ КОМАНД И СООБЩЕНИЙ
# ==========================================

@bot.message_handler(commands=['start'])
def handle_start(message):
    """Обработка команды /start"""
    welcome_text = (
        f"Привет, {message.from_user.first_name}!\n"
        "Я бот с интеграцией Mistral AI.\n"
        "Задай мне любой вопрос или используй меню ниже."
    )
    bot.send_message(message.chat.id, welcome_text, reply_markup=get_main_keyboard())


@bot.message_handler(commands=['help'])
def handle_help_cmd(message):
    """Обработка команды /help"""
    help_text = (
        "ℹ️ **Справка по боту:**\n\n"
        "• `/time` или кнопка '🕒 Показать время' — текущее время\n"
        "• `/date` или кнопка '📅 Показать дату' — текущая дата\n"
        "• `/ask <вопрос>` или просто напишите сообщение — вопрос к Mistral AI\n"
        "• Кнопка '❓ Примеры вопросов' — образцы вопросов"
    )
    bot.send_message(message.chat.id, help_text, parse_mode="Markdown")


@bot.message_handler(commands=['time'])
def handle_time_cmd(message):
    """Обработка команды /time"""
    current_time = datetime.datetime.now().strftime("%H:%M:%S")
    bot.send_message(message.chat.id, f"🕒 Текущее время: **{current_time}**", parse_mode="Markdown")


@bot.message_handler(commands=['date'])
def handle_date_cmd(message):
    """Обработка команды /date"""
    current_date = datetime.datetime.now().strftime("%d.%m.%Y")
    bot.send_message(message.chat.id, f"📅 Текущая дата: **{current_date}**", parse_mode="Markdown")


@bot.message_handler(commands=['ask'])
def handle_ask_cmd(message):
    """Обработка команды /ask [вопрос]"""
    # Получаем текст после команды /ask
    prompt = message.text.partition(' ')[2].strip()
    
    if not prompt:
        bot.send_message(message.chat.id, "Пожалуйста, укажите вопрос после команды. Пример:\n`/ask Как работает ИИ?`", parse_mode="Markdown")
        return
        
    process_mistral_request(message.chat.id, prompt)


# ==========================================
# ОБРАБОТКА ТЕКСТОВЫХ СООБЩЕНИЙ И КНОПОК
# ==========================================

def process_mistral_request(chat_id, prompt):
    """Отправляет статус ожидания, делает запрос к AI и отправляет результат"""
    # Отправка статуса "Mistral думает..."
    status_msg = bot.send_message(chat_id, "⏳ *Mistral думает...*", parse_mode="Markdown")
    
    # Запрос к Mistral AI
    answer = ask_mistral_api(prompt)
    
    # Удаление статусного сообщения
    try:
        bot.delete_message(chat_id, status_msg.message_id)
    except Exception:
        pass
        
    # Отправка ответа с авторазбивкой
    send_long_message(chat_id, answer)


@bot.message_handler(func=lambda message: True)
def handle_text_messages(message):
    """Обработка нажатий на кнопки и произвольного текста"""
    text = message.text

    if text == "🕒 Показать время":
        handle_time_cmd(message)
    elif text == "📅 Показать дату":
        handle_date_cmd(message)
    elif text == "ℹ️ Помощь":
        handle_help_cmd(message)
    elif text == "🤖 Спросить Mistral":
        bot.send_message(message.chat.id, "Напишите ваш вопрос следующим сообщением:")
    elif text == "❓ Примеры вопросов":
        examples = (
            "💡 **Примеры вопросов:**\n"
            "1. Объясни квантовую физику простыми словами.\n"
            "2. Напиши рецепт пасты Карбонара.\n"
            "3. Придумай 5 идей для подарка другу.\n"
            "4. Напиши функцию сортировки массивов на Python."
        )
        bot.send_message(message.chat.id, examples, parse_mode="Markdown")
    else:
        # Любое другое текстовое сообщение расценивается как прямой вопрос к нейросети
        process_mistral_request(message.chat.id, text)


# ==========================================
# ЗАПУСК БОТА
# ==========================================
if __name__ == "__main__":
    print("Бот запущен...")
    bot.infinity_polling()
