import os
import difflib
import pathlib

def compare_files(file1_path, file2_path):
    """讀取兩個檔案並回傳它們的內容。"""
    try:
        with open(file1_path, 'r', encoding='utf-8') as f1:
            content1 = f1.readlines()
        with open(file2_path, 'r', encoding='utf-8') as f2:
            content2 = f2.readlines()
        return content1, content2
    except FileNotFoundError as e:
        print(f"錯誤: 找不到檔案 {e.filename}")
        return None, None

def create_diff_html(content1, content2, file_stem, model1_name, model2_name):
    """使用 difflib 產生 HTML 格式的差異報告。"""
    diff = difflib.HtmlDiff(wrapcolumn=80)
    html_diff = diff.make_file(
        content1, 
        content2, 
        fromdesc=f"{model1_name} - {file_stem}", 
        todesc=f"{model2_name} - {file_stem}"
    )
    return html_diff

def main():
    """
    主執行函式。
    """
    script_dir = pathlib.Path(__file__).parent
    model1_name = 'gemini-2.5-pro'
    model2_name = 'gemini-1.5-flash'
    
    model1_output_dir = script_dir / 'output' / model1_name
    model2_output_dir = script_dir / 'output' / model2_name
    comparison_dir = script_dir / 'comparison_reports'

    # 確保輸出和比較資料夾存在
    for dir_path in [model1_output_dir, model2_output_dir]:
        if not dir_path.is_dir():
            print(f"錯誤: 找不到輸出資料夾 '{dir_path}'。")
            print("請先執行 gemini_ocr.py 來產生 OCR 結果。")
            return
            
    comparison_dir.mkdir(exist_ok=True)

    # 尋找兩個模型都有處理的檔案
    model1_files = {f.stem for f in model1_output_dir.glob('*.txt')}
    model2_files = {f.stem for f in model2_output_dir.glob('*.txt')}
    common_files = sorted(list(model1_files.intersection(model2_files)))

    if not common_files:
        print("在兩個模型的輸出資料夾中找不到任何共同的 .txt 檔案可以比較。")
        return

    print(f"找到 {len(common_files)} 個共同檔案，開始進行比較...\n")

    for file_stem in common_files:
        print(f"- 正在比較檔案: {file_stem}.txt")
        file1_path = model1_output_dir / f"{file_stem}.txt"
        file2_path = model2_output_dir / f"{file_stem}.txt"

        content1, content2 = compare_files(file1_path, file2_path)

        if content1 is not None and content2 is not None:
            html_report = create_diff_html(content1, content2, file_stem, model1_name, model2_name)
            report_path = comparison_dir / f"compare_{file_stem}.html"
            
            try:
                with open(report_path, 'w', encoding='utf-8') as f:
                    f.write(html_report)
                print(f"  - 比較報告已儲存至: {report_path}")
            except IOError as e:
                print(f"  - 儲存報告時發生錯誤: {e}")

    print("\n所有檔案比較完成。")

if __name__ == "__main__":
    main()
