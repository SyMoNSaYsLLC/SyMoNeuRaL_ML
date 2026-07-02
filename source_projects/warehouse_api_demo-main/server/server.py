from fastapi import FastAPI, HTTPException
from pydantic import BaseModel


class Product(BaseModel):
    units: str
    qty: int


catalog = {
    "tomatoes": Product(units="boxes", qty=1000),
    "wine": Product(units="bottles", qty=500),
    "bread": Product(units="loafs", qty=50),
    "milk": Product(units="bottles", qty=100)
}


app = FastAPI(title="Warehouse API")


@app.get("/products")
async def get_products():
    return list(catalog.keys())


@app.get("/warehouse")
async def get_inventory():
    return {
        name: {
            "units": item.units,
            "qty": item.qty
        }
        for name, item in catalog.items()
    }


@app.get("/warehouse/{product}")
async def load_truck(product, order_qty=0):
    available = catalog[product].qty

    #####################################################
    # Intentional defect for testing:
    # Using >= instead of > incorrectly rejects orders
    # equal to available inventory.
    #####################################################
    if int(order_qty) >= int(available):
        raise HTTPException(
            status_code=400,
            detail=f"Sorry, only {available} units are available, please try again…"
        )

    catalog[product].qty -= int(order_qty)

    return {
        "product": product,
        "order_qty": order_qty,
        "units": catalog[product].units,
        "remaining_qty": catalog[product].qty
    }