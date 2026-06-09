import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.timezone import localtime
from asgiref.sync import sync_to_async
from .models import TelegramUser, TelegramGroup, Expense


@sync_to_async
def _expense_list(group_id):
    from django.db.models import Sum
    qs = Expense.objects.filter(status=True).select_related('user', 'group')
    if group_id:
        qs = qs.filter(group__chat_id=group_id)
    qs = qs.order_by('-created_at')[:50]
    return [
        {
            'id': e.id,
            'amount': str(e.amount),
            'description': e.description,
            'user': e.user.full_name or e.user.username,
            'group': e.group.title if e.group else None,
            'created_at': localtime(e.created_at).strftime('%Y-%m-%d %H:%M'),
        }
        for e in qs
    ]


@sync_to_async
def _expense_create(telegram_id, amount, description, group_chat_id):
    user = TelegramUser.objects.filter(telegram_id=telegram_id).first()
    if not user:
        return None, 'Foydalanuvchi topilmadi'
    group = None
    if group_chat_id:
        group = TelegramGroup.objects.filter(chat_id=group_chat_id).first()
        if not group:
            return None, 'Guruh topilmadi'
    expense = Expense.objects.create(user=user, group=group, amount=amount, description=description)
    return {'id': expense.id, 'amount': str(expense.amount)}, None


@sync_to_async
def _expense_delete(expense_id):
    deleted, _ = Expense.objects.filter(id=expense_id).delete()
    return deleted


@sync_to_async
def _total(group_id):
    from django.db.models import Sum
    qs = Expense.objects.filter(status=True).select_related('user', 'group')
    if group_id:
        qs = qs.filter(group__chat_id=group_id)
    result = qs.aggregate(total=Sum('amount'))
    by_user = list(
        qs.values('user__full_name', 'user__username')
        .annotate(total=Sum('amount'))
        .order_by('-total')
    )
    return {
        'total': str(result['total'] or 0),
        'count': qs.count(),
        'by_user': [
            {'name': r['user__full_name'] or r['user__username'], 'total': str(r['total'])}
            for r in by_user
        ],
    }


@sync_to_async
def _clear(group_chat_id):
    qs = Expense.objects.filter(status=True)
    if group_chat_id:
        qs = qs.filter(group__chat_id=group_chat_id)
    return qs.update(status=False)


@csrf_exempt
async def expense_list(request):
    if request.method != 'GET':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    group_id = request.GET.get('group_id')
    data = await _expense_list(group_id)
    return JsonResponse({'expenses': data, 'count': len(data)})


@csrf_exempt
async def expense_create(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    try:
        body = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    telegram_id = body.get('telegram_id')
    amount = body.get('amount')
    if not telegram_id or not amount:
        return JsonResponse({'error': 'telegram_id va amount majburiy'}, status=400)
    try:
        amount = float(amount)
        if amount <= 0:
            raise ValueError
    except (ValueError, TypeError):
        return JsonResponse({'error': "amount noto'g'ri"}, status=400)

    data, error = await _expense_create(
        telegram_id, amount,
        body.get('description', ''),
        body.get('group_id'),
    )
    if error:
        return JsonResponse({'error': error}, status=404)
    return JsonResponse(data, status=201)


@csrf_exempt
async def expense_delete(request, expense_id):
    if request.method != 'DELETE':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    deleted = await _expense_delete(expense_id)
    if deleted:
        return JsonResponse({'deleted': expense_id})
    return JsonResponse({'error': 'Topilmadi'}, status=404)


@csrf_exempt
async def total(request):
    if request.method != 'GET':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    data = await _total(request.GET.get('group_id'))
    return JsonResponse(data)


@csrf_exempt
async def clear(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    try:
        body = json.loads(request.body or '{}')
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    updated = await _clear(body.get('group_id'))
    return JsonResponse({'cleared': updated})