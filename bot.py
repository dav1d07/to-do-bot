from apscheduler.schedulers.asyncio import AsyncIOScheduler
from datetime import datetime
from telegram import Update, ReplyKeyboardMarkup, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, CallbackQueryHandler, filters
import json
import os

print("BOT VERSION 25-JUNE-TEST")

TOKEN = "8846752534:AAF0vwOmgvfYf7QQpTfcLbv28o005wyF-dc"

DATA_FILE = "tasks.json"

def load_tasks():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_tasks(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

tasks = load_tasks()
def schedule_user_tasks(app):
    for user_id, user_tasks in tasks.items():
        for t in user_tasks:
            if "time" not in t:
                continue

            hour, minute = map(int, t["time"].split(":"))

            scheduler.add_job(
                send_reminder,
                "cron",
                hour=hour,
                minute=minute,
                args=[app, user_id, t["task"]]
            )

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        ["➕ Add Task"],
        ["📋 List Tasks"],
        ["🗑 Clear Tasks"]
    ]

    reply_markup = ReplyKeyboardMarkup(
        keyboard,
        resize_keyboard=True
    )

    await update.message.reply_text(
        "Welcome to your To-Do Bot!",
        reply_markup=reply_markup
    )
async def add(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    task = " ".join(context.args)

    if not task:
        await update.message.reply_text("Usage: /add your task")
        return

    if user_id not in tasks:
        tasks[user_id] = []

    tasks[user_id].append({
        "task": task,
        "done": False
    })

    save_tasks(tasks)

    await update.message.reply_text(f"Added: {task}")

async def list_tasks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)

    if user_id not in tasks or not tasks[user_id]:
        await update.message.reply_text("Your list is empty.")
        return

    text = "\n".join(
        f"{i+1}. {'✅' if task['done'] else '⬜'} {task['task']}"
        for i, task in enumerate(tasks[user_id])
    )

    await update.message.reply_text(text)

async def delete(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)

    if user_id not in tasks or not tasks[user_id]:
        await update.message.reply_text("No tasks to delete.")
        return

    if not context.args:
        await update.message.reply_text("Usage: /delete 1")
        return

    try:
        index = int(context.args[0]) - 1

        if index < 0 or index >= len(tasks[user_id]):
            await update.message.reply_text("Invalid task number.")
            return

        removed = tasks[user_id].pop(index)
        save_tasks(tasks)

        await update.message.reply_text(f"Deleted: {removed}")

    except ValueError:
        await update.message.reply_text("Please enter a number.")

async def clear(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)

    tasks[user_id] = []
    save_tasks(tasks)

    await update.message.reply_text("All tasks deleted.")
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text

    if text == "📋 List Tasks":
        await show_habits(update, context)

    elif text == "🗑 Clear Tasks":
        await clear(update, context)

    elif text == "➕ Add Task":
        await update.message.reply_text(
            "Type:\n/add Your task"
        )
async def resetday(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)

    tasks[user_id] = [
        {"task": "Morning adhkar", "done": False, "time": "06:00"},
        {"task": "Morning Qur'an", "done": False, "time": "06:10"},
        {"task": "Evening adhkar", "done": False, "time": "18:00"},
        {"task": "Evening Qur'an", "done": False, "time": "18:10"},
        {"task": "Learn Russian", "done": False, "time": "21:00"},
        {"task": "Learn Arabic", "done": False, "time": "21:30"},
        {"task": "Learn something new for work", "done": False, "time": "20:00"},
        {"task": "Give charity", "done": False, "time": "12:00"}
    ]

    save_tasks(tasks)

    await update.message.reply_text("Daily habits + reminders reset 🔔")
def schedule_daily_tasks(app):
    scheduler.remove_all_jobs()

    for user_id, user_tasks in tasks.items():
        for t in user_tasks:
            time = t.get("time")

            if not time:
                continue

            print(f"Scheduling {t['task']} at {time}")

            hour, minute = map(int, time.split(":"))

            scheduler.add_job(
                send_reminder,
                "cron",
                hour=hour,
                minute=minute,
                args=[app, user_id, t["task"]]
            )
async def done(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)

    if user_id not in tasks:
        await update.message.reply_text("No habits found.")
        return

    if not context.args:
        await update.message.reply_text("Usage: /done 1")
        return

    try:
        index = int(context.args[0]) - 1

        if index < 0 or index >= len(tasks[user_id]):
            await update.message.reply_text("Invalid number.")
            return

        tasks[user_id][index]["done"] = True
        save_tasks(tasks)

        await update.message.reply_text("Habit completed ✅")

    except ValueError:
        await update.message.reply_text("Enter a number.")

async def show_habits(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)

    if user_id not in tasks:
        await update.message.reply_text("No habits found. Use /resetday")
        return

    keyboard = []

    for i, t in enumerate(tasks[user_id]):
        mark = "✅" if t["done"] else "☑"
        keyboard.append([
            InlineKeyboardButton(
                f"{mark} {t['task']}",
                callback_data=str(i)
            )
        ])

    await update.message.reply_text(
        "Your tasks:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
async def reminder_job(context: ContextTypes.DEFAULT_TYPE):
    job = context.job
    await context.bot.send_message(
        job.chat_id,
        text=f"Reminder: {job.data}"
    )
async def remind(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) < 2:
        await update.message.reply_text("Usage: /remind 10 Morning adhkar")
        return

    minutes = int(context.args[0])
    text = " ".join(context.args[1:])

    job = context.job_queue.run_once(
        reminder_job,
        minutes * 60,
        chat_id=update.effective_chat.id,
        data=text
    )

    await update.message.reply_text(f"Reminder set in {minutes} minutes")
async def button_click(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_id = str(query.from_user.id)
    index = int(query.data)

    if user_id not in tasks:
        return

    tasks[user_id][index]["done"] = not tasks[user_id][index]["done"]
    save_tasks(tasks)

    # rebuild buttons
    keyboard = []

    for i, t in enumerate(tasks[user_id]):
        mark = "✅" if t["done"] else "☑"
        keyboard.append([
            InlineKeyboardButton(
                f"{mark} {t['task']}",
                callback_data=str(i)
            )
        ])

    await query.edit_message_reply_markup(
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
scheduler = AsyncIOScheduler()
def reset_all_users():
    global tasks

    for user_id in tasks:
        tasks[user_id] = [
            {"task": "Morning adhkar", "done": False},
            {"task": "Evening adhkar", "done": False},
            {"task": "Morning Qur'an", "done": False},
            {"task": "Evening Qur'an", "done": False},
            {"task": "Learn Russian", "done": False},
            {"task": "Learn Arabic", "done": False},
            {"task": "Learn something new for work", "done": False},
            {"task": "Give charity", "done": False}
        ]

    save_tasks(tasks)
    print("Daily reset completed")
async def post_init(app: Application):
    scheduler.start()
    schedule_daily_tasks(app)
async def settime(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)

    if len(context.args) != 2:
        await update.message.reply_text(
            "Usage: /settime 2 07:30"
        )
        return

    try:
        index = int(context.args[0]) - 1
        new_time = context.args[1]

        tasks[user_id][index]["time"] = new_time

        save_tasks(tasks)

        scheduler.remove_all_jobs()
        scheduler.add_job(reset_all_users, "cron", hour=0, minute=0)
        schedule_daily_tasks(context.application)
        await update.message.reply_text(
            f"Time changed to {new_time}"
        )

    except:
        await update.message.reply_text(
            "Example: /settime 2 07:30"
        )
async def removetime(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)

    if len(context.args) != 1:
        await update.message.reply_text(
            "Usage: /removetime 1"
        )
        return

    try:
        index = int(context.args[0]) - 1

        tasks[user_id][index].pop("time", None)

        save_tasks(tasks)

        scheduler.remove_all_jobs()
        scheduler.add_job(
            reset_all_users,
            "cron",
            hour=0,
            minute=0
        )
        schedule_daily_tasks(context.application)

        await update.message.reply_text(
            "Reminder removed 🔕"
        )

    except:
        await update.message.reply_text(
            "Invalid task number."
        )
async def progress(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)

    if user_id not in tasks or not tasks[user_id]:
        await update.message.reply_text("No tasks found.")
        return

    total = len(tasks[user_id])
    completed = sum(1 for t in tasks[user_id] if t["done"])
    percent = round(completed / total * 100)

    await update.message.reply_text(
        f"📊 Daily Progress\n\n"
        f"✅ Completed: {completed}\n"
        f"⬜ Remaining: {total - completed}\n\n"
        f"Progress: {percent}%"
    )
async def send_reminder(app, user_id, text):
    await app.bot.send_message(
        chat_id=int(user_id),
        text=f"🔔 Reminder:\n{text}"
    )
async def myid(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        f"Your ID: {update.effective_user.id}"
    )
scheduler = AsyncIOScheduler()

app = Application.builder().token(TOKEN).post_init(post_init).build()

app.add_handler(CommandHandler("myid", myid))
app.add_handler(CommandHandler("settime", settime))
app.add_handler(
    CommandHandler("removetime", removetime)
)
app.add_handler(CommandHandler("progress", progress))
app.add_handler(CommandHandler("remind", remind))
app.add_handler(CallbackQueryHandler(button_click))
app.add_handler(CommandHandler("done", done))
app.add_handler(CommandHandler("resetday", resetday))
app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("add", add))
app.add_handler(CommandHandler("list", show_habits))
app.add_handler(CommandHandler("delete", delete))
app.add_handler(CommandHandler("clear", clear))
app.add_handler(
    MessageHandler(filters.TEXT & ~filters.COMMAND, button_handler)
)

print("Bot is running...")
print("STARTING POLLING")
scheduler.add_job(reset_all_users, "cron", hour=0, minute=0)
app.run_polling()

