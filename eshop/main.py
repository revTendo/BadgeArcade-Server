print("Shopdeck Server - SOAP XML Services\n\nBy Let's Shop Team 2024")
print("----------------------------------")

import os
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "shopdeck.settings")

try:
    import db_bootstrap
    db_bootstrap.ensure()
except Exception:
    import logging
    logging.getLogger("shopdeck").exception("Database bootstrap failed")

from flask import Flask
import ecs, ias, cas, cdn, assetcdn

app = Flask(__name__)
app.register_blueprint(ecs.ecs)
app.register_blueprint(ias.ias)
app.register_blueprint(cas.cas)
app.register_blueprint(cdn.ccs)
app.register_blueprint(assetcdn.cdn)

print("READY!")

if __name__ == "__main__":
    app.run(host=os.environ.get("SOAP_HOST", "0.0.0.0"), port=int(os.environ.get("SOAP_PORT", "8724")))
