from flask import Flask, jsonify, render_template
from barrage import run_barrage

app = Flask(__name__)
latest_run = None


@app.route("/")
def dashboard():
    return render_template("dashboard.html", run=latest_run)


@app.route("/api/launch", methods=["POST"])
def launch():
    """Player presses the button — fire everything."""
    global latest_run
    latest_run = run_barrage()
    return jsonify(latest_run)


@app.route("/api/results")
def results():
    if not latest_run:
        return jsonify({"error": "No barrage yet"}), 404
    return jsonify(latest_run)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
