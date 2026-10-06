#!/usr/bin/env python3
"""本文の表記検査。

書き終えた本文について、次を報告する。判定はせず、材料を並べるだけにしてある。
表記の良し悪しは人が決めるものだからである。

  - 話ごとの文字数
  - 使用漢字の一覧（簡体字・繁体字が混じっていれば、眺めれば見つかる）
  - 半角の記号の混入箇所
  - 場面転換の区切り行が作品内で揃っているか

使い方:  python3 tools/check.py
"""

import glob
import os
import re
import sys
from collections import Counter

# 作品名 -> (本文の glob パターン, 一話の下限, 一話の上限)
# 文字数の目安は作品ごとに違う。各作品の構成案の「文体」節と一致させること。
WORKS = {
    "匣庭のジャステイル": ("chapters/*.txt", 1200, 5000),
    "おおきくしますね": ("works/おおきくしますね/chapters/*.txt", 7000, 10000),
}

KANJI = re.compile(r"[一-鿿]")
HANKAKU = re.compile(r"[?!｡｢｣､･ｦ-ﾟ]")
JAPANESE = re.compile(r"[ぁ-んァ-ヴ一-鿿ａ-ｚA-Za-z0-9]")


def separator_of(line: str) -> bool:
    """場面転換の区切り行とみなせるか。

    日本語の文字を含まない空でない行のうち、鉤括弧を含むもの（「……」のような
    無言の台詞）は台詞なので除く。
    """
    stripped = line.strip()
    if not stripped or JAPANESE.search(stripped):
        return False
    return not set("「」『』") & set(stripped)


def check_work(title: str, pattern: str, lo: int, hi: int) -> int:
    paths = sorted(glob.glob(pattern))
    if not paths:
        print(f"  （本文が見つからない: {pattern}）")
        return 0

    problems = 0
    kanji: set[str] = set()
    separators: Counter[str] = Counter()

    print(f"\n■ {title}  — {len(paths)} 話")
    print("\n  文字数")
    for path in paths:
        text = open(path, encoding="utf-8").read()
        n = len(text)
        mark = " " if lo <= n <= hi else "*"
        print(f"  {mark} {n:>6,} 文字  {os.path.basename(path)}")
        if mark == "*":
            problems += 1

        kanji |= set(KANJI.findall(text))
        for line in text.split("\n"):
            if separator_of(line):
                separators[line] += 1

        for m in HANKAKU.finditer(text):
            line_no = text.count("\n", 0, m.start()) + 1
            around = text[max(0, m.start() - 12):m.start() + 12].replace("\n", "⏎")
            print(f"    半角記号 {m.group()!r}  {os.path.basename(path)}:{line_no}  …{around}…")
            problems += 1

    print(f"\n  * はこの作品の目安 {lo:,}〜{hi:,} 文字の外")

    print(f"\n  使用漢字 {len(kanji)} 種 — 簡体字・繁体字が紛れていないか眺めること")
    ordered = "".join(sorted(kanji))
    for i in range(0, len(ordered), 60):
        print("    " + ordered[i:i + 60])

    print("\n  場面転換の区切り行")
    for line, count in separators.most_common():
        print(f"    {count:>3} 回  {line!r}")
    if len(separators) > 1:
        print("    → 二種類以上ある。作品内では一つに揃えること")
        problems += 1

    return problems


def main() -> int:
    total = 0
    for title, (pattern, lo, hi) in WORKS.items():
        total += check_work(title, pattern, lo, hi)
    print()
    if total:
        print(f"要確認 {total} 件。いずれも自動判定なので、意図した表記なら無視してよい。")
    else:
        print("気になる点は見つからなかった。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
