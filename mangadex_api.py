import logging
from time import time, sleep
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
        response = requests.request(**kwargs)
        if response.status_code == 429:
            rate_limit_reset = int(response.headers["x-ratelimit-retry-after"])
            sleep(rate_limit_reset - time() + 1)
            response = requests.request(**kwargs)
        if not response.ok and not suppress_error:
            raise requests.HTTPError(f"I am not ok: {response.json()['errors']}")
        return response.json()

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

    def start_upload(self, manga: str, groups: list[str]) -> None:
        if self.upload_session:
            self.send_request("delete", f"upload/{self.upload_session}")
        self.send_request("post", "upload/begin", json={"manga": manga, "groups": groups})

    # TODO batch pages
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

    def get_chapter_list(self, filters: dict) -> list[dict]:
        # API gets mad if you request shit with no filters so just return nothing
        if all(value is None for value in filters.values()):
            return []
        # some hardcoded params
        filters["limit"] = 100
        filters["offset"] = 0
        filters["contentRating[]"] = ["safe", "suggestive", "erotica", "pornographic"]
        # replace None with "none" for volumes
        if filters["volume[]"] is not None:
            filters["volume[]"] = ["none" if value is None else value for value in filters["volume[]"]]
        # chapter number filter is done client-side since API only accepts 1 chapter
        chapter_filter = filters.pop("chapter numbers")
        response = self.send_request("get", "chapter", False, params=filters)
        total_chapters = response["total"]
        chapter_list = response["data"]
        while len(chapter_list) < total_chapters:
            filters["offset"] += 100
            chapter_list.extend(self.send_request("get", "chapter", False, params=filters)["data"])
        # apply chapter number filter
        if chapter_filter is not None:
            chapter_list_filtered = []
            for chapter in chapter_list:
                if chapter["attributes"]["chapter"] in chapter_filter["normal_filters"]:
                    chapter_list_filtered.append(chapter)
                    continue
                for range_check in chapter_filter["range_filters"]:
                    if range_check(chapter["attributes"]["chapter"]):
                        chapter_list_filtered.append(chapter)
                        break
            chapter_list = chapter_list_filtered
        return chapter_list

    def edit_chapter(self, chapter: dict) -> None:
        chapter.pop("manga")
        chapter_id = chapter.pop("id")
        self.send_request("put", f"chapter/{chapter_id}", json=chapter)

    def delete_chapter(self, chapter_id: str) -> None:
        self.send_request("delete", f"chapter/{chapter_id}")
