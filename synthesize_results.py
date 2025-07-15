import os
import sys
import pathlib
import google.generativeai as genai
from dotenv import load_dotenv
import docx

# --- 配置 ---
# 用於校對的強大模型
SYNTHESIZE_MODEL = 'gemini-2.5-pro'
# 兩個來源模型的名稱
MODEL1_NAME = 'gemini-2.5-pro'
MODEL2_NAME = 'gemini-1.5-flash'

def get_file_content(file_path):
    """安全地讀取檔案內容。"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        print(f"  - 警告: 找不到檔案 {file_path}，將跳過此檔案的該版本。")
        return None
    except Exception as e:
        print(f"  - 錯誤: 讀取檔案 {file_path} 時發生錯誤: {e}")
        return None

def synthesize_texts(model, text1, text2):
    """使用指定的 Gemini 模型來分析和融合兩個版本的文字。"""
    if text1 is None and text2 is None:
        print("  - 錯誤: 兩個版本的文字都無法讀取，無法進行融合。")
        return None
    
    # 如果其中一個版本不存在，直接回傳存在的那個版本
    if text1 is None:
        print("  - 資訊: 版本 A (pro) 不存在，直接使用版本 B (flash) 的結果。")
        return text2
    if text2 is None:
        print("  - 資訊: 版本 B (flash) 不存在，直接使用版本 A (pro) 的結果。")
        return text1

    prompt = f"""你是一位專業的文字校對員。

這裡有同一份文件來自兩種不同 OCR 模型的辨識結果。
版本 A 來自一個較強大的模型，版本 B 來自一個較快速的模型。

請仔細比較這兩份文字，綜合判斷並輸出一份最準確、最通順的最終版本。
你的任務是融合兩者的優點，修正任何一方可能存在的錯誤（例如：錯字、漏字、格式錯誤）。

**請直接輸出最終校對完成的文字內容，不要包含任何額外的說明、標題或前言。**

--- 版本 A ({MODEL1_NAME}) ---
{text1}

--- 版本 B ({MODEL2_NAME}) ---
{text2}

--- 最終校對版本 ---
"""

    try:
        print("  - 正在呼叫 Gemini API 進行分析與校對...")
        response = model.generate_content(prompt)
        if response.prompt_feedback.block_reason:
            print(f"  - 錯誤：由於 {response.prompt_feedback.block_reason.name}，請求被阻擋。")
            return None
        print("  - 分析校對成功。")
        return response.text
    except Exception as e:
        print(f"  - 呼叫 Gemini API 進行校對時發生錯誤: {e}")
        return None

def save_final_result(text_content, txt_path, docx_path):
    """將最終結果儲存為 .txt 和 .docx 檔案。"""
    try:
        print(f"  - 正在儲存最終 TXT 檔案至: {txt_path}")
        txt_path.parent.mkdir(parents=True, exist_ok=True)
        with open(txt_path, 'w', encoding='utf-8') as f:
            f.write(text_content)
    except Exception as e:
        print(f"  - 儲存最終 TXT 檔案時發生錯誤: {e}")

    try:
        print(f"  - 正在儲存最終 Word 檔案至: {docx_path}")
        doc = docx.Document()
        doc.add_paragraph(text_content)
        doc.save(docx_path)
        print("  - 檔案儲存成功。")
    except Exception as e:
        print(f"  - 儲存最終 Word 檔案時發生錯誤: {e}")

def main():
    """
    主執行函式。
    """
    load_dotenv()
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key or api_key == "YOUR_API_KEY_HERE":
        print("錯誤：找不到或尚未設定 GEMINI_API_KEY。")
        sys.exit(1)

    try:
        print(f"正在設定用於校對的 Gemini API ({SYNTHESIZE_MODEL})...")
        genai.configure(api_key=api_key)
        synthesis_model = genai.GenerativeModel(SYNTHESIZE_MODEL)
        print("Gemini API 設定成功。")
    except Exception as e:
        print(f"初始化 Gemini API 時發生錯誤: {e}")
        sys.exit(1)

    script_dir = pathlib.Path(__file__).parent
    model1_output_dir = script_dir / 'output' / MODEL1_NAME
    model2_output_dir = script_dir / 'output' / MODEL2_NAME
    final_output_dir = script_dir / 'output' / 'final_corrected'

    # 確保來源資料夾存在
    if not model1_output_dir.is_dir() or not model2_output_dir.is_dir():
        print(f"錯誤: 找不到來源資料夾 '{model1_output_dir}' 或 '{model2_output_dir}'。")
        print("請先執行 gemini_ocr.py 產生 OCR 結果。")
        return

    final_output_dir.mkdir(exist_ok=True)

    # 獲取所有需要處理的檔案（以 pro 模型的結果為基準）
    files_to_process = {f.stem for f in model1_output_dir.glob('*.txt')}
    # 也加入 flash 模型的結果，以防 pro 處理失敗但 flash 成功
    files_to_process.update({f.stem for f in model2_output_dir.glob('*.txt')})

    if not files_to_process:
        print("在來源資料夾中找不到任何 .txt 檔案可以處理。")
        return

    print(f"\n找到 {len(files_to_process)} 個獨特的檔案需要進行校對與融合，開始處理...")
    print(f"最終結果將儲存至: {final_output_dir}\n")

    for file_stem in sorted(list(files_to_process)):
        print(f"正在處理檔案: {file_stem}.txt")
        
        path1 = model1_output_dir / f"{file_stem}.txt"
        path2 = model2_output_dir / f"{file_stem}.txt"

        content1 = get_file_content(path1)
        content2 = get_file_content(path2)

        final_text = synthesize_texts(synthesis_model, content1, content2)

        if final_text:
            output_stem = final_output_dir / file_stem
            txt_output_path = output_stem.with_suffix('.txt')
            docx_output_path = output_stem.with_suffix('.docx')
            save_final_result(final_text, txt_output_path, docx_output_path)
            print(f"檔案 {file_stem}.txt 校對與融合完成。\n")
        else:
            print(f"無法為檔案 {file_stem}.txt 產生最終的校對版本。\n")

    print("所有檔案處理完畢。")

if __name__ == "__main__":
    main()
