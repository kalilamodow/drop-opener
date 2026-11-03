import asyncio
import time

import psutil

from drop_opener.rlapi import PsyNet


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

    psynet = await PsyNet.log_in_with_exchange_code(exchange_code)


def _start():
    asyncio.run(main())
