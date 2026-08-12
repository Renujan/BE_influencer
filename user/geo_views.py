import json
import urllib.request
import urllib.parse
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Content-Type': 'application/json'
}

@csrf_exempt
@require_http_methods(["GET"])
def external_countries(request):
    """
    Returns list of external countries with ISO codes, dial codes, currency.
    """
    try:
        req = urllib.request.Request('https://countriesnow.space/api/v0.1/countries/codes', headers=HEADERS)
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            items = data.get('data', [])
            return JsonResponse({'data': items, 'status': 200}, status=200)
    except Exception as e:
        return JsonResponse({'error': str(e), 'status': 500}, status=500)

@csrf_exempt
@require_http_methods(["GET"])
def currency(request, country_name):
    """
    Returns currency for given country_name.
    """
    country_name = urllib.parse.unquote(country_name).strip()
    try:
        req = urllib.request.Request(
            'https://countriesnow.space/api/v0.1/countries/currency',
            data=json.dumps({'country': country_name}).encode('utf-8'),
            headers=HEADERS
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            res_data = json.loads(resp.read().decode('utf-8'))
            return JsonResponse(res_data, status=200)
    except Exception as e:
        return JsonResponse({'error': str(e), 'status': 500}, status=500)

@csrf_exempt
@require_http_methods(["GET"])
def states(request, country_name):
    """
    Returns states/provinces for given country_name.
    """
    country_name = urllib.parse.unquote(country_name).strip()
    try:
        req = urllib.request.Request(
            'https://countriesnow.space/api/v0.1/countries/states',
            data=json.dumps({'country': country_name}).encode('utf-8'),
            headers=HEADERS
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            res_data = json.loads(resp.read().decode('utf-8'))
            return JsonResponse(res_data, status=200)
    except Exception as e:
        return JsonResponse({'error': str(e), 'status': 500}, status=500)

@csrf_exempt
@require_http_methods(["GET"])
def cities(request, country_name, state_name):
    """
    Returns cities/districts for given country_name and state_name.
    """
    country_name = urllib.parse.unquote(country_name).strip()
    state_name = urllib.parse.unquote(state_name).strip()
    try:
        req = urllib.request.Request(
            'https://countriesnow.space/api/v0.1/countries/state/cities',
            data=json.dumps({'country': country_name, 'state': state_name}).encode('utf-8'),
            headers=HEADERS
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            res_data = json.loads(resp.read().decode('utf-8'))
            return JsonResponse(res_data, status=200)
    except Exception as e:
        return JsonResponse({'error': str(e), 'status': 500}, status=500)
