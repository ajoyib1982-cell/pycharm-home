import telebot
from telebot import types
import psycopg2

TOKEN = "9085020416:AAH80BlnVcUNGjgZYW_45hs7Z7PfA0G_UD8"
bot = telebot.TeleBot(TOKEN)

DB_CONFIG = {
    "dbname": "vagon_marketing",
    "user": "postgres",
    "password": "27031982@USmanov",
    "host": "localhost",
    "port": "5432"
}


def get_db_connection():
    return psycopg2.connect(**DB_CONFIG)


# ЖШШИР ёки Лотинча Фамилия орқали ходимни базадан қидириш
def check_staff_in_db(query):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Агар киритилган сўров 14 рақамли ЖШШИР бўлса
        if query.isdigit() and len(query) == 14:
            cursor.execute("SELECT pinfl, fio, role, status FROM staff WHERE pinfl = %s;", (query,))
        else:
            # Акс ҳолда лотин тилидаги фамилия бўйича қидирамиз (катта-кичик ҳарфга эътибор бермасдан)
            query_upper = f"%{query.upper()}%"
            cursor.execute("SELECT pinfl, fio, role, status FROM staff WHERE UPPER(fio) LIKE %s;", (query_upper,))

        result = cursor.fetchone()
        cursor.close()
        conn.close()

        if result:
            return {"pinfl": result[0], "fio": result[1], "role": result[2], "status": result[3]}
    except Exception as e:
        print(f"Базага уланишда хатолик: {e}")
    return None


def save_report_to_db(pinfl, report_text):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO daily_reports (pinfl, report_text, created_at) VALUES (%s, %s, NOW());",
            (pinfl, report_text)
        )
        conn.commit()
        cursor.close()
        conn.close()
        return True
    except Exception as e:
        print(f"Ҳисоботни сақлашда хатолик: {e}")
        return False


# Фойдаланувчилар ҳолатини сақлаш
user_states = {}


@bot.message_handler(commands=['start'])
def send_welcome(message):
    chat_id = message.chat.id
    if chat_id in user_states:
        del user_states[chat_id]

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=1)
    btn_contact = types.KeyboardButton("📞 Маълумот юбориш")
    markup.add(btn_contact)

    bot.send_message(
        chat_id,
        "Ассалому алайкум! «Андижон юк вагонларини қуриш ва таъмирлаш заводи» АЖ "
        "маркетинг бўлими ботига хуш келибсиз.\n\n"
        "Тизимга кириш учун **ЖШШИР рақамингизни** ёки **лотин тилидаги фамилиянгизни** (масалан: *USMANOV* ёки *ABDUJALILOV*) киритинг:",
        parse_mode="Markdown",
        reply_markup=markup
    )


@bot.message_handler(func=lambda message: True)
def handle_message(message):
    chat_id = message.chat.id
    text = message.text.strip()

    # 1. Ҳисобот кутилаётган бўлса
    if chat_id in user_states and user_states[chat_id].get("state") == "waiting_for_report":
        pinfl = user_states[chat_id]["pinfl"]
        success = save_report_to_db(pinfl, text)

        if success:
            bot.send_message(chat_id, "✅ Ҳисоботингиз муваффақиятли қабул қилинди ва базага сақланди!")
        else:
            bot.send_message(chat_id, "⚠️ Ҳисоботни сақлашда хатолик юз берди.")

        user_states[chat_id]["state"] = "logged_in"
        show_main_menu(chat_id)
        return

    # 2. ЖШШИР ёки Фамилия бўйича текшириш
    staff = check_staff_in_db(text)
    if staff:
        user_states[chat_id] = {
            "pinfl": staff["pinfl"],
            "fio": staff["fio"],
            "role": staff["role"],
            "state": "logged_in"
        }
        bot.send_message(
            chat_id,
            f"✅ Хуш келибсиз, **{staff['fio']}**!\n"
            f"📌 Лавозимингиз: *{staff['role']}*\n"
            f"🔄 Ҳолатингиз: *{staff['status']}*",
            parse_mode="Markdown"
        )
        show_main_menu(chat_id)
        return

    # 3. Меню тугмаларини текшириш
    if chat_id in user_states and user_states[chat_id].get("state") == "logged_in":
        user_data = user_states[chat_id]

        if text == "📋 Менинг вазифаларим":
            bot.send_message(chat_id,
                             f"📌 **{user_data['fio']}**, сизнинг фаол вазифаларингиз:\n1. Идоралараро хатларни кўриб чиқиш — Жараёнда")
        elif text == "📬 Хатлар ва Топшириқлар":
            bot.send_message(chat_id, "📬 [ijro.gov.uz](https://edo.ijro.uz/) орқали янги топшириқлар юкланмоқда...",
                             parse_mode="Markdown")
        elif text == "📊 Бозор ва Нарх таҳлили":
            bot.send_message(chat_id, "📊 Вагонсозлик бозори ва эҳтиёт қисмлар нархлари базаси очилди.")
        elif text == "🏛 Биржа ва Танловлар":
            bot.send_message(chat_id,
                             "🏛 [uzex.uz](https://uzex.uz) ва [xt-xarid.uz](https://xt-xarid.uz) лотлари мониторинги.",
                             parse_mode="Markdown")
        elif text == "📝 Тижорий таклиф яратиш":
            bot.send_message(chat_id, "📝 Харидорлар учун тижорий таклиф тайёрлаш модули фаоллашди.")
        elif text == "📤 Кунлик ҳисобот юбориш":
            user_states[chat_id]["state"] = "waiting_for_report"
            bot.send_message(chat_id, "✍️ Бугунги кун давомида бажарган ишларингизни қисқача ёзиб шу ерга юборинг:")
        else:
            bot.send_message(chat_id, "❓ Noma'lum buyruq. Илтимос, меню тугмаларидан фойдаланинг.")
    else:
        bot.send_message(chat_id,
                         "❌ Маълумот топилмади. Илтимос, тўғри ЖШШИР рақамингизни ёки лотин тилидаги фамилиянгизни (масалан: **USMANOV** ёки **ABDUJALILOV**) киритинг:")


def show_main_menu(chat_id):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    btn1 = types.KeyboardButton("📋 Менинг вазифаларим")
    btn2 = types.KeyboardButton("📬 Хатлар ва Топшириқлар")
    btn3 = types.KeyboardButton("📊 Бозор ва Нарх таҳлили")
    btn4 = types.KeyboardButton("🏛 Биржа ва Танловлар")
    btn5 = types.KeyboardButton("📝 Тижорий таклиф яратиш")
    btn6 = types.KeyboardButton("📤 Кунлик ҳисобот юбориш")
    markup.add(btn1, btn2, btn3, btn4, btn5, btn6)
    bot.send_message(chat_id, "Қуйидаги менюдан керакли бўлимни танланг:", reply_markup=markup)


if __name__ == "__main__":
    print("Бот PostgreSQL базаси билан муваффақиятли ишга тушди...")
    bot.infinity_polling()