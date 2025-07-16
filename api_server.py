from flask import Flask, jsonify
import os
import json

app = Flask(__name__)

@app.route('/json/<filename>', methods=['GET'])
def get_json_file(filename):
    file_path = os.path.join("spec", f"{filename}.json")  # 👈 changed from "data"
    if os.path.exists(file_path):
        try:
            with open(file_path, 'r') as f:
                return jsonify(json.load(f))
        except json.JSONDecodeError:
            return jsonify({"error": "Invalid JSON format"}), 400
    return jsonify({"error": f"{filename}.json not found"}), 404

if __name__ == '__main__':
    app.run(debug=True)
