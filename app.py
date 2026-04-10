from flask import Flask, request, jsonify
import sqlite3
from datetime import datetime
import os

app = Flask(__name__)

conn = sqlite3.connect("tienda.db", check_same_thread=False)
cursor = conn.cursor()

# ================= HOME (INTERFAZ PRO) =================
@app.route("/")
def home():
	return """
<!DOCTYPE html>
<html>
<head>
<title>Tienda PRO</title>

<style>
body {
	background: #1e1e1e;
	color: white;
	font-family: Arial;
}

.container {
	width: 90%;
	margin: auto;
}

h1 {
	text-align: center;
}

.card {
	background: #2b2b2b;
	padding: 15px;
	margin: 10px;
	border-radius: 10px;
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
	cursor: pointer;
}

button:hover {
	background: #45a049;
}

.table {
	width: 100%;
	border-collapse: collapse;
}

.table th, .table td {
	padding: 10px;
	border-bottom: 1px solid #444;
	text-align: center;
}
</style>

</head>

<body>

<div class="container">

<h1>🛍️ Sistema de Tienda PRO</h1>

<div class="card">
	<h3>💰 Vender</h3>
	<input id="codigo" placeholder="Código">
	<input id="cantidad" placeholder="Cantidad">
	<button onclick="vender()">Vender</button>
</div>

<div class="card">
	<h3>📦 Productos</h3>
	<button onclick="cargar()">Actualizar lista</button>
	<table class="table" id="tabla">
		<thead>
			<tr>
				<th>Código</th>
				<th>Nombre</th>
				<th>Talle</th>
				<th>Stock</th>
				<th>Precio</th>
			</tr>
		</thead>
		<tbody></tbody>
	</table>
</div>

<div class="card">
	<h3>📊 Resultado</h3>
	<pre id="res"></pre>
</div>

</div>

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
		cargar()
	})
}

function cargar(){
	fetch('/productos')
	.then(r=>r.json())
	.then(data=>{
		let tbody = document.querySelector("#tabla tbody")
		tbody.innerHTML = ""

		data.forEach(p=>{
			let fila = `
				<tr>
					<td>${p[0]}</td>
					<td>${p[1]}</td>
					<td>${p[2]}</td>
					<td>${p[3]}</td>
					<td>$${p[4]}</td>
				</tr>
			`
			tbody.innerHTML += fila
		})
	})
}

cargar()

</script>

</body>
</html>
"""

# ================= API =================

@app.route("/productos")
def productos():
	cursor.execute("SELECT * FROM productos")
	return jsonify(cursor.fetchall())

@app.route("/vender", methods=["POST"])
def vender():
	data = request.json

	cursor.execute("SELECT * FROM productos WHERE codigo=?", (data['codigo'],))
	prod = cursor.fetchone()

	if prod and prod[3] >= data['cantidad']:
		total = data['cantidad'] * prod[4]

		cursor.execute("UPDATE productos SET cantidad=? WHERE codigo=?",
					   (prod[3] - data['cantidad'], data['codigo']))

		cursor.execute("INSERT INTO ventas (nombre,cantidad,total,metodo,fecha) VALUES (?,?,?,?,?)",
					   (prod[1], data['cantidad'], total, "online", datetime.now().strftime("%Y-%m-%d %H:%M")))

		conn.commit()
		return jsonify({"total": total})

	return jsonify({"error": "Sin stock o no existe"})

# ================= RUN =================

port = int(os.environ.get("PORT", 10000))
app.run(host="0.0.0.0", port=port)