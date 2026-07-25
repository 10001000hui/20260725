# Python 專案自動化配置 Skill 說明文件

此專案已配置一個專屬的 **Python 環境準備 Skill**，能自動化建立新專案資料夾、配置虛擬環境並安裝指定套件。

---

## 1. 什麼時候使用這個 Skill？
* 當您要在這個工作區下**開始一個新的 Python 程式開發**時。
* 當您需要一個**獨立乾淨的 Python 虛擬環境 (`venv`)**，且預設需要使用 `pyinstaller` (打包)、`pypdf` (合併)、`google-generativeai` (Gemini API)、`python-docx` (Word) 與 `openpyxl` (Excel) 時。

---

## 2. 怎麼使用它？

### 步驟 A：觸發語句
在與 Antigravity AI 助理聊天時，輸入以下指令：
* `幫我開一個新專案` (系統會詢問您專案名稱)
* `幫我開一個新專案 <您的專案名稱>` (例如：`幫我開一個新專案 pdf_tool`)

### 步驟 B：自動化執行內容
助理收到指令後，會自動執行以下動作：
1. 在目前目錄下建立名為 `<您的專案名稱>` 的新資料夾。
2. 在該資料夾內建立虛擬環境：`python -m venv venv`。
3. 建立並寫入 `requirements.txt`，包含預設套件。
4. 在虛擬環境中安裝套件，避免與您電腦的全域 Python 環境衝突。
5. 建立 `.gitignore`（自動忽略 `venv` 等不需 Git 追蹤的檔案）。
6. 建立一個包含基礎結構的 `main.py` 起始程式。
7. 完成後回覆：**「環境好了,可以開始寫了」**。

---

## 3. 換台電腦時，如何一鍵裝回環境？
本 Skill 會為每個新專案自動產出 `requirements.txt`。當您將專案複製到其他電腦時，只需跟著以下步驟即可快速還原環境：

1. **開啟終端機 (Terminal)** 並切換至您的專案資料夾。
2. **建立虛擬環境** (選用，但強烈建議)：
   ```bash
   python -m venv venv
   ```
3. **啟用虛擬環境**：
   * **Windows (PowerShell)**: `.\venv\Scripts\Activate.ps1`
   * **macOS / Linux**: `source venv/bin/activate`
4. **一鍵安裝所有套件**：
   ```bash
   pip install -r requirements.txt
   ```

這樣就能確保在不同電腦上都有完全一致的開發環境！
