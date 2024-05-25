import json
import logging
import os
from time import sleep, time
from typing import IO, Callable
from zipfile import ZipFile

import requests
from natsort import natsorted

from mangadex_mass_uploader.utils import Singleton


class MangaDexAPI(metaclass=Singleton):
    API_URL = "https://api.mangadex.org"
    AUTH_URL = "https://auth.mangadex.org/realms/mangadex/protocol/openid-connect"

    def __init__(self):
        self.logger = logging.getLogger("main")
        self._client_id = None
        self._client_secret = None
        self._session_token = None
        self._refresh_token = None
        self._refresh_at = None

    def login(
        self, username: str, password: str, client_id: str, client_secret: str, remember_me: str
    ):
        token = self.send_request(
            "post",
            "token",
            False,
            auth_url=True,
            data={
                "grant_type": "password",
                "username": username,
                "password": password,
                "client_id": client_id,
                "client_secret": client_secret,
            },
        )
        self._client_id = client_id
        self._client_secret = client_secret
        self._session_token = token["access_token"]
        self._refresh_token = token["refresh_token"]
        self._refresh_at = time() + token["expires_in"] - 5
        if remember_me:
            self.save_login(username)

    def save_login(self, file_name: str):
        with open(f"{os.environ['KIVY_HOME']}/logins/{file_name}.json", "w") as file:
            json.dump(
                {
                    "refresh_token": self._refresh_token,
                    "client_id": self._client_id,
                    "client_secret": self._client_secret,
                },
                file,
            )

    def load_login(self, file_name: str):
        with open(f"{os.environ['KIVY_HOME']}/logins/{file_name}.json", "r") as file:
            creds = json.load(file)
            self._refresh_token = creds["refresh_token"]
            self._client_id = creds["client_id"]
            self._client_secret = creds["client_secret"]
        self._refresh_at = 0
        # update refresh token and re-save
        _ = self.session_token
        self.save_login(file_name)

    @staticmethod
    def on_error(error_message: str):
        raise requests.HTTPError(f"I am not ok: {error_message}")

    def send_request(
        self,
        method: str,
        endpoint: str,
        req_auth: bool = True,
        on_error: Callable[[str | None], None] = on_error,
        auth_url: bool = False,
        **kwargs,
    ) -> dict:
        api_url = self.AUTH_URL if auth_url else self.API_URL
        kwargs |= {"method": method, "url": f"{api_url}/{endpoint}"}
        if req_auth:
            kwargs |= {"headers": {"Authorization": f"Bearer {self.session_token}"}}
        response = requests.request(**kwargs)
        if response.status_code == 429:
            rate_limit_reset = int(response.headers["x-ratelimit-retry-after"])
            sleep(rate_limit_reset - time() + 1)
            response = requests.request(**kwargs)
        if not response.ok:
            error_text = response.json()
            error_text = error_text.get(
                "errors", error_text.get("error_description", error_text.get("error"))
            )
            on_error(error_text)
        return response.json()

    @property
    def session_token(self) -> str:
        if time() > self._refresh_at:
            token = self.send_request(
                "post",
                "token",
                False,
                auth_url=True,
                data={
                    "grant_type": "refresh_token",
                    "refresh_token": self._refresh_token,
                    "client_id": self._client_id,
                    "client_secret": self._client_secret,
                },
            )
            self._session_token = token["access_token"]
            self._refresh_token = token["refresh_token"]
            self._refresh_at = time() + token["expires_in"] - 5
        return self._session_token

    @property
    def upload_session(self) -> str | None:
        response = self.send_request("get", "upload", on_error=lambda error: None)
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
        self.start_upload(chapter.pop("manga"), chapter.pop("groups"))
        page_order = []
        if "file" in chapter:
            with ZipFile(chapter.pop("file")) as file:
                pages = [
                    page
                    for page in natsorted(file.namelist())
                    if page.endswith((".jpg", ".jpeg", ".png", ".gif"))
                ]
                for page in pages:
                    page_order.append(self.upload_page(file.open(page)))
        self.commit_upload(chapter, page_order)

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
            filters["volume[]"] = [
                "none" if value is None else value for value in filters["volume[]"]
            ]
        # chapter number filter is done client-side since API only accepts 1 chapter
        chapter_filter = filters.pop("chapter numbers")
        response = self.send_request("get", "chapter", False, params=filters)
        total_chapters = response["total"]
        if total_chapters > 10_000:
            self.logger.warn(
                "There are more than 10,000 chapters selected, only the first 10,000 can be fetched."
            )
        chapter_list = response["data"]
        while len(chapter_list) < total_chapters and filters["offset"] < 10_000 - 100:
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

    def get_unavailable_chapter_list(self, filters: dict) -> list[dict]:
        # API gets mad if you request shit with no filters so just return nothing
        if all(value is None for value in filters.values()):
            return []
        # some hardcoded params
        filters["limit"] = 100
        filters["offset"] = 0
        # replace None with "none" for volumes
        if filters["volume[]"] is not None:
            filters["volume[]"] = [
                "none" if value is None else value for value in filters["volume[]"]
            ]
        # chapter number filter is done client-side since API only accepts 1 chapter
        chapter_filter = filters.pop("chapter numbers")
        volume_filter = filters.pop("volume[]")
        response = self.send_request("get", "admin/chapter", params=filters)
        total_chapters = response["total"]
        if total_chapters > 10_000:
            self.logger.warn(
                "There are more than 10,000 chapters selected, only the first 10,000 can be fetched."
            )
        chapter_list = response["data"]
        while len(chapter_list) < total_chapters and filters["offset"] < 10_000 - 100:
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
        if volume_filter is not None:
            chapter_list_filtered = []
            for chapter in chapter_list:
                if chapter["attributes"]["volume"] in volume_filter:
                    chapter_list_filtered.append(chapter)
            chapter_list = chapter_list_filtered
        return chapter_list

    def get_chapters_by_id(self, chapter_ids: list[str]) -> list[dict]:
        chapter_list = []
        if len(chapter_ids) == 0:
            return chapter_list
        # some hardcoded params
        filters = {
            "limit": 100,
            "offset": 0,
            "contentRating[]": ["safe", "suggestive", "erotica", "pornographic"],
        }
        # request 100 ids at a time
        while len(chapter_ids) > 0:
            filters["ids[]"] = chapter_ids[:100]
            chapter_ids = chapter_ids[100:]
            response = self.send_request("get", "chapter", False, params=filters)
            chapter_list.extend(response["data"])
        return chapter_list

    def edit_chapter(self, chapter: dict) -> None:
        chapter.pop("manga")
        chapter.pop("uploader", None)
        chapter_id = chapter.pop("id")
        self.send_request("put", f"chapter/{chapter_id}", json=chapter)

    def delete_chapter(self, chapter_id: str) -> None:
        self.send_request("delete", f"chapter/{chapter_id}")

    def deactivate_chapter(self, chapter_id: str) -> None:
        self.send_request("delete", f"admin/chapter/{chapter_id}/activate")

    def reactivate_chapter(self, chapter_id: str) -> None:
        self.send_request("post", f"admin/chapter/{chapter_id}/activate")

    def restore_chapter(self, chapter_id: str) -> None:
        self.send_request("post", f"admin/chapter/{chapter_id}/restore")

    def edit_chapter_manga(self, chapter_id: str, manga_id: str) -> None:
        self.send_request("post", f"admin/chapter/{chapter_id}/move", json={"manga": manga_id})

    def edit_chapter_uploader(self, chapter_id: str, uploader_id: str) -> None:
        self.send_request("put", f"admin/chapter/{chapter_id}", json={"uploader": uploader_id})
