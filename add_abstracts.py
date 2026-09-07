#!/usr/bin/env python3
"""
papers.bib 안에 arxiv={...} 가 있는 항목마다 arXiv API에서 초록을 받아
abstract={...} 를 넣어준다.

사용법 (저장소 최상단에서):
    python3 add_abstracts.py

- 이미 abstract 가 있는 항목은 건너뛴다.
- 원본은 papers.bib.bak 으로 백업된다.
- 추가 설치 필요 없음 (파이썬 기본 라이브러리만 사용).
"""

import re
import shutil
import sys
import time
import urllib.request
import xml.etree.ElementTree as ET

BIB = "_bibliography/papers.bib"
API = "http://export.arxiv.org/api/query?id_list="
NS = {"a": "http://www.w3.org/2005/Atom"}


def fetch_abstract(arxiv_id):
    """arXiv API에서 초록 한 편을 받아온다."""
    req = urllib.request.Request(
        API + arxiv_id, headers={"User-Agent": "bib-abstract-filler/1.0"}
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        xml = r.read()
    entry = ET.fromstring(xml).find("a:entry", NS)
    if entry is None:
        return None
    node = entry.find("a:summary", NS)
    if node is None or not node.text:
        return None
    return node.text


def clean(text):
    """BibTeX 에 넣어도 안전하게 다듬는다."""
    text = " ".join(text.split())          # 줄바꿈, 중복 공백 정리
    text = text.replace("\\", " ")          # 백슬래시 제거
    text = text.replace("{", "(").replace("}", ")")   # 중괄호는 파싱을 깨뜨림
    for ch in ("%", "&", "#", "$", "_"):    # LaTeX 특수문자 이스케이프
        text = text.replace(ch, "\\" + ch)
    return text


def main():
    try:
        src = open(BIB, encoding="utf-8").read()
    except FileNotFoundError:
        sys.exit(f"{BIB} 을(를) 못 찾았습니다. 저장소 최상단에서 실행하세요.")

    shutil.copy(BIB, BIB + ".bak")

    # 항목 단위로 자른다
    chunks = re.split(r"(?=^@\w+\{)", src, flags=re.M)
    added = skipped = failed = 0

    for i, chunk in enumerate(chunks):
        if not chunk.lstrip().startswith("@"):
            continue
        if re.search(r"^\s*abstract\s*=", chunk, flags=re.M):
            skipped += 1
            continue
        m = re.search(r"^\s*arxiv\s*=\s*\{([^}]+)\}", chunk, flags=re.M)
        if not m:
            continue

        arxiv_id = m.group(1).strip()
        key = re.match(r"@\w+\{([^,]+),", chunk.lstrip()).group(1)
        print(f"  {key}  ({arxiv_id}) ... ", end="", flush=True)

        try:
            abstract = fetch_abstract(arxiv_id)
        except Exception as e:
            print(f"실패: {e}")
            failed += 1
            time.sleep(3)
            continue

        if not abstract:
            print("초록 없음")
            failed += 1
            time.sleep(3)
            continue

        line = "  abstract={%s},\n" % clean(abstract)
        # arxiv 줄 바로 위에 끼워 넣는다
        chunks[i] = chunk[: m.start()] + line + chunk[m.start():]
        added += 1
        print("완료")
        time.sleep(3)   # arXiv 요청 간격 권장값

    open(BIB, "w", encoding="utf-8").write("".join(chunks))
    print(f"\n추가 {added}건 / 이미 있음 {skipped}건 / 실패 {failed}건")
    print(f"원본 백업: {BIB}.bak")


if __name__ == "__main__":
    main()
