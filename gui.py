import os
import glob
import ctypes
import win32gui
import win32con
import win32api
from ctypes import wintypes

# --- Configuration ---
BG_COLOR = 0x2B2B2B
TEXT_COLOR = 0xFFFFFF
HIGHLIGHT_COLOR = 0x444444
BUTTON_COLOR = 0x555555
WINDOW_W, WINDOW_H = 1000, 700

# Layout settings
COLUMNS = 6
ROWS = 4
PAGE_SIZE = 15
ICON_SIZE = 60
START_X, START_Y = 120, 180
SPACING_X, SPACING_Y = 140, 160

try:
    ctypes.windll.shcore.SetProcessDpiAwareness(1)
except Exception:
    pass

class SHFILEINFO(ctypes.Structure):
    _fields_ = [
        ("hIcon", wintypes.HICON),
        ("iIcon", ctypes.c_int),
        ("dwAttributes", ctypes.c_ulong),
        ("szDisplayName", ctypes.c_wchar * 260),
        ("szTypeName", ctypes.c_wchar * 80),
    ]

class LaunchpadGUI:
    def __init__(self):
        self.visible = False
        self.apps = []
        self.current_page = 0
        self.search_query = ""
        self.scan_apps()
        
        wc = win32gui.WNDCLASS()
        wc.lpfnWndProc = self.wnd_proc
        wc.lpszClassName = "LaunchpadApp"
        wc.hbrBackground = win32gui.CreateSolidBrush(BG_COLOR)
        win32gui.RegisterClass(wc)
        
        screen_w = win32api.GetSystemMetrics(win32con.SM_CXSCREEN)
        screen_h = win32api.GetSystemMetrics(win32con.SM_CYSCREEN)
        x = (screen_w - WINDOW_W) // 2
        y = (screen_h - WINDOW_H) // 2
        
        self.hwnd = win32gui.CreateWindowEx(
            win32con.WS_EX_TOPMOST | win32con.WS_EX_TOOLWINDOW,
            "LaunchpadApp", "Launchpad",
            win32con.WS_POPUP | win32con.WS_BORDER,
            x, y, WINDOW_W, WINDOW_H, 0, 0, 0, None
        )

    def scan_apps(self):
        user_home = os.path.expanduser("~")
        search_paths = [
            os.path.join(os.environ.get("PROGRAMDATA", "C:\\ProgramData"), "Microsoft\\Windows\\Start Menu\\Programs"),
            os.path.join(os.environ.get("APPDATA", ""), "Microsoft\\Windows\\Start Menu\\Programs"),
            os.path.join(user_home, "Desktop"),
            os.path.join(user_home, "Downloads"),
            os.path.join(user_home, "\AppData\Roaming\Microsoft\Windows\Start Menu\Programs")
        ]
        
        found_files = set()
        for path in search_paths:
            if not os.path.exists(path): continue
            for file in glob.glob(os.path.join(path, "**", "*.*"), recursive=True):
                if not (file.endswith(".exe") or file.endswith(".lnk")): continue
                if file in found_files: continue
                
                found_files.add(file)
                sfi = SHFILEINFO()
                res = ctypes.windll.shell32.SHGetFileInfoW(file, 0, ctypes.byref(sfi), ctypes.sizeof(sfi), 0x000000100 | 0x000000000)
                
                name = os.path.basename(file)
                if file.endswith(".lnk"): name = name.replace(".lnk", "")
                else: name = name.replace(".exe", "")
                    
                self.apps.append({"name": name, "icon": sfi.hIcon if res else None, "path": file})

    def wnd_proc(self, hwnd, msg, wp, lp):
        if msg == win32con.WM_CHAR:
            if wp == 8: self.search_query = self.search_query[:-1]
            elif wp >= 32: self.search_query += chr(wp)
            self.current_page = 0
            win32gui.InvalidateRect(hwnd, None, True)
            return 0
        
        elif msg == win32con.WM_KEYDOWN:
            if wp == win32con.VK_RIGHT: self.next_page()
            elif wp == win32con.VK_LEFT: self.prev_page()
            return 0

        elif msg == win32con.WM_LBUTTONUP:
            x, y = win32api.GetCursorPos()
            client_x, client_y = win32gui.ScreenToClient(hwnd, (x, y))
            
            # Check Nav Buttons
            if 20 <= client_x <= 70 and (WINDOW_H//2 - 25) <= client_y <= (WINDOW_H//2 + 25):
                self.prev_page()
                return 0
            if (WINDOW_W - 70) <= client_x <= (WINDOW_W - 20) and (WINDOW_H//2 - 25) <= client_y <= (WINDOW_H//2 + 25):
                self.next_page()
                return 0

            # Check App Icons
            filtered = self.get_filtered_apps()
            start = self.current_page * PAGE_SIZE
            page_apps = filtered[start:start + PAGE_SIZE]
            for i, app in enumerate(page_apps):
                col, row = i % COLUMNS, i // COLUMNS
                ax = START_X + col * SPACING_X
                ay = START_Y + row * SPACING_Y
                if ax <= client_x <= ax + ICON_SIZE and ay <= client_y <= ay + ICON_SIZE:
                    try: os.startfile(app["path"])
                    except: pass
            return 0

        elif msg == win32con.WM_PAINT:
            hdc, ps = win32gui.BeginPaint(hwnd)
            rect = win32gui.GetClientRect(hwnd)
            win32gui.FillRect(hdc, rect, win32gui.CreateSolidBrush(BG_COLOR))
            
            # Search Bar
            win32gui.FillRect(hdc, (50, 20, WINDOW_W - 50, 80), win32gui.CreateSolidBrush(HIGHLIGHT_COLOR))
            win32gui.SetTextColor(hdc, TEXT_COLOR)
            win32gui.SetBkMode(hdc, win32con.TRANSPARENT)
            display_text = f"Search: {self.search_query}_" if self.search_query else "Search apps..."
            win32gui.DrawText(hdc, display_text, -1, (60, 30, WINDOW_W - 60, 70), win32con.DT_LEFT | win32con.DT_VCENTER)
            
            # Nav Buttons
            win32gui.FillRect(hdc, (20, WINDOW_H//2 - 25, 70, WINDOW_H//2 + 25), win32gui.CreateSolidBrush(BUTTON_COLOR))
            win32gui.DrawText(hdc, "<", -1, (20, WINDOW_H//2 - 25, 70, WINDOW_H//2 + 25), win32con.DT_CENTER | win32con.DT_VCENTER)
            win32gui.FillRect(hdc, (WINDOW_W - 70, WINDOW_H//2 - 25, WINDOW_W - 20, WINDOW_H//2 + 25), win32gui.CreateSolidBrush(BUTTON_COLOR))
            win32gui.DrawText(hdc, ">", -1, (WINDOW_W - 70, WINDOW_H//2 - 25, WINDOW_W - 20, WINDOW_H//2 + 25), win32con.DT_CENTER | win32con.DT_VCENTER)
            
            # Grid
            filtered = self.get_filtered_apps()
            start = self.current_page * PAGE_SIZE
            page_apps = filtered[start:start + PAGE_SIZE]
            for i, app in enumerate(page_apps):
                col, row = i % COLUMNS, i // COLUMNS
                x, y = START_X + col * SPACING_X, START_Y + row * SPACING_Y
                if app["icon"]:
                    win32gui.DrawIconEx(hdc, x, y, app["icon"], ICON_SIZE, ICON_SIZE, 0, None, win32con.DI_NORMAL)
                win32gui.DrawText(hdc, app["name"][:12], -1, (x - 20, y + ICON_SIZE + 5, x + ICON_SIZE + 20, y + ICON_SIZE + 50), win32con.DT_CENTER)
            win32gui.EndPaint(hwnd, ps)
            return 0
        return win32gui.DefWindowProc(hwnd, msg, wp, lp)

    def next_page(self):
        if (self.current_page + 1) * PAGE_SIZE < len(self.get_filtered_apps()):
            self.current_page += 1
            win32gui.InvalidateRect(self.hwnd, None, True)

    def prev_page(self):
        if self.current_page > 0:
            self.current_page -= 1
            win32gui.InvalidateRect(self.hwnd, None, True)

    def get_filtered_apps(self):
        return [a for a in self.apps if self.search_query.lower() in a["name"].lower()]

    def toggle(self):
        self.visible = not self.visible
        if self.visible:
            win32gui.ShowWindow(self.hwnd, win32con.SW_SHOW)
            win32gui.SetForegroundWindow(self.hwnd)
        else:
            win32gui.ShowWindow(self.hwnd, win32con.SW_HIDE)
