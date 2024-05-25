import dataclasses
import functools
import logging
import os
import re
from dataclasses import dataclass
from itertools import zip_longest
from typing import Callable, Iterable

from natsort import natsorted
from requests import HTTPError
from typing_extensions import Self

from mangadex_mass_uploader.mangadex_api import MangaDexAPI

logger = logging.getLogger("main")


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
    uploader_id: str | None = None

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
            "uploader": self.uploader_id,
            "groups": self.groups,
            "volume": self.volume,
            "chapter": self.chapter,
            "title": self.title,
            "translatedLanguage": self.language,
            "externalUrl": self.external_url,
            "version": self.version,
        }
        if self.external_url is None:
            ch_dict.pop("externalUrl")
        if self.file is None:
            ch_dict.pop("file")
        if self.id is None:
            ch_dict.pop("id")
        if self.version is None:
            ch_dict.pop("version")
        if self.uploader_id is None:
            ch_dict.pop("uploader")
        return ch_dict

    @classmethod
    def from_api(cls, chapter: dict) -> Self:
        groups = [
            relation["id"]
            for relation in chapter["relationships"]
            if relation["type"] == "scanlation_group"
        ]
        groups += [None] * (5 - len(groups))
        uploader_id = [
            relation["id"] for relation in chapter["relationships"] if relation["type"] == "user"
        ]
        uploader_id = uploader_id[0] if len(uploader_id) != 0 else None
        return cls(
            manga_id=[
                relation["id"]
                for relation in chapter["relationships"]
                if relation["type"] == "manga"
            ][0],
            uploader_id=uploader_id,
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
            external_url=chapter["attributes"]["externalUrl"],
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
        if self.uploader_id is not None:
            ch_repr += f"uploader: {self.uploader_id}\n"
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


def parse_upload_input(text_inputs: Iterable, files: list[str]) -> list[Chapter]:
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
    files = files + [None] * (chapter_count - len(files))
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
        try:
            entry = re.sub(r"\s*", "", entry)
            start, end = natsorted(range_element for range_element in entry.split("-", 1))
            range_filters |= {functools.partial(is_in_range, start, end)}
        except (ValueError, TypeError):
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
        logger.exception(f"Could not get chapters from the API")
        return []
    return [Chapter.from_api(chapter) for chapter in chapters]


def fetch_unavailable_chapters(text_inputs: Iterable) -> list[Chapter]:
    filters = parse_edit_filters(text_inputs)
    try:
        chapters = MangaDexAPI().get_unavailable_chapter_list(filters)
    except HTTPError:
        logger.exception(f"Could not get chapters from the API")
        return []
    return [Chapter.from_api(chapter) for chapter in chapters]


def fetch_chapters_from_ids(chapter_ids: list[str]) -> list[Chapter]:
    try:
        chapters = MangaDexAPI().get_chapters_by_id(chapter_ids)
    except HTTPError:
        logger.exception(f"Could not get chapters from the API")
        return []
    return [Chapter.from_api(chapter) for chapter in chapters]


def prepare_chapters_for_restore(chapters: list[Chapter]) -> tuple[list[Chapter], list[Chapter]]:
    # fetch current version of chapts from API and match to restored versions by id
    chapt_dict = {chapt.id: {"restored": chapt} for chapt in chapters}
    fetched_chapts = fetch_chapters_from_ids([chapt_id for chapt_id in chapt_dict])
    for chapt in fetched_chapts:
        chapt_dict[chapt.id]["current"] = chapt
    restored_chapts = []
    current_chapts = []
    for chapt_pair in chapt_dict.values():
        # chapter deleted/disabled/failed to fetch, can't restore
        if "current" not in chapt_pair:
            continue
        restored_chapts.append(chapt_pair["restored"])
        current_chapts.append(chapt_pair["current"])
    return restored_chapts, current_chapts


def parse_edit_inputs(
    text_inputs: Iterable, chapter_count: int
) -> dict[str, list[str | dict[str, str | Callable]]]:
    edited_values: dict[str, list[str | dict[str, str | Callable]]] = {}
    for field_id, element in text_inputs:
        parsed_values: list[str | list] = element.text.split("\n")
        # groups are split by comma and transposed to separate lists
        if field_id == "groups":
            parsed_values = zip_longest(
                *[value.split(",", 4) for value in parsed_values], fillvalue=""
            )
            for idx, values in enumerate(parsed_values):
                edited_values[f"group_{idx + 1}_id"] = list(values)
            continue
        # extract conditional inputs from volume field
        if field_id == "volume":
            cond_vols = [value for value in parsed_values if ":" in value]
            edited_values["conditional_volume"] = parse_conditional_volumes(cond_vols)
            parsed_values = [value for value in parsed_values if ":" not in value]
        edited_values[field_id] = parsed_values
    for field_id, parsed_values in edited_values.items():
        if field_id == "conditional_volume":
            continue
        # single inputs are repeated
        if len(parsed_values) == 1:
            edited_values[field_id] = parsed_values * chapter_count
        # shorter inputs are padded to chapter_count
        edited_values[field_id] += [""] * (chapter_count - len(parsed_values))
    return edited_values


def parse_conditional_volumes(text_input: list[str]) -> list[dict[str, str | Callable]]:
    parsed_input = []
    for entry in text_input:
        parsed_entry = {}
        parsed_entry["new_value"], ch_filter = entry.split(":", 1)
        # empty inputs are ignored
        if parsed_entry["new_value"] == "":
            continue
        # space is used to set field to null
        if parsed_entry["new_value"] == " ":
            parsed_entry["new_value"] = None
        else:
            parsed_entry["new_value"] = parsed_entry["new_value"].strip()

        ch_filter = re.sub(r"\s*", "", ch_filter)
        try:
            start, end = natsorted(range_element for range_element in ch_filter.split("-", 1))
            parsed_entry["filter"] = functools.partial(is_in_range, start, end)
        except ValueError:
            parsed_entry["filter"] = lambda chapter: chapter == ch_filter
        parsed_input.append(parsed_entry)
    return parsed_input


def parse_edits(selected_chapters: list[Chapter], text_inputs: Iterable) -> list[Chapter]:
    edit_values = parse_edit_inputs(text_inputs, len(selected_chapters))
    # conditional vols are done separately later
    cond_vols: list[dict[str, str | callable]] = edit_values.pop("conditional_volume")
    edited_chapters: list[Chapter] = []
    for chapter in selected_chapters:
        new_values = {}
        for field in edit_values:
            new_value = edit_values[field].pop(0)
            # empty inputs are ignored
            if new_value == "":
                continue
            # space is used to set field to null
            if new_value == " ":
                new_value = None
            else:
                new_value = new_value.strip()
            new_values[field] = new_value
        edited_chapter = dataclasses.replace(chapter, **new_values)
        # apply conditional vol changes
        for entry in cond_vols:
            if not entry["filter"](chapter.chapter):
                continue
            edited_chapter.volume = entry["new_value"]
        edited_chapters.append(edited_chapter)
    return edited_chapters
