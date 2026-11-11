import asyncio
import threading
import time
import tkinter as tk
import typing

import psutil

from drop_opener import products, rlapi
from drop_opener.products import get_products
from drop_opener.rlapi import PsyNetConnection

type LogFn = typing.Callable[[str], None]


class TkinterTerminal:
    def __init__(self, fun: typing.Callable[[LogFn], typing.Awaitable[None]]):
        self.root = tk.Tk()
        self.root.title("drop opener")
        self.root.geometry("400x600")
        self.root.grid_rowconfigure(0, weight=1)
        self.root.grid_columnconfigure(0, weight=1)

        self.text_box = tk.Text(self.root, wrap=tk.WORD, fg="white", bg="black")
        self.text_box.tag_configure("error", foreground="yellow")
        self.text_box.grid(row=0, column=0, sticky=tk.NSEW)

        run_thread = threading.Thread(
            target=asyncio.run, args=(self._run(fun),), daemon=True
        )
        run_thread.start()

        self.root.mainloop()

    async def _run(
        self,
        fun: typing.Callable[[LogFn], typing.Awaitable[None]],
    ):
        try:
            await fun(lambda text: self._log(text))
        except Exception as e:  # noqa: BLE001
            self._logerr(f"\n{type(e)}:\n{e}")

    def _log(self, text: str):
        self.text_box.insert(tk.END, "\n" + text)

    def _logerr(self, text: str):
        start_index = self.text_box.index(tk.END)
        self.text_box.insert(tk.END, "\n" + text, "error")
        self.text_box.tag_add("error", start_index, tk.END)


def get_rocket_league_process(log: LogFn) -> psutil.Process:
    class RLAlreadyStartedException(Exception): ...

    log("Waiting for rocket league process...")
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

                log("Got rocket league process!")
                return process

        first_try = False
        time.sleep(0.1)


async def main(log: typing.Callable[[str], None]) -> None:
    log("**** drop opener ****")
    log("Launch rocket league, I will detect it once it's started.")
    process = get_rocket_league_process(log)
    process.terminate()
    cmdline = " ".join(process.cmdline())
    exchange_code = cmdline.split("-AUTH_PASSWORD=")[1].split(" ")[0]

    log("\nLogging in to PsyNet...")
    psynet = await PsyNetConnection.log_in_with_exchange_code(exchange_code)
    log("Logged in to PsyNet.")

    log("\nFetching products...")
    product_database = await get_products()
    log(f"Fetched product database ({len(product_database)} items)")

    log("\nFetching inventory...")
    inventory = await psynet.inventory()
    log(f"Fetched inventory ({len(inventory.ProductData)} items)")
    to_open = filter_openable_drops(inventory.ProductData, product_database)
    log(f"Total {len(to_open)} drops to open.")

    if len(to_open) == 0:
        log("No drops to open, quitting")
        return

    log("\nAbout to open drops...")
    drop_results = await psynet.open_containers([x.InstanceID for x in to_open])
    log("Results:")
    for drop in drop_results.Drops:
        product = product_database[drop.ProductID]
        log(f" - {product.name} ({fix_quality_name(product.quality)} {product.slot})")

    await psynet.close()


QUALITY_RENAMES = {
    "Common": "Base",
    "Uncommon": "Sport",
    "Rare": "Special",
    "Very Rare": "Deluxe",
    "Limited": "Luxury",
}


def fix_quality_name(original: str) -> str:
    return QUALITY_RENAMES.get(original) or original


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
    TkinterTerminal(main)
