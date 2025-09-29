from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes, CallbackQueryHandler, MessageHandler, filters
import os
from dotenv import load_dotenv
from youtubesearchpython import VideosSearch
import yt_dlp

load_dotenv(dotenv_path="/storage/emulated/0/yt_bot/api.env")

TOKEN = os.getenv("TOKEN")
ALLOWED_USER = os.getenv("ALLOWED_USER")

if ALLOWED_USER is None:
    print("❌ ALLOWED_USER .env ফাইলে নেই বা ঠিকমতো পড়া যায়নি।")
    exit()

ALLOWED_USER = int(ALLOWED_USER)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ALLOWED_USER:
        await update.message.reply_text("❌ এই বট শুধু Owner ব্যবহার করতে পারবেন।")
        return
    await update.message.reply_text(
        "হাই! আমি YouTube Downloader Bot 🤖\n"
        "ভিডিও সার্চ করতে লিখো:\n"
        "/search ভিডিও_টাইটেল\n"
        "ভিডিও ডাউনলোড করতে লিংক পাঠাও।"
    )


async def search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ALLOWED_USER:
        await update.message.reply_text("❌ এই বট শুধু Owner ব্যবহার করতে পারবেন।")
        return

    query = " ".join(context.args)
    if not query:
        await update.message.reply_text("❌ দয়া করে ভিডিও নাম লিখুন। উদাহরণ:\n/search python tutorial")
        return

    await update.message.reply_text(f"🔍 Searching for '{query}'...")
    videosSearch = VideosSearch(query, limit=10)
    results = videosSearch.result()["result"]

    reply_text = "🔎 Search Results:\n\n"
    for i, video in enumerate(results[:5], start=1):
        title = video["title"]
        channel = video.get("channel", {}).get("name", "N/A")
        duration = video.get("duration", "N/A")
        views = video.get("viewCount", {}).get("short", "N/A")
        link = video.get("link", "N/A")
        reply_text += f"{i}. 🎬 {title}\n👤 {channel}\n⏱ {duration} | 👀 {views}\n🔗 {link}\n\n"

    keyboard = [[InlineKeyboardButton("More", callback_data=query)]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(reply_text, reply_markup=reply_markup)


async def more_results(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query.data
    await update.callback_query.answer()
    videosSearch = VideosSearch(query, limit=10)
    results = videosSearch.result()["result"]

    reply_text = "📜 More Results:\n\n"
    for i, video in enumerate(results[5:], start=6):
        title = video["title"]
        channel = video.get("channel", {}).get("name", "N/A")
        duration = video.get("duration", "N/A")
        views = video.get("viewCount", {}).get("short", "N/A")
        link = video.get("link", "N/A")
        reply_text += f"{i}. 🎬 {title}\n👤 {channel}\n⏱ {duration} | 👀 {views}\n🔗 {link}\n\n"

    await update.callback_query.message.reply_text(reply_text)


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ALLOWED_USER:
        await update.message.reply_text("❌ এই বট শুধু Owner ব্যবহার করতে পারবেন।")
        return

    url = update.message.text
    if "youtube.com" not in url and "youtu.be" not in url:
        await update.message.reply_text("❌ এটি একটি YouTube লিংক নয়।")
        return

    await update.message.reply_text("📥 লিংক চেক করা হচ্ছে...")
    ydl_opts = {"listformats": True}

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)}")
        return

    formats = info.get("formats", [])
    keyboard = []
    reply_text = f"🎬 {info.get('title')}\n\nAvailable Formats:\n"

    for fmt in formats:
        if fmt.get("ext") == "mp4" and fmt.get("height"):
            format_id = fmt["format_id"]
            resolution = fmt.get("height")
            size = fmt.get("filesize") or 0
            size_mb = size / (1024 * 1024) if size else "N/A"
            reply_text += f"Resolution: {resolution}p | Size: {size_mb} MB\n"
            keyboard.append([InlineKeyboardButton(f"{resolution}p", callback_data=f"download|{url}|{format_id}")])

    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(reply_text, reply_markup=reply_markup)


async def download_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = update.callback_query.data.split("|")
    if len(data) != 3:
        await update.callback_query.answer()
        return
    _, url, format_id = data
    await update.callback_query.answer()
    await update.callback_query.message.reply_text("⏳ ডাউনলোড শুরু হচ্ছে...")

    download_path = f"/storage/emulated/0/yt_bot/downloaded_video.mp4"

    ydl_opts = {
        "format": format_id,
        "outtmpl": download_path,
        "quiet": True
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
    except Exception as e:
        await update.callback_query.message.reply_text(f"❌ ডাউনলোড এrror: {str(e)}")
        return

    await update.callback_query.message.reply_text("✅ ডাউনলোড শেষ হয়েছে।\nআপনি নীচের ফাইল থেকে ডাউনলোড করতে পারবেন।")
    await context.bot.send_document(chat_id=update.effective_chat.id, document=open(download_path, "rb"), filename="video.mp4")


def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("search", search))
    app.add_handler(CallbackQueryHandler(more_results, pattern="^.*$"))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(CallbackQueryHandler(download_video, pattern=r"download\|"))
    print("Bot running...")
    app.run_polling()


if __name__ == "__main__":
    main()
