import os
import json
import logging
import asyncio
from http.server import BaseHTTPRequestHandler
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

# Setup logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Ambil Token dari Environment Variable Vercel
TOKEN = os.environ.get("BOT_TOKEN")

# --- FUNGSI ALGORITMA (Tetap Sama) ---
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

# --- HANDLERS BOT (Tetap Sama) ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    markup = InlineKeyboardMarkup([
        [InlineKeyboardButton("🪄 Bikin Varian", callback_data="bikin_varian")]
    ])
    welcome_text = (
        "Halo! Selamat datang di <b>Username Generator</b>.\n\n"
        "Bot ini akan membantu Anda membuat berbagai variasi username "
        "berdasarkan kata dasar yang Anda masukkan.\n\n"
        "<b>Dua metode yang tersedia:</b>\n"
        "📄 <b>SOP</b> — menduplikasi huruf pada kata (cepat, varian sedikit).\n"
        "➕ <b>TAMHUR</b> — menyisipkan huruf a-z di tiap posisi (varian banyak).\n\n"
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

    if data == "bikin_varian":
        markup = InlineKeyboardMarkup([
            [InlineKeyboardButton("📄 SOP", callback_data="method_sop"),
             InlineKeyboardButton("➕ TAMHUR", callback_data="method_tamhur")]
        ])
        text = (
            "<b>Bikin Varian 🪄</b>\n"
            "━━━━━━━━━━━━━━━━━━━━\n\n"
            "<b>📄 SOP — Duplikasi Huruf</b>\n"
            "Setiap huruf <b>diduplikasi</b> tepat di posisinya.\n"
            "Hasil: sepanjang kata + 1 huruf.\n"
            "Contoh <code>ikan</code>:\n"
            "  <code>iikan, ikkan, ikaan, ikann</code>\n"
            "▶ 4 varian per kata.\n\n"
            "<b>➕ TAMHUR — Tambah Huruf a-z</b>\n"
            "Huruf <b>a–z</b> disisipkan di setiap posisi (depan, tengah, belakang).\n"
            "Contoh <code>ikan</code>:\n"
            "  <code>aikan, bikan, ..., zikan</code>\n"
            "  <code>iakan, ibkan, ..., izkan</code> ... dst.\n"
            "▶ 26 × (panjang+1) varian per kata.\n\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "Pilih metode di bawah 👇"
        )
        await query.edit_message_text(text, parse_mode='HTML', reply_markup=markup)

    elif data in ["method_sop", "method_tamhur"]:
        method = "sop" if data == "method_sop" else "tamhur"
        context.user_data['method'] = method
        if method == "sop":
            info = (
                "<b>📄 SOP — Duplikasi Huruf</b>\n"
                "Setiap huruf <b>diduplikasi</b> di posisinya.\n"
                "Contoh: <code>ikan</code> ➔ <code>iikan, ikkan, ikaan, ikann</code>."
            )
        else:
            info = (
                "<b>➕ TAMHUR — Tambah Huruf a-z</b>\n"
                "Setiap huruf a-z <b>disisipkan</b> di tiap posisi.\n"
                "Contoh: <code>ikan</code> ➔ <code>aikan...zikan, iakan...izkan</code>."
            )
        text = f"{info}\n\nSilakan kirim daftar username Anda (satu per baris, maksimal 10 username).\nContoh:\n<code>ikan\nayam</code>"
        await query.message.reply_text(text, parse_mode='HTML')

    elif data == "generate_now":
        if 'words' in context.user_data and 'method' in context.user_data:
            words = context.user_data['words']
            method = context.user_data['method']
            
            await query.edit_message_text("⏳ Mohon tunggu, sedang membuat varian...")
            
            all_results = []
            for word in words:
                if method == 'sop':
                    variants = generate_sop(word)
                else:
                    variants = generate_tamhur(word)
                
                all_results.append(f"<b>Kata Dasar: {word}</b>")
                all_results.extend(variants)
                all_results.append("")
            
            final_text = "\n".join(all_results)
            if len(final_text) > 4000:
                final_text = final_text[:4000] + "\n\n... (Hasil terpotong karena terlalu panjang)"
                
            markup = InlineKeyboardMarkup([
                [InlineKeyboardButton("🔄 Buat Ulang", callback_data="bikin_varian")]
            ])
            await query.edit_message_text(
                f"✅ <b>Hasil Generate ({method.upper()}):</b>\n\n<code>{final_text}</code>", 
                parse_mode='HTML',
                reply_markup=markup
            )
            del context.user_data['words']

async def handle_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    if 'method' not in context.user_data:
        await update.message.reply_text("Silakan ketik /start untuk memulai.")
        return
    lines = [line.strip().lower() for line in text.split('\n') if line.strip()]
    
    if len(lines) == 0:
        await update.message.reply_text("❌ Format salah. Kirimkan teks biasa.")
        return
    if len(lines) > 10:
        await update.message.reply_text("❌ Maksimal 10 username dalam satu waktu.")
        return
    for line in lines:
        if not line.isalpha():
            await update.message.reply_text(f"❌ Username '{line}' tidak valid. Hanya boleh huruf a-z (tanpa spasi/angka).")
            return

    context.user_data['words'] = lines
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
    # Bangun aplikasi
    app = Application.builder().token(TOKEN).build()
    
    # Daftarkan handler
    app.add_handler(CommandHandler(["start", "help"], start))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_input))
    
    # Proses pesan
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
