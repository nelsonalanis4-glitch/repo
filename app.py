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
<title>POS PRO</title>

<script src="https://cdnjs.cloudflare.com/ajax/libs/quagga/0.12.1/quagga.min.js"></script>

<style>
body { background:#1e1e1e; color:white; font-family:Arial; }
.container { width:90%; margin:auto; }
.card { background:#2b2b2b; padding:15px; margin:10px; border-radius:10px; }
button { padding:10px; margin:5px; border:none; border-radius:5px; background:#4CAF50; color:white; cursor:pointer;}
button:hover { background:#45a049; }
input { padding:8px; margin:5px; border-radius:5px; border:none; }
table { width:100%; border-collapse: collapse; }
td,th { padding:8px; border-bottom:1px solid #444; text-align:center; }
</style>

</head>

<body>

<div class="container">

<h1>🛒 POS TIENDA PRO</h1>

<div class="card">
<h3>📷 Escáner</h3>
<div id="scanner" style="width:300px;"></div>
<button onclick="iniciarScanner()">Iniciar escáner</button>
</div>

<div class="card">
<h3>🛒 Carrito</h3>
<table id="carrito"></table>
<h2>Total: $<span id="total">0</span></h2>
<button onclick="finalizarVenta()">Finalizar venta</button>
<button onclick="vaciar()">Vaciar</button>
</div>

<div class="card">
<h3>📦 Panel Admin PRO</h3>

<input id="buscar" placeholder="🔍 Buscar..." onkeyup="cargar()">

<br><br>

<h4>➕ Agregar producto</h4>
<input id="c" placeholder="Código">
<input id="n" placeholder="Nombre">
<input id="t" placeholder="Talle">
<input id="cant" placeholder="Cantidad">
<input id="p" placeholder="Precio">
<button onclick="agregarProducto()">Guardar</button>

<br><br>

<button onclick="cargar()">Actualizar</button>
<table id="tabla"></table>

</div>

</div>

<script>

let carrito = []
let total = 0
let lastCode = null

function beep(){
	new Audio("https://www.soundjay.com/buttons/sounds/beep-07.mp3").play()
}

function iniciarScanner(){
	Quagga.init({
		inputStream:{
			type:"LiveStream",
			target:document.querySelector('#scanner'),
			constraints:{facingMode:"environment"}
		},
		decoder:{readers:["code_128_reader","ean_reader"]}
	}, err=>{
		if(!err) Quagga.start()
	})

	Quagga.onDetected(res=>{
		let codigo = res.codeResult.code
		if(codigo !== lastCode){
			lastCode = codigo
			beep()
			agregar(codigo)
			setTimeout(()=>{ lastCode = null }, 1500)
		}
	})
}

function agregar(codigo){
	fetch('/productos')
	.then(r=>r.json())
	.then(data=>{
		let p = data.find(x=>x[0]==codigo)
		if(p){
			let item = carrito.find(i=>i.codigo==codigo)
			if(item){
				item.cantidad++
				item.subtotal = item.cantidad * item.precio
			}else{
				carrito.push({
					codigo:p[0],
					nombre:p[1],
					precio:p[4],
					cantidad:1,
					subtotal:p[4]
				})
			}
			actualizar()
		}
	})
}

function actualizar(){
	let t = document.getElementById("carrito")
	t.innerHTML = "<tr><th>Cod</th><th>Nombre</th><th>Cant</th><th>Precio</th><th>Subtotal</th></tr>"
	total = 0

	carrito.forEach(i=>{
		total += i.subtotal
		t.innerHTML += `<tr>
		<td>${i.codigo}</td>
		<td>${i.nombre}</td>
		<td>${i.cantidad}</td>
		<td>$${i.precio}</td>
		<td>$${i.subtotal}</td>
		</tr>`
	})

	document.getElementById("total").innerText = total
}

function finalizarVenta(){
	carrito.forEach(i=>{
		fetch('/vender',{
			method:'POST',
			headers:{'Content-Type':'application/json'},
			body:JSON.stringify({codigo:i.codigo,cantidad:i.cantidad})
		})
	})

	alert("Venta realizada 💰")
	carrito=[]
	actualizar()
	cargar()
}

function vaciar(){
	carrito=[]
	actualizar()
}

function cargar(){
	fetch('/productos')
	.then(r=>r.json())
	.then(data=>{

		let filtro = document.getElementById("buscar").value.toLowerCase()

		let html = "<tr><th>Cod</th><th>Nombre</th><th>Talle</th><th>Stock</th><th>Precio</th><th>Acciones</th></tr>"

		data
		.filter(p => p[1].toLowerCase().includes(filtro))
		.forEach(p=>{

			let alerta = p[3] <= 3 ? "style='color:red;font-weight:bold'" : ""

			html += `<tr>
			<td>${p[0]}</td>
			<td>${p[1]}</td>
			<td>${p[2]}</td>
			<td ${alerta}>${p[3]}</td>
			<td>$${p[4]}</td>
			<td>
				<button onclick="editar('${p[0]}','${p[1]}','${p[2]}',${p[3]},${p[4]})">✏️</button>
				<button onclick="eliminar('${p[0]}')">🗑️</button>
			</td>
			</tr>`
		})

		document.getElementById("tabla").innerHTML = html
	})
}

function agregarProducto(){
	fetch('/agregar_producto',{
		method:'POST',
		headers:{'Content-Type':'application/json'},
		body: JSON.stringify({
			codigo:c.value,
			nombre:n.value,
			talle:t.value,
			cantidad:parseInt(cant.value),
			precio:parseFloat(p.value)
		})
	})
	.then(()=>{ alert("Guardado ✅"); cargar() })
}

function eliminar(codigo){
	if(confirm("¿Eliminar producto?")){
		fetch('/eliminar_producto',{
			method:'POST',
			headers:{'Content-Type':'application/json'},
			body: JSON.stringify({codigo:codigo})
		})
		.then(()=>cargar())
	}
}

function editar(c,n,t,cant,p){
	let nombre = prompt("Nombre:", n)
	let talle = prompt("Talle:", t)
	let cantidad = prompt("Cantidad:", cant)
	let precio = prompt("Precio:", p)

	fetch('/editar_producto',{
		method:'POST',
		headers:{'Content-Type':'application/json'},
		body: JSON.stringify({
			codigo:c,
			nombre:nombre,
			talle:talle,
			cantidad:parseInt(cantidad),
			precio:parseFloat(precio)
		})
	})
	.then(()=>cargar())
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

@app.route("/agregar_producto", methods=["POST"])
def agregar_producto():
	data = request.json
	cursor.execute("INSERT OR REPLACE INTO productos VALUES (?,?,?,?,?)",
				   (data['codigo'], data['nombre'], data['talle'], data['cantidad'], data['precio']))
	conn.commit()
	return jsonify({"ok": True})

@app.route("/eliminar_producto", methods=["POST"])
def eliminar_producto():
	data = request.json
	cursor.execute("DELETE FROM productos WHERE codigo=?", (data['codigo'],))
	conn.commit()
	return jsonify({"ok": True})

@app.route("/editar_producto", methods=["POST"])
def editar_producto():
	data = request.json
	cursor.execute("""
	UPDATE productos 
	SET nombre=?, talle=?, cantidad=?, precio=? 
	WHERE codigo=?
	""", (data['nombre'], data['talle'], data['cantidad'], data['precio'], data['codigo']))
	conn.commit()
	return jsonify({"ok": True})

@app.route("/vender", methods=["POST"])
def vender():
	if "user" not in session:
		return jsonify({"error":"no autorizado"})

	data = request.json
	cursor.execute("SELECT * FROM productos WHERE codigo=?", (data['codigo'],))
	prod = cursor.fetchone()

	if prod and prod[3] >= data['cantidad']:
		total = data['cantidad'] * prod[4]

		cursor.execute("UPDATE productos SET cantidad=? WHERE codigo=?",
					   (prod[3]-data['cantidad'], data['codigo']))

		cursor.execute("INSERT INTO ventas (nombre,cantidad,total,metodo,fecha) VALUES (?,?,?,?,?)",
					   (prod[1], data['cantidad'], total, "web", datetime.now().strftime("%Y-%m-%d %H:%M")))

		conn.commit()
		return jsonify({"ok":True})

	return jsonify({"error":"sin stock"})

# ================= RUN =================
port = int(os.environ.get("PORT", 10000))
app.run(host="0.0.0.0", port=port)