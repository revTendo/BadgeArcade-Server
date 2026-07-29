import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "shopdeck.settings")

_SOAP_PREFIXES = ("/ecs", "/cas", "/ias", "/ccs", "/assets")

class _Dispatcher:
    def __init__(self, flask_wsgi, django_wsgi):
        self.flask_wsgi = flask_wsgi
        self.django_wsgi = django_wsgi

    def __call__(self, environ, start_response):
        path = environ.get("PATH_INFO", "") or "/"
        if path.startswith(_SOAP_PREFIXES):
            return self.flask_wsgi(environ, start_response)
        return self.django_wsgi(environ, start_response)

def build_app():
    import logging

    try:
        import db_bootstrap
        db_bootstrap.ensure()
    except Exception:
        logging.getLogger("eshop").exception("Database bootstrap failed")

    from flask import Flask

    import ecs, ias, cas, cdn, assetcdn

    flask_app = Flask(
        "shopdeck_soap",
        template_folder=os.path.join(_HERE, "templates"),
    )
    flask_app.config["MAX_CONTENT_LENGTH"] = 64 * 1024 * 1024
    flask_app.secret_key = os.environ.get("ESHOP_SECRET_KEY") or os.urandom(32)

    flask_app.register_blueprint(ecs.ecs)
    flask_app.register_blueprint(ias.ias)
    flask_app.register_blueprint(cas.cas)
    flask_app.register_blueprint(cdn.ccs)
    flask_app.register_blueprint(assetcdn.cdn)

    @flask_app.after_request
    def _dbg_bodies(response):
        try:
            from flask import request as _rq
            import sys
            p = _rq.path
            if any(k in p for k in ("/samurai/", "/ninja/", "/ecs/", "/ias/", "/cas/")):
                body_in = _rq.get_data(as_text=True)[:800]
                ctype = response.headers.get("Content-Type", "")
                body_out = ""
                if any(t in ctype for t in ("json", "xml", "text")):
                    body_out = response.get_data(as_text=True)[:1800]
                sys.stderr.write(
                    "\n===DBG " + _rq.method + " " + p + "?" +
                    _rq.query_string.decode(errors="replace") + "\n" +
                    "---REQ " + body_in + "\n" +
                    "---RES[" + str(response.status_code) + " " + ctype + "] " + body_out + "\n===END\n"
                )
        except Exception as e:
            import sys; sys.stderr.write("[dbg err] " + str(e) + "\n")
        return response

    from django.core.wsgi import get_wsgi_application
    django_app = get_wsgi_application()

    flask_app.wsgi_app = _Dispatcher(flask_app.wsgi_app, django_app)
    return flask_app
