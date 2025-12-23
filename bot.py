import os
import asyncio
from telegram import Update, InputMediaPhoto, InputMediaVideo
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters
)

BOT_TOKEN = os.getenv("BOT_TOKEN")
AUDIT_CHANNEL_ID = os.getenv("AUDIT_CHANNEL_ID")

# Store media messages by media_group_id
album_buffer = {}
album_tasks = {}

# Delay in seconds to wait for all album items
ALBUM_DELAY = 1.5

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📩 Welcome to the Anonymous Forwarder Bot! 🔒\n\n"
        "Send any message and I will forward it anonymously.\n"
        "✨ Works for text, photos, videos, documents, and albums!"
    )

def audit_header(update: Update):
    user = update.effective_user
    return (
        "🕵️ Audit Log\n"
        f"👤 Name: {user.first_name}\n"
        f"🔗 Username: @{user.username if user.username else 'N/A'}\n"
        f"🆔 User ID: {user.id}\n\n"
    )

async def process_album(media_group_id, chat_id, context, header):
    await asyncio.sleep(ALBUM_DELAY)  # wait for all items

    media_items = album_buffer.get(media_group_id)
    if not media_items:
        return

    # Send album to user
    await context.bot.send_media_group(chat_id, media_items)

    # Send album to audit channel with header
    await context.bot.send_message(chat_id=AUDIT_CHANNEL_ID, text=header + "📦 Media Album")
    await context.bot.send_media_group(chat_id=AUDIT_CHANNEL_ID, media=media_items)

    # Cleanup
    album_buffer.pop(media_group_id, None)
    album_tasks.pop(media_group_id, None)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    chat_id = update.effective_chat.id
    header = audit_header(update)

    # ===== ALBUM HANDLING =====
    if msg.media_group_id:
        gid = msg.media_group_id
        if gid not in album_buffer:
            album_buffer[gid] = []

        # Handle photos and videos
        if msg.photo:
            album_buffer[gid].append(InputMediaPhoto(msg.photo[-1].file_id, caption=msg.caption))
        elif msg.video:
            album_buffer[gid].append(InputMediaVideo(msg.video.file_id, caption=msg.caption))

        # Only start the task once per media_group_id
        if gid not in album_tasks:
            album_tasks[gid] = context.application.create_task(
                process_album(gid, chat_id, context, header)
            )
        return  # do not process this message further

    # ===== NON-ALBUM MESSAGES =====
    await msg.copy(chat_id=chat_id)  # anonymous forward

    # Audit
    await context.bot.send_message(chat_id=AUDIT_CHANNEL_ID, text=header)
    await msg.copy(chat_id=AUDIT_CHANNEL_ID)

def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    # Handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.ALL, handle_message))

    app.run_polling()

if __name__ == "__main__":
    main()
