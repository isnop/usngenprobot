import os
import json
import logging
import asyncio
from http.server import BaseHTTPRequestHandler
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

TOKEN = os.environ.get("BOT_TOKEN")

# --- 🛠️ SOLUSI: GLOBAL STATE ---
# Kamus ini akan menyimpan data user selama server Vercel masih menyala.
USER_STATE = {}

# --- FUNGSI ALGORITMA ---
def generate_sop(word):
    results = []
    for i in range(len(word)):
        new_word = word[:i] + word[i] + word[i:]
        results.append(new_word)
    return results

def generate_tamhur(word):
    results = []
    alphabet = 'abcdefghijklmnopqrstuvwxyz'
    for i in range(len(word) + 1):
        for char in alphabet:
            new_word = word[:i] + char + word[i:]
            results.append(new_word)
    return results

# --- HANDLERS BOT ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    markup = InlineKeyboardMarkup([
        [InlineKeyboardButton("🪄 Bikin Varian", callback_data="bikin_varian")]
    ])
    welcome_text = (
        "Halo! Selamat datang di <b>Username Generator</b>.\n\n"
        "Bot ini akan membantu Anda membuat berbagai variasi username "
        "berdasarkan kata dasar yang Anda masukkan.\n\n"
        "<b>Dua metode yang tersedia:</b>\n"
        "📄 <b>SOP</b> — menduplikasi huruf pada kata.\n"
        "➕ <b>TAMHUR</b> — menyisipkan huruf a-z di tiap posisi.\n\n"
        "Klik tombol di bawah untuk memulai 👇"
    )
    if update.message:
        await update.message.reply_text(welcome_text, parse_mode='HTML', reply_markup=markup)
    else:
        await update.callback_query.edit_message_text(welcome_text, parse_mode='HTML', reply_markup=markup)

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    user_id = query.from_user.id

    # Pastikan user punya tempat penyimpanan di global state
    if user_id not in USER_STATE:
        USER_STATE[user_id] = {}

    if data == "bikin_varian":
        markup = InlineKeyboardMarkup([
            [InlineKeyboardButton("📄 SOP", callback_data="method_sop"),
             InlineKeyboardButton("➕ TAMHUR", callback_data="method_tamhur")]
        ])
        text = (
            "<b>Bikin Varian 🪄</b>\n"
            "━━━━━━━━━━━━━━━━━━━━\n\n"
            "Pilih metode di bawah 👇"
        )
        await query.edit_message_text(text, parse_mode='HTML', reply_markup=markup)

    elif data in ["method_sop", "method_tamhur"]:
        method = "sop" if data == "method_sop" else "tamhur"
        # Simpan method ke global state
        USER_STATE[user_id]['method'] = method
        
        info = "📄 <b>SOP</b>" if method == "sop" else "➕ <b>TAMHUR</b>"
        text = f"{info} dipilih.\n\nSilakan kirim daftar username Anda (satu per baris, maksimal 10 username).\nContoh:\n<code>ikan\nayam</code>"
        await query.message.reply_text(text, parse_mode='HTML')

    elif data == "generate_now":
        # Cek apakah data ada di global state
        if 'words' in USER_STATE[user_id] and 'method' in USER_STATE[user_id]:
            words = USER_STATE[user_id]['words']
            method = USER_STATE[user_id]['method']
            
            await query.edit_message_text("⏳ Mohon tunggu, sedang membuat varian...")
            
            all_results = []
            for word in words:
                variants = generate_sop(word) if method == 'sop' else generate_tamhur(word)
                all_results.append(f"<b>Kata Dasar: {word}</b>")
                all_results.extend(variants)
                all_results.append("")
            
            final_text = "\n".join(all_results)
            if len(final_text) > 4000:
                final_text = final_text[:4000] + "\n\n... (Hasil terpotong)"
                
            markup = InlineKeyboardMarkup([
                [InlineKeyboardButton("🔄 Buat Ulang", callback_data="bikin_varian")]
            ])
            await query.edit_message_text(
                f"✅ <b>Hasil Generate ({method.upper()}):</b>\n\n<code>{final_text}</code>", 
                parse_mode='HTML',
                reply_markup=markup
            )
            # Hapus data 'words' setelah dipakai (opsional)
            del USER_STATE[user_id]['words']
        else:
            # Jaga-jaga kalau Vercel beneran mati/cold start
            await query.edit_message_text("⚠️ Sesi Anda telah berakhir. Silakan ketik /start untuk memulai lagi.")

async def handle_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text.strip()
    
    # Cek dari global state
    if user_id not in USER_STATE or 'method' not in USER_STATE[user_id]:
        await update.message.reply_text("⚠️ Silakan ketik /start untuk memulai.")
        return

    lines = [line.strip().lower() for line in text.split('\n') if line.strip()]
    
    if len(lines) == 0:
        return await update.message.reply_text("❌ Format salah.")
    if len(lines) > 10:
        return await update.message.reply_text("❌ Maksimal 10 username.")
        
    for line in lines:
        if not line.isalpha():
            return await update.message.reply_text(f"❌ '{line}' tidak valid. Hanya huruf a-z.")

    # Simpan words ke global state
    USER_STATE[user_id]['words'] = lines
    
    markup = InlineKeyboardMarkup([
        [InlineKeyboardButton("🪄 Generate Sekarang", callback_data="generate_now")]
    ])
    
    preview = "\n".join(lines)
    await update.message.reply_text(
        f"📝 <b>Daftar Username:</b>\n<code>{preview}</code>\n\nKlik tombol di bawah untuk memproses.",
        parse_mode='HTML',
        reply_markup=markup
    )

# --- FUNGSI SERVERLESS VERCEL ---
async def process_update(update_data: dict):
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler(["start", "help"], start))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_input))
    
    update = Update.de_json(data=update_data, bot=app.bot)
    await app.initialize()
    await app.process_update(update)
    await app.shutdown()

class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length)
        try:
            update_data = json.loads(body)
            asyncio.run(process_update(update_data))
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b'OK')
        except Exception as e:
            logger.error(f"Error: {e}")
            self.send_response(500)
            self.end_headers()

    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b'Bot is running')
