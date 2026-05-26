import yfinance as yf
from flask import Flask
import threading
import time
import os
import asyncio

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup
)

from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes
)

from datetime import datetime

from config import BOT_TOKEN, CHAT_ID


# =====================================
# FLASK WEB SERVER
# =====================================

app_web = Flask(__name__)

@app_web.route('/')
def home():
    return "BOT RUNNING"


def run_web():

    port = int(
        os.environ.get(
            "PORT",
            10000
        )
    )

    app_web.run(
        host='0.0.0.0',
        port=port
    )


# =====================================
# DANH SÁCH CỔ PHIẾU
# =====================================

SYMBOLS = [

    # BANK
    "VCB.VN",
    "BID.VN",
    "CTG.VN",
    "TCB.VN",
    "MBB.VN",
    "STB.VN",
    "SHB.VN",

    # CHỨNG KHOÁN
    "SSI.VN",
    "VND.VN",
    "VIX.VN",
    "HCM.VN",
    "FTS.VN",

    # BĐS
    "DIG.VN",
    "DXG.VN",
    "NVL.VN",
    "PDR.VN",
    "KDH.VN",

    # THÉP
    "HPG.VN",
    "HSG.VN",
    "NKG.VN",

    # CÔNG NGHỆ
    "FPT.VN",
    "CMG.VN",
    "ELC.VN",

    # BÁN LẺ
    "MWG.VN",
    "FRT.VN",
    "DGW.VN",

    # ĐIỆN
    "REE.VN",
    "POW.VN",
    "GEG.VN",

    # DẦU KHÍ
    "GAS.VN",
    "PVD.VN",
    "BSR.VN",

    # PHÂN BÓN
    "DGC.VN",
    "DCM.VN",
    "DPM.VN",

    # XÂY DỰNG
    "CTD.VN",
    "HHV.VN",
    "VCG.VN",

    # LOGISTICS
    "GMD.VN",
    "HAH.VN",
    "VSC.VN",

    # KHÁC
    "PNJ.VN",
    "DBC.VN",
    "GEX.VN"
]


# =====================================
# GET DATA
# =====================================

def get_stock_data(symbol):

    try:

        df = yf.download(

            symbol,

            period="2mo",

            interval="1d",

            progress=False,

            threads=False
        )

        if df.empty:
            return None

        return df

    except Exception as e:

        print(f"Lỗi {symbol}: {e}")

        return None


# =====================================
# DETECT WHALE
# =====================================

def detect_whale(df):

    try:

        close = df['Close']
        volume = df['Volume']

        if hasattr(close, "columns"):
            close = close.iloc[:, 0]

        if hasattr(volume, "columns"):
            volume = volume.iloc[:, 0]

        if len(df) < 21:
            return None

        price_today = float(
            close.iloc[-1]
        )

        price_yesterday = float(
            close.iloc[-2]
        )

        pct_change = (
            (price_today - price_yesterday)
            / price_yesterday
        ) * 100

        vol_today = float(
            volume.iloc[-1]
        )

        vol_ma20 = float(
            volume.iloc[-21:-1].mean()
        )

        if vol_ma20 == 0:
            return None

        ratio = vol_today / vol_ma20

        is_whale = (
            ratio >= 3
            and
            pct_change >= 1.5
        )

        return {

            "change": round(
                pct_change,
                2
            ),

            "ratio": round(
                ratio,
                2
            ),

            "whale": is_whale
        }

    except Exception as e:

        print(f"detect_whale error: {e}")

        return None


# =====================================
# SAVE HISTORY
# =====================================

def save_history(msg):

    try:

        with open(
            "history.txt",
            "a",
            encoding="utf-8"
        ) as f:

            f.write(
                "\n====================\n"
            )

            f.write(msg)

            f.write("\n")

    except Exception as e:

        print(f"save_history error: {e}")


# =====================================
# BUILD MESSAGE
# =====================================

def build_message():

    result_gain = []

    result_whale = []

    result_volume = []

    for symbol in SYMBOLS:

        try:

            # =========================
            # CHỐNG RATE LIMIT
            # =========================

            time.sleep(1)

            df = yf.download(

                symbol,

                period="2mo",

                interval="1d",

                progress=False,

                threads=False

            )

            if df.empty:
                continue

            close = df['Close']
            volume = df['Volume']

            if hasattr(close, "columns"):
                close = close.iloc[:, 0]

            if hasattr(volume, "columns"):
                volume = volume.iloc[:, 0]

            if len(close) < 21:
                continue

            # =========================
            # PRICE CHANGE
            # =========================

            today = float(
                close.iloc[-1]
            )

            yesterday = float(
                close.iloc[-2]
            )

            change = (
                (today - yesterday)
                / yesterday
            ) * 100

            # =========================
            # VOLUME
            # =========================

            vol_today = float(
                volume.iloc[-1]
            )

            vol_ma20 = float(
                volume.iloc[-21:-1].mean()
            )

            ratio = (
                vol_today / vol_ma20
            ) if vol_ma20 > 0 else 0

            # =========================
            # TOP GAIN
            # =========================

            result_gain.append({

                "ticker": symbol.replace(
                    ".VN",
                    ""
                ),

                "change": round(
                    change,
                    2
                )
            })

            # =========================
            # VOLUME BREAKOUT
            # =========================

            if ratio >= 2:

                result_volume.append({

                    "ticker": symbol.replace(
                        ".VN",
                        ""
                    ),

                    "ratio": round(
                        ratio,
                        2
                    )
                })

            # =========================
            # WHALE DETECT
            # =========================

            is_whale = (

                ratio >= 3

                and

                change >= 1.5

            )

            if is_whale:

                result_whale.append({

                    "ticker": symbol.replace(
                        ".VN",
                        ""
                    ),

                    "change": round(
                        change,
                        2
                    ),

                    "ratio": round(
                        ratio,
                        2
                    )
                })

        except Exception as e:

            print(
                f"Lỗi {symbol}: {e}"
            )

            continue

    # =========================
    # SORT
    # =========================

    result_gain = sorted(

        result_gain,

        key=lambda x: x["change"],

        reverse=True

    )[:5]

    result_volume = sorted(

        result_volume,

        key=lambda x: x["ratio"],

        reverse=True

    )[:5]

    result_whale = sorted(

        result_whale,

        key=lambda x: x["ratio"],

        reverse=True

    )[:5]

    # =========================
    # BUILD MESSAGE
    # =========================

    msg = (

        f"📊 STOCK BOT\n"

        f"{datetime.now().strftime('%d/%m %H:%M')}\n\n"

    )

    # =========================
    # TOP GAIN
    # =========================

    msg += "🚀 TOP TĂNG GIÁ\n"

    if result_gain:

        for i, x in enumerate(

            result_gain,

            1

        ):

            msg += (

                f"{i}. "

                f"{x['ticker']} "

                f"| +{x['change']}%\n"

            )

    else:

        msg += "Không có dữ liệu\n"

    # =========================
    # VOLUME
    # =========================

    msg += "\n🔥 THANH KHOẢN TĂNG MẠNH\n"

    if result_volume:

        for i, x in enumerate(

            result_volume,

            1

        ):

            msg += (

                f"{i}. "

                f"{x['ticker']} "

                f"| x{x['ratio']}\n"

            )

    else:

        msg += "Không có dữ liệu\n"

    # =========================
    # WHALE
    # =========================

    msg += "\n🐋 DÒNG TIỀN CÁ MẬP\n"

    if result_whale:

        for i, x in enumerate(

            result_whale,

            1

        ):

            msg += (

                f"{i}. "

                f"{x['ticker']} "

                f"| +{x['change']}% "

                f"| x{x['ratio']}\n"

            )

    else:

        msg += "Không phát hiện cá mập\n"

    return msg



# =====================================
# START
# =====================================

async def start(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    keyboard = [

        [
            InlineKeyboardButton(
                "📈 Quét cổ phiếu",
                callback_data="scan"
            )
        ],

        [
            InlineKeyboardButton(
                "📜 Xem lịch sử",
                callback_data="history"
            )
        ]
    ]

    reply_markup = InlineKeyboardMarkup(
        keyboard
    )

    await update.message.reply_text(

        "✅ BOT HOẠT ĐỘNG",

        reply_markup=reply_markup
    )


# =====================================
# BUTTON HANDLER
# =====================================

async def button_handler(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    query = update.callback_query

    await query.answer()

    # SCAN

    if query.data == "scan":

        await query.message.reply_text(
            "⏳ Đang quét..."
        )

        try:

            msg = build_message()

            save_history(msg)

            await query.message.reply_text(msg)

        except Exception as e:

            await query.message.reply_text(
                f"Lỗi scan: {e}"
            )

    # HISTORY

    elif query.data == "history":

        try:

            with open(
                "history.txt",
                "r",
                encoding="utf-8"
            ) as f:

                data = f.read()

            if len(data) > 3500:
                data = data[-3500:]

            await query.message.reply_text(data)

        except:

            await query.message.reply_text(
                "Chưa có lịch sử"
            )


# =====================================
# AUTO SEND
# =====================================

def auto_send_loop(app):

    while True:

        try:

            now = time.strftime("%H:%M")

            if now == "15:00":

                msg = build_message()

                save_history(msg)

                asyncio.run(

                    app.bot.send_message(

                        chat_id=CHAT_ID,

                        text=msg
                    )
                )

                print(
                    "Đã gửi auto 15h"
                )

                time.sleep(60)

            time.sleep(20)

        except Exception as e:

            print(
                f"auto_send_loop error: {e}"
            )

            time.sleep(30)


# =====================================
# MAIN
# =====================================

def main():

    # WEB SERVER

    web_thread = threading.Thread(

        target=run_web,

        daemon=True
    )

    web_thread.start()

    # TELEGRAM

    app = Application.builder().token(
        BOT_TOKEN
    ).build()

    # HANDLERS

    app.add_handler(
        CommandHandler(
            "start",
            start
        )
    )

    app.add_handler(
        CallbackQueryHandler(
            button_handler
        )
    )

    # AUTO THREAD

    auto_thread = threading.Thread(

        target=auto_send_loop,

        args=(app,),

        daemon=True
    )

    auto_thread.start()

    print("BOT RUNNING...")
    
    app.run_polling(

        drop_pending_updates=True,

        allowed_updates=Update.ALL_TYPES,

        close_loop=False,

        stop_signals=None

)

    


# =====================================
# RUN
# =====================================

if __name__ == "__main__":

    main()
