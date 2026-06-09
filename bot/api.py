import json
from django.http import JsonResponse
from django.utils.timezone import localtime
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.db.models import Sum
from .models import TelegramUser, TelegramGroup, Expense


def _get_qs(request):
    """group_id query param bo'lsa shu guruh, bo'lmasa hamma."""
    group_id = request.GET.get('group_id') or (
        request.POST.get('group_id') if request.method == 'POST'
        else json.loads(request.body or '{}').get('group_id')
    )
    qs = Expense.objects.filter(status=True).select_related('user', 'group')
    if group_id:
        qs = qs.filter(group__chat_id=group_id)
    return qs


@csrf_exempt
@require_http_methods(['GET'])
def expense_list(request):
    qs = _get_qs(request).order_by('-created_at')[:50]
    data = [
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
    return JsonResponse({'expenses': data, 'count': len(data)})


@csrf_exempt
@require_http_methods(['POST'])
def expense_create(request):
    try:
        body = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    telegram_id = body.get('telegram_id')
    amount = body.get('amount')
    description = body.get('description', '')
    group_chat_id = body.get('group_id')

    if not telegram_id or not amount:
        return JsonResponse({'error': 'telegram_id va amount majburiy'}, status=400)

    try:
        amount = float(amount)
        if amount <= 0:
            raise ValueError
    except (ValueError, TypeError):
        return JsonResponse({'error': 'amount noto\'g\'ri'}, status=400)

    user = TelegramUser.objects.filter(telegram_id=telegram_id).first()
    if not user:
        return JsonResponse({'error': 'Foydalanuvchi topilmadi'}, status=404)

    group = None
    if group_chat_id:
        group = TelegramGroup.objects.filter(chat_id=group_chat_id).first()
        if not group:
            return JsonResponse({'error': 'Guruh topilmadi'}, status=404)

    expense = Expense.objects.create(
        user=user, group=group, amount=amount, description=description
    )
    return JsonResponse({'id': expense.id, 'amount': str(expense.amount)}, status=201)


@csrf_exempt
@require_http_methods(['DELETE'])
def expense_delete(request, expense_id):
    deleted, _ = Expense.objects.filter(id=expense_id).delete()
    if deleted:
        return JsonResponse({'deleted': expense_id})
    return JsonResponse({'error': 'Topilmadi'}, status=404)


@csrf_exempt
@require_http_methods(['GET'])
def total(request):
    qs = _get_qs(request)
    result = qs.aggregate(total=Sum('amount'))
    count = qs.count()

    by_user = list(
        qs.values('user__full_name', 'user__username')
        .annotate(total=Sum('amount'))
        .order_by('-total')
    )

    return JsonResponse({
        'total': str(result['total'] or 0),
        'count': count,
        'by_user': [
            {
                'name': r['user__full_name'] or r['user__username'],
                'total': str(r['total']),
            }
            for r in by_user
        ],
    })


@csrf_exempt
@require_http_methods(['POST'])
def clear(request):
    try:
        body = json.loads(request.body or '{}')
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    group_chat_id = body.get('group_id')
    qs = Expense.objects.filter(status=True)
    if group_chat_id:
        qs = qs.filter(group__chat_id=group_chat_id)

    updated = qs.update(status=False)
    return JsonResponse({'cleared': updated})
