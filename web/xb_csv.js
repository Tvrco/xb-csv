/* Frontend helpers for xb-csv. */
import { app } from "../../../scripts/app.js";

async function json(url, options) {
  const response = await fetch(url, options);
  if (!response.ok) throw new Error(await response.text());
  return response.json();
}

function setCombo(widget, values, selected) {
  widget.options.values = values.length ? values : ["无可用列"];
  widget.value = values.includes(selected) ? selected : widget.options.values[0];
  widget.callback?.(widget.value);
}

async function refreshColumns(node, selected) {
  const file = node.widgets?.find((item) => item.name === "csv_file");
  const column = node.widgets?.find((item) => item.name === "column");
  const column2 = node.widgets?.find((item) => item.name === "column_2");
  if (!file || !column || !column2 || !file.value || file.value === "请先上传 CSV") return;
  try {
    const result = await json(`/xb_csv/headers?file=${encodeURIComponent(file.value)}`);
    setCombo(column, result.headers, selected || column.value);
    setCombo(column2, result.headers, column2.value || result.headers[1] || result.headers[0]);
    node.setDirtyCanvas(true, true);
  } catch (error) {
    console.warn("[xb-csv]", error);
  }
}

app.registerExtension({
  name: "xb-csv.upload",
  async nodeCreated(node) {
    if (node.comfyClass !== "xb-csv") return;
    const file = node.widgets?.find((item) => item.name === "csv_file");
    const column = node.widgets?.find((item) => item.name === "column");
    const column2 = node.widgets?.find((item) => item.name === "column_2");
    if (!file || !column || !column2) return;

    file.callback = () => refreshColumns(node);
    const upload = node.addWidget("button", "上传 CSV", null, async () => {
      const input = document.createElement("input");
      input.type = "file";
      input.accept = ".csv,text/csv";
      input.onchange = async () => {
        if (!input.files?.length) return;
        const body = new FormData();
        body.append("file", input.files[0]);
        try {
          const result = await json("/xb_csv/upload", { method: "POST", body });
          file.options.values = [result.file];
          file.value = result.file;
          setCombo(column, result.headers, result.headers[0]);
          setCombo(column2, result.headers, result.headers[1] || result.headers[0]);
          node.setDirtyCanvas(true, true);
        } catch (error) {
          alert(`xb-csv 上传失败：${error.message}`);
        }
      };
      input.click();
    });
    upload.serialize = false;
    await refreshColumns(node);
  },
});

