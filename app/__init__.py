"""Creates the Flask application (application factory, so tests can build their own copy)."""
import os

from flask import Flask, redirect, url_for


def create_app(test_config=None):
    app = Flask(__name__)
    app.config.from_object("config")
    if test_config:
        app.config.update(test_config)

    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
    os.makedirs(os.path.join(app.static_folder, "images", "vehicles"), exist_ok=True)

    from . import db
    db.init_app(app)

    # One blueprint per module. Billing has no routes; booking calls its function directly.
    from .auth.routes import bp as auth_bp
    from .inventory.routes import bp as inventory_bp
    from .booking.routes import bp as booking_bp
    app.register_blueprint(auth_bp)
    app.register_blueprint(inventory_bp)
    app.register_blueprint(booking_bp)

    from .auth.service import current_user

    @app.context_processor
    def add_user_to_templates():
        return {"user": current_user()}        # used by the nav bar in base.html

    @app.template_filter("money")
    def money(value):
        return "R{:,.2f}".format(float(value or 0))

    @app.template_filter("status_label")
    def status_label(status):
        if status == "Maintenance":
            return "Under maintenance"
        return status

    @app.template_filter("image_url")
    def image_url(filename):
        if not filename:
            filename = "placeholder.svg"
        return url_for("static", filename="images/vehicles/" + filename)

    @app.route("/")
    def index():
        return redirect(url_for("inventory.vehicles"))

    return app
