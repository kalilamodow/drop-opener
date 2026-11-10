"""
Fetches the products file from toga-files to get the current crate drop ids
"""

import csv
from dataclasses import dataclass
from io import StringIO

import httpx2

URL = "https://raw.githubusercontent.com/ShinyEmii/Toga-Files/refs/heads/master/products.csv"


@dataclass
class ProductDefinition:
    name: str
    slot: str
    quality: str


async def get_products() -> dict[int, ProductDefinition]:
    async with httpx2.AsyncClient() as client:
        response = await client.get(URL)
        response = response.text

    io = StringIO(response)
    reader = csv.reader(io)

    result = {}
    reader.__next__()  # skip header
    for product_definition in reader:
        id = product_definition[0]
        label = product_definition[2]
        slot = product_definition[3]
        quality = product_definition[4]

        result[int(id)] = ProductDefinition(label, slot, quality)

    return result
