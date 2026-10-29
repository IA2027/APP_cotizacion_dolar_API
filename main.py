
import threading
from datetime import datetime

import requests

from kivy.app import App
from kivy.clock import Clock
from kivy.metrics import dp, sp
from kivy.graphics import Color, RoundedRectangle
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.scrollview import ScrollView


# ==================================================
# CONFIGURACIÓN
# ==================================================

API_URL = "https://monedapi.ar/api/v2/usd"

FONDO = (0.09, 0.10, 0.12, 1)
TARJETA_COLOR = (0.13, 0.15, 0.19, 1)
AZUL = (0.05, 0.28, 0.65, 1)
BLANCO = (1, 1, 1, 1)
GRIS_CLARO = (0.78, 0.81, 0.86, 1)
VERDE = (0.30, 0.90, 0.60, 1)
AZUL_CLARO = (0.40, 0.67, 1, 1)
ROJO = (1, 0.25, 0.30, 1)


# ==================================================
# FUNCIONES AUXILIARES
# ==================================================

def precio(valor):
    """Convierte los valores numéricos a formato argentino."""

    if valor is None or valor == "":
        return "No disponible"

    try:
        numero = float(valor)
        texto = f"{numero:,.2f}"
        texto = texto.replace(",", "X")
        texto = texto.replace(".", ",")
        texto = texto.replace("X", ".")
        return texto
    except (ValueError, TypeError):
        return str(valor)


def crear_texto(
    contenido,
    tamano=18,
    color=BLANCO,
    alineacion="left"
):
    """Crea etiquetas sin etiquetas de formato visibles."""

    etiqueta = Label(
        text=str(contenido),
        font_size=sp(tamano),
        color=color,
        halign=alineacion,
        valign="middle",
        size_hint_y=None,
        height=dp(tamano * 2)
    )

    etiqueta.bind(
        size=lambda objeto, tamanio: setattr(
            objeto, "text_size", tamanio
        )
    )

    return etiqueta


# ==================================================
# TARJETA DE COTIZACIÓN
# ==================================================

class Tarjeta(BoxLayout):

    def __init__(self, **kwargs):
        altura = kwargs.pop("height", dp(175))

        super().__init__(
            orientation="vertical",
            padding=[dp(18), dp(12), dp(18), dp(12)],
            spacing=dp(5),
            size_hint_y=None,
            height=altura,
            **kwargs
        )

        with self.canvas.before:
            Color(*TARJETA_COLOR)
            self.fondo_tarjeta = RoundedRectangle(
                pos=self.pos,
                size=self.size,
                radius=[dp(14)]
            )

        self.bind(
            pos=self.actualizar_fondo,
            size=self.actualizar_fondo
        )

    def actualizar_fondo(self, *args):
        self.fondo_tarjeta.pos = self.pos
        self.fondo_tarjeta.size = self.size


# ==================================================
# APLICACIÓN PRINCIPAL
# ==================================================

class DolarArgentinaApp(App):

    def build(self):
        self.title = "Dólar Argentina"

        raiz = BoxLayout(
            orientation="vertical",
            padding=dp(15),
            spacing=dp(10)
        )

        with raiz.canvas.before:
            Color(*FONDO)
            self.fondo_principal = RoundedRectangle(
                pos=raiz.pos,
                size=raiz.size
            )

        raiz.bind(
            pos=self.actualizar_fondo_principal,
            size=self.actualizar_fondo_principal
        )

        # ------------------------------
        # ENCABEZADO
        # ------------------------------

        encabezado = BoxLayout(
            orientation="vertical",
            size_hint_y=None,
            height=dp(105),
            spacing=dp(2)
        )

        titulo = crear_texto(
            "DÓLAR ARGENTINA",
            tamano=29,
            color=ROJO,
            alineacion="center"
        )
        titulo.height = dp(50)

        subtitulo = crear_texto(
            "Cotizaciones actualizadas",
            tamano=17,
            color=GRIS_CLARO,
            alineacion="center"
        )
        subtitulo.height = dp(35)

        encabezado.add_widget(titulo)
        encabezado.add_widget(subtitulo)

        raiz.add_widget(encabezado)

        # ------------------------------
        # ESTADO DE LA CONEXIÓN
        # ------------------------------

        self.estado = crear_texto(
            "Conectando con el servicio...",
            tamano=15,
            color=GRIS_CLARO,
            alineacion="center"
        )
        self.estado.height = dp(35)

        raiz.add_widget(self.estado)

        # ------------------------------
        # ÁREA DESPLAZABLE
        # ------------------------------

        self.scroll = ScrollView(
            do_scroll_x=False,
            do_scroll_y=True,
            bar_width=dp(8),
            scroll_type=["bars", "content"]
        )

        self.contenido = BoxLayout(
            orientation="vertical",
            spacing=dp(12),
            padding=[dp(2), dp(5), dp(2), dp(15)],
            size_hint_y=None
        )

        self.contenido.bind(
            minimum_height=self.contenido.setter("height")
        )

        self.scroll.add_widget(self.contenido)
        raiz.add_widget(self.scroll)

        # ------------------------------
        # BOTÓN ACTUALIZAR
        # ------------------------------

        self.boton = Button(
            text="ACTUALIZAR COTIZACIONES",
            size_hint_y=None,
            height=dp(58),
            font_size=sp(18),
            bold=True,
            background_normal="",
            background_color=AZUL,
            color=BLANCO
        )

        self.boton.bind(
            on_release=self.actualizar_cotizaciones
        )

        raiz.add_widget(self.boton)

        # Consultar al abrir la aplicación.
        Clock.schedule_once(
            lambda dt: self.actualizar_cotizaciones(),
            0.5
        )

        return raiz

    # ==================================================
    # ACTUALIZAR FONDO
    # ==================================================

    def actualizar_fondo_principal(self, objeto, *args):
        self.fondo_principal.pos = objeto.pos
        self.fondo_principal.size = objeto.size

    # ==================================================
    # CONSULTAR API
    # ==================================================

    def actualizar_cotizaciones(self, *args):
        self.boton.disabled = True
        self.boton.text = "CONSULTANDO..."
        self.estado.text = "Obteniendo cotizaciones..."
        self.estado.color = GRIS_CLARO

        hilo = threading.Thread(
            target=self.consultar_api,
            daemon=True
        )
        hilo.start()

    def consultar_api(self):
        try:
            respuesta = requests.get(
                API_URL,
                timeout=20
            )

            respuesta.raise_for_status()
            datos = respuesta.json()

            # Algunas APIs entregan una lista directamente.
            # Este bloque también admite respuestas envueltas
            # dentro de un diccionario.
            if isinstance(datos, dict):
                if isinstance(datos.get("data"), list):
                    datos = datos["data"]
                elif isinstance(datos.get("results"), list):
                    datos = datos["results"]
                elif isinstance(datos.get("quotes"), list):
                    datos = datos["quotes"]
                else:
                    raise ValueError(
                        "La respuesta de la API no contiene "
                        "una lista de cotizaciones reconocible."
                    )

            if not isinstance(datos, list):
                raise ValueError(
                    "La API no devolvió una lista de cotizaciones."
                )

            Clock.schedule_once(
                lambda dt: self.mostrar_cotizaciones(datos),
                0
            )

        except Exception as error:
            mensaje = str(error)

            Clock.schedule_once(
                lambda dt: self.mostrar_error(mensaje),
                0
            )

    # ==================================================
    # MOSTRAR TODAS LAS COTIZACIONES
    # ==================================================

    def mostrar_cotizaciones(self, datos):
        self.contenido.clear_widgets()

        cotizaciones = [
            dato for dato in datos
            if isinstance(dato, dict)
        ]

        # Primero se muestran las cotizaciones oficiales.
        cotizaciones.sort(
            key=lambda dato: (
                str(dato.get("origin", "")).upper()
                != "OFICIAL"
            )
        )

        if not cotizaciones:
            self.mostrar_error(
                "No se encontraron cotizaciones."
            )
            return

        encabezado = crear_texto(
            f"COTIZACIONES DISPONIBLES: {len(cotizaciones)}",
            tamano=19,
            color=GRIS_CLARO,
            alineacion="center"
        )
        encabezado.height = dp(45)
        self.contenido.add_widget(encabezado)

        for dato in cotizaciones:

            nombre = (
                dato.get("name")
                or dato.get("origin")
                or "Cotización del dólar"
            )

            origen = str(
                dato.get("origin", "")
            ).upper()

            # Destacar el dólar oficial.
            if origen == "OFICIAL":
                tarjeta = Tarjeta(
                    height=dp(190)
                )
                tarjeta.background_color = AZUL
            else:
                tarjeta = Tarjeta(
                    height=dp(175)
                )

            # Nombre de la cotización.
            etiqueta_nombre = crear_texto(
                nombre,
                tamano=22,
                color=BLANCO
            )
            etiqueta_nombre.height = dp(42)

            tarjeta.add_widget(etiqueta_nombre)

            # Precio de compra.
            compra = crear_texto(
                "COMPRA:  $ " + precio(dato.get("buy")),
                tamano=23,
                color=VERDE
            )
            compra.height = dp(43)

            tarjeta.add_widget(compra)

            # Precio de venta.
            venta = crear_texto(
                "VENTA:  $ " + precio(dato.get("sell")),
                tamano=23,
                color=AZUL_CLARO
            )
            venta.height = dp(43)

            tarjeta.add_widget(venta)

            # Fecha de actualización proporcionada por la API.
            fecha = dato.get("updatedAt")

            if fecha:
                etiqueta_fecha = crear_texto(
                    "Actualizado: " + str(fecha),
                    tamano=12,
                    color=GRIS_CLARO
                )
                etiqueta_fecha.height = dp(25)
                tarjeta.add_widget(etiqueta_fecha)

            self.contenido.add_widget(tarjeta)

        hora = datetime.now().strftime(
            "%d/%m/%Y %H:%M:%S"
        )

        self.estado.text = (
            f"{len(cotizaciones)} cotizaciones recibidas"
            f" | Consulta: {hora}"
        )
        self.estado.color = VERDE

        self.boton.disabled = False
        self.boton.text = "ACTUALIZAR COTIZACIONES"

    # ==================================================
    # MOSTRAR ERRORES
    # ==================================================

    def mostrar_error(self, mensaje):
        self.contenido.clear_widgets()

        error = crear_texto(
            "NO SE PUDIERON OBTENER LAS COTIZACIONES",
            tamano=20,
            color=ROJO,
            alineacion="center"
        )
        error.height = dp(70)

        detalle = crear_texto(
            mensaje,
            tamano=15,
            color=BLANCO,
            alineacion="center"
        )
        detalle.height = dp(100)

        self.contenido.add_widget(error)
        self.contenido.add_widget(detalle)

        self.estado.text = "Error de conexión"
        self.estado.color = ROJO

        self.boton.disabled = False
        self.boton.text = "VOLVER A INTENTAR"


# ==================================================
# INICIAR APLICACIÓN
# ==================================================

if __name__ == "__main__":
    DolarArgentinaApp().run()
