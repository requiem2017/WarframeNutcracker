from PIL import ImageGrab
import win32gui
import win32com.client
import re
from fuzzywuzzy import fuzz
from paddleocr import PaddleOCR
import numpy as np
import time
import winsound
import gc  # Garbage collector for explicit memory cleanup
import logging

nutFlag = False

from ahk import AHK
ahk = AHK(executable_path="C:\\Program Files\\AutoHotkey\\v1.1.37.02\\AutoHotkeyU64.exe")


# Initialize OCR and AHK once
logging.disable(logging.DEBUG)
logging.disable(logging.WARNING)
ocr = PaddleOCR(lang="ch")



scale = 1

def checkRed(image):

    red_threshold = 200  # Intensity
    percentage_threshold = 0.2  # 20% threshold

    red_channel = image[:, :, 0]  # R
    green_channel = image[:, :, 1]  # G
    blue_channel = image[:, :, 2]  # B

    red_dominant = (red_channel > red_threshold) & (red_channel > green_channel) & (red_channel > blue_channel)


    red_pixel_count = np.sum(red_dominant)
    total_pixel_count = image.shape[0] * image.shape[1]
    red_percentage = red_pixel_count / total_pixel_count


    return red_percentage > percentage_threshold

def imageOcr(image, crop_ratios=(0, 0, 1, 1), matchText="", flag = 1):
    #crop using ratio
    img_width, img_height = image.size
    left = int(img_width * crop_ratios[0])
    top = int(img_height * crop_ratios[1])
    right = int(img_width * crop_ratios[2])
    bottom = int(img_height * crop_ratios[3])
    image_array = np.array(image)
    cropped_array = image_array[top:bottom, left:right]

    #check oxygen
    if flag == 3:
        return checkRed(cropped_array), cropped_array

    result = ocr.ocr(cropped_array, cls=True)

    if not result or not result[0]:
        return False, cropped_array

    texts = "".join([line[-1][0] for line in result[0]])

    #check relic UI
    if flag == 1:
        score = fuzz.partial_token_sort_ratio(matchText, texts)
        return score > 80, cropped_array
    #check death UI
    elif flag == 2:
        if "活中" in texts:
            return False, cropped_array
        for i in matchText:
            if i in texts:
                return True, cropped_array
    else:
        raise Exception("Unknown usecase of imageOCR")
    
    return False, cropped_array



class WindowMgr:
    def __init__(self):
        self._handle = None

    def find_window_wildcard(self, wildcard):
        self._handle = None
        win32gui.EnumWindows(self._window_enum_callback, wildcard)

    def _window_enum_callback(self, hwnd, wildcard):
        if re.match(wildcard, str(win32gui.GetWindowText(hwnd))) is not None:
            self._handle = hwnd

    def set_foreground(self):
        shell = win32com.client.Dispatch("WScript.Shell")
        shell.SendKeys('%')
        win32gui.SetForegroundWindow(self._handle)

    def get_rect(self):
        return win32gui.GetWindowRect(self._handle)

def getScreenshot(window, scale):
    dimensions = tuple(int(i * scale) for i in window.get_rect())
    return ImageGrab.grab(dimensions, include_layered_windows=False, all_screens=True)

window = WindowMgr()
window.find_window_wildcard("Warframe.*")
oxygenCount = 0
while True:
    screenshot = getScreenshot(window, scale)

    if nutFlag:
        result, _ = imageOcr(screenshot, (0.21, 0.03, 0.31, 0.09), "选择")

        
        if result:
            oxygenCount = 0
            winsound.Beep(1000, 1000)
            time.sleep(1)
            winsound.Beep(2000, 1000)
            
            ahk.block_input("MouseMove")
            currWindow = ahk.get_active_window()
            ahk.win_activate("Warframe")
            time.sleep(np.random.uniform(0.1, 0.3))
            randRange = 20
            ahk.mouse_move(
                x=np.random.uniform(474-randRange, 474+randRange), 
                y=np.random.uniform(303-randRange, 303+randRange), 
                speed=np.random.uniform(10, 20)
            )

            for _ in range(2):
                ahk.click()
                time.sleep(np.random.uniform(0.1, 0.3))

            ahk.key_press('Space Down')
            time.sleep(np.random.uniform(0.05, 0.08))
            ahk.key_press('Space Up')
            time.sleep(np.random.uniform(0.1, 0.3))

            if currWindow.get_title() != "Warframe":
                currWindow.activate()
            ahk.block_input("MouseMoveOff")

    warningFlag, cropped_array = imageOcr(screenshot, (0.4, 0.4, 0.6, 1), "复活死亡", flag = 2)
    if warningFlag:
        print ("death flag detected")
    '''
    flag2, cropped_array = imageOcr(screenshot, (0.01, 0.18, 0.1, 0.25), "", flag = 3)
    if flag2:
        oxygenCount == 1
    if flag2:
        print("oxygen limit")
    '''

    if (warningFlag or oxygenCount > 5):
        for _ in range(5):
            winsound.Beep(1000, 500)
            time.sleep(0.5)

        
        ahk.block_input("MouseMove")
        ahk.win_activate("Warframe")
        time.sleep(np.random.uniform(0.1, 0.3))

        randRange = 200
        ahk.mouse_move(
            x=np.random.uniform(700-randRange, 700+randRange), 
            y=np.random.uniform(500-randRange, 500+randRange), 
            speed=np.random.uniform(10, 20)
        )
        ahk.click()
        time.sleep(np.random.uniform(0.1, 0.3))

        ahk.key_press('Esc Down')
        time.sleep(np.random.uniform(0.05, 0.08))
        ahk.key_press('Esc Up')

        ahk.block_input("MouseMoveOff")
    
        raise Exception("Check death") 
        #exit()

    # Explicitly delete screenshot and invoke garbage collection
    del screenshot
    gc.collect()

    time.sleep(3)
