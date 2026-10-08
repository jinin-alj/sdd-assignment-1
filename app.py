from flask import Flask, jsonify
import config


def create_app() -> Flask:
    app = Flask(__name__)

    @app.get("/")
    def index():
        """return a short status message so callers know the app is up."""
        return jsonify({"service": "inventory-orders", "status": "ok"})
    return app


if __name__ == "__main__":
    port = config.get_port()
    print(f"Starting app on 0.0.0.0:{port}, data dir {config.get_data_dir()}")
    create_app().run(host="0.0.0.0", port=port)
