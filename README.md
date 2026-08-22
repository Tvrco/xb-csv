# xb-csv

ComfyUI CSV prompt loader custom node.

## Install

Copy this folder to `ComfyUI/custom_nodes/xb-csv`, then restart ComfyUI.

## Usage

1. Add `xb-csv（CSV 提示词）` from `xb/CSV`.
2. Click `上传 CSV`.
3. Select two columns from the detected header lists. The node outputs both columns row-by-row.
4. Set `row_count` to the number of prompts to read. `start_row` is 1-based and excludes the header row.
5. Connect `提示词` to a downstream string/CLIP node. The output is a ComfyUI string list, so downstream nodes that support list expansion can process each row separately.

CSV files are stored under `ComfyUI/input/xb_csv` and are encoded as UTF-8/UTF-8-SIG, GB18030, or UTF-16 when read.

