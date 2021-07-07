from zipfile import ZipFile

import requests


class MangaDexAPI:
    endpoint = "https://api.mangadex.org"

    def __init__(self):
        self.__refresh = None
        self.__session = None

    def login(self, username, password):
        response = requests.post(f"{MangaDexAPI.endpoint}/auth/login",
                                 json={"username": username, "password": password})
        if not response.ok:
            raise requests.HTTPError(f"MD API error - {response.status_code}: {response.reason}")
        response = response.json()["token"]
        self.__session = response["session"]
        self.__refresh = response["refresh"]
        # TODO actually use refresh token on expire

    def upload_chapter(self, chapter):
        # delete any existing upload session
        existing_session_resp = requests.get(f"{MangaDexAPI.endpoint}/upload/",
                                             headers={"Authorization": f"Bearer {self.__session}"})
        if existing_session_resp.ok:
            session_id = existing_session_resp.json()["data"]["id"]
            del_session_resp = requests.delete(f"{MangaDexAPI.endpoint}/upload/{session_id}",
                                               headers={"Authorization": f"Bearer {self.__session}"})
            if not del_session_resp.ok:
                raise requests.HTTPError(f"MD API error - {del_session_resp.status_code}: {del_session_resp.reason}")
        elif not existing_session_resp.status_code == 404:
            raise requests.HTTPError(f"MD API error - {existing_session_resp.status_code}: {existing_session_resp.reason}")

        # actual upload part
        response = requests.post(f"{MangaDexAPI.endpoint}/upload/begin",
                                 json={"groups": [group for group in chapter.groups if group is not None],
                                       "manga": chapter.manga},
                                 headers={"Authorization": f"Bearer {self.__session}"})
        if not response.ok:
            raise requests.HTTPError(f"MD API error - {response.status_code}: {response.reason}")
        session_id = response.json()["data"]["id"]
        page_ids = []
        with ZipFile(chapter.file.name) as file:
            for page in file.namelist():
                if not page.endswith((".jpg", ".jpeg", ".png", ".gif")):
                    continue
                response = requests.post(f"{MangaDexAPI.endpoint}/upload/{session_id}",
                                         files={"page": file.open(page)},
                                         headers={"Authorization": f"Bearer {self.__session}"})
                if not response.ok:
                    raise requests.HTTPError(f"MD API error - {response.status_code}: {response.reason}")
                page_ids.append(response.json()["data"][0]["id"])
        response = requests.post(f"{MangaDexAPI.endpoint}/upload/{session_id}/commit",
                                 json={"chapterDraft": {"volume": chapter.volume,
                                                        "chapter": chapter.chapter,
                                                        "title": chapter.title,
                                                        "translatedLanguage": chapter.translatedLanguage},
                                       "pageOrder": page_ids},
                                 headers={"Authorization": f"Bearer {self.__session}"})
        if not response.ok:
            raise requests.HTTPError(f"MD API error - {response.status_code}: {response.reason}")
