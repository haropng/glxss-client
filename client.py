import usb.core
import usb.util
import pyautogui
import mss
import numpy as np
import cv2
import time
import coloredlogs
import logging

# 配置日志
logger = logging.getLogger(__name__)
coloredlogs.install(level="DEBUG")

# 设备信息
device_vid = 0x2e09
device_pid = 0x0030

device = None  # 全局设备对象

# 打开设备
def open_device():
    global device
    device = usb.core.find(idVendor=device_vid, idProduct=device_pid)
    if device is None:
        logger.error("未找到目标设备，请检查连接！")
        exit(1)
    logger.info(f"找到设备，Bus: {device.bus}, Address: {device.address}")
    if device.is_kernel_driver_active(0):
        logger.info("正在解除内核驱动绑定...")
        device.detach_kernel_driver(0)

# 获取 LCD 信息
def lcd_get_info():
    data = device.ctrl_transfer(0xA1, 0x04, 0x00, 0x03, 0x08)
    width = data[0] | (data[1] << 8)
    height = data[2] | (data[3] << 8)
    orientation = data[4]
    rotation = data[5]
    brightness = data[6] | (data[7] << 8)
    logger.info(f"LCD 信息: 宽度: {width}, 高度: {height}, 方向: {orientation}, 旋转: {rotation}, 亮度: {brightness}")
    return {"width": width, "height": height, "orientation": orientation, "rotation": rotation, "brightness": brightness}

# 传输图像到设备
def lcd_xfer_image(width, height, data):
    buf = bytearray()
    buf += width.to_bytes(4, byteorder="little")
    buf += height.to_bytes(4, byteorder="little")
    buf += b"\x01\x00\x00\x00\x00\x00\x00\x00"  # 固定头部
    buf += data
    device.write(0x01, buf)
    logger.debug(f"传输图像数据：{len(data)} 字节")

# 捕获屏幕
def capture_screen():
    with mss.mss() as sct:
        monitor = sct.monitors[1]  # 捕获主显示器
        screenshot = sct.grab(monitor)
        frame = np.array(screenshot)[:, :, :3]  # 去掉 alpha 通道
        return frame

# 调整分辨率
def resize_frame(frame, width, height):
    return cv2.resize(frame, (width, height))

# 转换为 ARGB8888 格式
def convert_to_argb8888(frame):
    return cv2.cvtColor(frame, cv2.COLOR_BGR2RGBA)

# 主循环
def main_loop(lcd_info):
    width, height = lcd_info["width"], lcd_info["height"]
    while True:
        start_time = time.time()
        try:
            # 捕获屏幕
            frame = capture_screen()
            # 调整分辨率
            frame = resize_frame(frame, width, height)
            # 转换为设备支持的格式
            frame = convert_to_argb8888(frame)
            # 传输到设备
            lcd_xfer_image(width, height, frame.tobytes())
        except Exception as e:
            logger.error(f"传输失败: {e}")
            break
        # 控制帧率
        time.sleep(max(0, 1 / 30 - (time.time() - start_time)))

# 主函数
def main():
    open_device()  # 打开设备
    lcd_info = lcd_get_info()  # 获取 LCD 信息
    main_loop(lcd_info)  # 启动主循环

if __name__ == "__main__":
    main()
