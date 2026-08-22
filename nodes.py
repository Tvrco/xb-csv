import csv
import os
import re
from pathlib import Path

from aiohttp import web

import folder_paths


NODE_DIR = Path(__file__).resolve().parent
UPLOAD_DIR = Path(folder_paths.get_input_directory()) / "xb_csv"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


def _safe_name(name: str) -> str:
    name = os.path.basename(name or "")
    name = re.sub(r"[^\w.\-\u4e00-\u9fff ]+", "_", name).strip(" .")
    if not name:
        name = "uploaded"
    if not name.lower().endswith(".csv"):
        name += ".csv"
    return name


def _csv_path(name: str) -> Path:
    clean = _safe_name(name)
    path = (UPLOAD_DIR / clean).resolve()
    if path.parent != UPLOAD_DIR.resolve():
        raise ValueError("Invalid CSV filename")
    return path


def _read_csv(path: Path):
    last_error = None
    for encoding in ("utf-8-sig", "gb18030", "utf-16"):
        try:
            with path.open("r", encoding=encoding, newline="") as handle:
                sample = handle.read(8192)
                handle.seek(0)
                try:
                    dialect = csv.Sniffer().sniff(sample, delimiters=",;\t|")
                except csv.Error:
                    dialect = csv.excel
                rows = list(csv.reader(handle, dialect))
            if not rows:
                return [], []
            headers = []
            seen = {}
            for index, value in enumerate(rows[0]):
                header = value.strip() or f"列 {index + 1}"
                seen[header] = seen.get(header, 0) + 1
                headers.append(header if seen[header] == 1 else f"{header} ({seen[header]})")
            data = []
            for row in rows[1:]:
                padded = row + [""] * max(0, len(headers) - len(row))
                data.append(padded[: len(headers)])
            return headers, data
        except (UnicodeDecodeError, csv.Error, OSError) as exc:
            last_error = exc
    raise ValueError(f"无法读取 CSV：{last_error}")


def _available_files():
    return sorted(p.name for p in UPLOAD_DIR.glob("*.csv"))


async def upload_csv(request):
    reader = await request.multipart()
    field = await reader.next()
    if field is None or field.name != "file":
        raise web.HTTPBadRequest(text="请上传名为 file 的 CSV 文件")
    original_name = field.filename or ""
    if not original_name.lower().endswith(".csv"):
        raise web.HTTPBadRequest(text="只支持 CSV 文件")
    filename = _safe_name(original_name)
    path = _csv_path(filename)
    with path.open("wb") as handle:
        while True:
            chunk = await field.read_chunk()
            if not chunk:
                break
            handle.write(chunk)
    try:
        headers, data = _read_csv(path)
    except ValueError as exc:
        path.unlink(missing_ok=True)
        raise web.HTTPBadRequest(text=str(exc))
    return web.json_response({"file": filename, "headers": headers, "rows": len(data)})


async def list_csv(request):
    return web.json_response({"files": _available_files()})


async def csv_headers(request):
    try:
        path = _csv_path(request.query.get("file", ""))
        if not path.is_file():
            raise ValueError("CSV 文件不存在")
        headers, data = _read_csv(path)
        return web.json_response({"headers": headers, "rows": len(data)})
    except ValueError as exc:
        raise web.HTTPBadRequest(text=str(exc))


try:
    from server import PromptServer

    PromptServer.instance.routes.post("/xb_csv/upload")(upload_csv)
    PromptServer.instance.routes.get("/xb_csv/files")(list_csv)
    PromptServer.instance.routes.get("/xb_csv/headers")(csv_headers)
except Exception as exc:
    print(f"[xb-csv] HTTP routes unavailable: {exc}")


class XBCSV:
    @classmethod
    def INPUT_TYPES(cls, **kwargs):
        files = _available_files() or ["请先上传 CSV"]
        return {
            "required": {
                "csv_file": (files, {"default": files[0]}),
                "column": (["请先选择 CSV"], {"default": "请先选择 CSV"}),
                "column_2": (["请先选择 CSV"], {"default": "请先选择 CSV"}),
                "row_count": ("INT", {"default": 1, "min": 1, "max": 9999, "step": 1}),
                "start_row": ("INT", {"default": 1, "min": 1, "max": 999999, "step": 1}),
            }
        }

    RETURN_TYPES = ("STRING", "STRING", "INT")
    RETURN_NAMES = ("提示词 1", "提示词 2", "实际行数")
    FUNCTION = "load"
    CATEGORY = "xb/CSV"
    OUTPUT_IS_LIST = (True, True, False)

    def load(self, csv_file, column, column_2, row_count=1, start_row=1):
        path = _csv_path(csv_file)
        if not path.is_file():
            raise FileNotFoundError(f"CSV 文件不存在：{csv_file}")
        headers, rows = _read_csv(path)
        for selected in (column, column_2):
            if not headers or selected not in headers:
                raise ValueError(f"CSV 中没有列：{selected}。可用列：{', '.join(headers)}")
        index_1 = headers.index(column)
        index_2 = headers.index(column_2)
        begin = max(0, int(start_row) - 1)
        end = begin + max(1, int(row_count))
        selected_rows = rows[begin:end]
        values_1 = [row[index_1].strip() for row in selected_rows]
        values_2 = [row[index_2].strip() for row in selected_rows]
        if not any(values_1) and not any(values_2):
            raise ValueError("选定范围内没有非空提示词")
        if not any(values_1):
            values_1 = [""] * len(values_2)
        if not any(values_2):
            values_2 = [""] * len(values_1)
        return (values_1, values_2, len(selected_rows))


NODE_CLASS_MAPPINGS = {"xb-csv": XBCSV}
NODE_DISPLAY_NAME_MAPPINGS = {"xb-csv": "xb-csv（CSV 提示词）"}

