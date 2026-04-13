from flask import Flask, request, jsonify, session, redirect
import sqlite3
from datetime import datetime
import os

app = Flask(__name__)
app.secret_key = "clave_secreta"

conn = sqlite3.connect("tienda.db", check_same_thread=False)
cursor = conn.cursor()

# ================= TABLAS =================
cursor.execute('''CREATE TABLE IF NOT EXISTS productos (
	codigo TEXT PRIMARY KEY,
	nombre TEXT,
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
			return jsonify({"ok": True})

		return jsonify({"error": "Datos incorrectos"})

	return """
	<body style="background:#1e1e1e;text-align:center;color:white">
	<h2>🔐 Login</h2>
	<input id="u" placeholder="Usuario"><br><br>
	<input id="p" type="password" placeholder="Clave"><br><br>
	<button onclick="login()">Ingresar</button>

	<script>
	function login(){
		fetch('/login',{
			method:'POST',
			headers:{'Content-Type':'application/json'},
			body:JSON.stringify({usuario:u.value,clave:p.value})
		})
		.then(r=>r.json())
		.then(d=>{
			if(d.ok) location.href="/"
			else alert("Error")
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
<head>
<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
<style>
body{background:#1e1e1e;color:white;font-family:Arial}
.card{background:#2b2b2b;padding:15px;margin:10px;border-radius:10px}
button{padding:10px;margin:5px;background:#4CAF50;color:white;border:none}
input{padding:5px;margin:5px}
</style>
</head>

<body>

<h1>🛒 POS PRO</h1>

<div class="card">
<h3>📦 Productos</h3>

<input id="c" placeholder="Código">
<input id="n" placeholder="Nombre">
<input id="cant" placeholder="Stock">
<input id="p" placeholder="Precio">

<button onclick="guardar()">Guardar</button>

<hr>

<div id="lista"></div>
</div>

<div class="card">
<h3>🛒 Venta rápida</h3>

<input id="codVenta" placeholder="Código">
<input id="cantidadVenta" placeholder="Cantidad">

<button onclick="vender()">Vender</button>
</div>

<div class="card">
<h3>📊 Dashboard</h3>
<canvas id="grafico"></canvas>
</div>

<script>

function guardar(){
	fetch('/agregar_producto',{
		method:'POST',
		headers:{'Content-Type':'application/json'},
		body:JSON.stringify({
			codigo:c.value,
			nombre:n.value,
			cantidad:parseInt(cant.value),
			precio:parseFloat(p.value)
		})
	})
	.then(()=>cargar())
}

function cargar(){
	fetch('/productos')
	.then(r=>r.json())
	.then(data=>{
		let html=""
		data.forEach(p=>{
			html+=p[0]+" - "+p[1]+" (Stock:"+p[2]+") $"+p[3]+"<br>"
		})
		lista.innerHTML=html
	})
}

function vender(){
	fetch('/vender',{
		method:'POST',
		headers:{'Content-Type':'application/json'},
		body:JSON.stringify({
			codigo:codVenta.value,
			cantidad:parseInt(cantidadVenta.value)
		})
	})
	.then(r=>r.json())
	.then(d=>{
		if(d.ok){
			window.open('/ticket','_blank')
			alert("Venta OK 💰")
			cargar()
			cargarGrafico()
		}else{
			alert("Error o sin stock")
		}
	})
}

function cargarGrafico(){
	fetch('/ventas_data')
	.then(r=>r.json())
	.then(data=>{
		let labels = data.map(x=>x.fecha)
		let valores = data.map(x=>x.total)

		new Chart(document.getElementById("grafico"),{
			type:'bar',
			data:{
				labels:labels,
				datasets:[{label:'Ventas',data:valores}]
			}
		})
	})
}

cargar()
cargarGrafico()

</script>

</body>
</html>
"""

# ================= PRODUCTOS =================
@app.route("/productos")
def productos():
	cursor.execute("SELECT * FROM productos")
	return jsonify(cursor.fetchall())

@app.route("/agregar_producto", methods=["POST"])
def agregar_producto():
	data = request.json
	cursor.execute("INSERT OR REPLACE INTO productos VALUES (?,?,?,?)",
				   (data['codigo'], data['nombre'], data['cantidad'], data['precio']))
	conn.commit()
	return jsonify({"ok":True})

# ================= VENDER =================
@app.route("/vender", methods=["POST"])
def vender():
	data = request.json

	cursor.execute("SELECT * FROM productos WHERE codigo=?", (data['codigo'],))
	p = cursor.fetchone()

	if not p or p[2] < data['cantidad']:
		return jsonify({"error":True})

	total = data['cantidad'] * p[3]

	cursor.execute("UPDATE productos SET cantidad=? WHERE codigo=?",
				   (p[2]-data['cantidad'], data['codigo']))

	cursor.execute("INSERT INTO ventas (nombre,cantidad,total,metodo,fecha) VALUES (?,?,?,?,?)",
				   (p[1], data['cantidad'], total, "efectivo", datetime.now().strftime("%H:%M")))

	conn.commit()
	return jsonify({"ok":True})

# ================= TICKET =================
@app.route("/ticket")
def ticket():
	cursor.execute("SELECT * FROM ventas ORDER BY id DESC LIMIT 1")
	v = cursor.fetchone()

	if not v:
		return "Sin ventas"

	return f"""
	<body onload="window.print()" style="text-align:center;font-family:monospace">
	<h2>🧾 TICKET</h2>
	<hr>
	<p>{v[1]}</p>
	<p>Cant: {v[2]}</p>
	<p>Total: ${v[3]}</p>
	<hr>
	<p>{v[5]}</p>
	</body>
	"""

# ================= DASHBOARD DATA =================
@app.route("/ventas_data")
def ventas_data():
	cursor.execute("SELECT fecha, total FROM ventas")
	data = cursor.fetchall()
	return jsonify([{"fecha":d[0],"total":d[1]} for d in data])

# ================= RUN =================
port = int(os.environ.get("PORT", 10000))
app.run(host="0.0.0.0", port=port)