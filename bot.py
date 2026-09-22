# ============ HIDE TOKEN FROM LOGS ============
import logging
logging.getLogger("httpx").setLevel(logging.WARNING)

import os
import random
import asyncio
import threading
from flask import Flask
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

TELEGRAM_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
if not TELEGRAM_TOKEN:
    raise ValueError("No TELEGRAM_BOT_TOKEN set!")

# ============ GAME STATE ============
games = {}
scores = {}
streaks = {}

# ============ FLASK ============
flask_app = Flask(__name__)

@flask_app.route('/')
def health_check():
    return "Math Game Bot is running!", 200

# ============ HELPERS ============
def generate_question(level):
    if level == "easy":
        a = random.randint(1, 20)
        b = random.randint(1, 20)
        op = random.choice(["+", "-"])
        if op == "+":
            answer = a + b
        else:
            if a < b:
                a, b = b, a
            answer = a - b
        question = f"{a} {op} {b}"

    elif level == "medium":
        op = random.choice(["+", "-", "*"])
        if op == "*":
            a = random.randint(2, 12)
            b = random.randint(2, 12)
            answer = a * b
        elif op == "+":
            a = random.randint(10, 100)
            b = random.randint(10, 100)
            answer = a + b
        else:
            a = random.randint(20, 100)
            b = random.randint(10, 50)
            if a < b:
                a, b = b, a
            answer = a - b
        question = f"{a} {op} {b}"

    else:  # hard
        op = random.choice(["+", "-", "*", "/"])
        if op == "*":
            a = random.randint(10, 20)
            b = random.randint(10, 20)
            answer = a * b
        elif op == "/":
            b = random.randint(2, 12)
            answer = random.randint(2, 20)
            a = b * answer
        elif op == "+":
            a = random.randint(100, 999)
            b = random.randint(100, 999)
            answer = a + b
        else:
            a = random.randint(200, 999)
            b = random.randint(100, 500)
            if a < b:
                a, b = b, a
            answer = a - b
        question = f"{a} {op} {b}"

    return question, answer

def get_level_emoji(level):
    return {"easy": "🟢", "medium": "🟡", "hard": "🔴"}.get(level, "🟢")

def get_rank(score):
    if score >= 200:
        return "🏆 Math Genius"
    elif score >= 100:
        return "🥇 Math Master"
    elif score >= 50:
        return "🥈 Math Expert"
    elif score >= 20:
        return "🥉 Math Student"
    else:
        return "🌱 Beginner"

def get_level_keyboard():
    keyboard = [
        [
            InlineKeyboardButton("🟢 Easy", callback_data="level_easy"),
            InlineKeyboardButton("🟡 Medium", callback_data="level_medium"),
            InlineKeyboardButton("🔴 Hard", callback_data="level_hard"),
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

# ============ COMMANDS ============

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_id = user.id
    if user_id not in scores:
        scores[user_id] = 0
        streaks[user_id] = 0

    welcome = (
        f"👋 Hello {user.first_name}!\n\n"
        "Welcome to <b>Math Challenge Bot!</b> 🧮\n\n"
        "Test your math skills and beat your high score!\n\n"
        "<b>Commands:</b>\n"
        "/play - Start a math question\n"
        "/easy - Easy questions\n"
        "/medium - Medium questions\n"
        "/hard - Hard questions\n"
        "/score - Check your score\n"
        "/help - How to play\n\n"
        "Choose your difficulty level 👇"
    )
    await update.message.reply_text(
        welcome,
        parse_mode='HTML',
        reply_markup=get_level_keyboard()
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = (
        "<b>How to play Math Challenge:</b>\n\n"
        "1. Choose a difficulty level\n"
        "2. Solve the math question\n"
        "3. Type your answer and send it\n"
        "4. Build your streak for bonus points!\n\n"
        "<b>Difficulty levels:</b>\n"
        "🟢 Easy - Addition and subtraction\n"
        "🟡 Medium - Includes multiplication\n"
        "🔴 Hard - All operations, bigger numbers\n\n"
        "<b>Scoring:</b>\n"
        "🟢 Easy: +5 points\n"
        "🟡 Medium: +10 points\n"
        "🔴 Hard: +20 points\n"
        "🔥 Streak bonus: x2 after 3 correct in a row!\n\n"
        "Send /play to start!"
    )
    await update.message.reply_text(help_text, parse_mode='HTML')

async def play_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Choose your difficulty level 👇",
        reply_markup=get_level_keyboard()
    )

async def easy_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await start_game(update, update.effective_user.id, "easy")

async def medium_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await start_game(update, update.effective_user.id, "medium")

async def hard_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await start_game(update, update.effective_user.id, "hard")

async def start_game(update, user_id, level):
    question, answer = generate_question(level)
    games[user_id] = {
        'question': question,
        'answer': answer,
        'level': level,
        'attempts': 0
    }

    if user_id not in scores:
        scores[user_id] = 0
    if user_id not in streaks:
        streaks[user_id] = 0

    emoji = get_level_emoji(level)
    streak = streaks[user_id]
    streak_text = f"🔥 Current streak: {streak}" if streak > 0 else ""

    text = (
        f"{emoji} <b>Math Challenge - {level.capitalize()}</b>\n\n"
        f"What is:\n\n"
        f"<code>{question} = ?</code>\n\n"
        f"{streak_text}\n"
        "Type your answer below!"
    )

    if hasattr(update, 'message') and update.message:
        await update.message.reply_text(text, parse_mode='HTML')
    else:
        await update.edit_message_text(text, parse_mode='HTML')

async def score_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    score = scores.get(user_id, 0)
    streak = streaks.get(user_id, 0)
    rank = get_rank(score)

    text = (
        "<b>Your Stats</b>\n\n"
        f"⭐ Score: {score}\n"
        f"🔥 Streak: {streak}\n"
        f"🎖️ Rank: {rank}\n\n"
        "Keep playing to improve!\n"
        "Send /play for a new question!"
    )
    await update.message.reply_text(text, parse_mode='HTML')

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text.strip()

    if user_id not in games:
        await update.message.reply_text(
            "No active game!\n\nSend /play to start.",
            reply_markup=get_level_keyboard()
        )
        return

    game = games[user_id]
    game['attempts'] += 1

    try:
        guess = int(text)
    except ValueError:
        await update.message.reply_text(
            "Please send a number as your answer!"
        )
        return

    correct_answer = game['answer']
    level = game['level']

    if guess == correct_answer:
        # Calculate points
        base_points = {"easy": 5, "medium": 10, "hard": 20}[level]
        streaks[user_id] = streaks.get(user_id, 0) + 1
        streak = streaks[user_id]

        # Bonus for streak
        if streak >= 3:
            points = base_points * 2
            streak_msg = f"🔥 Streak x{streak} - Double points!"
        else:
            points = base_points
            streak_msg = f"🔥 Streak: {streak}"

        if user_id not in scores:
            scores[user_id] = 0
        scores[user_id] += points

        del games[user_id]

        keyboard = [
            [
                InlineKeyboardButton("▶️ Next Question", callback_data=f"next_{level}"),
                InlineKeyboardButton("📊 My Score", callback_data="score"),
            ]
        ]

        text = (
            "✅ <b>Correct!</b>\n\n"
            f"Answer: <code>{correct_answer}</code>\n"
            f"Points earned: +{points}\n"
            f"Total score: {scores[user_id]}\n"
            f"{streak_msg}\n\n"
            "What next?"
        )
        await update.message.reply_text(
            text,
            parse_mode='HTML',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    else:
        if game['attempts'] >= 3:
            # Too many wrong attempts
            streaks[user_id] = 0
            del games[user_id]

            keyboard = [[InlineKeyboardButton("▶️ Try Again", callback_data=f"next_{level}")]]
            text = (
                f"❌ <b>Wrong!</b>\n\n"
                f"Correct answer: <code>{correct_answer}</code>\n"
                f"Streak reset to 0\n\n"
                "Better luck next time!"
            )
            await update.message.reply_text(
                text,
                parse_mode='HTML',
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        else:
            remaining = 3 - game['attempts']
            text = (
                f"❌ <b>Wrong!</b> Try again.\n\n"
                f"<code>{game['question']} = ?</code>\n\n"
                f"Attempts remaining: {remaining}"
            )
            await update.message.reply_text(text, parse_mode='HTML')

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    data = query.data

    if data.startswith("level_"):
        level = data.replace("level_", "")
        question, answer = generate_question(level)
        games[user_id] = {
            'question': question,
            'answer': answer,
            'level': level,
            'attempts': 0
        }
        if user_id not in scores:
            scores[user_id] = 0
        if user_id not in streaks:
            streaks[user_id] = 0

        emoji = get_level_emoji(level)
        streak = streaks.get(user_id, 0)
        streak_text = f"🔥 Current streak: {streak}" if streak > 0 else ""

        text = (
            f"{emoji} <b>Math Challenge - {level.capitalize()}</b>\n\n"
            f"What is:\n\n"
            f"<code>{question} = ?</code>\n\n"
            f"{streak_text}\n"
            "Type your answer below!"
        )
        await query.edit_message_text(text, parse_mode='HTML')

    elif data.startswith("next_"):
        level = data.replace("next_", "")
        question, answer = generate_question(level)
        games[user_id] = {
            'question': question,
            'answer': answer,
            'level': level,
            'attempts': 0
        }

        emoji = get_level_emoji(level)
        streak = streaks.get(user_id, 0)
        streak_text = f"🔥 Current streak: {streak}" if streak > 0 else ""

        text = (
            f"{emoji} <b>Math Challenge - {level.capitalize()}</b>\n\n"
            f"What is:\n\n"
            f"<code>{question} = ?</code>\n\n"
            f"{streak_text}\n"
            "Type your answer below!"
        )
        await query.edit_message_text(text, parse_mode='HTML')

    elif data == "score":
        score = scores.get(user_id, 0)
        streak = streaks.get(user_id, 0)
        rank = get_rank(score)
        text = (
            "<b>Your Stats</b>\n\n"
            f"⭐ Score: {score}\n"
            f"🔥 Streak: {streak}\n"
            f"🎖️ Rank: {rank}\n\n"
            "Send /play for a new question!"
        )
        await query.edit_message_text(text, parse_mode='HTML')

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.error(f"Update {update} caused error {context.error}")

# ============ BOT STARTUP ============
async def run_bot_async():
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("play", play_command))
    app.add_handler(CommandHandler("easy", easy_command))
    app.add_handler(CommandHandler("medium", medium_command))
    app.add_handler(CommandHandler("hard", hard_command))
    app.add_handler(CommandHandler("score", score_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(CallbackQueryHandler(button_callback))
    app.add_error_handler(error_handler)

    await app.initialize()
    await app.start()
    await app.updater.start_polling(
        allowed_updates=Update.ALL_TYPES,
        drop_pending_updates=True
    )
    logger.info("Math Game Bot is polling and ready!")
    while True:
        await asyncio.sleep(1)

def run_bot():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(run_bot_async())

bot_thread = threading.Thread(target=run_bot, daemon=True)
bot_thread.start()
