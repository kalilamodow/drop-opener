import asyncio
import pprint
import time

import psutil

from drop_opener import products, rlapi
from drop_opener.products import get_products
from drop_opener.rlapi import PsyNetConnection


def get_rocket_league_process() -> psutil.Process:
    class RLAlreadyStartedException(Exception): ...

    print("Waiting for rocket league process...")
    first_try = True

    while True:
        for process in psutil.process_iter():
            try:
                exe = process.exe()
            except psutil.AccessDenied:
                continue

            if "RocketLeague.exe" in exe:
                if first_try:
                    raise RLAlreadyStartedException(
                        "Looks like rocket league was already open. Only launch it once I'm ready!"
                    )

                print("Got rocket league process!")
                return process

        first_try = False
        time.sleep(0.1)


async def main() -> None:
    print("**** drop opener ****")
    print("Launch rocket league, I will detect it once it's started.")
    process = get_rocket_league_process()
    process.terminate()
    cmdline = " ".join(process.cmdline())
    exchange_code = cmdline.split("-AUTH_PASSWORD=")[1].split(" ")[0]

    print()
    psynet = await PsyNetConnection.log_in_with_exchange_code(exchange_code)
    print("Logged in to PsyNet.")

    print()
    print("Fetching products...")
    product_database = await get_products()
    print(f"Fetched product database ({len(product_database)} items)")

    print()
    print("Fetching inventory...")
    inventory = await psynet.inventory()
    print(f"Fetched inventory ({len(inventory.ProductData)} items)")
    to_open = filter_openable_drops(inventory.ProductData, product_database)
    print(f"Total {len(to_open)} drops to open.")

    await psynet.close()


def filter_openable_drops(
    inventory: list[rlapi.PsyNetProduct],
    database: dict[int, products.ProductDefinition],
) -> list[rlapi.PsyNetProduct]:
    return [
        product
        for product in inventory
        if database[product.ProductID].slot == "Crate"  # is a drop
    ]


def _start():
    asyncio.run(main())
