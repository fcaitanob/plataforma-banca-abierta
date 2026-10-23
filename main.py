
import os

import requests
from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse

app = FastAPI(
    title="Plataforma de Banca Abierta",
    description="Simulación de una plataforma de finanzas abiertas",
    version="1.0.0",
)

API_BASE_URL = os.getenv(
    "API_BASE_URL",
    "https://api-banca-abierta.onrender.com",
)

AUTH0_DOMAIN = os.getenv("AUTH0_DOMAIN", "").strip()
AUTH0_CLIENT_ID = os.getenv("AUTH0_CLIENT_ID", "").strip()
AUTH0_CLIENT_SECRET = os.getenv("AUTH0_CLIENT_SECRET", "").strip()
AUTH0_AUDIENCE = os.getenv(
    "AUTH0_AUDIENCE",
    "https://api-banca-abierta.onrender.com",
)


@app.get("/", response_class=HTMLResponse)
def inicio():
    return """
    <!DOCTYPE html>
    <html lang="es">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <title>Plataforma de Banca Abierta</title>
        <style>
            body {
                font-family: Arial, sans-serif;
                max-width: 850px;
                margin: 40px auto;
                padding: 0 20px;
                background: #f4f6f8;
                color: #243247;
            }
            h1 { color: #164e63; }
            .panel {
                background: white;
                padding: 24px;
                margin: 18px 0;
                border-radius: 10px;
                box-shadow: 0 2px 8px #0001;
            }
            button {
                display: block;
                width: 100%;
                margin: 12px 0;
                padding: 13px;
                border: 0;
                border-radius: 6px;
                background: #0e7490;
                color: white;
                font-size: 15px;
                cursor: pointer;
            }
            button:hover { background: #155e75; }
            button:disabled { opacity: 0.6; cursor: wait; }
            pre {
                background: #17212f;
                color: #d8e8f5;
                padding: 18px;
                border-radius: 8px;
                white-space: pre-wrap;
                overflow-wrap: anywhere;
                min-height: 80px;
            }
            .nota { color: #526477; font-size: 14px; }
        </style>
    </head>
    <body>
        <h1>Plataforma de Banca Abierta</h1>
        <p>Simulación de una plataforma que consulta información
        de una entidad prestamista.</p>

        <div class="panel">
            <h2>1. Consultar tasa pública</h2>
            <p class="nota">
                Consulta la tasa de interés sin utilizar un token.
            </p>
            <button onclick="consultar('/consultar/tasa')">
                Consultar tasa pública
            </button>
        </div>

        <div class="panel">
            <h2>2. Consultar oferta protegida</h2>
            <p class="nota">
                El servidor obtiene un token OAuth 2.0 de Auth0
                y lo utiliza para consultar la oferta.
            </p>
            <button onclick="consultar('/consultar/oferta')">
                Consultar oferta con OAuth 2.0
            </button>
        </div>

        <div class="panel">
            <h2>3. Intentar acceder sin token</h2>
            <p class="nota">
                Simula una solicitud sin credenciales.
                La API debería responder HTTP 401.
            </p>
            <button onclick="consultar('/probar/sin-token')">
                Probar acceso sin token
            </button>
        </div>

        <div class="panel">
            <h2>Resultado de la consulta</h2>
            <pre id="resultado">Esperando una consulta...</pre>
        </div>

        <script>
            async function consultar(ruta) {
                const salida = document.getElementById("resultado");
                const botones = document.querySelectorAll("button");

                botones.forEach(b => b.disabled = true);
                salida.textContent = "Consultando...";

                try {
                    const respuesta = await fetch(ruta);
                    const datos = await respuesta.json();

                    salida.textContent =
                        "HTTP " + respuesta.status + "\\n\\n" +
                        JSON.stringify(datos, null, 2);
                } catch (error) {
                    salida.textContent = "Error de conexión: " + error;
                } finally {
                    botones.forEach(b => b.disabled = false);
                }
            }
        </script>
    </body>
    </html>
    """


@app.get("/consultar/tasa")
def consultar_tasa():
    try:
        respuesta = requests.get(
            f"{API_BASE_URL}/api/v1/prestamos/tasa",
            timeout=20,
        )

        return JSONResponse(
            status_code=respuesta.status_code,
            content=respuesta.json(),
        )
    except requests.RequestException:
        return JSONResponse(
            status_code=502,
            content={"error": "No se pudo conectar con la API bancaria"},
        )
    except ValueError:
        return JSONResponse(
            status_code=502,
            content={"error": "La API bancaria devolvió una respuesta inválida"},
        )


def obtener_token():
    if not all([
        AUTH0_DOMAIN,
        AUTH0_CLIENT_ID,
        AUTH0_CLIENT_SECRET,
        AUTH0_AUDIENCE,
    ]):
        raise RuntimeError(
            "Falta configurar alguna variable de entorno de Auth0"
        )

    respuesta = requests.post(
        f"https://{AUTH0_DOMAIN}/oauth/token",
        json={
            "client_id": AUTH0_CLIENT_ID,
            "client_secret": AUTH0_CLIENT_SECRET,
            "audience": AUTH0_AUDIENCE,
            "grant_type": "client_credentials",
        },
        timeout=20,
    )

    if not respuesta.ok:
        raise RuntimeError(
            f"Auth0 no pudo emitir el token (HTTP {respuesta.status_code})"
        )

    datos = respuesta.json()
    token = datos.get("access_token")

    if not token:
        raise RuntimeError("Auth0 no devolvió un token de acceso")

    return token


@app.get("/consultar/oferta")
def consultar_oferta():
    try:
        token = obtener_token()

        respuesta = requests.get(
            f"{API_BASE_URL}/api/v1/prestamos/oferta",
            headers={"Authorization": f"Bearer {token}"},
            timeout=20,
        )

        return JSONResponse(
            status_code=respuesta.status_code,
            content=respuesta.json(),
        )
    except RuntimeError as error:
        return JSONResponse(
            status_code=502,
            content={"error": str(error)},
        )
    except requests.RequestException:
        return JSONResponse(
            status_code=502,
            content={"error": "Error de comunicación con Auth0 o la API bancaria"},
        )
    except ValueError:
        return JSONResponse(
            status_code=502,
            content={"error": "Se recibió una respuesta inválida"},
        )


@app.get("/probar/sin-token")
def probar_sin_token():
    try:
        respuesta = requests.get(
            f"{API_BASE_URL}/api/v1/prestamos/oferta",
            timeout=20,
        )

        try:
            datos = respuesta.json()
        except ValueError:
            datos = {"respuesta": respuesta.text}

        return JSONResponse(
            status_code=respuesta.status_code,
            content={
                "prueba": "Solicitud sin token",
                "resultado_esperado": 401,
                "respuesta_api": datos,
            },
        )
    except requests.RequestException:
        return JSONResponse(
            status_code=502,
            content={"error": "No se pudo conectar con la API bancaria"},
        )
