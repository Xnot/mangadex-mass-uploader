from dataclasses import dataclass
from itertools import zip_longest
from typing import Iterable


@dataclass
class Chapter:
    manga: str
    groups: list[str]
    volume: str
    chapter: str
    title: str
    translatedLanguage: str
    externalUrl: str | None
    file: str | None


def split_inputs(inputs: Iterable) -> dict[str, list[str]]:
    inputs_dict = {}
    for field_id, element in inputs:
        inputs_dict[field_id] = [value.strip() for value in element.text.split("\n")]
    return inputs_dict


def parse_upload_input(text_inputs: Iterable, files: list) -> list[Chapter]:
    inputs = split_inputs(text_inputs)
    file_count = len(files)
    ext_url_count = len(inputs["external_url"])
    chapter_count = max(file_count, ext_url_count)
    if not chapter_count:
        return []
    chapters = {"file": files}
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
        values = values[:chapter_count]
        chapters[field_id] = values
    # transpose into [{"file": 1, "chapter": 1}, {"file": 2, "chapter": 2}]
    chapter_dicts = []
    for chapter in zip_longest(*chapters.values()):
        ch_dict = {key: value for key, value in zip(chapters.keys(), chapter)}
        ch_dict["manga"] = ch_dict.pop("manga_id")
        ch_dict["groups"] = [
            ch_dict.pop(f"group_{idx}_id") for idx in range(1, 6) if ch_dict[f"group_{idx}_id"]
        ]
        ch_dict["chapter_draft"] = {
            "volume": ch_dict.pop("volume"),
            "chapter": ch_dict.pop("chapter"),
            "title": ch_dict.pop("title"),
            "translatedLanguage": ch_dict.pop("language"),
            "externalUrl": ch_dict.pop("external_url"),
        }
        chapter_dicts.append(ch_dict)
    return chapter_dicts
