import time

import psutil

# build secret can only be retrieved automatically with static analysis which I'm too stupid to do. so I'll try to keep
# these updated.
BUILD_ID = "-1885667689"
FEATURE_SET = "PrimeUpdate60_1"
BUILD_SECRET = "76656a5b51ec57a13549eef732c8a8367638aa3a7989bade1f7e4e5f93d57625"


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


def main() -> None:
    print("**** drop opener ****")
    print("Launch rocket league, I will detect it once it's started.")
    process = get_rocket_league_process()
    process.terminate()
    print("cmdline:", process.cmdline())
