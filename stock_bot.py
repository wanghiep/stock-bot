from telegram import Update, ReplyKeyboardMarkup

from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters
)

import config

BOT_TOKEN = config.BOT_TOKEN
CHAT_ID = config.CHAT_ID

import pandas as pd
import yfinance as yf

from datetime import datetime

import os

from apscheduler.schedulers.background import BackgroundScheduler


# =========================
# HISTORY FILE
# =========================

HISTORY_FILE = "history.csv"

if os.path.exists(HISTORY_FILE):

    history_df = pd.read_csv(HISTORY_FILE)

else:

    history_df = pd.DataFrame(
        columns=["Date", "Ticker", "Type"]
    )


# =========================
# STOCK LIST
# =========================

symbols = [

    # BANK
    "VCB.VN",
    "BID.VN",
    "CTG.VN",
    "TCB.VN",
    "MBB.VN",
    "SHB.VN",

    # CHỨNG KHOÁN
    "SSI.VN",
    "VND.VN",
    "VIX.VN",
    "HCM.VN",

    # BĐS
    "DIG.VN",
    "DXG.VN",
    "NVL.VN",
    "PDR.VN",

    # THÉP
    "HPG.VN",
    "HSG.VN",
    "NKG.VN",

    # KHÁC
    "FPT.VN",
    "MWG.VN",
    "PNJ.VN",
    "GEX.VN",
    "DBC.VN",
    "DGC.VN"
]


# =========================
# START
# =========================

async def start(update: Update,
                context: ContextTypes.DEFAULT_TYPE):

    keyboard = [
        ['📈 Quét cổ phiếu'],
        ['📜 Xem lịch sử']
    ]

    reply_markup = ReplyKeyboardMarkup(
        keyboard,
        resize_keyboard=True
    )

    await update.message.reply_text(
        "✅ Bot hoạt động OK!",
        reply_markup=reply_markup
    )


# =========================
# BUILD MESSAGE
# =========================

def build_stock_message():

    global history_df

    result_volume = []
    result_gain = []
    result_money = []

    for symbol in symbols:

        try:

            df = yf.download(
                symbol,
                period="1mo",
                interval="1d",
                progress=False,
                auto_adjust=False
            )

            if df.empty:
                continue

            if len(df) < 11:
                continue

            # =====================
            # FIX MULTI INDEX
            # =====================

            close_data = df['Close']
            volume_data = df['Volume']

            if hasattr(close_data, 'columns'):
                close_data = close_data.iloc[:, 0]

            if hasattr(volume_data, 'columns'):
                volume_data = volume_data.iloc[:, 0]

            # =====================
            # VALUES
            # =====================

            today_volume = float(
                volume_data.iloc[-1]
            )

            avg10 = float(
                volume_data.iloc[-11:-1].mean()
            )

            today_close = float(
                close_data.iloc[-1]
            )

            yesterday_close = float(
                close_data.iloc[-2]
            )

            # =====================
            # CHANGE %
            # =====================

            pct_change = (
                (today_close - yesterday_close)
                / yesterday_close
            ) * 100

            # =====================
            # TOP GAIN
            # =====================

            result_gain.append({

                "Ticker": symbol.replace(
                    ".VN",
                    ""
                ),

                "Change": round(
                    pct_change,
                    2
                )
            })

            # =====================
            # VOLUME X2
            # =====================

            if avg10 > 0:

                if today_volume >= avg10 * 2:

                    ratio = (
                        today_volume / avg10
                    )

                    result_volume.append({

                        "Ticker": symbol.replace(
                            ".VN",
                            ""
                        ),

                        "Ratio": round(
                            ratio,
                            2
                        )
                    })

            # =====================
            # MONEY FLOW
            # =====================

            if pct_change >= 2:

                if today_volume >= avg10 * 1.5:

                    result_money.append({

                        "Ticker": symbol.replace(
                            ".VN",
                            ""
                        ),

                        "Change": round(
                            pct_change,
                            2
                        ),

                        "Ratio": round(
                            today_volume / avg10,
                            2
                        )
                    })

        except Exception as e:

            print(
                f"Lỗi {symbol}: {e}"
            )

            continue

    # =====================
    # DATAFRAME
    # =====================

    df_volume = pd.DataFrame(
        result_volume
    )

    df_gain = pd.DataFrame(
        result_gain
    )

    df_money = pd.DataFrame(
        result_money
    )

    # =====================
    # SORT
    # =====================

    if not df_volume.empty:

        df_volume = df_volume.sort_values(
            by="Ratio",
            ascending=False
        ).head(3)

    if not df_money.empty:

        df_money = df_money.sort_values(
            by="Ratio",
            ascending=False
        ).head(5)

    if not df_gain.empty:

        df_gain = df_gain.sort_values(
            by="Change",
            ascending=False
        ).head(5)

    # =====================
    # SAVE HISTORY
    # =====================

    today_str = datetime.today().strftime(
        "%Y-%m-%d"
    )

    new_rows = []

    # SAVE VOLUME

    if not df_volume.empty:

        for _, row in df_volume.iterrows():

            exists = (

                (history_df["Date"] == today_str)
                &
                (history_df["Ticker"] == row["Ticker"])
                &
                (history_df["Type"] == "Volume")

            ).any()

            if not exists:

                new_rows.append({

                    "Date": today_str,
                    "Ticker": row["Ticker"],
                    "Type": "Volume"
                })

    # SAVE GAIN

    if not df_gain.empty:

        for _, row in df_gain.iterrows():

            exists = (

                (history_df["Date"] == today_str)
                &
                (history_df["Ticker"] == row["Ticker"])
                &
                (history_df["Type"] == "Gain")

            ).any()

            if not exists:

                new_rows.append({

                    "Date": today_str,
                    "Ticker": row["Ticker"],
                    "Type": "Gain"
                })

    # SAVE FILE

    if len(new_rows) > 0:

        history_df = pd.concat(
            [history_df, pd.DataFrame(new_rows)],
            ignore_index=True
        )

        history_df.to_csv(
            HISTORY_FILE,
            index=False
        )

    # =====================
    # MESSAGE
    # =====================

    message = "📈 STOCK SCAN\n\n"

    # =====================
    # VOLUME
    # =====================

    message += "🔥 THANH KHOẢN TĂNG MẠNH\n"

    if not df_volume.empty:

        for i, row in enumerate(
            df_volume.itertuples(),
            1
        ):

            message += (
                f"{i}. "
                f"{row.Ticker} "
                f"| x{row.Ratio}\n"
            )

    else:

        message += (
            "Không có dữ liệu.\n"
        )

    # =====================
    # MONEY FLOW
    # =====================

    message += "\n💰 DÒNG TIỀN VÀO MẠNH\n"

    if not df_money.empty:

        for i, row in enumerate(
            df_money.itertuples(),
            1
        ):

            message += (
                f"{i}. "
                f"{row.Ticker} "
                f"| +{row.Change}% "
                f"| x{row.Ratio}\n"
            )

    else:

        message += (
            "Không có dữ liệu.\n"
        )

    # =====================
    # TOP GAIN
    # =====================

    message += "\n🚀 TOP TĂNG GIÁ\n"

    if not df_gain.empty:

        for i, row in enumerate(
            df_gain.itertuples(),
            1
        ):

            message += (
                f"{i}. "
                f"{row.Ticker} "
                f"| {row.Change}%\n"
            )

    else:

        message += (
            "Không có dữ liệu.\n"
        )

    return message


# =========================
# BUTTON SCAN
# =========================

async def scan(update: Update,
               context: ContextTypes.DEFAULT_TYPE):

    await update.message.reply_text(
        "⏳ Đang quét thị trường..."
    )

    message = build_stock_message()

    await update.message.reply_text(
        message
    )


# =========================
# AUTO SEND
# =========================

def auto_send_job(app):

    try:

        message = build_stock_message()

        app.bot.send_message(
            chat_id=CHAT_ID,
            text=message
        )

        print("Đã gửi auto 15h")

    except Exception as e:

        print(
            f"Auto send error: {e}"
        )


# =========================
# HISTORY
# =========================

async def history(update: Update,
                  context: ContextTypes.DEFAULT_TYPE):

    global history_df

    if history_df.empty:

        await update.message.reply_text(
            "Chưa có dữ liệu lịch sử."
        )

        return

    latest = history_df.tail(20)

    message = "📜 LỊCH SỬ GẦN NHẤT\n\n"

    for _, row in latest.iterrows():

        message += (
            f"{row['Date']} | "
            f"{row['Ticker']} | "
            f"{row['Type']}\n"
        )

    await update.message.reply_text(
        message
    )


# =========================
# MAIN
# =========================

def main():

    app = Application.builder().token(
        BOT_TOKEN
    ).build()

    # =====================
    # SCHEDULER
    # =====================

    scheduler = BackgroundScheduler()

    scheduler.add_job(
        lambda: auto_send_job(app),
        trigger='cron',
        hour=15,
        minute=0
    )

    scheduler.start()

    # =====================
    # HANDLER
    # =====================

    app.add_handler(
        CommandHandler(
            "start",
            start
        )
    )

    app.add_handler(
        MessageHandler(
            filters.Regex("^📈 Quét cổ phiếu$"),
            scan
        )
    )

    app.add_handler(
        MessageHandler(
            filters.Regex("^📜 Xem lịch sử$"),
            history
        )
    )

    print("BOT RUNNING...")

    app.run_polling()


# =========================
# RUN
# =========================

if __name__ == "__main__":
    main()