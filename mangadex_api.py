import logging
from time import time
from typing import IO, Union
from zipfile import ZipFile

import requests
from natsort import natsorted


class MangaDexAPI:
    API_URL = "https://api.mangadex.org"

    def __init__(self):
        self.logger = self.logger = logging.getLogger("api_logger")
        self._session_token = None
        self._refresh_token = None
        self._refresh_at = None

    def login(self, username: str, password: str):
        token = self.send_request(
            "post",
            "auth/login",
            False,
            json={"username": username, "password": password},
        )
        self._session_token = token["token"]["session"]
        self._refresh_token = token["token"]["refresh"]
        self._refresh_at = time() + 880
        if self.upload_session:
            self.logger.warning("You have an existing upload session. It will be deleted once uploading begins.")

    def __del__(self):
        self.send_request("post", "auth/logout")

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
            raise requests.HTTPError(f"I am not ok: {response['errors']}")
        return response

    @property
    def session_token(self) -> str:
        if time() > self._refresh_at:
            response = self.send_request("post", "auth/refresh", False, json={"token": self._refresh_token})
            self._session_token = response["token"]["session"]
            self._refresh_at = time() + 880
        return self._session_token

    @property
    def upload_session(self) -> Union[str, None]:
        response = self.send_request("get", "upload", suppress_error=True)
        if response["result"] == "ok":
            return response["data"]["id"]

    # TODO treat errors
    def start_upload(self, manga: str, groups: list[str]) -> None:
        if self.upload_session:
            self.send_request("delete", f"upload/{self.upload_session}")
        self.send_request("post", "upload/begin", json={"manga": manga, "groups": groups})

    # TODO batch pages
    # TODO treat errors
    def upload_page(self, page: IO[bytes]) -> str:
        response = self.send_request("post", f"upload/{self.upload_session}", files={"page": page})
        return response["data"][0]["id"]

    def commit_upload(self, chapter_draft: dict[str, str], page_order: list[str]) -> None:
        self.send_request(
            "post",
            f"upload/{self.upload_session}/commit",
            json={"chapterDraft": chapter_draft, "pageOrder": page_order},
        )

    def upload_chapter(self, chapter: dict) -> None:
        self.start_upload(chapter["manga"], chapter["groups"])
        with ZipFile(chapter["file"]) as file:
            pages = [page for page in natsorted(file.namelist()) if page.endswith((".jpg", ".jpeg", ".png", ".gif"))]
            page_order = []
            for page in pages:
                page_order.append(self.upload_page(file.open(page)))
        self.commit_upload(chapter["chapter_draft"], page_order)
