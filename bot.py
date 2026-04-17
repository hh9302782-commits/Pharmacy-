import os
import logging
import anthropic
import fitz  # PyMuPDF
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

# ===== الإعدادات =====
TELEGRAM_TOKEN = "YOUR_TELEGRAM_BOT_TOKEN"
ANTHROPIC_API_KEY = "YOUR_ANTHROPIC_API_KEY"

logging.basicConfig(level=logging.INFO)
client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)


def extract_text_from_pdf(pdf_bytes: bytes) -> str:
    """استخراج النص من ملف PDF"""
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    text = ""
    for page in doc:
        text += page.get_text()
    return text.strip()


def translate_medical_text(text: str) -> str:
    """ترجمة النص الطبي من الإنجليزية إلى العربية باستخدام Claude"""
    # تقسيم النص إذا كان طويلاً جداً (أكثر من 3000 كلمة)
    words = text.split()
    chunks = []
    chunk_size = 3000

    for i in range(0, len(words), chunk_size):
        chunks.append(" ".join(words[i:i+chunk_size]))

    translated_parts = []

    for i, chunk in enumerate(chunks):
        message = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=4000,
            messages=[
                {
                    "role": "user",
                    "content": f"""أنت مترجم طبي متخصص. قم بترجمة النص الطبي التالي من الإنجليزية إلى العربية الفصحى مع الحفاظ على:
- المصطلحات الطبية الدقيقة
- التنسيق والبنية الأصلية
- وضح المصطلح الإنجليزي بين قوسين بعد المصطلح العربي للمصطلحات التقنية

النص:
{chunk}

الترجمة:"""
                }
            ]
        )
        translated_parts.append(message.content[0].text)

    return "\n\n".join(translated_parts)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🏥 أهلاً بك في بوت ترجمة المحاضرات الطبية!\n\n"
        "📄 أرسل لي ملف PDF بالإنجليزية وسأترجمه لك إلى العربية فوراً.\n\n"
        "⚠️ ملاحظة: الملفات الكبيرة قد تستغرق بعض الوقت."
    )


async def handle_pdf(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالجة ملفات PDF المرسلة"""
    msg = await update.message.reply_text("⏳ جاري معالجة الملف... الرجاء الانتظار")

    try:
        # تحميل الملف
        file = await context.bot.get_file(update.message.document.file_id)
        pdf_bytes = await file.download_as_bytearray()

        # استخراج النص
        await msg.edit_text("📖 جاري استخراج النص من PDF...")
        text = extract_text_from_pdf(bytes(pdf_bytes))

        if not text:
            await msg.edit_text("❌ لم أتمكن من استخراج النص. تأكد أن الملف يحتوي على نص قابل للقراءة.")
            return

        # الترجمة
        await msg.edit_text("🔄 جاري الترجمة... قد يستغرق هذا دقيقة أو أكثر حسب حجم الملف")
        translation = translate_medical_text(text)

        # إرسال الترجمة
        await msg.edit_text("✅ اكتملت الترجمة!")

        # إرسال النتيجة (تقسيم إذا كانت طويلة)
        max_length = 4000
        if len(translation) <= max_length:
            await update.message.reply_text(f"📋 **الترجمة:**\n\n{translation}", parse_mode="Markdown")
        else:
            # تقسيم الرسالة
            parts = [translation[i:i+max_length] for i in range(0, len(translation), max_length)]
            for i, part in enumerate(parts):
                header = f"📋 **الترجمة (جزء {i+1}/{len(parts)}):**\n\n" if i == 0 else f"**تابع... ({i+1}/{len(parts)}):**\n\n"
                await update.message.reply_text(header + part, parse_mode="Markdown")

    except Exception as e:
        logging.error(f"Error: {e}")
        await msg.edit_text(f"❌ حدث خطأ: {str(e)}")


async def handle_wrong_format(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("📄 الرجاء إرسال ملف PDF فقط.")


def main():
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.Document.PDF, handle_pdf))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_wrong_format))

    print("✅ البوت شغّال!")
    app.run_polling()


if __name__ == "__main__":
    main()
