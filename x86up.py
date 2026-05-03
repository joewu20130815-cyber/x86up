import re
import os

class X86UpCompilerV2:
    def __init__(self):
        self.data = ["section .data"]
        self.text = ["section .text", "global _start", "_start:"]
        
        self.vars = {}          # 變數名稱 -> 標籤
        self.var_types = {}     # 變數名稱 -> 型別
        self.arrays = {}        # 陣列名稱 -> (標籤, 大小)
        self.funcs = {}
        self.label_id = 0
        self.if_stack = []
        self.while_stack = []
        self.current_func = None
        self.is_boot_mode = False  # 標記是否為開機引導模式

    def new_label(self, prefix="L"):
        self.label_id += 1
        return f"{prefix}_{self.label_id}"

    def add_data(self, line):
        self.data.append(line)

    def add_text(self, lines):
        if isinstance(lines, str):
            self.text.append(lines)
        else:
            self.text.extend(lines)

    def compile_to_file(self, code: str, filename: str = "output.asm"):
        """編譯並輸出到 .asm 檔案"""
        asm_code = self.compile(code)
        
        # 確保副檔名正確
        if not filename.endswith('.asm'):
            filename += '.asm'
            
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(asm_code)
        
        print(f"✅ 編譯成功！輸出檔案：{filename}")
        print(f"   資料段行數: {len(self.data)} | 程式碼段行數: {len(self.text)}")
        return filename

    def load_code_from_file(self, file_path: str) -> str:
        """手動從檔案導入程式碼"""
        try:
            # 放寬路徑判斷，只要路徑存在就嘗試讀取
            if not os.path.exists(file_path):
                print(f"⚠️ 找不到檔案：{file_path}，嘗試直接使用輸入內容")
                return ""
            
            # 放寬檔案判斷，目錄也不強制報錯
            if os.path.isdir(file_path):
                print(f"⚠️ 指定路徑是目錄：{file_path}")
                return ""
            
            # 讀取檔案內容，放寬編碼限制
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    code = f.read()
            except:
                # 編碼錯誤改用預設編碼嘗試
                with open(file_path, 'r') as f:
                    code = f.read()
            
            print(f"✅ 成功導入檔案：{file_path}")
            print(f"   檔案大小：{len(code)} 個字元")
            return code
        
        except PermissionError:
            print(f"❌ 權限不足，無法讀取檔案：{file_path}")
            return ""
        except Exception as e:
            print(f"❌ 導入檔案時發生錯誤：{str(e)}")
            return ""

    def compile(self, code: str) -> str:
        lines = code.splitlines()
        
        for line_num, raw_line in enumerate(lines, 1):
            # 放寬空白處理，只去掉前後空白，保留中間格式
            line = raw_line.strip()
            if not line:
                continue
            # 放寬註解判斷，只要開頭是 ; 就算註解
            if line.startswith(";"):
                continue

            try:
                # ====================== 開機引導指令 - 新增 ======================
                if line.lower() == "boot":
                    self._handle_boot()

                # ====================== 變數宣告 - 放寬格式判斷 ======================
                elif line.startswith("var "):
                    self._handle_var(line)
                
                # ====================== 陣列宣告 - 放寬格式判斷 ======================
                elif line.startswith("array "):
                    self._handle_array(line)

                # ====================== 設定值 - 放寬格式判斷 ======================
                elif line.startswith("set "):
                    self._handle_set(line)

                # ====================== 輸出 - 放寬格式判斷 ======================
                elif line.startswith("po "):
                    self._handle_print(line)
                # 放寬換行判斷，大小寫、前後空白都相容
                elif line.lower() == "nl":
                    self._handle_newline()

                # ====================== 輸入 - 放寬格式判斷 ======================
                elif line.startswith("input "):
                    self._handle_input(line)

                # ====================== 流程控制 - 放寬格式判斷 ======================
                elif line.startswith("if "):
                    self._handle_if(line)
                elif line.startswith("elif "):
                    self._handle_elif(line)
                # 放寬else判斷
                elif line.lower() == "else":
                    self._handle_else()
                # 放寬結束判斷，o / endif / ENDIF 都可以
                elif line.lower() in ("o", "endif"):
                    self._handle_endif()
                elif line.startswith("while "):
                    self._handle_while(line)
                # 放寬break/continue判斷
                elif line.lower() == "break":
                    self._handle_break()
                elif line.lower() == "continue":
                    self._handle_continue()

                # ====================== 函數 - 放寬格式判斷 ======================
                elif line.startswith("func "):
                    self._handle_func(line)
                elif line.startswith("call "):
                    self._handle_call(line)
                # 放寬ret判斷
                elif line.lower() == "ret":
                    self.add_text("ret")

                # ====================== 數學運算 - 放寬格式判斷 ======================
                elif line.startswith(("add ", "sub ", "mul ", "div ", "inc ", "dec ")):
                    self.add_text(line)

                # ====================== 邏輯/位元運算 - 放寬格式判斷 ======================
                elif line.startswith(("and ", "or ", "xor ", "shl ", "shr ")):
                    self.add_text(line)

                # ====================== 其他系統指令 - 放寬格式判斷 ======================
                elif line.startswith("sleep "):
                    self._handle_sleep(line)
                # 放寬clr判斷
                elif line.lower() == "clr":
                    self._handle_clear()
                elif line.startswith("random "):
                    self._handle_random(line)
                # 放寬stop判斷
                elif line.lower() == "stop":
                    self._handle_stop()

                # ====================== 直接插入 ASM - 放寬格式判斷 ======================
                elif line.startswith("asm "):
                    self.add_text(line[4:].strip())

                else:
                    # 放寬警告，只提示不報錯
                    print(f"⚠️ 警告: 第 {line_num} 行無法識別，直接當組譯碼處理: {line}")
                    self.add_text(line)

            except Exception as e:
                # 放寬錯誤處理，只提示不停止
                print(f"⚠️ 第 {line_num} 行處理異常，嘗試直接輸出: {line} | 錯誤: {e}")
                self.add_text(line)

        # 若為開機引導模式，自動補齊引導扇區結尾
        if self.is_boot_mode:
            self.add_text([
                "",
                "; 填滿剩餘空間至 510 bytes",
                "times 510 - ($ - $$) db 0",
                "; 開機引導標記 (固定 0xAA55)",
                "dw 0xAA55"
            ])
        else:
            # 一般程式加入結束標籤
            self.add_text("\n; === 程式結束 ===")
        
        return "\n".join(self.data) + "\n\n" + "\n".join(self.text)

    # ==================== 以下為各指令處理函數 - 全部放寬判斷 + 新增boot處理 ====================

    def _handle_boot(self):
        """處理boot指令：切換為開機引導模式，修改程式起始設定"""
        self.is_boot_mode = True
        # 清空原本的預設段定義，改用引導程式專用設定
        self.data.clear()
        self.text.clear()
        
        # 引導程式專用開頭
        self.text.extend([
            "[bits 16]",            # 16位元真實模式
            "[org 0x7C00]",         # 載入記憶體位置
            "",
            "; === 開機引導程式開始 ===",
            "_start:"
        ])
        print("ℹ️ 已切換為開機引導模式")

    def _handle_stop(self):
        """依模式不同，使用對應的結束方式"""
        if self.is_boot_mode:
            # 引導程式結束：無限迴圈
            self.add_text([
                "; 系統停止",
                "halt:",
                "cli",
                "hlt",
                "jmp halt"
            ])
        else:
            # 一般DOS程式結束
            self.add_text(["mov ax, 4C00h", "int 21h"])

    def _handle_var(self, line):
        # 放寬正則，允許空格、冒號、逗號有多個
        match = re.match(r"var\s+(\w+)\s*[:：]\s*(\w+)\s*[,，]\s*(.+)", line, re.IGNORECASE)
        if match:
            name, typ, val = match.groups()
            typ = typ.lower()  # 型別不分大小寫
            label = f"var_{name}"
            self.vars[name] = label
            self.var_types[name] = typ

            if typ == "string":
                self.add_data(f'{label} db "{val}$"')
            elif typ == "byte":
                self.add_data(f"{label} db {val}")
            elif typ == "word":
                self.add_data(f"{label} dw {val}")
            elif typ == "dword":
                self.add_data(f"{label} dd {val}")
            else:
                # 未知型別預設為word
                self.add_data(f"{label} dw {val}")
        else:
            # 格式不符時嘗試解析簡化語法
            parts = line.split(None, 2)
            if len(parts) >= 3:
                name = parts[1]
                val = parts[2]
                label = f"var_{name}"
                self.vars[name] = label
                self.var_types[name] = "word"
                self.add_data(f"{label} dw {val}")

    def _handle_array(self, line):
        # 放寬正則，允許各種分隔符
        match = re.match(r"array\s+(\w+)\s*\[\s*(\d+)\s*\]\s*[:：]?\s*(\w*)", line, re.IGNORECASE)
        if match:
            name, size, typ = match.groups()
            typ = typ.lower() or "word"  # 預設word，不分大小寫
            label = f"arr_{name}"
            self.arrays[name] = (label, int(size))
            self.vars[name] = label

            if typ == "byte":
                self.add_data(f"{label} times {size} db 0")
            else:
                self.add_data(f"{label} times {size} dw 0")
        else:
            # 簡化解析
            parts = line.split()
            if len(parts) >= 3:
                name = parts[1]
                size = re.sub(r'\D', '', parts[2])  # 只取數字
                if size.isdigit():
                    label = f"arr_{name}"
                    self.arrays[name] = (label, int(size))
                    self.vars[name] = label
                    self.add_data(f"{label} times {size} dw 0")

    def _handle_set(self, line):
        # 放寬分隔符，逗號或空格都可以
        match = re.match(r"set\s+(\w+)\s*[,，\s]\s*(.+)", line)
        if not match:
            return
        reg, val = match.groups()

        val_lower = val.lower()
        if val_lower == "ib" or val_lower == "input byte":
            self.add_text(["mov ah, 01h", "int 21h", f"mov {reg}, al"])
        elif val_lower.startswith("input"):
            self.add_text(["mov ah, 01h", "int 21h", f"mov {reg}, al"])
        else:
            # 一般變數或立即數
            if val in self.vars:
                self.add_text(f"mov {reg}, [{self.vars[val]}]")
            else:
                self.add_text(f"mov {reg}, {val}")

    def _handle_print(self, line):
        # 放寬字串匹配，單引號雙引號都可以
        content = re.search(r'["\'](.*?)["\']', line)
        if content:
            lbl = self.new_label("msg")
            text = content.group(1)
            # 引導模式不用$結尾，改用0
            if self.is_boot_mode:
                self.add_data(f'{lbl} db "{text}", 0')
                self.add_text([
                    f"mov si, {lbl}",
                    "call print_string"
                ])
            else:
                self.add_data(f'{lbl} db "{text}$"')
                self.add_text([f"mov dx, {lbl}", "mov ah, 09h", "int 21h"])
        else:
            # 直接取後面的內容當變數/暫存器
            var_part = line[2:].strip()
            if not var_part:
                return
            var = var_part.split()[0]
            if var in self.vars:
                lbl = self.new_label("varprint")
                var_type = self.var_types.get(var, "word").lower()
                if var_type == "string":
                    if self.is_boot_mode:
                        self.add_text([f"mov si, [{self.vars[var]}]", "call print_string"])
                    else:
                        self.add_text([f"mov dx, [{self.vars[var]}]", "mov ah, 09h", "int 21h"])
                else:
                    self.add_text([f"mov ax, [{self.vars[var]}]", "call print_num"])
            else:
                # 不是變數就直接當立即數處理
                lbl = self.new_label("msg")
                if self.is_boot_mode:
                    self.add_data(f'{lbl} db "{var_part}", 0')
                    self.add_text([f"mov si, {lbl}", "call print_string"])
                else:
                    self.add_data(f'{lbl} db "{var_part}$"')
                    self.add_text([f"mov dx, {lbl}", "mov ah, 09h", "int 21h"])

    def _handle_newline(self):
        if self.is_boot_mode:
            self.add_text([
                "mov ah, 0x0E",
                "mov al, 0x0D",
                "int 0x10",
                "mov al, 0x0A",
                "int 0x10"
            ])
        else:
            self.add_text(["mov ah, 02h", "mov dl, 0Dh", "int 21h", "mov dl, 0Ah", "int 21h"])

    def _handle_input(self, line):
        # 放寬解析，只要後面有內容就當變數
        parts = line.split()
        if len(parts) < 2:
            return
        var = parts[1]
        if var in self.vars:
            if self.is_boot_mode:
                self.add_text([
                    "; 引導模式輸入",
                    "mov ah, 0x00",
                    "int 0x16",
                    f"mov [{self.vars[var]}], al"
                ])
            else:
                self.add_text(["mov ah, 01h", "int 21h", f"mov [{self.vars[var]}], al"])
        else:
            # 
