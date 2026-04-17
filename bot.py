 import os
import logging
import fitz  # PyMuPDF
import google.generativeai as genai
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

# ===== الإعدادات =====

TELEGRAM_TOKEN = os.environ.get(“TELEGRAM_TOKEN”)
GEMINI_API_KEY = os.environ.get(“GEMINI_API_KEY”)

logging.basicConfig(level=logging.INFO)
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel(“gemini-1.5-flash”)

def extract_text_from_pdf(pdf_bytes: bytes) -> str:
doc = fitz.open(stream=pdf_bytes, filetype=“pdf”)
text = “”
for page in doc:
text += page.get_text()
return text.strip()

def translate_medical_text(text: str) -> str:
words = text.split()
chunks = []
chunk_size = 3000
for i in range(0, len(words), chunk_size):
chunks.append(” “.join(words[i:i+chunk_size]))

```
translated_parts = []
for chunk in chunks:
    prompt = f"""أنت مترجم طبي متخصص. ترجم النص الطبي التالي من الإنجليزية إلى العربية الفصحى مع الحفاظ على:
```

- المصطلحات الطبية الدقيقة
- التنسيق والبنية الأصلية
- وضح المصطلح الإنجليزي بين قوسين بعد المصطلح العربي

النص:
{chunk}

الترجمة:”””
response = model.generate_content(prompt)
translated_parts.append(response.text)

```
return "\n\n".join(translated_parts)
```

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
await update.message.reply_text(
“🏥 أهلاً بك في بوت ترجمة المحاضرات الطبية!\n\n”
“📄 أرسل لي ملف PDF بالإنجليزية وسأترجمه لك إلى العربية فوراً.\n\n”
“⚠️ ملاحظة: الملفات الكبيرة قد تستغرق بعض الوقت.”
)

async def handle_pdf(update: Update, context: ContextTypes.DEFAULT_TYPE):
msg = await update.message.reply_text(“⏳ جاري معالجة الملف… الرجاء الانتظار”)
try:
file = await context.bot.get_file(update.message.document.file_id)
pdf_bytes = await file.download_as_bytearray()

```
    await msg.edit_text("📖 جاري استخراج النص من PDF...")
    text = extract_text_from_pdf(bytes(pdf_bytes))

    if not text:
        await msg.edit_text("❌ لم أتمكن من استخراج النص. تأكد أن الملف يحتوي على نص قابل للقراءة.")
        return

    await msg.edit_text("🔄 جاري الترجمة... قد يستغرق هذا دقيقة أو أكثر حسب حجم الملف")
    translation = translate_medical_text(text)

    await msg.edit_text("✅ اكتملت الترجمة!")

    max_length = 4000
    if len(translation) <= max_length:
        await update.message.reply_text(f"📋 الترجمة:\n\n{translation}")
    else:
        parts = [translation[i:i+max_length] for i in range(0, len(translation), max_length)]
        for i, part in enumerate(parts):
            header = f"📋 الترجمة (جزء {i+1}/{len(parts)}):\n\n" if i == 0 else f"تابع... ({i+1}/{len(parts)}):\n\n"
            await update.message.reply_text(header + part)

except Exception as e:
    logging.error(f"Error: {e}")
    await msg.edit_text(f"❌ حدث خطأ: {str(e)}")
```

async def handle_wrong_format(update: Update, context: ContextTypes.DEFAULT_TYPE):
await update.message.reply_text(“📄 الرجاء إرسال ملف PDF فقط.”)

def main():
app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
app.add_handler(CommandHandler(“start”, start))
app.add_handler(MessageHandler(filters.Document.PDF, handle_pdf))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_wrong_format))
print(“✅ البوت شغّال!”)
app.run_polling()

if **name** == “**main**”:
main()
