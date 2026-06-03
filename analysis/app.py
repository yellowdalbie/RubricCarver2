import os
import json
from flask import Flask, render_template, jsonify, make_response, request
import data_extractor

app = Flask(__name__)

@app.route('/')
def index():
    r = make_response(render_template("dashboard.html", refresh_secs=30))
    r.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    return r
    # Pass refresh_secs if needed for initial JS config, we'll use 30 as default


@app.route('/api/experiments')
def api_experiments():
    experiments_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "experiments")
    if not os.path.exists(experiments_dir):
        return jsonify([])
    experiments = []
    for d in os.listdir(experiments_dir):
        config_path = os.path.join(experiments_dir, d, "config.json")
        if os.path.isdir(os.path.join(experiments_dir, d)) and os.path.exists(config_path):
            with open(config_path, 'r', encoding='utf-8') as f:
                cfg = json.load(f)
            experiments.append({"id": d, "name": cfg.get("name", d)})
    return jsonify(sorted(experiments, key=lambda x: x["id"], reverse=True))

@app.route('/api/data')
def api_data():
    exp_name = request.args.get('exp', 'exp1_analytic')
    data = data_extractor.build_data(exp_name, refresh_secs=30)
    return jsonify(data)

if __name__ == '__main__':
    print("Starting RubricCarver Dashboard API Server...")
    # host='0.0.0.0' allows access from local network
    app.run(host='0.0.0.0', port=5555, debug=True)
