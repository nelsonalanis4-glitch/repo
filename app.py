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
	<h2 style='color:white;text-align:center'>Login</h2>
	<body style="background:#1e1e1e;text-align:center">
	<input id="u" placeholder="Usuario"><br><br>
	<input id="p" placeholder="Clave" type="password"><br><br>
	<button onclick="login()">Ingresar</button>

	<script>
	function login(){
		fetch('/login',{
			method:'POST',
			headers:{'Content-Type':'application/json'},
			body: JSON.stringify({
				usuario:u.value,
				clave:p.value
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
	"""

# ================= HOME =================
@app.route("/")
def home():
	if "user" not in session:
		return redirect("/login")

	return """
<!DOCTYPE html>
<html>
<body style="background:#1e1e1e;color:white;text-align:center">

<h2>🛒 POS EMPRESA</h2>

<h3>Total: $<span id="total">0</span></h3>

<select id="metodo">
<option value="efectivo">Efectivo</option>
<option value="qr">QR MercadoPago</option>
</select>

<br><br>

<button onclick="pagar()">Cobrar</button>

<script>

let total = 1000 // prueba

function pagar(){

	let metodo = document.getElementById("metodo").value

	if(metodo == "qr"){
		fetch('/crear_pago',{
			method:'POST',
			headers:{'Content-Type':'application/json'},
			body: JSON.stringify({ total: total })
		})
		.then(r=>r.json())
		.then(d=>{
			window.open(d.url,'_blank')
		})

		alert("Esperando pago QR...")
		return
	}

	fetch('/vender',{
		method:'POST',
		headers:{'Content-Type':'application/json'},
		body: JSON.stringify({codigo:"test",cantidad:1,metodo:"efectivo"})
	})

	alert("Pago efectivo OK")
}

</script>

</body>
</html>
"""

# ================= CREAR PAGO =================
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
		],
		"notification_url": "https://TU-APP.onrender.com/webhook"
	}

	preference = sdk.preference().create(preference_data)["response"]

	return jsonify({"url": preference["init_point"]})

# ================= WEBHOOK =================
@app.route("/webhook", methods=["POST"])
def webhook():
	data = request.json

	if data.get("type") == "payment":
		payment_id = data["data"]["id"]

		pago = sdk.payment().get(payment_id)
		info = pago["response"]

		if info["status"] == "approved":

			total = info["transaction_amount"]

			cursor.execute("""
			INSERT INTO ventas (nombre,cantidad,total,metodo,fecha)
			VALUES (?,?,?,?,?)
			""", ("VENTA QR", 1, total, "QR", datetime.now().strftime("%Y-%m-%d %H:%M")))

			conn.commit()

	return "OK"

# ================= TICKET =================
@app.route("/ticket/<int:pago_id>")
def ticket(pago_id):

	pago = sdk.payment().get(pago_id)
	info = pago["response"]

	if info["status"] != "approved":
		return "Pago no aprobado"

	return f"""
	<body onload="window.print()" style="text-align:center">
	<h2>TICKET</h2>
	<p>Total: ${info['transaction_amount']}</p>
	<p>Estado: {info['status']}</p>
	</body>
	"""

# ================= PANEL PAGOS =================
@app.route("/pagos")
def pagos():
	cursor.execute("SELECT * FROM ventas ORDER BY id DESC LIMIT 20")
	data = cursor.fetchall()

	html = "<h2>Pagos</h2><table border=1>"
	html += "<tr><th>ID</th><th>Nombre</th><th>Total</th><th>Método</th><th>Fecha</th></tr>"

	for v in data:
		html += f"<tr><td>{v[0]}</td><td>{v[1]}</td><td>${v[3]}</td><td>{v[4]}</td><td>{v[5]}</td></tr>"

	html += "</table>"
	return html

# ================= API =================
@app.route("/vender", methods=["POST"])
def vender():
	data = request.json

	cursor.execute("INSERT INTO ventas (nombre,cantidad,total,metodo,fecha) VALUES (?,?,?,?,?)",
				   ("VENTA", data['cantidad'], 1000, data['metodo'], datetime.now().strftime("%Y-%m-%d %H:%M")))

	conn.commit()
	return jsonify({"ok":True})

# ================= RUN =================
port = int(os.environ.get("PORT", 10000))
app.run(host="0.0.0.0", port=port)