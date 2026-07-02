import os
import requests
from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates


API_URL = os.getenv("API_URL", "http://server:8000/warehouse")
PRODUCTS_URL = os.getenv("PRODUCTS_URL", "http://server:8000/products")

app = FastAPI(title="Warehouse Client")

app.mount(
    "/static",
    StaticFiles(directory="static"),
    name="static"
)

templates = Jinja2Templates(directory="templates")


@app.get("/", response_class=HTMLResponse)
def form(request: Request):
    r = requests.get(PRODUCTS_URL)
    products = r.json()

    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "products": products
        }
    )


@app.post("/", response_class=HTMLResponse)
def send(
    request: Request,
    product: str = Form(...),
    order_qty: str = Form("")
):
    r = requests.get(
        f"{API_URL}/{product}",
        params={"order_qty": order_qty}
    )
    data = r.json()

    return templates.TemplateResponse(
        request=request,
        name="result.html",
        context={
            "result": data
        }
    )


@app.get("/inventory", response_class=HTMLResponse)
def inventory(request: Request):
    r = requests.get(API_URL)
    data = r.json()

    return templates.TemplateResponse(
        request=request,
        name="inventory.html",
        context={
            "inventory": data
        }
    )