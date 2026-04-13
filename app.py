from flask import Flask, request, jsonify, session, redirect
import sqlite3
from datetime import datetime
import os
import mercadopago

app = Flask(__name__)
app.secret_key = "clave_secreta"

# 🔥 TOKEN MERCADOPAGO
sdk = mercadopago.SDK("TU_ACCESS_TOKEN_AQUI")

conn = sqlite3.connect("tienda.db", check_same_thread=False)
cursor = conn.cursor()

# ================= TABLAS =================
cursor.execute('''CREATE TABLE IF NOT EXISTS productos (
	codigo TEXT PRIMARY KEY,
	nombre TEXT,
	talle TEXT,
	cantidad INTEGER,
	precio REAL
)''')

cursor.execute('''CREATE TABLE IF NOT EXISTS ventas (
	id INTEGER PRIMARY KEY AUTOINCREMENT,
	nombre TEXT,
	cantidad INTEGER,
	total REAL,
	metodo TEXT,
	fecha TEXT
)''')

cursor.execute('''CREATE TABLE IF NOT EXISTS usuarios (
	usuario TEXT PRIMARY KEY,
	clave TEXT,
	rol TEXT
)''')

cursor.execute("INSERT OR IGNORE INTO usuarios VALUES ('admin','1234','admin')")
cursor.execute("INSERT OR IGNORE INTO usuarios VALUES ('empleado','1234','empleado')")
conn.commit()

# ================= LOGIN =================
@app.route("/login", methods=["GET","POST"])
def login():
	if request.method == "POST":
		data = request.json
		cursor.execute("SELECT * FROM usuarios WHERE usuario=? AND clave=?",
					   (data['usuario'], data['clave']))
		user = cursor.fetchone()

		if user:
			session["user"] = user[0]
			session["rol"] = user[2]
			return jsonify({"ok": True})

		return jsonify({"error": "Datos incorrectos"})

	return """
	<html>
	<body style="background:#1e1e1e;color:white;text-align:center;font-family:Arial">
	<h2>🔐 Login</h2>
	<input id="u" placeholder="Usuario"><br><br>
	<input id="p" placeholder="Clave" type="password"><br><br>
	<button onclick="login()">Ingresar</button>

	<script>
	function login(){
		fetch('/login',{
			method:'POST',
			headers:{'Content-Type':'application/json'},
			body: JSON.stringify({
				usuario: document.getElementById('u').value,
				clave: document.getElementById('p').value
			})
		})
		.then(r=>r.json())
		.then(d=>{
			if(d.ok){ window.location="/" }
			else{ alert("Error") }
		})
	}
	</script>
	</body>
	</html>
	"""

# ================= HOME =================
@app.route("/")
def home():
	if "user" not in session:
		return redirect("/login")

	return """
<!DOCTYPE html>
<html>
<head>
<title>POS EMPRESA</title>

<script src="https://cdnjs.cloudflare.com/ajax/libs/quagga/0.12.1/quagga.min.js"></script>

<style>
body { background:#1e1e1e; color:white; font-family:Arial; }
.container { width:90%; margin:auto; }
.card { background:#2b2b2b; padding:15px; margin:10px; border-radius:10px; }
button { padding:10px; margin:5px; border:none; border-radius:5px; background:#4CAF50; color:white; cursor:pointer;}
input, select { padding:8px; margin:5px; border-radius:5px; border:none; }
table { width:100%; border-collapse: collapse; }
td,th { padding:8px; border-bottom:1px solid #444; text-align:center; }
</style>

</head>

<body>

<div class="container">

<h1>🛒 POS EMPRESA</h1>

<div class="card">
<h3>🛒 Carrito</h3>
<table id="carrito"></table>

<h2>Total: $<span id="total">0</span></h2>

<select id="metodo">
	<option value="efectivo">💵 Efectivo</option>
	<option value="transferencia">💳 QR MercadoPago</option>
</select>

<button onclick="finalizarVenta()">Finalizar venta</button>
</div>

<script>
let carrito = []
let total = 0

function finalizarVenta(){

	let metodo = document.getElementById("metodo").value

	if(carrito.length == 0){
		alert("Carrito vacío")
		return
	}

	// 🔥 SI ES QR
	if(metodo == "transferencia"){
		fetch('/crear_pago',{
			method:'POST',
			headers:{'Content-Type':'application/json'},
			body: JSON.stringify({ total: total })
		})
		.then(r=>r.json())
		.then(d=>{
			window.open(d.url,'_blank')
		})

		alert("Escaneá el QR para pagar 💳")
		return
	}

	// 💵 EFECTIVO
	procesarVenta("efectivo")
}

function procesarVenta(metodo){
	carrito.forEach(i=>{
		fetch('/vender',{
			method:'POST',
			headers:{'Content-Type':'application/json'},
			body:JSON.stringify({
				codigo:i.codigo,
				cantidad:i.cantidad,
				metodo:metodo
			})
		})
	})

	alert("Venta realizada 💰")
	carrito=[]
}
</script>

</body>
</html>
"""

# ================= MERCADOPAGO =================
@app.route("/crear_pago", methods=["POST"])
def crear_pago():
	data = request.json

	preference_data = {
		"items": [
			{
				"title": "Compra Tienda",
				"quantity": 1,
				"unit_price": float(data["total"])
			}
		]
	}

	preference_response = sdk.preference().create(preference_data)
	preference = preference_response["response"]

	return jsonify({"url": preference["init_point"]})

# ================= API =================
@app.route("/vender", methods=["POST"])
def vender():
	data = request.json
	cursor.execute("SELECT * FROM productos WHERE codigo=?", (data['codigo'],))
	prod = cursor.fetchone()

	if prod:
		total = data['cantidad'] * prod[4]

		cursor.execute("UPDATE productos SET cantidad=? WHERE codigo=?",
					   (prod[3]-data['cantidad'], data['codigo']))

		cursor.execute("INSERT INTO ventas (nombre,cantidad,total,metodo,fecha) VALUES (?,?,?,?,?)",
					   (prod[1], data['cantidad'], total, data['metodo'], datetime.now().strftime("%Y-%m-%d %H:%M")))

		conn.commit()
		return jsonify({"ok":True})

	return jsonify({"error":"sin stock"})

# ================= RUN =================
port = int(os.environ.get("PORT", 10000))
app.run(host="0.0.0.0", port=port)