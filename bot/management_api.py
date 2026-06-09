import io
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.core.management import call_command
from asgiref.sync import sync_to_async


@sync_to_async
def _run(command, *args, **kwargs):
    stdout = io.StringIO()
    stderr = io.StringIO()
    try:
        call_command(command, *args, stdout=stdout, stderr=stderr, **kwargs)
        return {
            'success': True,
            'output': stdout.getvalue().strip(),
            'error': stderr.getvalue().strip() or None,
        }
    except Exception as e:
        return {
            'success': False,
            'output': stdout.getvalue().strip(),
            'error': str(e),
        }


@csrf_exempt
async def cmd_migrate(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    return JsonResponse(await _run('migrate'))


@csrf_exempt
async def cmd_setwebhook(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    return JsonResponse(await _run('setwebhook'))


@csrf_exempt
async def cmd_delete_webhook(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    return JsonResponse(await _run('setwebhook', delete=True))


@csrf_exempt
async def cmd_createsu(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    return JsonResponse(await _run('createsu'))


@csrf_exempt
async def cmd_collectstatic(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    return JsonResponse(await _run('collectstatic', interactive=False))
