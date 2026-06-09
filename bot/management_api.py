import io
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.core.management import call_command


def _run_command(command, *args, **kwargs):
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
@require_http_methods(['POST'])
def cmd_migrate(request):
    result = _run_command('migrate')
    return JsonResponse(result)


@csrf_exempt
@require_http_methods(['POST'])
def cmd_setwebhook(request):
    result = _run_command('setwebhook')
    return JsonResponse(result)


@csrf_exempt
@require_http_methods(['POST'])
def cmd_delete_webhook(request):
    result = _run_command('setwebhook', delete=True)
    return JsonResponse(result)


@csrf_exempt
@require_http_methods(['POST'])
def cmd_createsu(request):
    result = _run_command('createsu')
    return JsonResponse(result)


@csrf_exempt
@require_http_methods(['POST'])
def cmd_collectstatic(request):
    result = _run_command('collectstatic', interactive=False)
    return JsonResponse(result)
