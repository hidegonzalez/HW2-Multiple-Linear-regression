#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
學號一鍵替換與作業打包腳本 (Student ID Batch Renamer & Packaging Utility)
使用方式：
    python rename_student_id.py <您的真實學號>
範例：
    python rename_student_id.py 7114056001
功能：
    1. 將所有程式碼、報告、Notebook 及設定檔中的 7114056XXX 替換為您的真實學號。
    2. 自動重命名主程式、Notebook 與 PDF 報告檔名。
    3. 自動重新編譯 PDF 技術報告以顯示您的真實學號。
    4. 自動打包符合規範的壓縮檔：<您的學號>_hw2.zip。
"""

import os
import sys
import shutil
import zipfile
import subprocess

def main():
    if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
        try:
            sys.stdout.reconfigure(encoding='utf-8')
        except Exception:
            pass

    print("=" * 70)
    print("  物聯網應用與資料分析 HW2 - 學號一鍵替換與自動打包工具")
    print("=" * 70)

    if len(sys.argv) < 2:
        new_id = input("\n請輸入您的真實學號 (例如 7114056001): ").strip()
    else:
        new_id = sys.argv[1].strip()

    if not new_id:
        print("[錯誤] 學號不能為空！")
        sys.exit(1)

    old_id = "7114056XXX"
    current_dir = os.path.dirname(os.path.abspath(__file__))

    print(f"\n[1/4] 開始將 placeholder '{old_id}' 替換為真實學號 '{new_id}'...")

    # 1. 替換檔案內容中的學號
    text_files_to_update = [
        f"{old_id}_hw2.py",
        f"{old_id}_hw2.ipynb",
        "generate_report_pdf.py",
        "generate_chatgpt_pdf.py",
        "README.md",
        "專案歷程.md",
        "app.py",
        "index.html",
        "style.css",
        "app.js"
    ]

    for fname in text_files_to_update:
        fpath = os.path.join(current_dir, fname)
        if os.path.exists(fpath):
            try:
                with open(fpath, 'r', encoding='utf-8') as f:
                    content = f.read()
                if old_id in content:
                    content = content.replace(old_id, new_id)
                    with open(fpath, 'w', encoding='utf-8') as f:
                        f.write(content)
                    print(f"  - 已更新內容: {fname}")
            except Exception as e:
                print(f"  - 更新 {fname} 時發生錯誤: {e}")

    # 2. 重命名核心作業檔案
    print(f"\n[2/4] 重新命名作業繳交檔案...")
    rename_mapping = [
        (f"{old_id}_hw2.py", f"{new_id}_hw2.py"),
        (f"{old_id}_hw2.ipynb", f"{new_id}_hw2.ipynb"),
        (f"{old_id}_hw2_report.pdf", f"{new_id}_hw2_report.pdf"),
    ]

    for old_name, new_name in rename_mapping:
        old_path = os.path.join(current_dir, old_name)
        new_path = os.path.join(current_dir, new_name)
        if os.path.exists(old_path):
            if os.path.exists(new_path) and old_path != new_path:
                os.remove(new_path)
            os.rename(old_path, new_path)
            print(f"  - 檔名變更: {old_name} -> {new_name}")

    # 3. 重新編譯 PDF 報告以帶入新學號
    print(f"\n[3/4] 重新編譯包含新學號之技術報告 PDF...")
    gen_script = os.path.join(current_dir, "generate_report_pdf.py")
    if os.path.exists(gen_script):
        try:
            res = subprocess.run([sys.executable, gen_script], capture_output=True, text=True, encoding='utf-8', errors='replace')
            if res.returncode == 0:
                print(f"  - 成功重新編譯: {new_id}_hw2_report.pdf")
                try:
                    import pymupdf
                    pdf_doc = pymupdf.open(f"{new_id}_hw2_report.pdf")
                    preview_dir = os.path.join(current_dir, "figures", "pdf_preview")
                    os.makedirs(preview_dir, exist_ok=True)
                    for i, page in enumerate(pdf_doc):
                        pix = page.get_pixmap(dpi=150)
                        pix.save(os.path.join(preview_dir, f"page_{i+1}.png"))
                    print(f"  - 已同步更新 6 頁預覽截圖至 figures/pdf_preview/")
                except Exception as ex:
                    print(f"  - 預覽圖更新提示: {ex}")
            else:
                print(f"  - 編譯警訊: {res.stderr}")
        except Exception as e:
            print(f"  - 執行編譯腳本錯誤: {e}")

    # 4. 打包最終作業 Zip
    old_zip = os.path.join(current_dir, f"{old_id}_hw2.zip")
    if os.path.exists(old_zip):
        os.remove(old_zip)
    zip_filename = f"{new_id}_hw2.zip"
    zip_path = os.path.join(current_dir, zip_filename)
    print(f"\n[4/4] 封裝最終繳交壓縮檔: {zip_filename}...")

    # 決定納入 zip 的檔案清單
    files_to_pack = [
        f"{new_id}_hw2.py",
        f"{new_id}_hw2.ipynb",
        f"{new_id}_hw2_report.pdf",
        "chatgpt_dialogue.pdf",
        "README.md",
        "requirements.txt",
        "rename_student_id.py",
        "專案歷程.md",
        "驗證報告.md",
        "操作說明報告.md",
        "generate_actual_ui_details.py",
        "app.py",
        "index.html",
        "style.css",
        "app.js",
        "Procfile",
        "render.yaml",
        ".gitignore",
        ".nojekyll"
    ]

    folders_to_pack = [
        "data",
        "figures",
        "models",
        ".github"
    ]

    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        # 加入個別檔案
        for fname in files_to_pack:
            fpath = os.path.join(current_dir, fname)
            if os.path.exists(fpath):
                zipf.write(fpath, arcname=fname)
                print(f"  + 納入檔案: {fname}")

        # 加入資料夾
        for folder in folders_to_pack:
            folder_path = os.path.join(current_dir, folder)
            if os.path.exists(folder_path):
                for root, _, files in os.walk(folder_path):
                    for file in files:
                        full_fpath = os.path.join(root, file)
                        rel_path = os.path.relpath(full_fpath, current_dir)
                        zipf.write(full_fpath, arcname=rel_path)
                print(f"  + 納入資料夾: {folder}/")

    zip_size_mb = os.path.getsize(zip_path) / (1024 * 1024)
    print("\n" + "=" * 70)
    print(f" [完成] 作業打包成功！")
    print(f" 壓縮檔案: {zip_path}")
    print(f" 檔案大小: {zip_size_mb:.2f} MB")
    print(f" 繳交檔案清單包含：")
    print(f"   1. {new_id}_hw2.py           (主分析程式碼)")
    print(f"   2. {new_id}_hw2.ipynb        (Jupyter Notebook 含完整輸出與圖形)")
    print(f"   3. {new_id}_hw2_report.pdf   (CRISP-DM 6頁完整技術報告，含 NotebookLM & GPT 標示)")
    print(f"   4. chatgpt_dialogue.pdf      (ChatGPT 對話過程匯出檔)")
    print(f"   5. README.md                 (專案說明、Kaggle 比較與重現指南)")
    print(f"   6. data/, figures/, models/  (資料集、高清圖表與持久化模型)")
    print("=" * 70)

if __name__ == "__main__":
    main()
