from time import time
from typing import IO, Union

import requests


class MangaDexAPI:
    API_URL = "https://api.mangadex.org"

    def __init__(self, username: str, password: str):
        token = self.send_request(
            "post",
            "auth/login",
            False,
            json={"username": username, "password": password},
        )
        self._session_token = token["token"]["session"]
        self._refresh_token = token["token"]["refresh"]
        self._refresh_at = time() + 880
        self._upload_session = self.get_upload_session()
        if self._upload_session:
            # TODO wrap in logger
            print("upload session will get nuked btw")

    def __del__(self):
        self.send_request("post", "auth/logout", True)

    def send_request(
        self,
        method: str,
        endpoint: str,
        req_auth: bool = True,
        suppress_error: bool = False,
        **kwargs,
    ) -> dict:
        kwargs |= {"method": method, "url": f"{self.API_URL}/{endpoint}"}
        if req_auth:
            kwargs |= {"headers": {"Authorization": f"Bearer {self.session_token}"}}
        response = requests.request(**kwargs).json()
        if not suppress_error and response["result"] != "ok":
            # TODO wrap in logger
            raise requests.HTTPError(f"I am not ok: {response['errors']}")
        return response

    @property
    def session_token(self) -> str:
        if time() > self._refresh_at:
            response = self.send_request("post", "auth/refresh", False, json={"token": self._refresh_token})
            self._session_token = response["token"]["session"]
            self._refresh_at = time() + 880
        return self._session_token

    def get_upload_session(self) -> Union[str, None]:
        response = self.send_request("get", "upload", suppress_error=True)
        if response["result"] == "ok":
            return response["data"]["id"]

    def start_upload(self, manga: str, groups: Union[list[str], None] = None) -> None:
        if self._upload_session:
            self.send_request("delete", f"upload/{self._upload_session}")
        if groups is None:
            groups = []
        response = self.send_request("post", "upload/begin", json={"manga": manga, "groups": groups})
        self._upload_session = response["data"]["id"]

    # TODO batch pages
    def upload_page(self, page: IO[bytes]) -> str:
        response = self.send_request("post", f"upload/{self._upload_session}", files={"page": page})
        return response["data"][0]["id"]

    def commit_upload(self, chapter_draft: dict[str, str], page_order: list[str]) -> None:
        self.send_request(
            "post",
            f"upload/{self._upload_session}/commit",
            json={"chapter_draft": chapter_draft, "page_order": page_order},
        )

    def upload_chapter(self, chapter: dict) -> None:
        self.start_upload(chapter["manga"], chapter["groups"])
        for page in chapter["pages"]:
            self.upload_page(page)
        self.commit_upload(chapter["chapter_draft"], chapter["pages"].keys())
