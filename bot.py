import os
import asyncio
from telegram import Update, InputMediaPhoto, InputMediaVideo
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters

# ===== ENV VARIABLES =====
BOT_TOKEN = os.getenv("BOT_TOKEN")
AUDIT_CHANNEL_ID = os.getenv("AUDIT_CHANNEL_ID")

# ===== GLOBALS =====
album_buffer = {}     # media_group_id -> list of InputMedia items
album_tasks = {}      # media_group_id -> asyncio.Task
ALBUM_WINDOW = 5.0    # seconds to collect sequential photos/videos into one album

# ===== START COMMAND =====
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📩 Welcome to the Anonymous Forwarder Bot! 🔒\n\n"
        "Send any message and I will forward it anonymously.\n"
        "✨ Works for text, photos, videos, documents, and albums!"
    )

# ===== AUDIT HEADER =====
def audit_header(update: Update):
    user = update.effective_user
    return (
        "🕵️ Audit Log\n"
        f"👤 Name: {user.first_name}\n"
        f"🔗 Username: @{user.username if user.username else 'N/A'}\n"
        f"🆔 User ID: {user.id}\n\n"
    )

# ===== PROCESS ALBUM =====
async def process_album(group_id, chat_id, context, header):
    await asyncio.sleep(ALBUM_WINDOW)  # wait for all sequential media
    media_items = album_buffer.pop(group_id, [])
    if not media_items:
        album_tasks.pop(group_id, None)
        return

    # send album to user anonymously
    await context.bot.send_media_group(chat_id, media_items)

    # send album to audit channel
    await context.bot.send_message(chat_id=AUDIT_CHANNEL_ID, text=header + "📦 Media Album")
    await context.bot.send_media_group(chat_id=AUDIT_CHANNEL_ID, media_items)

    album_tasks.pop(group_id, None)

# ===== HANDLE MESSAGES =====
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    chat_id = update.effective_chat.id
    header = audit_header(update)

    # ===== ALBUM / MEDIA HANDLING =====
    if msg.photo or msg.video:
        # Use media_group_id if exists, otherwise assign pseudo id for sequential messages
        gid = msg.media_group_id or f"seq_{chat_id}_{int(msg.date.timestamp()) // int(ALBUM_WINDOW)}"

        if gid not in album_buffer:
            album_buffer[gid] = []

        if msg.photo:
            album_buffer[gid].append(InputMediaPhoto(msg.photo[-1].file_id, caption=msg.caption))
        elif msg.video:
            album_buffer[gid].append(InputMediaVideo(msg.video.file_id, caption=msg.caption))

        # schedule sending after ALBUM_WINDOW
        if gid not in album_tasks:
            album_tasks[gid] = context.application.create_task(process_album(gid, chat_id, context, header))
        return

    # ===== NON-MEDIA MESSAGES =====
    await msg.copy(chat_id=chat_id)  # anonymous forward
    await context.bot.send_message(chat_id=AUDIT_CHANNEL_ID, text=header)
    await msg.copy(chat_id=AUDIT_CHANNEL_ID)

# ===== MAIN =====
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.ALL, handle_message))
    app.run_polling()

if __name__ == "__main__":
    main()
