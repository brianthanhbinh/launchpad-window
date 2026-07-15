import win32con
import win32gui
import win32api
import os

# Biến toàn cục cố định vùng nhớ, tránh bị Python Garbage Collector xóa
_toggle_callback = None
_bg_color_ref = 0
_h_bitmap = None  # Lưu handle của ảnh bitmap

def get_windows_color(r, g, b):
    r = max(0, min(255, r))
    g = max(0, min(255, g))
    b = max(0, min(255, b))
    return r + (g << 8) + (b << 16)

def global_wnd_proc(hwnd, message, wparam, lparam):
    global _toggle_callback, _bg_color_ref, _h_bitmap
    
    if message == win32con.WM_PAINT:
        hdc, ps = win32gui.BeginPaint(hwnd)
        rect = win32gui.GetClientRect(hwnd)
        
        # 1. Vẽ nền nút bấm
        brush = win32gui.CreateSolidBrush(_bg_color_ref)
        win32gui.FillRect(hdc, rect, brush)
        win32gui.DeleteObject(brush)
        
        # 2. Vẽ file ảnh launchpadico.bmp nếu tải thành công
        if _h_bitmap:
            # Tạo một Memory Device Context tương thích để giữ cấu trúc ảnh
            hdc_mem = win32gui.CreateCompatibleDC(hdc)
            old_bitmap = win32gui.SelectObject(hdc_mem, _h_bitmap)
            
            # Lấy thông tin kích thước của Bitmap để vẽ chính xác
            bmp_info = win32gui.GetObject(_h_bitmap)
            bmp_w = bmp_info.bmWidth
            bmp_h = bmp_info.bmHeight
            
            # Tính toán căn giữa ảnh bitmap lọt lòng bên trong nút bấm
            rect_w = rect[2] - rect[0]
            rect_h = rect[3] - rect[1]
            dst_x = (rect_w - bmp_w) // 2
            dst_y = (rect_h - bmp_h) // 2
            
            # Sao chép dữ liệu pixel ảnh từ bộ nhớ ra màn hình (Render)
            win32gui.BitBlt(
                hdc, dst_x, dst_y, bmp_w, bmp_h, 
                hdc_mem, 0, 0, win32con.SRCCOPY
            )
            
            # Dọn dẹp cấu trúc DC bộ nhớ tạm thời
            win32gui.SelectObject(hdc_mem, old_bitmap)
            win32gui.DeleteDC(hdc_mem)
        else:
            # Fallback hiển thị chữ phòng trường hợp không tìm thấy file ảnh .bmp
            win32gui.SetTextColor(hdc, 0xFFFFFF)
            win32gui.SetBkMode(hdc, win32con.TRANSPARENT)
            win32gui.DrawText(hdc, "☰", -1, rect, win32con.DT_CENTER | win32con.DT_VCENTER | win32con.DT_SINGLELINE)
            
        win32gui.EndPaint(hwnd, ps)
        return 0
        
    elif message == win32con.WM_LBUTTONDOWN:
        if _toggle_callback:
            _toggle_callback()
        return 0
        
    elif message == win32con.WM_DESTROY:
        # Giải phóng tài nguyên ảnh trong RAM khi tắt ứng dụng
        if _h_bitmap:
            win32gui.DeleteObject(_h_bitmap)
        win32gui.PostQuitMessage(0)
        return 0
        
    return win32gui.DefWindowProc(hwnd, message, wparam, lparam)

def create_taskbar_button(toggle_callback, x=150, y=5, width=36, height=36, bg_color=(50, 50, 50)):
    global _toggle_callback, _bg_color_ref, _h_bitmap
    _toggle_callback = toggle_callback
    _bg_color_ref = get_windows_color(*bg_color)

    # Thử tìm và load file ảnh launchpadico.bmp từ thư mục hiện tại chạy script
    bmp_path = os.path.abspath("launchpadico.bmp")
    if os.path.exists(bmp_path):
        try:
            _h_bitmap = win32gui.LoadImage(
                0, bmp_path, win32con.IMAGE_BITMAP, 
                0, 0, win32con.LR_LOADFROMFILE | win32con.LR_CREATEDIBSECTION
            )
            print(f"DEBUG: Đã nạp thành công ảnh icon từ: {bmp_path}")
        except Exception as e:
            print(f"DEBUG: Lỗi khi load file bitmap: {e}")
            _h_bitmap = None
    else:
        print(f"DEBUG: CẢNH BÁO - Không tìm thấy file ảnh tại: {bmp_path}. Hệ thống sẽ dùng biểu tượng mặc định.")

    # 1. Tìm handle của Taskbar chính làm Owner
    hwnd_taskbar = win32gui.FindWindow("Shell_TrayWnd", None)
    if not hwnd_taskbar:
        print("DEBUG: Không tìm thấy thanh Taskbar hệ thống.")
        return None

    # Đo đạc vị trí thực tế của Taskbar để tính toán tọa độ tuyệt đối
    tb_left, tb_top, tb_right, tb_bottom = win32gui.GetWindowRect(hwnd_taskbar)
    absolute_x = tb_left + x
    absolute_y = tb_top + y

    # 2. Đăng ký Window Class
    wc = win32gui.WNDCLASS()
    wc.lpfnWndProc = global_wnd_proc
    wc.lpszClassName = "TaskbarLaunchpadButton"
    wc.hbrBackground = win32gui.CreateSolidBrush(_bg_color_ref)
    
    try:
        win32gui.RegisterClass(wc)
    except:
        pass  # Lớp ứng dụng đã được đăng ký trước đó

    # 3. Tạo Window POPUP liên kết OWNER bền vững
    hwnd_button = win32gui.CreateWindowEx(
        win32con.WS_EX_TOPMOST | win32con.WS_EX_TOOLWINDOW | win32con.WS_EX_NOACTIVATE,
        "TaskbarLaunchpadButton", 
        "LaunchpadBtn",
        win32con.WS_POPUP | win32con.WS_VISIBLE,
        absolute_x, absolute_y, width, height,
        hwnd_taskbar,  # Liên kết Owner cố định lớp đồ họa với Taskbar
        0, 
        win32api.GetModuleHandle(None), 
        None
    )

    if hwnd_button:
        print(f"DEBUG: Button created successfully! Handle: {hwnd_button}")
        
        # Đảm bảo cửa sổ nổi hàng đầu
        win32gui.SetWindowPos(
            hwnd_button, 
            win32con.HWND_TOPMOST, 
            absolute_x, absolute_y, width, height, 
            win32con.SWP_SHOWWINDOW | win32con.SWP_NOACTIVATE
        )
        win32gui.InvalidateRect(hwnd_button, None, True)
        win32gui.UpdateWindow(hwnd_button)
    else:
        print("DEBUG: FAILED to create button window.")
        
    return hwnd_button

if __name__ == "__main__":
    def my_callback():
        print("-> Launchpad Triggered!")

    # Chạy thử nghiệm
    btn_hwnd = create_taskbar_button(toggle_callback=my_callback, x=150, y=6, width=36, height=36)
    
    if btn_hwnd:
        win32gui.PumpMessages()

