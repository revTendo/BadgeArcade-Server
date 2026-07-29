'''
General purpose Middleware for both the eShop & Web UI servers
'''
from shopdeck import settings
from django.http import JsonResponse, HttpResponse, HttpResponseRedirect

class ShopMiddleware(object):
	def __init__(self, get_response):
		self.get_response = get_response

	def __call__(self, request):
		if settings.IN_MAINTENANCE:
			if request.path.startswith("/ninja/ws") or request.path.startswith("/samurai/ws"):
				return JsonResponse({"error": {"code": "6516", "message": settings.MAINTENANCE_MSG}}, status=400)
			else:
				return HttpResponse("Maintenance is in progress. Please come back later.", status=503)
		if not request.path.startswith("/admin") and request.user.is_authenticated and request.user.linked_ds == None:
			return HttpResponse("Your account is misconfigured. Contact an admin. It is not currently usable.")
		if request.user.is_authenticated and request.user.linked_ds != None:
			if request.user.linked_ds.is_terminated:
				return HttpResponse("Your account has been terminated.")
		if not request.user.is_authenticated and not request.path.startswith("/ninja") and not request.path.startswith("/samurai") and not request.path.startswith("/login") and not request.path.startswith("/signup") and not request.path == "/":
			return HttpResponseRedirect("/")
		response = self.get_response(request)
		return response

import sys as _dbg_sys

class DebugBodyMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        body_in = ""
        try:
            body_in = request.body.decode("utf-8", "replace")[:800]
        except Exception:
            pass
        response = self.get_response(request)
        try:
            ct = response.get("Content-Type", "")
            out = ""
            if hasattr(response, "content") and any(t in ct for t in ("json", "xml", "text")):
                out = response.content.decode("utf-8", "replace")[:2000]
            _dbg_sys.stderr.write(
                "\n===DBG " + request.method + " " + request.path + "?" +
                request.META.get("QUERY_STRING", "") + "\n" +
                "---REQ " + body_in + "\n" +
                "---RES[" + str(response.status_code) + " " + ct + "] " + out + "\n===END\n"
            )
            _dbg_sys.stderr.flush()
        except Exception as e:
            _dbg_sys.stderr.write("[dbg mw err] " + str(e) + "\n")
        return response
