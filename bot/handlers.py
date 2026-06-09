from decimal import Decimal, InvalidOperation
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    CallbackQueryHandler, filters, ContextTypes,
)
from django.conf import settings
from django.utils.timezone import localtime
from asgiref.sync import sync_to_async
from .models import TelegramUser, TelegramGroup, Expense


def _is_group(chat) -> bool:
    return chat.type in ('group', 'supergroup')

@sync_to_async
def _get_or_create_user(tg_user) -> TelegramUser:
    user, _ = TelegramUser.objects.get_or_create(
        telegram_id=tg_user.id,
        defaults={'username': tg_user.username or '', 'full_name': tg_user.full_name}
    )
    return user


@sync_to_async
def _get_or_create_group(chat) -> TelegramGroup:
    group, _ = TelegramGroup.objects.get_or_create(
        chat_id=chat.id,
        defaults={'title': chat.title or str(chat.id)}
    )
    return group


@sync_to_async
def _create_expense(tg_user, amount, description, group=None):
    user, _ = TelegramUser.objects.get_or_create(
        telegram_id=tg_user.id,
        defaults={'username': tg_user.username or '', 'full_name': tg_user.full_name}
    )
    return Expense.objects.create(
        user=user, group=group, amount=amount, description=description,
    ).id


@sync_to_async
def _get_expenses(tg_user, group=None):
    if group:
        qs = Expense.objects.filter(group=group, status=True)
    else:
        qs = Expense.objects.filter(user__telegram_id=tg_user.id, group__isnull=True, status=True)
    return list(qs.select_related('user').order_by('-created_at')[:10])


@sync_to_async
def _get_total(tg_user, group=None):
    from django.db.models import Sum
    if group:
        qs = Expense.objects.filter(group=group, status=True)
        grand = qs.aggregate(total=Sum('amount'))['total'] or 0
        count = qs.count()
        by_user = list(
            qs.values('user__full_name', 'user__username')
            .annotate(total=Sum('amount'))
            .order_by('-total')
        )
        return grand, count, by_user
    else:
        qs = Expense.objects.filter(user__telegram_id=tg_user.id, group__isnull=True, status=True)
        total = qs.aggregate(total=Sum('amount'))['total'] or 0
        return total, qs.count(), None


@sync_to_async
def _delete_expense(tg_user, expense_id, group=None):
    if group:
        deleted, _ = Expense.objects.filter(
            id=expense_id, group=group, user__telegram_id=tg_user.id
        ).delete()
    else:
        deleted, _ = Expense.objects.filter(
            id=expense_id, user__telegram_id=tg_user.id, group__isnull=True
        ).delete()
    return deleted


@sync_to_async
def _count_active(tg_user, group=None):
    if group:
        return Expense.objects.filter(group=group, status=True).count()
    return Expense.objects.filter(user__telegram_id=tg_user.id, group__isnull=True, status=True).count()


@sync_to_async
def _deactivate_all(tg_user, group=None):
    if group:
        return Expense.objects.filter(group=group, status=True).update(status=False)
    return Expense.objects.filter(user__telegram_id=tg_user.id, group__isnull=True, status=True).update(status=False)


@sync_to_async
def _get_my_expenses(tg_user, group=None):
    from django.db.models import Sum
    if group:
        qs = Expense.objects.filter(user__telegram_id=tg_user.id, group=group, status=True)
    else:
        qs = Expense.objects.filter(user__telegram_id=tg_user.id, status=True)
    qs = qs.select_related('group').order_by('-created_at')
    expenses = list(qs)
    total = qs.aggregate(total=Sum('amount'))['total'] or 0
    return expenses, total


async def _resolve_group(update: Update):
    chat = update.effective_chat
    if _is_group(chat):
        return await _get_or_create_group(chat)
    return None


# ── Handlers ──────────────────────────────────────────────────────────────────

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    tg_user = update.effective_user
    await _get_or_create_user(tg_user)
    await update.message.reply_text(
        f"Assalomu alaykum, {tg_user.first_name}! 👋\n\n"
        "Men xarajatlaringizni kuzatib boruvchi botman.\n\n"
        "📌 Buyruqlar:\n"
        "/add <summa> [izoh] — xarajat qo'shish\n"
        "/list — oxirgi 10 ta xarajat\n"
        "/total — jami xarajat\n"
        "/myexpenses — mening barcha xarajatlarim\n"
        "/delete <id> — xarajatni o'chirish\n"
        "/clear — barcha faol xarajatlarni o'chirish\n"
        "/help — yordam\n\n"
        "Guruhda: #harajat <summa> [izoh]"
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📌 Buyruqlar:\n\n"
        "/add <summa> [izoh] — xarajat qo'shish\n"
        "  Misol: /add 50000\n"
        "  Misol: /add 50000 tushlik uchun\n\n"
        "/list — oxirgi 10 ta xarajat\n"
        "/total — jami xarajat summasi\n"
        "/myexpenses — mening barcha xarajatlarim\n"
        "/delete <id> — xarajatni o'chirish\n"
        "/clear — barcha faol xarajatlarni o'chirish\n\n"
        "Guruhda:\n"
        "#harajat <summa> [izoh]\n"
        "  Misol: #harajat 50000 tushlik"
    )


async def add_expense(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args
    if not args:
        await update.message.reply_text("Format: /add 50000 [izoh]")
        return

    try:
        amount = Decimal(args[0].replace(',', '.'))
    except InvalidOperation:
        await update.message.reply_text("Summa noto'g'ri. Misol: /add 50000")
        return

    if amount <= 0:
        await update.message.reply_text("Summa 0 dan katta bo'lishi kerak.")
        return

    description = ' '.join(args[1:]) if len(args) > 1 else ''
    group = await _resolve_group(update)

    expense_id = await _create_expense(update.effective_user, amount, description, group)
    await update.message.reply_text(
        f"✅ Xarajat qo'shildi!\n"
        f"🆔 ID: {expense_id}\n"
        f"💰 {amount:,.0f} so'm"
        + (f" — {description}" if description else "")
    )


async def list_expenses(update: Update, context: ContextTypes.DEFAULT_TYPE):
    group = await _resolve_group(update)
    expenses = await _get_expenses(update.effective_user, group)

    if not expenses:
        await update.message.reply_text("Hali xarajat yo'q.")
        return

    title = f"📋 {update.effective_chat.title} — oxirgi xarajatlar:\n" if group else "📋 Oxirgi xarajatlar:\n"
    lines = [title]
    for e in expenses:
        desc = f" — {e.description}" if e.description else ''
        date = localtime(e.created_at).strftime('%d.%m %H:%M')
        who = f" [{e.user.full_name or e.user.username}]" if group else ''
        lines.append(f"#{e.id} | {e.amount:,.0f} so'm{desc}{who} | {date}")

    await update.message.reply_text('\n'.join(lines))


async def total_expenses(update: Update, context: ContextTypes.DEFAULT_TYPE):
    group = await _resolve_group(update)
    total, count, by_user = await _get_total(update.effective_user, group)

    if group:
        lines = [f"💵 {update.effective_chat.title} — jami xarajat:\n"]
        for row in by_user:
            name = row['user__full_name'] or row['user__username'] or '—'
            lines.append(f"👤 {name}: {row['total']:,.0f} so'm")
        lines.append(f"\n📊 Jami: {total:,.0f} so'm ({count} ta)")
        await update.message.reply_text('\n'.join(lines))
    else:
        await update.message.reply_text(
            f"💵 Jami xarajat: {total:,.0f} so'm\n"
            f"📊 Xarajatlar soni: {count} ta"
        )


async def delete_expense(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args
    if not args:
        await update.message.reply_text("ID kiriting. Misol: /delete 5")
        return

    try:
        expense_id = int(args[0])
    except ValueError:
        await update.message.reply_text("ID raqam bo'lishi kerak.")
        return

    group = await _resolve_group(update)
    deleted = await _delete_expense(update.effective_user, expense_id, group)
    if deleted:
        await update.message.reply_text(f"🗑 #{expense_id} xarajat o'chirildi.")
    else:
        await update.message.reply_text(f"#{expense_id} topilmadi yoki siz qo'shmagansiz.")


async def clear_expenses(update: Update, context: ContextTypes.DEFAULT_TYPE):
    group = await _resolve_group(update)
    count = await _count_active(update.effective_user, group)

    if count == 0:
        await update.message.reply_text("Faol xarajatlar yo'q.")
        return

    label = update.effective_chat.title if group else "sizning"
    keyboard = InlineKeyboardMarkup([[
        InlineKeyboardButton("✅ Ha, o'chirish", callback_data="clear_confirm"),
        InlineKeyboardButton("❌ Bekor qilish", callback_data="clear_cancel"),
    ]])
    await update.message.reply_text(
        f"⚠️ {label} — {count} ta faol xarajat o'chirilsinmi?",
        reply_markup=keyboard,
    )


async def clear_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "clear_confirm":
        group = await _resolve_group(update)
        updated = await _deactivate_all(query.from_user, group)
        await query.edit_message_text(f"✅ {updated} ta xarajat o'chirildi.")
    else:
        await query.edit_message_text("❌ Bekor qilindi.")


async def hashtag_expense(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text or ''
    after = text.split('#harajat', 1)[1].strip()
    parts = after.split()

    if not parts:
        await update.message.reply_text(
            "Format: #harajat <summa> [izoh]\nMisol: #harajat 50000 tushlik uchun"
        )
        return

    try:
        amount = Decimal(parts[0].replace(',', '.'))
    except InvalidOperation:
        await update.message.reply_text("Summa noto'g'ri. Misol: #harajat 50000 tushlik")
        return

    if amount <= 0:
        await update.message.reply_text("Summa 0 dan katta bo'lishi kerak.")
        return

    description = ' '.join(parts[1:]) if len(parts) > 1 else ''
    group = await _resolve_group(update)

    expense_id = await _create_expense(update.effective_user, amount, description, group)
    sender = update.effective_user.first_name
    await update.message.reply_text(
        f"✅ {sender} xarajat qo'shdi!\n"
        f"🆔 ID: {expense_id}\n"
        f"💰 {amount:,.0f} so'm"
        + (f" — {description}" if description else "")
    )


async def my_expenses(update: Update, context: ContextTypes.DEFAULT_TYPE):
    group = await _resolve_group(update)
    expenses, total = await _get_my_expenses(update.effective_user, group)

    if not expenses:
        await update.message.reply_text("Sizning faol xarajatlaringiz yo'q.")
        return

    if group:
        header = f"📋 {update.effective_chat.title} — mening xarajatlarim ({len(expenses)} ta):\n"
    else:
        header = f"📋 Mening barcha xarajatlarim ({len(expenses)} ta):\n"

    lines = [header]
    for e in expenses:
        desc = f"  📝 {e.description}" if e.description else ''
        date = localtime(e.created_at).strftime('%d.%m.%Y %H:%M')
        group_label = '' if group else (f"  🏠 {e.group.title}" if e.group else '  💬 Shaxsiy')
        lines.append(f"#{e.id} | {e.amount:,.0f} so'm\n  📅 {date}{group_label}{desc}")

    lines.append(f"\n💵 Jami: {total:,.0f} so'm")

    text = '\n'.join(lines)
    for i in range(0, len(text), 4000):
        await update.message.reply_text(text[i:i + 4000])


async def unknown_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Noma'lum buyruq. /help — yordam.")


def build_application():
    app = Application.builder().token(settings.BOT_TOKEN).build()

    app.add_handler(CommandHandler('start', start))
    app.add_handler(CommandHandler('help', help_command))
    app.add_handler(CommandHandler('add', add_expense))
    app.add_handler(CommandHandler('list', list_expenses))
    app.add_handler(CommandHandler('total', total_expenses))
    app.add_handler(CommandHandler('myexpenses', my_expenses))
    app.add_handler(CommandHandler('delete', delete_expense))
    app.add_handler(CommandHandler('clear', clear_expenses))
    app.add_handler(CallbackQueryHandler(clear_callback, pattern="^clear_"))
    app.add_handler(MessageHandler(
        filters.TEXT & filters.Regex(r'(?i)#harajat') & (~filters.COMMAND),
        hashtag_expense,
    ))
    app.add_handler(MessageHandler(filters.COMMAND, unknown_command))

    return app
