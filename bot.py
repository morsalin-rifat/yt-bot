import os
import yt_dlp
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes

BOT_TOKEN = os.getenv("BOT_TOKEN")
ALLOWED_USER = os.getenv("ALLOWED_USER")  # Optional (তুই নিজের Telegram ID দিয়ে দিতে পারিস)

# ইউজার চেক (যদি ALLOWED_USER সেট করা থাকে)
def is_allowed(user_id: int) -> bool:
    if not ALLOWED_USER:
        return True
    return str(user_id) == str(ALLOWED_USER)

# /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_allowed(update.effective_user.id):
        await update.message.reply_text("❌ You are not allowed to use this bot.")
        return
    await update.message.reply_text("👋 Send me a YouTube link, I will fetch download options!")

# ইউটিউব লিংক রিসিভ হলে
async def handle_url(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_allowed(update.effective_user.id):
        return

    url = update.message.text.strip()
    await update.message.reply_text("🔎 Fetching formats... Please wait!")

    ydl_opts = {"quiet": True, "no_warnings": True}
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            formats = []
            buttons = []
            for f in info["formats"]:
                if f.get("ext") == "mp4" and f.get("filesize"):
                    res = f.get("format_note")
                    size = round(f["filesize"] / (1024 * 1024), 2)
                    format_id = f["format_id"]
                    btn_text = f"{res} ({size} MB)"
                    buttons.append([InlineKeyboardButton(btn_text, callback_data=f"download|{url}|{format_id}")])
            if not buttons:
                await update.message.reply_text("❌ No downloadable formats found.")
                return
            await update.message.reply_text("🎥 Select resolution:", reply_markup=InlineKeyboardMarkup(buttons))
    except Exception as e:
        await update.message.reply_text(f"⚠️ Error: {e}")

# বাটন প্রেস করলে
async def download_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if not is_allowed(query.from_user.id):
        await query.edit_message_text("❌ You are not allowed to use this bot.")
        return

    try:
        _, url, format_id = query.data.split("|")
        await query.edit_message_text("⬇️ Downloading video, please wait...")

        ydl_opts = {
            "format": format_id,
            "outtmpl": "video.%(ext)s"
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)

        # টেলিগ্রামে পাঠানো
        await query.message.reply_video(video=open(filename, "rb"), caption=f"✅ {info.get('title')}")

        os.remove(filename)  # ফাইল ডিলিট করে দিচ্ছি
        await query.edit_message_text("✅ Download complete! Video sent.")
    except Exception as e:
        await query.edit_message_text(f"⚠️ Download failed: {e}")

# Main function
def main():
    if not BOT_TOKEN:
        raise ValueError("❌ BOT_TOKEN not found! Set it in environment variables.")

    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_url))
    app.add_handler(CallbackQueryHandler(download_video, pattern="^download"))

    print("🤖 Bot started...")
    app.run_polling()

if __name__ == "__main__":
    main()
