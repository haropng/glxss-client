import usb.core
import usb.util
import pyautogui
import cv2
import numpy as np
import time
import logging
import coloredlogs
import argparse
import mss

# 设置日志
logger = logging.getLogger(__name__)
coloredlogs.install(level='DEBUG')

# 参数解析
parser = argparse.ArgumentParser(description="录制屏幕并将其输出到LCD")
parser.add_argument("--mode", type=int, default=1, choices=[1, 2, 3], help="选择运行模式：1 - 最大速度，2 - 最高质量，3 - 均衡模式")
args = parser.parse_args()

# 设备信息
fw_path = "G25_MainFW_1.9.2.decrypted.img"
device_vid = 0x2e09
device_pid = 0x0030
device: usb.core.Device = None

def open_device():
    """打开设备并设置配置"""
    global device
    device = usb.core.find(idVendor=device_vid, idProduct=device_pid)
    if device is None:
        logger.error("Device not found, please try again")
        exit(1)
    else:
        logger.info(f"Found device at bus {device.bus} device {device.address}")
        device.set_configuration()

def lcd_xfer_image(width, height, data):
    """将图像数据传输到LCD"""
    buf = bytearray()
    buf += width.to_bytes(4, byteorder="little")
    buf += height.to_bytes(4, byteorder="little")
    buf += b"\x01\x00\x00\x00\x00\x00\x00\x00"
    buf += data
    try:
        device.write(0x01, buf)
    except usb.core.USBError as e:
        logger.error(f"Failed to write image data to LCD: {e}")
        raise

def capture_screen(image_format="BGRA"):
    """实时捕获屏幕"""
    # 获取屏幕分辨率
    with mss.mss() as sct:
        monitor = sct.monitors[1]  # 获取第一个屏幕
        screenshot = sct.grab(monitor)
        frame = np.array(screenshot)

    # 根据自定义的图像格式转换
    if image_format == "BGRA":
        frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGRA)
    elif image_format == "RGBA":
        frame = cv2.cvtColor(frame, cv2.COLOR_RGB2RGBA)
    elif image_format == "BGR":
        frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
    elif image_format == "RGB":
        frame = cv2.cvtColor(frame, cv2.COLOR_RGB2RGB)
    
    # 获取LCD尺寸，假设已经通过lcd_get_info获取
    info = lcd_get_info()
    img_resized = cv2.resize(frame, (info["width"], info["height"]))
    img_data = img_resized.tobytes()

    return info["width"], info["height"], img_data

def lcd_get_info():
    """获取LCD信息"""
    try:
        data = device.ctrl_transfer(0xa1, 0x04, 0x00, 0x03, 0x08)
        width = data[0] | (data[1] << 8)
        height = data[2] | (data[3] << 8)
        orientation = data[4]
        rotation = data[5]
        brightness = data[6] | (data[7] << 8)
        logger.info(f"LCD info: width: {width}, height: {height}, orientation: {orientation}, rotation: {rotation}, brightness: {brightness}")
        return {
            "width": width,
            "height": height,
            "orientation": orientation,
            "rotation": rotation,
            "brightness": brightness
        }
    except usb.core.USBError as e:
        logger.error(f"Failed to get LCD info: {e}")
        raise

def main():
    """主函数"""
    try:
        open_device()
        logger.info(f"Mode: {args.mode}")
        logger.info("Starting screen capture and display to LCD...")

        while True:
            if args.mode == 1:
                # 最大速度模式：低延迟
                width, height, img_data = capture_screen(image_format="BGR")  # 使用BGR图像格式
            elif args.mode == 2:
                # 最高质量模式：高质量图像
                width, height, img_data = capture_screen(image_format="RGBA")  # 使用RGBA图像格式
            elif args.mode == 3:
                # 均衡模式：合理的质量和速度
                width, height, img_data = capture_screen(image_format="BGRA")  # 使用BGRA图像格式

            # 将图像数据传输到LCD
            lcd_xfer_image(width, height, img_data)

            # 控制屏幕更新的间隔，避免过高的更新频率
            time.sleep(0.05)  # 调整为合适的更新间隔

    except Exception as e:
        logger.error(f"Error during execution: {e}")
        exit(1)

if __name__ == "__main__":
    main()
