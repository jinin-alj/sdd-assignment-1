from flask import Flask, jsonify
import config
from library import repository
from library.routes import library_blueprint


def create_app() -> Flask:
    """build the Flask app and register its routes and error handlers"""
    app = Flask(__name__)

    # create what is missing on every boot, but never drop or re-seed existing data
    repository.create_tables()
    repository.seed_games()

    app.register_blueprint(library_blueprint)

    @app.get("/")
    def index():
        """return a short status message so callers know the app is up."""
        return jsonify({"service": "game-night-planner", "status": "ok"})
    
    @app.errorhandler(404)
    def not_found(error):
        """return json instead of flask's default html error page"""
        return jsonify({"error": "not found"}), 404
    
    @app.errorhandler(500)
    def server_error(error):
        """log the real error but only tell the caller something went wrong"""
        print(f"Unexpected error: {error}")
        return jsonify({"error": "something went wrong"}), 500

    return app
    
if __name__ == "__main__":
    port = config.get_port()
    print(f"Starting app on 0.0.0.0:{port}, data dir {config.get_data_dir()}")
    create_app().run(host="0.0.0.0", port=port)
