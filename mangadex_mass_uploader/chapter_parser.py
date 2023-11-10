import functools
import os
import re
from dataclasses import dataclass
from typing import Callable, Iterable, Self

from kivy import Logger
from natsort import natsorted
from requests import HTTPError

from mangadex_mass_uploader.mangadex_api import MangaDexAPI


@dataclass
class Chapter:
    manga_id: str
    group_1_id: str | None
    group_2_id: str | None
    group_3_id: str | None
    group_4_id: str | None
    group_5_id: str | None
    volume: str | None
    chapter: str | None
    title: str | None
    language: str
    external_url: str | None = None
    file: str | None = None
    id: str | None = None
    version: int | None = None

    @property
    def groups(self) -> list[str]:
        groups = [
            self.group_1_id,
            self.group_2_id,
            self.group_3_id,
            self.group_4_id,
            self.group_5_id,
        ]
        return [group for group in groups if group is not None]

    def to_api(self) -> dict:
        ch_dict = {
            "id": self.id,
            "file": self.file,
            "manga": self.manga_id,
            "groups": self.groups,
            "volume": self.volume,
            "chapter": self.chapter,
            "title": self.title,
            "translatedLanguage": self.language,
            "externalUrl": self.external_url,
            "version": self.version,
        }
        if self.id is None:
            ch_dict.pop("id")
        if self.file is None:
            ch_dict.pop("file")
        if self.external_url is None:
            ch_dict.pop("externalUrl")
        if self.version is None:
            ch_dict.pop("version")
        return ch_dict

    @classmethod
    def from_api(cls, chapter: dict) -> Self:
        groups = [
            relation["id"]
            for relation in chapter["relationships"]
            if relation["type"] == "scanlation_group"
        ]
        groups += [None] * (5 - len(groups))
        return cls(
            manga_id=[
                relation["id"]
                for relation in chapter["relationships"]
                if relation["type"] == "manga"
            ][0],
            group_1_id=groups[0],
            group_2_id=groups[1],
            group_3_id=groups[2],
            group_4_id=groups[3],
            group_5_id=groups[4],
            id=chapter["id"],
            volume=chapter["attributes"]["volume"],
            chapter=chapter["attributes"]["chapter"],
            title=chapter["attributes"]["title"],
            language=chapter["attributes"]["translatedLanguage"],
            version=chapter["attributes"]["version"],
        )

    def __repr__(self):
        ch_repr = f"--------------------------------------\n"
        if self.id is not None:
            ch_repr += f"id: {self.id}\n"
        if self.version is not None:
            ch_repr += f"version: {self.version}\n"
        if self.file is not None:
            ch_repr += f"file: {os.path.basename(str(self.file))}\n"
        if self.external_url is not None:
            ch_repr += f"ext_url: {self.external_url}\n"
        ch_repr += (
            f"manga: {self.manga_id}\n"
            f"groups: {self.groups}\n"
            f"vol: {self.volume}, ch: {self.chapter}, "
            f"title: {self.title}, lang: {self.language}\n"
        )
        return ch_repr


def split_inputs(inputs: Iterable) -> dict[str, list[str]]:
    inputs_dict = {}
    for field_id, element in inputs:
        inputs_dict[field_id] = [value.strip() for value in element.text.split("\n")]
    return inputs_dict


def parse_upload_input(text_inputs: Iterable, files: list) -> list[Chapter]:
    inputs = split_inputs(text_inputs)
    chapter_count = max(len(files), *map(len, inputs.values()))
    if not chapter_count:
        return []
    # if one numerical chapter is inputted, the subsequent chapters are incremented by 1
    if len(inputs["chapter"]) == 1 and inputs["chapter"][0].isdigit():
        first_digit = int(inputs["chapter"][0])
        inputs["chapter"] = [
            str(value) for value in range(first_digit, first_digit + chapter_count)
        ]
    for field_id, values in inputs.items():
        # for non-numerical chapter and other fields, single inputs are repeated
        if len(values) == 1:
            values = values * chapter_count
        # get rid of invalid/extra inputs
        values = [None if value == "" else value for value in values]
        # pad list to match chapter count
        values += [None] * (chapter_count - len(values))
        inputs[field_id] = values
    # pad file list and add to inputs
    files += [None] * (chapter_count - len(files))
    inputs["file"] = files
    return [
        Chapter(**{key: val[idx] for key, val in inputs.items()}) for idx in range(chapter_count)
    ]


def parse_edit_filters(text_inputs: Iterable) -> dict[str, None | set[None | str | dict]]:
    filters = {}
    for field_id, element in text_inputs:
        split_values = element.text.split("\n")
        if len(split_values) == 1 and split_values[0] == "":
            filters[field_id] = None
            continue
        filters[field_id] = {None if value == "" else value for value in split_values}
        if field_id == "chapter numbers":
            filters[field_id] = parse_range_filters(filters[field_id])
    return filters


def parse_range_filters(filter_set: set[None | str]) -> dict[str, set[None | str | Callable]]:
    normal_filters = set()
    range_filters = set()
    for entry in filter_set:
        entry = re.sub(r"\s*", "", entry)
        try:
            start, end = natsorted(range_element for range_element in entry.split("-", 1))
            range_filters |= {functools.partial(is_in_range, start, end)}
        except (ValueError, AttributeError):
            normal_filters |= {entry}
    return {"normal_filters": normal_filters, "range_filters": range_filters}


def is_in_range(start: str, end: str, chapter: None | str) -> bool:
    if chapter is None:
        return False
    # fallbacks for trailing -
    if start == "":
        return chapter == end
    if end == "":
        return chapter == start
    # fallbacks for non-numerical bullshit
    num_pattern = r"[0-9]+(\.[0-9]+)?"
    chapter_match = re.search(num_pattern, chapter)
    start_match = re.search(num_pattern, start)
    end_match = re.search(num_pattern, end)
    if any([chapter_match is None, start_match is None, end_match is None]):
        return chapter == start or chapter == end
    # here we pretend that we don't know math for asdf
    if "." not in end_match[0]:
        return float(start_match[0]) <= float(chapter_match[0]) < int(end_match[0]) + 1
    # real range check, just in case the user actually does the right thing
    return float(start_match[0]) <= float(chapter_match[0]) <= float(end_match[0])


def fetch_chapters(text_inputs: Iterable) -> list[Chapter]:
    filters = parse_edit_filters(text_inputs)
    try:
        chapters = MangaDexAPI().get_chapter_list(filters)
    except HTTPError:
        Logger.exception(f"Could not get chapters from the API")
        return []
    return [Chapter.from_api(chapter) for chapter in chapters]
