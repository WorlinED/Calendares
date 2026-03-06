import json
import logging
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters

logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s', level=logging.INFO)

TOKEN = "TOKEN"
WEBAPP_URL = "https://worlined.github.io/Calendares/Calendar.html"

# ── /start ──
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = InlineKeyboardMarkup([[
        InlineKeyboardButton("📅 Открыть календарь", web_app=WebAppInfo(url=WEBAPP_URL))
    ]])
    await update.message.reply_text(
        "👋 Привет! Это твой личный календарь.\n\nНажми кнопку чтобы открыть:",
        reply_markup=keyboard
    )

# ── Получаем данные из Mini App (напоминания) ──
async def web_app_data(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        data = json.loads(update.effective_message.web_app_data.data)

        if data.get("type") == "reminder":
            title = data.get("title", "Событие")
            date_str = data.get("date", "")
            time_str = data.get("time", "")

            if not time_str:
                await update.message.reply_text(f"✅ Событие «{title}» сохранено!\n⚠️ Время не указано — уведомление не запланировано.")
                return

            # Парсим дату и время
            try:
                event_dt = datetime.strptime(f"{date_str} {time_str}", "%d.%m.%Y %H:%M")
                remind_dt = event_dt - timedelta(minutes=30)
                now = datetime.now()

                if remind_dt <= now:
                    await update.message.reply_text(f"✅ Событие «{title}» сохранено!\n⚠️ До события меньше 30 минут — уведомление не успею отправить.")
                    return

                delay = (remind_dt - now).total_seconds()
                chat_id = update.effective_chat.id

                # Планируем уведомление
                context.job_queue.run_once(
                    send_reminder,
                    when=delay,
                    data={"chat_id": chat_id, "title": title, "time": time_str, "date": date_str},
                    name=f"reminder_{chat_id}_{title}"
                )

                await update.message.reply_text(
                    f"✅ Событие сохранено!\n\n"
                    f"📅 {title}\n"
                    f"🕐 {date_str} в {time_str}\n"
                    f"🔔 Напомню в {remind_dt.strftime('%H:%M')} (за 30 минут)"
                )

            except ValueError:
                await update.message.reply_text(f"✅ Событие «{title}» сохранено!")

    except Exception as e:
        logging.error(f"Ошибка обработки данных: {e}")

# ── Отправка напоминания ──
async def send_reminder(context: ContextTypes.DEFAULT_TYPE):
    job = context.job
    data = job.data
    await context.bot.send_message(
        chat_id=data["chat_id"],
        text=f"🔔 Напоминание!\n\n📌 {data['title']}\n🕐 Сегодня в {data['time']}\n\nДо события 30 минут ⏰"
    )

# ── /help ──
async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = InlineKeyboardMarkup([[
        InlineKeyboardButton("📅 Открыть календарь", web_app=WebAppInfo(url=WEBAPP_URL))
    ]])
    await update.message.reply_text(
        "📋 Как пользоваться:\n\n"
        "1. Открой календарь кнопкой ниже\n"
        "2. Выбери дату → нажми «+ Событие»\n"
        "3. Укажи время и включи 🔔 уведомление\n"
        "4. Бот напомнит за 30 минут!\n\n"
        "📝 В блокноте можно создавать заметки с тегами\n"
        "✅ В задачах — следить за прогрессом",
        reply_markup=keyboard
    )

if __name__ == "__main__":
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(MessageHandler(filters.StatusUpdate.WEB_APP_DATA, web_app_data))
    print("Бот запущен ✅")
    app.run_polling()
