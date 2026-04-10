from flask import Flask, request, jsonify
import sqlite3
from datetime import datetime

app = Flask(__name__)

conn = sqlite3.connect("tienda.db", check_same_thread=False)
cursor = conn.cursor()

@app.route("/")
def home():
    return """
    <html>
    <head>
        <title>Tienda Online</title>
        <style>
            body {
                background: #1e1e1e;
                color: white;
                font-family: Arial;
                text-align: center;
            }
            input, button {
                padding: 10px;
                margin: 5px;
                border-radius: 5px;
                border: none;
            }
            button {
                background: #4CAF50;
                color: white;
            }
        </style>
    </head>
    <body>

        <h2>??? Sistema de Tienda</h2>

        <input id="codigo" placeholder="Código"><br>
        <input id="cantidad" placeholder="Cantidad"><br>

        <button onclick="vender()">Vender</button>

        <h3>Resultado:</h3>
        <pre id="res"></pre>

        <script>
        function vender(){
            fetch('/vender',{
                method:'POST',
                headers:{'Content-Type':'application/json'},
                body: JSON.stringify({
                    codigo: document.getElementById('codigo').value,
                    cantidad: parseInt(document.getElementById('cantidad').value)
                })
            })
            .then(r=>r.json())
            .then(d=>{
                document.getElementById('res').innerText = JSON.stringify(d,null,2)
            })
        }
        </script>

    </body>
    </html>
    """

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