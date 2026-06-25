from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters
import json
import os

TOKEN = "8846752534:AAFC1cwuib1CmuKb5vJYAVBJgnH-Io_Ew1g"

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

    tasks[user_id].append(task)
    save_tasks(tasks)

    await update.message.reply_text(f"Added: {task}")

async def list_tasks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)

    if user_id not in tasks or not tasks[user_id]:
        await update.message.reply_text("Your list is empty.")
        return

    text = "\n".join(
        f"{i+1}. {task}"
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
        await list_tasks(update, context)

    elif text == "🗑 Clear Tasks":
        await clear(update, context)

    elif text == "➕ Add Task":
        await update.message.reply_text(
            "Type:\n/add Your task"
        )
async def resetday(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)

    tasks[user_id] = [
        "Morning adhkar",
        "Evening adhkar",
        "Morning Qur'an",
        "Evening Qur'an",
        "Learn Russian",
        "Learn Arabic",
        "Learn something new for work",
        "Give charity"
    ]

    save_tasks(tasks)

    await update.message.reply_text(
        "Daily habits loaded."
    )

app = Application.builder().token(TOKEN).build()

app.add_handler(CommandHandler("resetday", resetday))
app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("add", add))
app.add_handler(CommandHandler("list", list_tasks))
app.add_handler(CommandHandler("delete", delete))
app.add_handler(CommandHandler("clear", clear))
app.add_handler(
    MessageHandler(filters.TEXT & ~filters.COMMAND, button_handler)
)

print("Bot is running...")
app.run_polling()

