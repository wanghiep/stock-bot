import yfinance as yf
import pandas as pd
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from datetime import datetime
from config import BOT_TOKEN, CHAT_ID

# =========================
# CONFIG CỔ PHIẾU
# =========================
SYMBOLS = [
    "VCB.VN","BID.VN","CTG.VN","TCB.VN","MBB.VN",
    "SHB.VN","SSI.VN","VND.VN","VIX.VN","HCM.VN",
    "HPG.VN","FPT.VN","MWG.VN","PNJ.VN","GEX.VN"
]

# =========================
# CÁ MẬP DETECT
# =========================
def detect_whale(df):
    try:
        close = df['Close']
        volume = df['Volume']

        if len(df) < 21:
            return None

        price_today = float(close.iloc[-1])
        price_yesterday = float(close.iloc[-2])

        pct_change = ((price_today - price_yesterday) / price_yesterday) * 100

        vol_today = float(volume.iloc[-1])
        vol_ma20 = float(volume.iloc[-21:-1].mean())

        if vol_ma20 == 0:
            return None

        ratio = vol_today / vol_ma20

        is_whale = (ratio >= 3) and (pct_change >= 1.5)

        return {
            "change": round(pct_change, 2),
            "ratio": round(ratio, 2),
            "whale": is_whale
        }

    except:
        return None

# =========================
# LẤY DATA
# =========================
def get_stock(symbol):
    try:
        df = yf.download(symbol, period="2mo", interval="1d", progress=False)
        return df
    except:
        return None

# =========================
# BUILD MESSAGE
# =========================
def build_message():

    result_whale = []
    result_gain = []

    for symbol in SYMBOLS:

        df = get_stock(symbol)
        if df is None or df.empty:
            continue

        try:
            close = df['Close']

            price_today = float(close.iloc[-1])
            price_yesterday = float(close.iloc[-2])

            change = ((price_today - price_yesterday) / price_yesterday) * 100

            # volume
            volume = df['Volume']
            vol_today = float(volume.iloc[-1])
            vol_ma20 = float(volume.iloc[-21:-1].mean()) if len(df) >= 21 else 0

            # gain list
            result_gain.append({
                "ticker": symbol.replace(".VN",""),
                "change": change
            })

            # whale detect
            if vol_ma20 > 0:
                ratio = vol_today / vol_ma20

                if ratio >= 3 and change >= 1.5:
                    result_whale.append({
                        "ticker": symbol.replace(".VN",""),
                        "change": round(change,2),
                        "ratio": round(ratio,2)
                    })

        except:
            continue

    # sort gain
    result_gain = sorted(result_gain, key=lambda x: x["change"], reverse=True)[:5]

    # message
    msg = f"📊 STOCK BOT - {datetime.now().strftime('%d/%m %H:%M')}\n\n"

    msg += "🔥 TOP TĂNG MẠNH:\n"
    for i, x in enumerate(result_gain,1):
        msg += f"{i}. {x['ticker']} | +{round(x['change'],2)}%\n"

    msg += "\n🐋 DÒNG TIỀN CÁ MẬP (20 PHIÊN):\n"
    if result_whale:
        for i, x in enumerate(result_whale[:5],1):
            msg += f"{i}. {x['ticker']} | +{x['change']}% | x{x['ratio']}\n"
    else:
        msg += "Không phát hiện cá mập\n"

    return msg

# =========================
# TELEGRAM HANDLERS
# =========================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    keyboard = [
        [InlineKeyboardButton("📈 Quét cổ phiếu", callback_data="scan")],
        [InlineKeyboardButton("📊 Lịch sử", callback_data="history")]
    ]

    await update.message.reply_text(
        "Bot sẵn sàng!",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query
    await query.answer()

    if query.data == "scan":
        msg = build_message()
        await query.message.reply_text(msg)

    if query.data == "history":
        await query.message.reply_text("Chưa có lịch sử lưu (có thể nâng cấp sau)")

# =========================
# AUTO 15H
# =========================
async def auto_send(app):
    msg = build_message()
    await app.bot.send_message(chat_id=CHAT_ID, text=msg)

# =========================
# MAIN
# =========================
def main():

    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button))

    scheduler = AsyncIOScheduler()

    scheduler.add_job(
        lambda: asyncio.create_task(auto_send(app)),
        trigger='cron',
        hour=15,
        minute=0
    )

    scheduler.start()

    print("BOT RUNNING...")

    app.run_polling()

# =========================
if __name__ == "__main__":
    main()
