"""
Provides a wrapper around psynet.
"""
# please star https://github.com/dank/rlapi!

import base64
import contextlib
import hashlib
import hmac
import json
from dataclasses import dataclass

import httpx2
import httpx2.websockets
import msgspec


def generate_psy_sig(body: str) -> str:
    PSY_KEY = b"c338bd36fb8c42b1a431d30add939fc7"
    digest = hmac.new(PSY_KEY, f"-{body}".encode(), hashlib.sha256).digest()

    return base64.b64encode(digest).decode("utf-8")


# build secret can only be retrieved automatically with static analysis which I'm too stupid to do. so I'll try to keep
# these updated.
BUILD_ID = "-1885667689"
FEATURE_SET = "PrimeUpdate60_1"
BUILD_SECRET = "76656a5b51ec57a13549eef732c8a8367638aa3a7989bade1f7e4e5f93d57625"

RL_EOS_DEPLOYMENT_ID = "da32ae9c12ae40e8a112c52e1f17f3ba"
RL_EOS_CLIENT_ID = "xyza7891p5D7s9R6Gm6moTHWGloerp7B"
RL_EOS_CLIENT_PASSWORD = "Knh18du4NVlFs+3uQ+ZPpDCVto0WYf4yXP8+OcwVt1o"


def eos_authorization_header():
    val = f"{RL_EOS_CLIENT_ID}:{RL_EOS_CLIENT_PASSWORD}"
    b64 = base64.b64encode(val.encode()).decode()
    header = f"Basic {b64}"
    return header


class EOSPsyNetAuthentication(msgspec.Struct):
    access_token: str
    account_id: str

    @staticmethod
    async def from_exchange_code(exchange_code: str) -> EOSPsyNetAuthentication:
        async with httpx2.AsyncClient() as client:
            response = await client.post(
                "https://api.epicgames.dev/epic/oauth/v2/token",
                data={
                    "grant_type": "exchange_code",
                    "scope": "basic_profile friends_list presence friends_management country openid",
                    "exchange_code": exchange_code,
                    "deployment_id": RL_EOS_DEPLOYMENT_ID,
                },
                headers={
                    # content type is auto set by requests i think
                    "Accept": "application/json",
                    "Authorization": eos_authorization_header(),
                    "User-Agent": "EOS-SDK/1.19.2.2-58776509 (Windows/10.0.26100.9549.64bit) Rocket League/261013.63066.530866",
                    "X-EOS-Version": "1.19.2.2-58776509",
                },
            )

        print(response.text)
        return msgspec.json.decode(response.text, type=EOSPsyNetAuthentication)


class PsyNetConnectionAuthenticationResponse(msgspec.Struct):
    Result: PsyNetConnectionAuthentication


class PsyNetConnectionAuthentication(msgspec.Struct):
    PerConURLv2: str
    SessionID: str
    PsyToken: str

    @staticmethod
    async def from_eos_authentication(
        eos: EOSPsyNetAuthentication,
    ) -> PsyNetConnectionAuthentication:
        data = {
            "Platform": "Epic",
            "PlayerName": "",
            "PlayerID": eos.account_id,
            "Language": "INT",
            "AuthTicket": eos.access_token,
            "BuildRegion": "",
            "FeatureSet": FEATURE_SET,
            "Device": "PC",
            "bSkipAuth": False,
            "bSetAsPrimaryAccount": True,
            "EpicAuthTicket": eos.access_token,
            "EpicAccountID": eos.account_id,
            "LocalFirstPlayerID": f"Epic|{eos.account_id}|0",
        }
        data = json.dumps(data)

        async with httpx2.AsyncClient() as client:
            response = await client.post(
                "https://api.rlpp.psynet.gg/rpc/Auth/AuthPlayer/v2",
                content=data,
                headers={
                    "Content-Type": "application/x-www-form-urlencoded",  # idk either
                    "PsyBuildID": BUILD_ID,
                    "PsyRequestID": "PsyNetMessage_X_0",
                    "PsySig": generate_psy_sig(data),
                    "PsyEnvironment": "Prod",
                    "User-Agent": "RL Win/260602.75104.519749 gzip (x86_64-pc-win32) curl-7.67.0 Schannel",
                    "PsyBuildSecret": BUILD_SECRET,
                },
            )

        print(response.text)
        return msgspec.json.decode(
            response.text, type=PsyNetConnectionAuthenticationResponse
        ).Result


@dataclass
class PsyNetConnection:
    _ctx: contextlib.AsyncExitStack
    _client: httpx2.AsyncClient
    _socket: httpx2.websockets.AsyncWebSocketSession

    _idem = 1  # the http request uses 0

    @staticmethod
    async def connect(auth: PsyNetConnectionAuthentication) -> PsyNetConnection:
        ctx = contextlib.AsyncExitStack()
        client = await ctx.enter_async_context(httpx2.AsyncClient())
        socket = await ctx.enter_async_context(
            client.websocket(
                auth.PerConURLv2,
                headers={
                    "PsyToken": auth.PsyToken,
                    "PsySessionID": auth.SessionID,
                    "PsyBuildID": BUILD_ID,
                    "PsyEnvironment": "Prod",
                },
            )
        )

        return PsyNetConnection(ctx, client, socket)

    @staticmethod
    async def log_in_with_exchange_code(exchange_code: str) -> PsyNetConnection:
        return await PsyNetConnection.connect(
            await PsyNetConnectionAuthentication.from_eos_authentication(
                await EOSPsyNetAuthentication.from_exchange_code(exchange_code)
            )
        )
