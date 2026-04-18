import os
import logging
import fitz
import google.generativeai as genai
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

logging.basicConfig(level=logging.INFO)
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel("gemini-1.5-flash")

def extract_text_from_pdf(pdf_bytes: bytes) -> str:
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    text = ""
    for page in doc:
        text += page.get_text()
    return text.strip()

def translate_medical_text(text: str) -> str:
    words = text.split()
    chunks = []
    chunk_size = 3000
    for i in range(0, len(words), chunk_size):
        chunks.append(" ".join(words[i:i+chunk_size]))
    translated_parts = []
    for chunk in chunks:
        prompt = f"ترجم النص الطبي التالي من الإنجليزية إلى العربية:\n\n{chunk}"
        response = model.generate_content(prompt)
        translated_parts.append(response.text)
    return "\n\n".join(translated_parts)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🏥 أهلاً! أرسل ملف PDF وسأترجمه لك.")

async def handle_pdf(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = await update.message.reply_text("⏳ جاري المعالجة...")
    try:
        file = await context.bot.get_file(update.message.document.file_id)
        pdf_bytes = await file.download_as_bytearray()
        await msg.edit_text("📖 جاري استخراج النص...")
        text = extract_text_from_pdf(bytes(pdf_bytes))
        if not text:
            await msg.edit_text("❌ الملف لا يحتوي على نص.")
            return
        await msg.edit_text("🔄 جاري الترجمة...")
        translation = translate_medical_text(text)
        await msg.edit_text("✅ اكتملت الترجمة!")
        max_length = 4000
        if len(translation) <= max_length:
            await update.message.reply_text(translation)
        else:
            parts = [translation[i:i+max_length] for i in range(0, len(translation), max_length)]
            for part in parts:
                await update.message.reply_text(part)
    except Exception as e:
        await msg.edit_text(f"❌ خطأ: {str(e)}")

async def handle_wrong_format(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("📄 أرسل ملف PDF فقط.")

def main():
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.Document.PDF, handle_pdf))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_wrong_format))
    app.run_polling()

if __name__ == "__main__":
    main()
