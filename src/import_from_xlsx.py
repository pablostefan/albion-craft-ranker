from __future__ import annotations

import argparse
import csv
import re
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, List, Tuple

NS = {
    "m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main",
    "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
    "pr": "http://schemas.openxmlformats.org/package/2006/relationships",
}


def col_to_num(col: str) -> int:
    n = 0
    for ch in col:
        n = n * 26 + (ord(ch) - 64)
    return n


def parse_ref(ref: str) -> Tuple[int | None, int | None]:
    m = re.match(r"([A-Z]+)(\d+)", ref)
    if not m:
        return None, None
    return int(m.group(2)), col_to_num(m.group(1))


def load_shared_strings(z: zipfile.ZipFile) -> List[str]:
    if "xl/sharedStrings.xml" not in z.namelist():
        return []
    sst = ET.fromstring(z.read("xl/sharedStrings.xml"))
    out: List[str] = []
    for si in sst.findall("m:si", NS):
        out.append("".join(t.text or "" for t in si.findall(".//m:t", NS)))
    return out


def get_sheet_xml_path(z: zipfile.ZipFile, sheet_name: str) -> str:
    wb = ET.fromstring(z.read("xl/workbook.xml"))
    rels = ET.fromstring(z.read("xl/_rels/workbook.xml.rels"))
    rid_to_target = {rel.attrib["Id"]: rel.attrib["Target"] for rel in rels.findall("pr:Relationship", NS)}

    for s in wb.find("m:sheets", NS).findall("m:sheet", NS):
        if s.attrib.get("name") == sheet_name:
            rid = s.attrib.get("{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id")
            target = rid_to_target.get(rid, "")
            if not target.startswith("worksheets/"):
                target = "worksheets/" + target.split("/")[-1]
            return "xl/" + target

    raise ValueError(f"Aba nao encontrada: {sheet_name}")


def iter_sheet_rows(z: zipfile.ZipFile, sheet_xml_path: str, shared: List[str]) -> List[Tuple[int, Dict[int, str]]]:
    root = ET.fromstring(z.read(sheet_xml_path))
    sd = root.find("m:sheetData", NS)
    out: List[Tuple[int, Dict[int, str]]] = []
    if sd is None:
        return out

    for row in sd.findall("m:row", NS):
        r = int(row.attrib.get("r", "0"))
        vals: Dict[int, str] = {}
        for c in row.findall("m:c", NS):
            rr, cc = parse_ref(c.attrib.get("r", ""))
            if rr is None:
                continue
            t = c.attrib.get("t")
            v = c.find("m:v", NS)
            val = ""
            if v is not None and v.text is not None:
                if t == "s":
                    try:
                        val = shared[int(v.text)]
                    except (ValueError, IndexError):
                        val = v.text
                else:
                    val = v.text
            else:
                isel = c.find("m:is", NS)
                if isel is not None:
                    val = "".join(x.text or "" for x in isel.findall(".//m:t", NS))
            vals[cc] = val
        if vals:
            out.append((r, vals))
    return out


def safe_float(v: str) -> float:
    try:
        return float((v or "").replace(",", "."))
    except ValueError:
        return 0.0


def convert_bd_itens_craft(xlsx_path: Path, out_csv: Path, include_journals: bool = False) -> int:
    with zipfile.ZipFile(xlsx_path) as z:
        shared = load_shared_strings(z)
        sheet = get_sheet_xml_path(z, "BD_Itens_Craft")
        rows = iter_sheet_rows(z, sheet, shared)

    # Cabeçalho esperado na linha com colunas como: ID Name, Quant_R1, Recuso_1 ...
    header_row_idx = None
    for rnum, vals in rows[:60]:
        maybe = "|".join(vals.get(i, "") for i in range(1, 30)).lower()
        if "id name" in maybe and "quant_r1" in maybe and "recuso_1" in maybe:
            header_row_idx = rnum
            break

    if header_row_idx is None:
        raise ValueError("Nao foi possivel localizar cabecalho em BD_Itens_Craft")

    output_rows: List[Tuple[str, str, float, float]] = []

    for rnum, vals in rows:
        if rnum <= header_row_idx:
            continue

        product_id = (vals.get(6, "") or "").strip()  # ID Name
        if not product_id:
            continue

        # Quant_R1..7 em 7,9,11,13,15,17,19 | Recuso_1..7 em 8,10,12,14,16,18,20
        for i in range(7):
            qty_col = 7 + i * 2
            mat_col = 8 + i * 2
            qty = safe_float(vals.get(qty_col, ""))
            mat = (vals.get(mat_col, "") or "").strip()
            if qty <= 0 or not mat:
                continue
            if not include_journals and "JOURNAL_" in mat:
                continue

            output_rows.append((product_id, mat, qty, 0.0))

    out_csv.parent.mkdir(parents=True, exist_ok=True)
    with out_csv.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["product_id", "material_id", "material_qty", "focus_cost"])
        for row in output_rows:
            w.writerow(row)

    return len(output_rows)


def main() -> None:
    parser = argparse.ArgumentParser(description="Converte aba BD_Itens_Craft do XLSX para recipes.csv")
    parser.add_argument("--xlsx", required=True)
    parser.add_argument("--out", default="data/recipes.csv")
    parser.add_argument("--include-journals", action="store_true")
    args = parser.parse_args()

    total = convert_bd_itens_craft(
        xlsx_path=Path(args.xlsx),
        out_csv=Path(args.out),
        include_journals=args.include_journals,
    )
    print(f"Receitas exportadas: {total}")
    print(f"Arquivo: {args.out}")


if __name__ == "__main__":
    main()
