#!/usr/bin/env python3
"""Inventory repo comments split into banner / narration / other buckets.

Usage:  python comment_inventory.py <repo-path>

The bucket split is the point of this script: a raw comment count cannot
distinguish load-bearing documentation from narration of the obvious, and a
blanket delete based on the raw count destroys the former.

Guards every path from `git ls-files` with an existence check (submodules,
sparse checkouts and case mismatches list files that are not on disk).
"""

import os
import re
import subprocess
import sys
from collections import Counter

CODE_EXT = {
    ".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs", ".py", ".go", ".rs",
    ".java", ".kt", ".rb", ".php", ".c", ".h", ".cpp", ".hpp", ".cs",
    ".css", ".scss", ".html", ".vue", ".svelte", ".sh", ".sql",
}

# Banner rules: // ==== TITLE ==== , // ---- TITLE ---- , /* #### TITLE ####
BANNER = re.compile(r"^\s*(//|#|/\*|\*|<!--)\s*[=\-#*~]{4,}")

# Narration rules: the comment opens with the verb the code performs next.
# Latin-script verb stems; extend the alternation for other languages.
NARRATION = re.compile(
    r"^\s*(//|#|/\*|\*|<!--)\s*"
    r"(incrementa|adiciona|retorna|devolve|cria|define|remove|deleta|"
    r"verifica|chama|importa|exporta|exibe|mostra|atualiza|inicializa|"
    r"salva|carrega|monta|renderiza|busca|procura|filtra|ordena|"
    r"converte|concatena|obtem|obtém|seta|atribui|abre|fecha|limpa|"
    r"itera|repete|executa|dispara|percorre|constroi|constrói|"
    r"sets?|gets?|returns?|adds?|removes?|creates?|updates?|"
    r"initiali[sz]es?|checks?|fetches?|renders?|handles?)\b",
    re.IGNORECASE,
)


def tracked_files(repo):
    out = subprocess.run(
        ["git", "ls-files"], cwd=repo, capture_output=True, text=True
    )
    return out.stdout.split()


def read_lines(repo, rel):
    path = os.path.join(repo, rel.replace("/", os.sep))
    if not os.path.isfile(path):
        return None
    with open(path, encoding="utf-8", errors="replace") as fh:
        return fh.read().split("\n")


def classify_line(stripped):
    if BANNER.match(stripped):
        return "banner"
    if NARRATION.match(stripped):
        return "narration"
    return "other"


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    repo = sys.argv[1]
    if not os.path.isdir(repo):
        print(f"not a directory: {repo}")
        return 2

    totals = Counter()
    per_file = []
    missing = 0

    for rel in tracked_files(repo):
        if os.path.splitext(rel)[1].lower() not in CODE_EXT:
            continue
        lines = read_lines(repo, rel)
        if lines is None:
            missing += 1
            continue
        buckets = Counter()
        for raw in lines:
            stripped = raw.strip()
            if stripped.startswith(("//", "/*", "*", "<!--", "#")):
                buckets[classify_line(stripped)] += 1
        if not buckets:
            continue
        totals.update(buckets)
        per_file.append((rel, buckets, len(lines)))

    per_file.sort(
        key=lambda row: -(row[1]["banner"] + row[1]["narration"] + row[1]["other"])
    )

    print(f"repo: {repo}   files with comments: {len(per_file)}")
    if missing:
        print(f"note: {missing} tracked path(s) not on disk, skipped")
    print()
    for rel, buckets, total in per_file:
        print(
            f"{buckets['banner']:4d} bnr "
            f"{buckets['narration']:4d} nar "
            f"{buckets['other']:4d} oth "
            f"/ {total:5d} lines  {rel}"
        )

    print()
    print("TOTALS (upper bound; `nar` includes marker lines inside template")
    print("literals, shader source and CSS content strings):")
    for key in ("banner", "narration", "other"):
        print(f"  {key:10s} {totals[key]}")
    print()
    print("Default action: narration -> delete; other -> keep (inspect on")
    print("request); banner -> ASK, usually deliberate author style.")
    return 0


if __name__ == "__main__":
    sys.exit(main())