import logging
from datetime import datetime
import sqlite3
import os
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler

# Constants
TOKEN = os.getenv("TOKEN")
ADMIN_ID = os.getenv("ADMIN_ID")
WAITING_FOR_MESSAGE = 1
WAITING_FOR_BROADCAST = 2

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Define the path for SQLite database inside the volume
db_path = '/volumes/{volume_id}/bot_users.db'  # Railway Volume path (replace {volume_id} with your volume ID)

# Database setup
def setup_database():
    # Use the db_path for the SQLite database
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (user_id INTEGER PRIMARY KEY,
                  username TEXT,
                  first_name TEXT,
                  last_name TEXT,
                  join_date TIMESTAMP)''')
    conn.commit()
    conn.close()

# Save user to database
def save_user(user_id, username, first_name, last_name):
    conn = sqlite3.connect(db_path)  # Use the db_path for the SQLite database
    c = conn.cursor()
    c.execute('''INSERT OR REPLACE INTO users (user_id, username, first_name, last_name, join_date)
                 VALUES (?, ?, ?, ?, ?)''',
              (user_id, username, first_name, last_name, datetime.now()))
    conn.commit()
    conn.close()

# Get the main keyboard markup
def get_main_keyboard():
    keyboard = [
        ['شبکه‌های اجتماعی من'],
        ['ارسال پیام']
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

# Get the admin keyboard markup
def get_admin_keyboard():
    keyboard = [
        ['ارسال پیام همگانی'],
        ['نمایش لیست کاربران']
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    save_user(user.id, user.username, user.first_name, user.last_name)
    
    welcome_message = (
        f"سلام {user.first_name} عزیز!\n"
        "به ربات من خوش آمدید. لطفاً یکی از گزینه‌های زیر را انتخاب کنید:"
    )
    
    await update.message.reply_text(
        welcome_message,
        reply_markup=get_main_keyboard()
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    user = update.effective_user
    
    if text == "شبکه‌های اجتماعی من":
        await update.message.reply_text("https://google.com")
        
    elif text == "ارسال پیام":
        await update.message.reply_text(
            "لطفاً پیام خود را وارد کنید:",
            reply_markup=ReplyKeyboardMarkup([['لغو']], resize_keyboard=True)
        )
        return WAITING_FOR_MESSAGE

async def panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if str(user.id) == ADMIN_ID:
        conn = sqlite3.connect(db_path)  # Use the db_path for the SQLite database
        c = conn.cursor()
        c.execute('SELECT COUNT(*) FROM users')
        user_count = c.fetchone()[0]
        conn.close()

        admin_message = (
            "🔐 پنل مدیریت:\n\n"
            f"📊 تعداد کل کاربران: {user_count}\n"
            "\n"
            "دستورات موجود:\n"
        )
        await update.message.reply_text(admin_message, reply_markup=get_admin_keyboard())
    else:
        await update.message.reply_text("شما دسترسی به این دستور ندارید.")

async def send_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if str(update.effective_user.id) != ADMIN_ID:
        return

    await update.message.reply_text(
        "لطفاً پیام همگانی خود را وارد کنید:",
        reply_markup=ReplyKeyboardMarkup([['لغو']], resize_keyboard=True)
    )
    return WAITING_FOR_BROADCAST

async def handle_broadcast_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message.text
    
    if message == "لغو":
        await update.message.reply_text(
            "عملیات لغو شد.",
            reply_markup=get_admin_keyboard()
        )
        return ConversationHandler.END

    # Send the message to all users
    conn = sqlite3.connect(db_path)  # Use the db_path for the SQLite database
    c = conn.cursor()
    c.execute('SELECT user_id FROM users')
    users = c.fetchall()
    conn.close()
    
    for user in users:
        try:
            await context.bot.send_message(user[0], message)
        except:
            continue
    
    await update.message.reply_text("پیام همگانی با موفقیت ارسال شد. ✅", reply_markup=get_admin_keyboard())
    return ConversationHandler.END

async def show_users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if str(update.effective_user.id) != ADMIN_ID:
        return
    
    conn = sqlite3.connect(db_path)  # Use the db_path for the SQLite database
    c = conn.cursor()
    c.execute('SELECT username, first_name, last_name, user_id FROM users')
    users = c.fetchall()
    conn.close()

    user_list = "لیست کاربران:\n\n"
    for user in users:
        user_list += f"📌 @{user[0]} - {user[1]} {user[2]} (ID: {user[3]})\n"
    
    if user_list == "لیست کاربران:\n\n":
        user_list = "هیچ کاربری وجود ندارد."
    
    await update.message.reply_text(user_list, reply_markup=get_admin_keyboard())

async def handle_user_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    message = update.message.text
    
    if message == "لغو":
        await update.message.reply_text(
            "عملیات لغو شد.",
            reply_markup=get_main_keyboard()
        )
        return ConversationHandler.END
    
    # Format the message for admin
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    user_link = f"[{user.first_name}](tg://user?id={user.id})"
    admin_notification = (
        f"📩 پیام جدید\n\n"
        f"👤 فرستنده: {user_link}\n"
        f"🆔 یوزرنیم: @{user.username if user.username else 'ندارد'}\n"
        f"📌 آیدی عددی: `{user.id}`\n"
        f"⏰ زمان: {current_time}\n\n"
        f"📝 متن پیام:\n{message}"
    )
    
    # Send to admin
    await context.bot.send_message(
        chat_id=ADMIN_ID,
        text=admin_notification,
        parse_mode='Markdown'
    )
    
    # Confirm to user
    await update.message.reply_text(
        "پیام شما با موفقیت ارسال شد. ✅",
        reply_markup=get_main_keyboard()
    )
    return ConversationHandler.END

async def admin_reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if str(update.effective_user.id) != ADMIN_ID:
        return
        
    if update.message.reply_to_message:
        # Extract user ID from the original message
        original_text = update.message.reply_to_message.text
        try:
            user_id = original_text.split("آیدی عددی: ")[1].split("\n")[0].strip('`')
            reply_text = update.message.text
            
            await context.bot.send_message(
                chat_id=user_id,
                text=f"پاسخ ادمین:\n\n{reply_text}"
            )
            
            await update.message.reply_text("پاسخ شما ارسال شد. ✅")
        except:
            await update.message.reply_text("خطا در ارسال پاسخ!")

def main():
    # Setup database
    setup_database()
    
    # Create application
    application = Application.builder().token(TOKEN).build()
    
    # Add conversation handler for user messages
    conv_handler = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex('^ارسال پیام$'), handle_message)],
        states={ 
            WAITING_FOR_MESSAGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_user_message)],
            WAITING_FOR_BROADCAST: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_broadcast_message)]
        },
        fallbacks=[MessageHandler(filters.Regex('^لغو$'), handle_message)]
    )
    
    # Add handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("panel", panel))  # Panel handler
    application.add_handler(CommandHandler("broadcast", send_broadcast))  # Broadcast handler
    application.add_handler(CommandHandler("users", show_users))  # Users list handler
    application.add_handler(conv_handler)
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_handler(MessageHandler(
        filters.TEXT & filters.REPLY & filters.User(int(ADMIN_ID)),
        admin_reply
    ))
    
    print('Bot Started')
    application.run_polling()

if __name__ == '__main__':
    main()
