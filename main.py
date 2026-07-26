import os
import logging
from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command, CommandStart
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.exceptions import TelegramBadRequest

# ---------- تنظیمات لاگ ----------
logging.basicConfig(level=logging.INFO)

# ---------- دریافت تنظیمات از متغیرهای محیطی ----------
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")
CHANNEL_LINK = os.getenv("CHANNEL_LINK")

if not BOT_TOKEN or not CHANNEL_ID:
    raise ValueError("BOT_TOKEN و CHANNEL_ID باید در Environment Variables تنظیم شوند!")

# ---------- ربات و دیسپچر ----------
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# ---------- وضعیت‌های کاربر (FSM) ----------
class UserState(StatesGroup):
    waiting_anonymous = State()
    waiting_identified = State()

# ---------- کیبوردها ----------
def join_channel_keyboard():
    """کیبورد بررسی عضویت"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📢 عضویت در کانال", url=CHANNEL_LINK or "https://t.me/telegram")],
        [InlineKeyboardButton(text="✅ عضو شدم، بررسی کن", callback_data="check_join")]
    ])

def main_menu_keyboard():
    """منوی اصلی بعد از عضویت"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎭 ارسال پیام ناشناس", callback_data="send_anon")],
        [InlineKeyboardButton(text="👤 ارسال پیام با شناسه", callback_data="send_id")],
        [InlineKeyboardButton(text="📜 قوانین", callback_data="rules")],
    ])

def back_to_menu_keyboard():
    """دکمه بازگشت به منو"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 بازگشت به منو", callback_data="back_menu")]
    ])

# ---------- هندلر /start ----------
@dp.message(CommandStart())
async def cmd_start(message: Message):
    """بررسی عضویت کاربر در کانال"""
    user_id = message.from_user.id
    
    try:
        member = await bot.get_chat_member(CHANNEL_ID, user_id)
        if member.status in ["member", "administrator", "creator"]:
            await message.answer(
                "سلام! به ربات اعترافات خوش اومدی.\n\n"
                "از منوی زیر یکی رو انتخاب کن:",
                reply_markup=main_menu_keyboard()
            )
        else:
            await message.answer(
                "⚠️ برای استفاده از ربات، ابتدا باید در کانال اصلی عضو بشی.",
                reply_markup=join_channel_keyboard()
            )
    except TelegramBadRequest:
        await message.answer(
            "⚠️ برای استفاده از ربات، ابتدا باید در کانال اصلی عضو بشی.",
            reply_markup=join_channel_keyboard()
        )

# ---------- بررسی عضویت (کالبک) ----------
@dp.callback_query(F.data == "check_join")
async def check_join(callback: CallbackQuery):
    user_id = callback.from_user.id
    try:
        member = await bot.get_chat_member(CHANNEL_ID, user_id)
        if member.status in ["member", "administrator", "creator"]:
            await callback.message.edit_text(
                "✅ عضویت تایید شد!\n\n"
                "خوش اومدی! از منوی زیر یکی رو انتخاب کن:",
                reply_markup=main_menu_keyboard()
            )
        else:
            await callback.answer("❌ هنوز عضو نشدی!", show_alert=True)
    except TelegramBadRequest:
        await callback.answer("❌ هنوز عضو کانال نیستی!", show_alert=True)

# ---------- پیام ناشناس ----------
@dp.callback_query(F.data == "send_anon")
async def start_anonymous(callback: CallbackQuery, state: FSMContext):
    await state.set_state(UserState.waiting_anonymous)
    await callback.message.edit_text(
        "🎭 حالت پیام ناشناس فعال شد.\n\n"
        "متنت رو بفرست (بدون نام و آیدی تو در کانال منتشر میشه):\n\n"
        "⚠️ برای انصراف دکمه پایین رو بزن.",
        reply_markup=back_to_menu_keyboard()
    )

# ---------- پیام با شناسه ----------
@dp.callback_query(F.data == "send_id")
async def start_identified(callback: CallbackQuery, state: FSMContext):
    await state.set_state(UserState.waiting_identified)
    await callback.message.edit_text(
        "👤 حالت پیام با شناسه فعال شد.\n\n"
        "📝 متنت رو بفرست (با نام و آیدی تو در کانال منتشر میشه):\n\n"
        "⚠️ برای انصراف دکمه پایین رو بزن.",
        reply_markup=back_to_menu_keyboard()
    )

# ---------- دریافت متن پیام ناشناس ----------
@dp.message(UserState.waiting_anonymous)
async def receive_anonymous(message: Message, state: FSMContext):
    if not message.text:
        await message.answer("❌ فقط متن می‌تونم دریافت کنم.")
        return
    
    try:
        await bot.send_message(
            chat_id=CHANNEL_ID,
            text=f"🎭 <b>پیام ناشناس:</b>\n\n{message.text}",
            parse_mode="HTML"
        )
        await message.answer(
            "✅ پیام ناشناس تو با موفقیت ارسال شد!\n\n"
            "📬 به زودی در کانال منتشر میشه.",
            reply_markup=main_menu_keyboard()
        )
    except Exception as e:
        await message.answer(f"❌ خطا در ارسال: {e}")
    
    await state.clear()

# ---------- دریافت متن پیام با شناسه ----------
@dp.message(UserState.waiting_identified)
async def receive_identified(message: Message, state: FSMContext):
    if not message.text:
        await message.answer("❌ فقط متن می‌تونم دریافت کنم.")
        return
    
    user = message.from_user
    username = f"@{user.username}" if user.username else ""
    full_name = user.full_name or "کاربر ناشناس"
    signature = f"\n\n— {full_name} {username}"
    
    try:
        await bot.send_message(
            chat_id=CHANNEL_ID,
            text=f"👤 <b>پیام با شناسه:</b>\n\n{message.text}{signature}",
            parse_mode="HTML"
        )
        await message.answer(
            "✅ پیام تو با شناسه ارسال شد!\n\n"
            "📬 به زودی در کانال منتشر میشه.",
            reply_markup=main_menu_keyboard()
        )
    except Exception as e:
        await message.answer(f"❌ خطا در ارسال: {e}")
    
    await state.clear()

# ---------- قوانین ----------
@dp.callback_query(F.data == "rules")
async def show_rules(callback: CallbackQuery):
    rules_text = (
        "<b>📜 قوانین ارسال پیام:</b>\n\n"
        "1️⃣ محتوای توهین‌آمیز و فحاشی ممنوع ❌\n"
        "2️⃣ انتشار اطلاعات شخصی دیگران ممنوع ❌\n"
        "3️⃣ محتوای سیاسی و مذهبی تند ممنوع ❌\n"
        "4️⃣ پیام‌های تبلیغاتی ممنوع ❌\n"
        "5️⃣ رعایت ادب و احترام الزامی است ✅\n\n"
        "⚠️ پیام‌های خلاف قوانین منتشر نخواهند شد."
    )
    await callback.message.edit_text(
        rules_text,
        parse_mode="HTML",
        reply_markup=back_to_menu_keyboard()
    )

# ---------- بازگشت به منو ----------
@dp.callback_query(F.data == "back_menu")
async def back_menu(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text(
        "از منوی زیر یکی رو انتخاب کن:",
        reply_markup=main_menu_keyboard()
    )

# ---------- اجرای ربات ----------
async def main():
    logging.info("ربات در حال اجراست...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
