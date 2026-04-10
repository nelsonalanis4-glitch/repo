from flask import Flask, request, jsonify
import sqlite3
from datetime import datetime

app = Flask(__name__)

conn = sqlite3.connect("tienda.db", check_same_thread=False)
cursor = conn.cursor()

@app.route("/")
def home():
	return "Sistema online funcionando"

@app.route("/productos")
def productos():
	cursor.execute("SELECT * FROM productos")
	return jsonify(cursor.fetchall())

@app.route("/vender", methods=["POST"])
def vender():
	data = request.json

	cursor.execute("SELECT * FROM productos WHERE codigo=?", (data['codigo'],))
	prod = cursor.fetchone()

	if prod:
		total = data['cantidad'] * prod[4]

		cursor.execute("UPDATE productos SET cantidad=? WHERE codigo=?",
					   (prod[3] - data['cantidad'], data['codigo']))

		cursor.execute("INSERT INTO ventas (nombre,cantidad,total,metodo,fecha) VALUES (?,?,?,?,?)",
					   (prod[1], data['cantidad'], total, "online", datetime.now().strftime("%Y-%m-%d %H:%M")))

		conn.commit()
		return jsonify({"total": total})

	return jsonify({"error": "no existe"})

import os

port = int(os.environ.get("PORT", 10000))
app.run(host="0.0.0.0", port=port)