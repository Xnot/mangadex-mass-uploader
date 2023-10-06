import os
from dataclasses import dataclass
from typing import Iterable


@dataclass
class Chapter:
    manga_id: str | None
    group_1_id: str | None
    group_2_id: str | None
    group_3_id: str | None
    group_4_id: str | None
    group_5_id: str | None
    volume: str | None
    chapter: str | None
    title: str | None
    language: str | None
    external_url: str | None
    file: str | None

    @property
    def groups(self) -> list[str]:
        return [
            self.group_1_id,
            self.group_2_id,
            self.group_3_id,
            self.group_4_id,
            self.group_5_id,
        ]

    def to_api(self) -> dict:
        return {
            "file": self.file,
            "manga": self.manga_id,
            "groups": self.groups,
            "chapter_draft": {
                "volume": self.volume,
                "chapter": self.chapter,
                "title": self.title,
                "translatedLanguage": self.language,
                "externalUrl": self.external_url,
            },
        }

    def __repr__(self):
        return (
            f"--------------------------------------\n"
            f"file: {os.path.basename(str(self.file))}\n"
            f"manga: {self.manga_id}\n"
            f"groups: {[group for group in self.groups if group is not None]}\n"
            f"vol: {self.volume}, ch: {self.chapter}, title: {self.title}, lang: {self.language}\n"
            f"ext_url: {self.external_url}\n"
        )


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
