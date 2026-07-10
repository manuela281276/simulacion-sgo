"""Aplicación web para la gestión operativa de la Compañía de Bomberos Chosica N.° 32.

Instale Flask:  pip install -r requirements.txt
Ejecute:        python simulacion_sistema_gestion_operativa.py
Abra:           http://127.0.0.1:5000
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from functools import wraps

from flask import Flask, flash, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash


@dataclass
class Bombero:
    codigo: str
    nombres: str
    apellidos: str
    password_hash: str
    entrada: datetime | None = None
    salida: datetime | None = None
    guardias: list[str] = field(default_factory=list)

    @property
    def nombre_completo(self) -> str:
        return f"{self.nombres} {self.apellidos}"

    @property
    def en_servicio(self) -> bool:
        return self.entrada is not None and self.salida is None


class SistemaGuardias:
    def __init__(self) -> None:
        self.bomberos: dict[str, Bombero] = {}
        self.guardias: dict[str, list[str]] = {}

    def registrar_bombero(self, codigo: str, nombres: str, apellidos: str, password: str) -> Bombero:
        codigo = codigo.strip().upper()
        if len(codigo) != 6 or codigo in self.bomberos:
            raise ValueError("El código debe tener 6 caracteres y no estar registrado.")
        if not nombres.strip() or not apellidos.strip():
            raise ValueError("Ingrese nombres y apellidos.")
        if len(password) != 7:
            raise ValueError("La contraseña debe tener exactamente 7 caracteres.")
        bombero = Bombero(codigo, nombres.strip(), apellidos.strip(), generate_password_hash(password))
        self.bomberos[codigo] = bombero
        return bombero

    def autenticar(self, codigo: str, password: str) -> Bombero | None:
        bombero = self.bomberos.get(codigo.strip().upper())
        if bombero and check_password_hash(bombero.password_hash, password):
            return bombero
        return None

    def marcar_asistencia(self, codigo: str) -> tuple[str, datetime]:
        bombero = self.bomberos[codigo]
        ahora = datetime.now()
        if not bombero.en_servicio:
            bombero.entrada, bombero.salida = ahora, None
            return "Entrada registrada", ahora
        bombero.salida = ahora
        return "Salida registrada", ahora

    def asignar_guardia(self, codigo: str, dia: str) -> None:
        dia = dia.strip()
        bombero = self.bomberos[codigo]
        if not dia:
            raise ValueError("Seleccione la fecha de la guardia nocturna.")
        if dia in bombero.guardias:
            raise ValueError("Ya tiene una guardia asignada para esa fecha.")
        bombero.guardias.append(dia)
        self.guardias.setdefault(dia, []).append(codigo)


app = Flask(__name__)
app.config["SECRET_KEY"] = "cambie-esta-clave-por-una-segura-en-produccion"
sistema = SistemaGuardias()


def login_requerido(vista):
    @wraps(vista)
    def protegida(*args, **kwargs):
        if "codigo" not in session:
            flash("Inicie sesión para continuar.", "aviso")
            return redirect(url_for("iniciar_sesion"))
        return vista(*args, **kwargs)
    return protegida


@app.route("/")
def inicio():
    if "codigo" in session:
        return redirect(url_for("panel"))
    return redirect(url_for("iniciar_sesion"))


@app.route("/registro", methods=["GET", "POST"])
def registro():
    if request.method == "POST":
        try:
            bombero = sistema.registrar_bombero(
                request.form["codigo"], request.form["nombres"],
                request.form["apellidos"], request.form["password"]
            )
            session["codigo"] = bombero.codigo
            flash("Registro exitoso. Su sesión se ha iniciado.", "exito")
            return redirect(url_for("panel"))
        except ValueError as error:
            flash(str(error), "error")
    return render_template("registro.html")


@app.route("/iniciar-sesion", methods=["GET", "POST"])
def iniciar_sesion():
    if request.method == "POST":
        bombero = sistema.autenticar(request.form["codigo"], request.form["password"])
        if bombero:
            session["codigo"] = bombero.codigo
            flash(f"Bienvenido(a), {bombero.nombres}.", "exito")
            return redirect(url_for("panel"))
        flash("Código o contraseña incorrectos.", "error")
    return render_template("login.html")


@app.post("/cerrar-sesion")
@login_requerido
def cerrar_sesion():
    session.clear()
    flash("La sesión se cerró correctamente.", "aviso")
    return redirect(url_for("iniciar_sesion"))


@app.get("/panel")
@login_requerido
def panel():
    actual = sistema.bomberos[session["codigo"]]
    diurno = [b for b in sistema.bomberos.values() if b.en_servicio]
    nocturno = [(dia, sistema.bomberos[codigo]) for dia in sorted(sistema.guardias) for codigo in sistema.guardias[dia]]
    return render_template("panel.html", actual=actual, diurno=diurno, nocturno=nocturno,
                           bomberos=sistema.bomberos.values())


@app.post("/asistencia")
@login_requerido
def asistencia():
    accion, momento = sistema.marcar_asistencia(session["codigo"])
    flash(f"{accion}: {momento:%d/%m/%Y %H:%M:%S}", "exito")
    return redirect(url_for("panel"))


@app.post("/guardias")
@login_requerido
def guardias():
    try:
        sistema.asignar_guardia(session["codigo"], request.form["dia"])
        flash("Guardia nocturna registrada.", "exito")
    except ValueError as error:
        flash(str(error), "error")
    return redirect(url_for("panel"))


if __name__ == "__main__":
    app.run(debug=True)
