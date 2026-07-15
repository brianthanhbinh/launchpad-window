import win32gui
import win32con
import button
import traceback
import gui  # Import the new GUI module

class LaunchpadGUI:
    def __init__(self):
        self.visible = False
        wc = win32gui.WNDCLASS()
        wc.lpfnWndProc = self.wnd_proc
        wc.lpszClassName = "LaunchpadApp"
        wc.hbrBackground = win32gui.CreateSolidBrush(0x1a1a1a)
        win32gui.RegisterClass(wc)
        
        # Create the hidden window
        self.hwnd = win32gui.CreateWindowEx(
            win32con.WS_EX_TOPMOST | win32con.WS_EX_TOOLWINDOW | win32con.WS_EX_NOACTIVATE,
            "LaunchpadApp", "Launchpad",
            win32con.WS_POPUP,
            400, 300, 600, 450, 0, 0, 0, None
        )

    def wnd_proc(self, hwnd, msg, wp, lp):
        if msg == win32con.WM_PAINT:
            hdc, ps = win32gui.BeginPaint(hwnd)
            win32gui.EndPaint(hwnd, ps)
            return 0
        return win32gui.DefWindowProc(hwnd, msg, wp, lp)

    def toggle(self):
        self.visible = not self.visible
        if self.visible:
            win32gui.ShowWindow(self.hwnd, win32con.SW_SHOW)
        else:
            win32gui.ShowWindow(self.hwnd, win32con.SW_HIDE)

if __name__ == "__main__":
    # Initialize the GUI from the external module
    app_gui = gui.LaunchpadGUI()
    
    # Create the taskbar button
    button.create_taskbar_button(app_gui.toggle, x=943, y=45, bg_color=(20, 20, 20))
    
    # Run the main message loop
    win32gui.PumpMessages()
