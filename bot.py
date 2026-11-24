import os
import re
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from asgiref.sync import sync_to_async
from django.conf import settings
from telegram import KeyboardButton, ReplyKeyboardMarkup, ReplyKeyboardRemove, Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

from appeals.models import EmployeAppleas
from monitor.models import Branches

FULL_NAME, PHONE, POSITION, BRANCH = range(4)


def normalize_phone(value):
    digits = re.sub(r"\D", "", value or "")
    if len(digits) == 9:
        digits = "998" + digits
    if len(digits) == 12 and digits.startswith("998"):
        return digits
    return digits


def employee_by_telegram(telegram_id):
    return EmployeAppleas.objects.filter(telegram_id=telegram_id).first()


def phone_taken(number):
    return EmployeAppleas.objects.filter(phone=number).exists()


def branch_names():
    return list(
        Branches.objects.exclude(name="")
        .exclude(name__isnull=True)
        .order_by("name")
        .values_list("name", flat=True)
    )


def find_branch(name):
    return (
        Branches.objects.filter(name__iexact=name).first()
        or Branches.objects.filter(name__icontains=name).first()
    )


def register_employee(full_name, phone, position, branch, telegram_id):
    return EmployeAppleas.objects.create(
        full_name=full_name,
        phone=phone,
        position=position,
        branch=branch,
        telegram_id=telegram_id,
    )


def branch_keyboard(names):
    if not names:
        return ReplyKeyboardRemove()
    rows = [[name] for name in names]
    return ReplyKeyboardMarkup(rows, resize_keyboard=True, one_time_keyboard=True)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    employee = await sync_to_async(employee_by_telegram)(user.id)
    if employee:
        await update.message.reply_text(
            f"Siz allaqachon ro‘yxatdan o‘tgansiz.\n"
            f"F.I.Sh.: {employee.full_name}\n"
            f"Telefon: {employee.phone}"
        )
        return ConversationHandler.END

    await update.message.reply_text("Xodim sifatida ro‘yxatdan o‘ting.\nF.I.Sh.ingizni yozing:")
    return FULL_NAME


async def full_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    name = (update.message.text or "").strip()
    if len(name) < 3:
        await update.message.reply_text("F.I.Sh.ni to‘liq yozing.")
        return FULL_NAME
    context.user_data["full_name"] = name
    keyboard = ReplyKeyboardMarkup(
        [[KeyboardButton("Telefon raqamni yuborish", request_contact=True)]],
        resize_keyboard=True,
        one_time_keyboard=True,
    )
    await update.message.reply_text(
        "Telefon raqamingizni yuboring yoki kontaktni ulashing.",
        reply_markup=keyboard,
    )
    return PHONE


async def phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    contact = update.message.contact
    raw = contact.phone_number if contact else (update.message.text or "")
    number = normalize_phone(raw)
    if len(number) < 9:
        await update.message.reply_text("Telefon raqam noto‘g‘ri. Qayta yuboring.")
        return PHONE

    if await sync_to_async(phone_taken)(number):
        await update.message.reply_text(
            "Bu telefon raqam bilan allaqachon ro‘yxatdan o‘tilgan. Bitta raqam — bir marta.",
            reply_markup=ReplyKeyboardRemove(),
        )
        return ConversationHandler.END

    context.user_data["phone"] = number
    await update.message.reply_text("Lavozimingizni yozing:", reply_markup=ReplyKeyboardRemove())
    return POSITION


async def position(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (update.message.text or "").strip()
    if len(text) < 2:
        await update.message.reply_text("Lavozimni yozing.")
        return POSITION
    context.user_data["position"] = text
    names = await sync_to_async(branch_names)()
    keyboard = branch_keyboard(names)
    if isinstance(keyboard, ReplyKeyboardRemove):
        await update.message.reply_text("Bo‘lim topilmadi. Bo‘lim nomini yozing.")
    else:
        await update.message.reply_text("Bo‘limni tanlang:", reply_markup=keyboard)
    return BRANCH


async def branch(update: Update, context: ContextTypes.DEFAULT_TYPE):
    name = (update.message.text or "").strip()
    found = await sync_to_async(find_branch)(name)
    if not found:
        await update.message.reply_text("Bo‘lim topilmadi. Ro‘yxatdan tanlang yoki to‘g‘ri nom yozing.")
        return BRANCH

    telegram_id = update.effective_user.id
    if await sync_to_async(employee_by_telegram)(telegram_id):
        await update.message.reply_text("Siz allaqachon ro‘yxatdan o‘tgansiz.", reply_markup=ReplyKeyboardRemove())
        return ConversationHandler.END

    phone = context.user_data.get("phone")
    if await sync_to_async(phone_taken)(phone):
        await update.message.reply_text(
            "Bu telefon raqam bilan allaqachon ro‘yxatdan o‘tilgan.",
            reply_markup=ReplyKeyboardRemove(),
        )
        return ConversationHandler.END

    employee = await sync_to_async(register_employee)(
        context.user_data.get("full_name") or "",
        phone,
        context.user_data.get("position") or "",
        found,
        telegram_id,
    )
    await update.message.reply_text(
        f"Ro‘yxatdan o‘tdingiz.\n"
        f"F.I.Sh.: {employee.full_name}\n"
        f"Telefon: {employee.phone}\n"
        f"Lavozim: {employee.position}\n"
        f"Bo‘lim: {found.name}",
        reply_markup=ReplyKeyboardRemove(),
    )
    context.user_data.clear()
    return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text("Bekor qilindi.", reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END


def main():
    token = os.environ.get("TELEGRAM_BOT_TOKEN") or getattr(settings, "TELEGRAM_BOT_TOKEN", "")
    if not token:
        raise SystemExit("TELEGRAM_BOT_TOKEN topilmadi")

    application = Application.builder().token(token).build()
    application.add_handler(
        ConversationHandler(
            entry_points=[CommandHandler("start", start)],
            states={
                FULL_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, full_name)],
                PHONE: [
                    MessageHandler(filters.CONTACT, phone),
                    MessageHandler(filters.TEXT & ~filters.COMMAND, phone),
                ],
                POSITION: [MessageHandler(filters.TEXT & ~filters.COMMAND, position)],
                BRANCH: [MessageHandler(filters.TEXT & ~filters.COMMAND, branch)],
            },
            fallbacks=[CommandHandler("cancel", cancel)],
        )
    )
    application.run_polling()


if __name__ == "__main__":
    main()
