import os
import telebot
import requests
from dotenv import load_dotenv
from telebot import types

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
GOOGLE_MAPS_API_KEY = os.getenv('GOOGLE_MAPS_API_KEY')

bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN)

def get_location_name(lat, lon, api_key):
    url = "https://maps.googleapis.com/maps/api/geocode/json"
    params = {
        'latlng': f"{lat},{lon}",
        'key': api_key,
        'language': 'uk'
    }
    response = requests.get(url, params=params)
    result = response.json()
    if result['status'] == 'OK':
        return result['results'][0].get('formatted_address', f"{lat:.5f}, {lon:.5f}")
    return f"{lat:.5f}, {lon:.5f}"

def search_truck_repair_shops(lat, lon, radius=50000):
    url = "https://maps.googleapis.com/maps/api/place/nearbysearch/json"
    params = {
    'location': f'{lat},{lon}',
    'radius': radius,
    'type': 'car_repair',
    'keyword': 'вантажівка TIR truck',
    'key': GOOGLE_MAPS_API_KEY,
    'language': 'uk, en'
}

    response = requests.get(url, params=params)
    print("Places API result:", response.json())  # Для дебагу
    return response.json()

def format_repair_shops_message(results, user_lat, user_lon):
    import urllib.parse
    place_name = get_location_name(user_lat, user_lon, GOOGLE_MAPS_API_KEY)
    if not results.get('results'):
        return f"На жаль, СТО не знайдено в радіусі 50 км поблизу {place_name} 😔"
    message = f"📍 Місце поломки: {place_name}\n"
    message += "Найближчі СТО:\n\n"
    for place in results['results'][:10]:
        name = place.get('name', 'Невідоме СТО')
        address = place.get('vicinity', 'Адреса не вказана')
        # Формування посилання по назві
        name_query = urllib.parse.quote_plus(name)
        maps_url = f"https://www.google.com/maps/search/?api=1&query={name_query}"
        message += f"🏁 {name}\n"
        message += f"📍 {address}\n"
        message += f"🌐 [Карта: {name}]({maps_url})\n\n"
    return message




@bot.message_handler(commands=['start'])
def send_welcome(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    location_btn = types.KeyboardButton("📍 Надіслати геолокацію", request_location=True)
    manual_btn = types.KeyboardButton("✏️ Ввести країну та індекс")
    markup.add(location_btn)
    markup.add(manual_btn)
    bot.reply_to(
        message,
        "Привіт! 🚛 Я допоможу знайти найближчі СТО.\n\n"
        "Оберіть один із способів:\n"
        "📍 Надіслати геолокацію - для автоматичного визначення\n"
        "✏️ Ввести країну та індекс - для ручного введення",
        reply_markup=markup
    )

@bot.message_handler(content_types=['location'])
def handle_location(message):
    lat = message.location.latitude
    lon = message.location.longitude
    results = search_truck_repair_shops(lat, lon)
    formatted_message = format_repair_shops_message(results, lat, lon)
    bot.send_message(
        message.chat.id,
        formatted_message,
        parse_mode='Markdown',
        disable_web_page_preview=True
    )

@bot.message_handler(func=lambda message: message.text == "✏️ Ввести країну та індекс")
def ask_manual_location(message):
    bot.send_message(
        message.chat.id,
        "Введіть адресу у форматі: Країна, Місто, Поштовий індекс\n"
        "Наприклад: Україна, Рівне, 33000"
    )
    bot.register_next_step_handler(message, process_manual_location)

def process_manual_location(message):
    address = message.text
    geocode_url = "https://maps.googleapis.com/maps/api/geocode/json"
    params = {
        'address': address,
        'key': GOOGLE_MAPS_API_KEY
    }
    response = requests.get(geocode_url, params=params)
    geocode_result = response.json()
    if geocode_result['status'] == 'OK':
        location = geocode_result['results'][0]['geometry']['location']
        lat = location['lat']
        lon = location['lng']
        results = search_truck_repair_shops(lat, lon)
        formatted_message = format_repair_shops_message(results, lat, lon)
        bot.send_message(
            message.chat.id,
            formatted_message,
            parse_mode='Markdown',
            disable_web_page_preview=True
        )
    else:
        bot.send_message(
            message.chat.id,
            "❌ Не вдалося знайти вказану адресу. Спробуйте ще раз або скористайтеся геолокацією."
        )

@bot.message_handler(commands=['help'])
def send_help(message):
    help_text = """
🚛 **Довідка по боту СТО**

**Команди:**
/start - Почати роботу з ботом
/help - Показати цю довідку

**Як користуватися:**
1️⃣ Натисніть "📍 Надіслати геолокацію" для автоматичного пошуку
2️⃣ Або натисніть "✏️ Ввести країну та індекс" для ручного введення

Бот знайде найближчі СТО в радіусі 50 км від вашого місцезнаходження.

❓ Якщо у вас виникли питання, зверніться до розробника.
    """
    bot.send_message(message.chat.id, help_text, parse_mode='Markdown')

if __name__ == '__main__':
    print("🚛 Бот СТО запущено...")
    bot.infinity_polling()
