"""hyperbole_lint.py - 比喩的な誇張 (起源・最上級・偉人化) の決定論 lint。

user が **何度も** 指摘してきた型: closing や現代への接続で LLM が
「〜の最初の頁にあります」「〜の父」「幕を開けた」「世界を変えた」のような
**検証できない比喩の最上級**を書く。ある回「教科書の最初の頁」を手で直し、
ある回で「数理生態学の最初の頁」がそのまま再発した (教科書の最初に来るのは
指数/ロジスティック成長で、ロトカ・ヴォルテラは最初ではない)。

これまでの防御は (a) config の `forbidden_phrases` (その回で決めた語だけ) と
(b) LLM の StyleChecker (煽り語は見るが比喩の誇張は「文体は良好」で通す) の 2 つで、
**全話共通の決定論の網が無かった**。この module がその網で、3 か所から呼ぶ:

  1. script_generator の prompt (生成時に「書かない」と渡す)
  2. script_generator.validate_scene_definition (生成直後の warning)
  3. qa_checker の script gate (dearu_lint と同じ層。WARN で人が判断)

判定は 2 段階:
  - "metaphor"  : 比喩そのもの (最初の頁 / の父 / 幕を開け / 世界を変え …)。**言い換える**。
  - "primacy"   : 事実としては書けるが根拠が要る主張 (史上初 / 世界で初めて / 唯一の人物 …)。
                  verified_facts に出典があるなら残してよい。

config の `hyperbole_allow: ["ノートの最初のページ"]` に**文脈ごと**書いた語は素通りする
(ある回の Scottish Book「ノートの最初のページに問題を書いた」は文字どおりの意味)。
"""

from __future__ import annotations

import re

# (kind, label, regex)。longest-first は不要 (個別 search、重複は文脈で除去)。
HYPERBOLE_PATTERNS: list[tuple[str, str, re.Pattern]] = [
    # ── 比喩の最上級 (言い換える) ──
    ("metaphor", "最初の頁", re.compile(r"最初の(?:頁|ページ|一頁)|第一頁|はじめの一頁")),
    ("metaphor", "最初の一歩", re.compile(r"最初の一歩")),
    ("metaphor", "〜の父/母 (称号)", re.compile(r"(?:学|論|術|法|性|さ|理)の(?:父|母)(?!親)")),
    ("metaphor", "生みの親", re.compile(r"[生産]みの親")),
    # 「夜明け」は時刻の意味 で FP になるので入れない。
    ("metaphor", "幕を開け/扉を開い", re.compile(r"幕を開け|扉を開い|道を切り開い")),
    ("metaphor", "金字塔/不朽", re.compile(r"金字塔|不朽の|不滅の")),
    ("metaphor", "世界を変え/動か", re.compile(r"世界を(?:変え|動か)")),
    (
        "metaphor",
        "最も偉大/最大の数学者",
        re.compile(r"最も偉大|最大の数学者|20世紀最大|二十世紀最大"),
    ),
    # ── 根拠が要る主張 (verified_facts に出典があれば残す) ──
    (
        "primacy",
        "史上初/世界初",
        re.compile(r"史上初|世界初|世界で初めて|人類で初めて|歴史上初めて|数学史上初めて"),
    ),
    ("primacy", "唯一の人物", re.compile(r"唯一の(?:人物|人|数学者)|ただ一人の(?:人物|数学者)")),
    ("primacy", "最大の発見/業績", re.compile(r"最大の(?:発見|業績|功績)|史上最(?:高|大)")),
    # 礎を築いた/基礎を築いた は事実として書けることもある (出荷 74 話で 4 件、Laplace/Hilbert 等)。
    ("primacy", "礎を築", re.compile(r"礎を築|礎となっ")),
]


def scan_text(text: str, allow: list[str] | None = None) -> list[dict]:
    """1 本の narration 文字列を走査し、ヒットを列挙する。

    allow に含まれる文脈 (部分文字列) の中にあるヒットは外す。
    返り値: [{"kind", "label", "match", "context"}]
    """
    out = []
    allow = [a for a in (allow or []) if isinstance(a, str) and a]
    for kind, label, pat in HYPERBOLE_PATTERNS:
        for m in pat.finditer(text):
            ctx = text[max(0, m.start() - 20) : m.end() + 12]
            if any(
                a in text and m.start() >= text.find(a) and m.end() <= text.find(a) + len(a)
                for a in allow
            ):
                continue
            out.append({"kind": kind, "label": label, "match": m.group(0), "context": ctx})
    return out


def scan_scene_definition(scene_definition: dict, allow: list[str] | None = None) -> list[dict]:
    """scene_definition の全 narration (と description.intro) を走査する。

    返り値の各要素に scene_id / sentence_index を付ける (intro は scene_id="description.intro")。
    """
    hits = []
    for section in scene_definition.get("sections", []):
        for scene in section.get("scenes", []):
            sid = scene.get("scene_id", "unknown")
            narr = scene.get("narration", [])
            if isinstance(narr, str):
                narr = [narr]
            for idx, raw in enumerate(narr):
                if not isinstance(raw, str):
                    continue
                for h in scan_text(raw.replace("|", ""), allow):
                    hits.append({"scene_id": sid, "sentence_index": idx, **h})
    intro = (scene_definition.get("description") or {}).get("intro")
    if isinstance(intro, str):
        for h in scan_text(intro, allow):
            hits.append({"scene_id": "description.intro", "sentence_index": 0, **h})
    return hits


def prompt_block() -> str:
    """script_generator の prompt に渡す「書かない」指示。"""
    return (
        "\n## 比喩的な誇張の禁止 (全話共通)\n"
        "次の型の表現は、事実として検証できないので書かないでください (言い換えること):\n"
        "- 起源の比喩:「〜の最初の頁にあります」「〜の第一頁」「〜の最初の一歩」"
        "「幕を開けた」「扉を開いた」「夜明け」「礎を築いた」\n"
        "- 称号:「〜の父」「〜の母」「生みの親」「最も偉大な」「20世紀最大の」「金字塔」「不朽の」\n"
        "- 世界規模の断定:「世界を変えた」「世界を動かした」\n"
        "「史上初」「世界で初めて」「唯一の人物」は、verified_facts に出典がある場合に限って書けます。\n"
        "現代への接続は「いまも〜に使われています」「〜の土台のひとつです」のように、"
        "確かめられる範囲で言い切ってください。\n"
    )
