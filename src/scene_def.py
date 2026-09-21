"""scene_def.py — scene_definition.json の走査ヘルパー (, 2026-09-19)。

`sd["sections"][i]["scenes"][j]` の入れ子を歩く `_iter_scenes` が src / scripts の 5 か所に
別々に書かれていた (欠けたキーや None の扱いが微妙に違う)。ここに 1 つ置く。

    from scene_def import iter_scenes
    for scene in iter_scenes(scene_def): ...
"""

from __future__ import annotations

from collections.abc import Iterator


def iter_sections(scene_def: dict) -> Iterator[dict]:
    """sections を順に。無い / None なら空。"""
    for section in (scene_def or {}).get("sections") or []:
        if isinstance(section, dict):
            yield section


def iter_scenes(scene_def: dict) -> Iterator[dict]:
    """全 section の scene を順に。無い / None なら空。"""
    for section in iter_sections(scene_def):
        for scene in section.get("scenes") or []:
            if isinstance(scene, dict):
                yield scene
