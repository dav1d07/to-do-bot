from apscheduler.schedulers.asyncio import AsyncIOScheduler
from telegram import Update, ReplyKeyboardMarkup, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, CallbackQueryHandler, filters
import json
import os
import re

print("BOT VERSION 25-JUNE-FINAL-12345")

TOKEN = os.environ.get("TOKEN")

DATA_FILE = "tasks.json"

# ─── Timezone ────────────────────────────────────────────────────────────────
# Change this to your local timezone so reminders fire at the right time.
# Examples: "Asia/Tashkent", "Europe/London", "America/New_York"
TIMEZONE = "Asia/Tashkent"

# ─── Default daily tasks (with reminder times) ───────────────────────────────
DEFAULT_HABITS = [
    {"task": "Morning adhkar",              "done": False, "time": "06:00"},
    {"task": "Morning Qur'an",              "done": False, "time": "06:10"},
    {"task": "Evening adhkar",              "done": False, "time": "18:00"},
    {"task": "Evening Qur'an",             "done": False, "time": "18:10"},
    {"task": "Learn Russian",              "done": False, "time": "21:00"},
    {"task": "Learn Arabic",               "done": False, "time": "21:30"},
    {"task": "Learn something new for work", "done": False, "time": "20:00"},
    {"task": "Give charity",               "done": False, "time": "12:00"},
]

# ─── Data helpers ─────────────────────────────────────────────────────────────
def load_tasks():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_tasks(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

tasks = load_tasks()

# ─── Scheduler ────────────────────────────────────────────────────────────────
scheduler = AsyncIOScheduler(timezone=TIMEZONE)

def is_valid_time(t: str) -> bool:
    """Return True if t matches HH:MM with valid hour/minute values."""
    match = re.fullmatch(r"(\d{1,2}):(\d{2})", t)
    if not match:
        return False
    hour, minute = int(match.group(1)), int(match.group(2))
    return 0 <= hour <= 23 and 0 <= minute <= 59

def schedule_daily_tasks(app):
    """Re-register all cron reminders from current tasks dict."""
    # Remove only reminder jobs (keep the midnight reset job)
    for job in scheduler.get_jobs():
        if job.id != "midnight_reset":
            job.remove()

    for user_id, user_tasks in tasks.items():
        for t in user_tasks:
            time_str = t.get("time")
            if not time_str:
                continue
            hour, minute = map(int, time_str.split(":"))
            scheduler.add_job(
                send_reminder,
                "cron",
                hour=hour,
                minute=minute,
                args=[app, user_id, t["task"]],
            )

# ─── Midnight reset ───────────────────────────────────────────────────────────
def reset_all_users():
    """Reset done flags at midnight but KEEP all tasks and times intact."""
    global tasks
    for user_id in tasks:
        for t in tasks[user_id]:
            t["done"] = False
    save_tasks(tasks)
    print("Daily reset completed — done flags cleared, tasks/times preserved.")

# ─── Reminder sender ──────────────────────────────────────────────────────────
async def send_reminder(app, user_id, text):
    try:
        await app.bot.send_message(
            chat_id=int(user_id),
            text=f"🔔 Reminder:\n{text}",
        )
        print(f"Reminder sent to {user_id}: {text}")
    except Exception as e:
        print(f"REMINDER ERROR for {user_id}: {e}")

# ─── post_init ────────────────────────────────────────────────────────────────
async def post_init(app: Application):
    print("POST_INIT: starting scheduler")
    scheduler.start()

    # Single midnight reset job registered here only
    scheduler.add_job(
        reset_all_users,
        "cron",
        hour=0,
        minute=0,
        id="midnight_reset",
        replace_existing=True,
    )

    schedule_daily_tasks(app)
    print("POST_INIT: scheduler ready")

# ─── Command handlers ─────────────────────────────────────────────────────────
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        ["➕ Add Task"],
        ["📋 List Tasks"],
        ["🗑 Clear Tasks"],
    ]
    await update.message.reply_text(
        "Welcome to your To-Do Bot!\n\n"
        "Commands:\n"
        "/add <task> — add a task\n"
        "/list — show tasks\n"
        "/done <n> — mark task done\n"
        "/delete <n> — delete a task\n"
        "/clear — delete all tasks\n"
        "/resetday — reload default daily tasks\n"
        "/settime <n> <HH:MM> — set reminder time\n"
        "/removetime <n> — remove reminder\n"
        "/progress — today's progress\n"
        "/remind <minutes> <text> — one-off reminder\n"
        "/rename <n> <new name> — rename a task\n"
        "/myid — show your Telegram ID",
        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True),
    )

async def add(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    task = " ".join(context.args)
    if not task:
        await update.message.reply_text("Usage: /add your task")
        return

    if user_id not in tasks:
        tasks[user_id] = []

    tasks[user_id].append({"task": task, "done": False})
    save_tasks(tasks)
    await update.message.reply_text(f"Added: {task}")

async def show_tasks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    if user_id not in tasks or not tasks[user_id]:
        await update.message.reply_text("No tasks found. Use /resetday to load defaults.")
        return

    keyboard = []
    for i, t in enumerate(tasks[user_id]):
        mark = "✅" if t["done"] else "☑"
        time_label = f"\n      🕐 {t['time']}" if t.get("time") else ""
        keyboard.append([
            InlineKeyboardButton(
                f"{mark} {t['task']}{time_label}",
                callback_data=str(i),
            )
        ])

    await update.message.reply_text(
        "Your tasks (tap to toggle):",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )

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

        # FIX: extract the task name string, not the whole dict
        removed_name = tasks[user_id].pop(index)["task"]
        save_tasks(tasks)
        schedule_daily_tasks(context.application)
        await update.message.reply_text(f"Deleted: {removed_name}")

    except ValueError:
        await update.message.reply_text("Please enter a number.")

async def clear(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    tasks[user_id] = []
    save_tasks(tasks)
    schedule_daily_tasks(context.application)
    await update.message.reply_text("All tasks deleted.")

async def resetday(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    import copy
    tasks[user_id] = copy.deepcopy(DEFAULT_HABITS)
    save_tasks(tasks)
    schedule_daily_tasks(context.application)
    await update.message.reply_text("Daily tasks reset with reminders 🔔")

async def done(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    if user_id not in tasks:
        await update.message.reply_text("No tasks found.")
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
        await update.message.reply_text("Task marked complete ✅")
    except ValueError:
        await update.message.reply_text("Enter a number.")

async def settime(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    if len(context.args) != 2:
        await update.message.reply_text("Usage: /settime 2 07:30")
        return

    # FIX: validate time format before touching any data
    new_time = context.args[1]
    if not is_valid_time(new_time):
        await update.message.reply_text("Invalid time. Use HH:MM format, e.g. 07:30")
        return

    try:
        index = int(context.args[0]) - 1
        if index < 0 or index >= len(tasks.get(user_id, [])):
            await update.message.reply_text("Invalid task number.")
            return

        tasks[user_id][index]["time"] = new_time
        save_tasks(tasks)
        schedule_daily_tasks(context.application)   # FIX: no duplicate midnight job
        await update.message.reply_text(f"Reminder set to {new_time} ✅")

    except (ValueError, KeyError):
        await update.message.reply_text("Example: /settime 2 07:30")

async def removetime(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    if len(context.args) != 1:
        await update.message.reply_text("Usage: /removetime 1")
        return

    try:
        index = int(context.args[0]) - 1
        if index < 0 or index >= len(tasks.get(user_id, [])):
            await update.message.reply_text("Invalid task number.")
            return

        tasks[user_id][index].pop("time", None)
        save_tasks(tasks)
        schedule_daily_tasks(context.application)   # FIX: no duplicate midnight job
        await update.message.reply_text("Reminder removed 🔕")

    except (ValueError, KeyError):
        await update.message.reply_text("Invalid task number.")

async def progress(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    if user_id not in tasks or not tasks[user_id]:
        await update.message.reply_text("No tasks found.")
        return

    total = len(tasks[user_id])
    completed = sum(1 for t in tasks[user_id] if t["done"])
    percent = round(completed / total * 100)
    bar_filled = round(percent / 10)
    bar = "🟩" * bar_filled + "⬜" * (10 - bar_filled)

    await update.message.reply_text(
        f"📊 Daily Progress\n\n"
        f"{bar}\n\n"
        f"✅ Completed: {completed}/{total}\n"
        f"Progress: {percent}%"
    )

async def remind(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) < 2:
        await update.message.reply_text("Usage: /remind 10 Morning adhkar")
        return

    try:
        minutes = int(context.args[0])
    except ValueError:
        await update.message.reply_text("First argument must be a number of minutes.")
        return

    text = " ".join(context.args[1:])

    context.job_queue.run_once(
        reminder_job,
        minutes * 60,
        chat_id=update.effective_chat.id,
        data=text,
    )
    await update.message.reply_text(f"Reminder set in {minutes} minute(s) ⏰")

async def reminder_job(context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(
        context.job.chat_id,
        text=f"🔔 Reminder: {context.job.data}",
    )

async def myid(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(f"Your Telegram ID: {update.effective_user.id}")

async def testreminder(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        await update.message.reply_text("Sending test reminder...")
        await send_reminder(context.application, update.effective_user.id, "TEST REMINDER")
        await update.message.reply_text("Test reminder sent ✅")
    except Exception as e:
        await update.message.reply_text(f"Error: {e}")

# ─── Inline button toggle ─────────────────────────────────────────────────────
async def button_click(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_id = str(query.from_user.id)
    try:
        index = int(query.data)
    except ValueError:
        return

    if user_id not in tasks or index >= len(tasks[user_id]):
        return

    tasks[user_id][index]["done"] = not tasks[user_id][index]["done"]
    save_tasks(tasks)

    keyboard = []
    for i, t in enumerate(tasks[user_id]):
        mark = "✅" if t["done"] else "☑"
        time_label = f"\n      🕐 {t['time']}" if t.get("time") else ""
        keyboard.append([
            InlineKeyboardButton(
                f"{mark} {t['task']}{time_label}",
                callback_data=str(i),
            )
        ])

    await query.edit_message_reply_markup(reply_markup=InlineKeyboardMarkup(keyboard))

# ─── Rename task ─────────────────────────────────────────────────────────────
async def rename(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    if len(context.args) < 2:
        await update.message.reply_text("Usage: /rename 2 New task name")
        return

    try:
        index = int(context.args[0]) - 1
        if index < 0 or index >= len(tasks.get(user_id, [])):
            await update.message.reply_text("Invalid task number.")
            return

        new_name = " ".join(context.args[1:])
        old_name = tasks[user_id][index]["task"]
        tasks[user_id][index]["task"] = new_name
        save_tasks(tasks)
        schedule_daily_tasks(context.application)
        await update.message.reply_text(f"Renamed:\n'{old_name}' → '{new_name}'")

    except (ValueError, KeyError):
        await update.message.reply_text("Usage: /rename 2 New task name")

# ─── Text button handler ──────────────────────────────────────────────────────
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if text == "📋 List Tasks":
        await show_tasks(update, context)
    elif text == "🗑 Clear Tasks":
        await clear(update, context)
    elif text == "➕ Add Task":
        await update.message.reply_text("Type:\n/add Your task here")

# ─── Error handler ────────────────────────────────────────────────────────────
async def error_handler(update, context):
    print(f"ERROR: {context.error}")

# ─── App setup ────────────────────────────────────────────────────────────────
app = Application.builder().token(TOKEN).post_init(post_init).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("add", add))
app.add_handler(CommandHandler("list", show_tasks))
app.add_handler(CommandHandler("delete", delete))
app.add_handler(CommandHandler("clear", clear))
app.add_handler(CommandHandler("done", done))
app.add_handler(CommandHandler("resetday", resetday))
app.add_handler(CommandHandler("settime", settime))
app.add_handler(CommandHandler("removetime", removetime))
app.add_handler(CommandHandler("progress", progress))
app.add_handler(CommandHandler("remind", remind))
app.add_handler(CommandHandler("rename", rename))
app.add_handler(CommandHandler("myid", myid))
app.add_handler(CommandHandler("testreminder", testreminder))
app.add_handler(CallbackQueryHandler(button_click))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, button_handler))
app.add_error_handler(error_handler)

print("Bot is running...")
app.run_polling()