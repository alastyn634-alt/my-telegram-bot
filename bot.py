import sqlite3
import logging
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    CallbackQueryHandler,
    MessageHandler,
    filters
)

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

TOKEN = "9153750679:AAG5KLaP-uYfqgbuXhiKD3PKBdW-2-yWJXw"
ADMIN_ID = 8914495935

def init_db():
    conn = sqlite3.connect('bot_database.db')
    cursor = conn.cursor()
    cursor.execute('CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, username TEXT, full_name TEXT, points INTEGER DEFAULT 20, is_banned INTEGER DEFAULT 0)')
    cursor.execute('CREATE TABLE IF NOT EXISTS blocked_numbers (phone_number TEXT PRIMARY KEY, blocked_by INTEGER, added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)')
    cursor.execute('CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT)')
    cursor.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('forced_channel', 'None')")
    conn.commit()
    conn.close()

init_db()

def get_user(user_id):
    conn = sqlite3.connect('bot_database.db')
    cursor = conn.cursor()
    cursor.execute('SELECT user_id, username, full_name, points, is_banned FROM users WHERE user_id = ?', (user_id,))
    user = cursor.fetchone()
    conn.close()
    return user

def add_or_update_user(user_id, username, full_name):
    conn = sqlite3.connect('bot_database.db')
    cursor = conn.cursor()
    cursor.execute('SELECT points FROM users WHERE user_id = ?', (user_id,))
    result = cursor.fetchone()
    if not result:
        cursor.execute('INSERT INTO users (user_id, username, full_name, points, is_banned) VALUES (?, ?, ?, 20, 0)', (user_id, username, full_name))
    else:
        cursor.execute('UPDATE users SET username = ?, full_name = ? WHERE user_id = ?', (username, full_name, user_id))
    conn.commit()
    conn.close()

def set_user_points(user_id, points):
    conn = sqlite3.connect('bot_database.db')
    cursor = conn.cursor()
    cursor.execute('UPDATE users SET points = ? WHERE user_id = ?', (points, user_id))
    conn.commit()
    conn.close()

def set_user_ban_status(user_id, status):
    conn = sqlite3.connect('bot_database.db')
    cursor = conn.cursor()
    cursor.execute('UPDATE users SET is_banned = ? WHERE user_id = ?', (status, user_id))
    conn.commit()
    conn.close()

def get_forced_channel():
    conn = sqlite3.connect('bot_database.db')
    cursor = conn.cursor()
    cursor.execute('SELECT value FROM settings WHERE key = "forced_channel"')
    res = cursor.fetchone()
    conn.close()
    return res[0] if res else "None"

def set_forced_channel(channel):
    conn = sqlite3.connect('bot_database.db')
    cursor = conn.cursor()
    cursor.execute('UPDATE settings SET value = ? WHERE key = "forced_channel"', (channel,))
    conn.commit()
    conn.close()

def add_blocked_number(phone, user_id):
    conn = sqlite3.connect('bot_database.db')
    cursor = conn.cursor()
    try:
        cursor.execute('INSERT INTO blocked_numbers (phone_number, blocked_by) VALUES (?, ?)', (phone, user_id))
        conn.commit()
        success = True
    except sqlite3.IntegrityError:
        success = False
    conn.close()
    return success

async def check_subscription(bot, user_id):
    channel = get_forced_channel()
    if channel == "None" or not channel:
        return True
    try:
        member = await bot.get_chat_member(chat_id=channel, user_id=user_id)
        if member.status in ['member', 'administrator', 'creator']:
            return True
    except Exception:
        pass
    return False

def main_menu(user_id):
    keyboard = [
        [InlineKeyboardButton("🚫 حظر الأرقام الآن (10 نقاط)", callback_data='block_menu')],
        [InlineKeyboardButton("👤 معلوماتي", callback_data='my_info')]
    ]
    if user_id == ADMIN_ID:
        keyboard.append([InlineKeyboardButton("⚙️ لوحة تحكم الآدمن", callback_data='admin_panel')])
    return InlineKeyboardMarkup(keyboard)

def back_to_home():
    return InlineKeyboardMarkup([[InlineKeyboardButton("🔙 القائمة الرئيسية", callback_data='home')]])

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    add_or_update_user(user.id, user.username, user.full_name)
    db_user = get_user(user.id)
    if db_user and db_user[4] == 1:
        await update.message.reply_text("❌ عذراً، لقد تم حظرك من استخدام هذا البوت بواسطة الإدارة.")
        return
    if not await check_subscription(context.bot, user.id):
        channel = get_forced_channel()
        await update.message.reply_text(f"⚠️ عذراً، يجب عليك الاشتراك في قناة البوت أولاً لتتمكن من استخدامه:\n👉 {channel}\n\nبعد الاشتراك, أرسل /start مجدداً.")
        return
    welcome_text = "✨ **أهلاً بك في أقوى بوت حظر أرقام** 🚫\n\nاختر ما تحتاجه من الأزرار أدناه:"
    if update.message:
        await update.message.reply_text(welcome_text, reply_markup=main_menu(user.id), parse_mode='Markdown')
    elif update.callback_query:
        query = update.callback_query
        await query.answer()
        await query.edit_message_text(text=welcome_text, reply_markup=main_menu(user.id), parse_mode='Markdown')

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user = query.from_user
    data = query.data
    db_user = get_user(user.id)
    if db_user and db_user[4] == 1:
        await query.edit_message_text("❌ تم حظرك من استخدام البوت.")
        return

    if data == 'home':
        await query.edit_message_text("👑 **𝑾𝒆𝒍𝒄𝒐𝒎𝒆 𝑻𝒐 𝑻𝒉𝒆 𝑳𝒆𝒈𝒆𝒏𝒅𝒂𝒓𝒚 𝑩𝒐𝒕 ** 🚫\n\nاختر ما تحتاجه من الأزرار أدناه:", reply_markup=main_menu(user.id), parse_mode='Markdown')
    elif data == 'block_menu':
        user_points = db_user[3]
        if user_points < 10:
            await query.edit_message_text(f"❌ عذراً، نقاطك غير كافية ({user_points} نقطة).\nتحتاج إلى 10 نقاط على الأقل لحظر رقم.", reply_markup=back_to_home())
            return
        context.user_data['waiting_for_number'] = True
        await query.edit_message_text("📱 **قسم حظر الأرقام الآن**\n\nأرسل رقم الهاتف الذي تريد حظره الآن:\n*(مثال: +201012345678 أو الرقم مباشرة)*", reply_markup=back_to_home(), parse_mode='Markdown')
    elif data == 'my_info':
        username = f"@{user.username}" if user.username else "لا يوجد"
        full_name = user.full_name
        user_id = user.id
        points = db_user[3]
        info_text = f"👤 **معلومات حسابك الشخصي:**\n\n🏷️ **الاسم:** {full_name}\n🔗 **اليوزر:** {username}\n🆔 **الأيدي:** `{user_id}`\n💎 **عدد النقاط:** {points} نقطة"
        await query.edit_message_text(text=info_text, reply_markup=back_to_home(), parse_mode='Markdown')
    elif data == 'admin_panel':
        if user.id != ADMIN_ID:
            await query.answer("هذا القسم خاص بالآدمن فقط!", show_alert=True)
            return
        admin_keyboard = [
            [InlineKeyboardButton("➕ تزويد نقاط", callback_data='admin_add_pts'), InlineKeyboardButton("➖ تقليل نقاط", callback_data='admin_sub_pts')],
            [InlineKeyboardButton("🚫 حظر مستخدم", callback_data='admin_ban'), InlineKeyboardButton("🟢 فك حظر مستخدم", callback_data='admin_unban')],
            [InlineKeyboardButton("📢 إضافة قناة اشتراك", callback_data='admin_set_channel'), InlineKeyboardButton("❌ إلغاء الاشتراك الإجباري", callback_data='admin_del_channel')],
            [InlineKeyboardButton("🔙 القائمة الرئيسية", callback_data='home')]
        ]
        await query.edit_message_text("⚙️ **لوحة تحكم الآدمن:**\nاختر العملية المطلوبة:", reply_markup=InlineKeyboardMarkup(admin_keyboard), parse_mode='Markdown')
    elif data.startswith('admin_'):
        if user.id != ADMIN_ID:
            return
        if data == 'admin_add_pts':
            context.user_data['admin_state'] = 'add_points'
            await query.edit_message_text("أرسل أيدي المستخدم والنقاط المراد إضافتها بهذا الشكل:\n`ID POINTS`\nمثال: `123456789 50`", reply_markup=back_to_home(), parse_mode='Markdown')
        elif data == 'admin_sub_pts':
            context.user_data['admin_state'] = 'sub_points'
            await query.edit_message_text("أرسل أيدي المستخدم والنقاط المراد خصمها بهذا الشكل:\n`ID POINTS`\nمثال: `123456789 20`", reply_markup=back_to_home(), parse_mode='Markdown')
        elif data == 'admin_ban':
            context.user_data['admin_state'] = 'ban_user'
            await query.edit_message_text("أرسل أيدي المستخدم المراد حظره:", reply_markup=back_to_home())
        elif data == 'admin_unban':
            context.user_data['admin_state'] = 'unban_user'
            await query.edit_message_text("أرسل أيدي المستخدم المراد فك حظره:", reply_markup=back_to_home())
        elif data == 'admin_set_channel':
            context.user_data['admin_state'] = 'set_channel'
            await query.edit_message_text("أرسل معرف القناة (يوزر القناة مع @ مثل `@ChannelName`):", reply_markup=back_to_home())
        elif data == 'admin_del_channel':
            set_forced_channel("None")
            await query.edit_message_text("✅ تم إلغاء الاشتراك الإجباري بنجاح.", reply_markup=back_to_home())

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    user = message.from_user
    text = message.text.strip()
    db_user = get_user(user.id)
    if db_user and db_user[4] == 1:
        return

    if context.user_data.get('waiting_for_number'):
        context.user_data['waiting_for_number'] = False
        if db_user[3] < 10:
            await message.reply_text("❌ عذراً، نقاطك أصبحت أقل من 10.", reply_markup=back_to_home())
            return
        set_user_points(user.id, db_user[3] - 10)
        status_msg = await message.reply_text("⏳ **انظر، يجري حظر رقم الهاتف هذا...**", parse_mode='Markdown')
        await asyncio.sleep(5)
        add_blocked_number(text, user.id)
        await status_msg.edit_text(f"✅ **تم حظر رقم الهاتف بنجاح!**\n📱 الرقم: `{text}`\n💎 تم خصم 10 نقاط من رصيدك.", reply_markup=back_to_home(), parse_mode='Markdown')
        return

    admin_state = context.user_data.get('admin_state')
    if admin_state and user.id == ADMIN_ID:
        context.user_data['admin_state'] = None
        if admin_state == 'set_channel':
            set_forced_channel(text)
            await message.reply_text(f"✅ تمت تعبئة قناة الاشتراك الإجباري بنجاح: {text}", reply_markup=back_to_home())
            return
        if admin_state in ['ban_user', 'unban_user']:
            try:
                target_id = int(text)
                if admin_state == 'ban_user':
                    set_user_ban_status(target_id, 1)
                    await message.reply_text(f"✅ تم حظر المستخدم `{target_id}` بنجاح.", reply_markup=back_to_home(), parse_mode='Markdown')
                else:
                    set_user_ban_status(target_id, 0)
                    await message.reply_text(f"✅ تم فك حظر المستخدم `{target_id}` بنجاح.", reply_markup=back_to_home(), parse_mode='Markdown')
            except ValueError:
                await message.reply_text("❌ الأيدي غير صحيح، يجب أن يكون أرقام فقط.", reply_markup=back_to_home())
            return
        if admin_state in ['add_points', 'sub_points']:
            try:
                parts = text.split()
                target_id = int(parts[0])
                amount = int(parts[1])
                target_user = get_user(target_id)
                if not target_user:
                    await message.reply_text("❌ هذا المستخدم غير مسجل في قاعدة بيانات البوت.", reply_markup=back_to_home())
                    return
                current_pts = target_user[3]
                if admin_state == 'add_points':
                    new_pts = current_pts + amount
                    set_user_points(target_id, new_pts)
                    await message.reply_text(f"✅ تمت إضافة {amount} نقطة للمستخدم `{target_id}`.\nإجمالي نقاطه الآن: {new_pts}", reply_markup=back_to_home(), parse_mode='Markdown')
                else:
                    new_pts = max(0, current_pts - amount)
                    set_user_points(target_id, new_pts)
                    await message.reply_text(f"✅ تم خصم {amount} نقطة من المستخدم `{target_id}`.\nإجمالي نقاطه الآن: {new_pts}", reply_markup=back_to_home(), parse_mode='Markdown')
            except Exception:
                await message.reply_text("❌ صيغة الإدخال غير صحيحة. استخدم الشكل: `ID POINTS`", reply_markup=back_to_home(), parse_mode='Markdown')
            return

def main():
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))
    print("🤖 بوت حظر الأرقام يعمل بكفاءة الآن...")
    app.run_polling()

if __name__ == '__main__':
    main()
