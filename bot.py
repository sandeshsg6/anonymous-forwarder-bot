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

# ===== ENV VARIABLES =====
BOT_TOKEN = os.getenv("BOT_TOKEN")
AUDIT_CHANNEL_ID = os.getenv("AUDIT_CHANNEL_ID")

# ===== GLOBALS =====
albums = {}       # stores media grouped by media_group_id
album_tasks = {}  # tracks async tasks for sending albums

# ===== START COMMAND =====
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📩 Welcome to the Anonymous Forwarder Bot! 🔒\n\n"
        "Send any message and I will forward it anonymously.\n"
        "✨ Works for text, photos, videos, documents, and albums!"
    )

# ===== HELPER: AUDIT HEADER =====
def audit_header(update: Update):
    user = update.effective_user
    return (
        "🕵️ Audit Log\n"
        f"👤 Name: {user.first_name}\n"
        f"🔗 Username: @{user.username if user.username else 'N/A'}\n"
        f"🆔 User ID: {user.id}\n\n"
    )

# ===== ASYNC FUNCTION TO SEND ALBUMS =====
async def process_album(group_id, chat_id, context, header):
    # wait for all media in the album
    await asyncio.sleep(1)  # Telegram may send media messages slightly delayed

    media = albums.get(group_id)
    if not media:
        return

    # send anonymous album
    await context.bot.send_media_group(chat_id, media)

    # send audit album with header
    await context.bot.send_message(
        chat_id=AUDIT_CHANNEL_ID,
        text=header + "📦 Media Album"
    )
    await context.bot.send_media_group(
        chat_id=AUDIT_CHANNEL_ID,
        media=media
    )

    # cleanup
    albums.pop(group_id, None)
    album_tasks.pop(group_id, None)

# ===== HANDLE ALL MESSAGES =====
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    chat_id = update.effective_chat.id
    header = audit_header(update)

    # ===== ALBUM HANDLING =====
    if msg.media_group_id:
        gid = msg.media_group_id

        if gid not in albums:
            albums[gid] = []

        if msg.photo:
            albums[gid].append(
                InputMediaPhoto(msg.photo[-1].file_id, caption=msg.caption)
            )
        elif msg.video:
            albums[gid].append(
                InputMediaVideo(msg.video.file_id, caption=msg.caption)
            )

        # only start the task once per media_group_id
        if gid not in album_tasks:
            album_tasks[gid] = context.application.create_task(
                process_album(gid, chat_id, context, header)
            )
        return

    # ===== NON-ALBUM MESSAGES =====
    await msg.copy(chat_id=chat_id)  # send anonymously

    # audit message
    await context.bot.send_message(chat_id=AUDIT_CHANNEL_ID, text=header)
    await msg.copy(chat_id=AUDIT_CHANNEL_ID)

# ===== MAIN FUNCTION =====
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    # handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.ALL, handle_message))

    # start polling
    app.run_polling()

# ===== RUN BOT =====
if __name__ == "__main__":
    main()
