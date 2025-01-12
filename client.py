import usb.core
import usb.util
import sys, time
import coloredlogs, logging
import cv2
import mss  # 用于屏幕截图

# 初始化日志
logger = logging.getLogger(__name__)
coloredlogs.install(level='DEBUG')

fw_path = "G25_MainFW_1.9.2.decrypted.img"
device_vid = 0x2e09
device_pid = 0x0030

device: usb.core.Device = None

# 固件加载函数
def load_fw():
    bootloader_vid = 0x03e7  
    bootloader_pid = 0x2150
    dev: usb.core.Device = usb.core.find(idVendor=bootloader_vid, idProduct=bootloader_pid)
    if dev is None:
        logger.error("Device not found, please try again")
    else:
        logger.info(f"Found Movidius MA2X5X bootloader device at bus {dev.bus} device {dev.address}")
        dev.set_configuration()
        with open(fw_path, "rb") as f:
            data = f.read()
            fw_size = len(data)
            logger.info(f"Firmware loaded from path: {fw_path}")
            start_time = time.time()
            dev.write(0x01, data)
            logger.info(f"loaded firmware of {fw_size / 1024:.1f} kiB in {(time.time() - start_time) * 1000:.1f} ms = {(fw_size / 1024) / (time.time() - start_time):.1f} kiB/s")
            logger.info("Firmware loaded successfully")

# 设备等待
def wait_for_device(timeout_ms = 5000):
    logger.info("Waiting for device")
    start_time = time.time()
    while True:
        device = usb.core.find(idVendor=device_vid, idProduct=device_pid)
        if device is not None:
            break
        if time.time() - start_time > timeout_ms / 1000:
            logger.error("Device not found, please try again")
            sys.exit(1)
        time.sleep(0.1)
    logger.info("Device found")

# 打开设备
def open_device():
    global device
    device = usb.core.find(idVendor=device_vid, idProduct=device_pid)
    if device is None:
        logger.error("Device not found, please try again")
    else:
        logger.info(f"Found device at bus {device.bus} device {device.address}")

# 获取LCD信息
def lcd_get_info():
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

# 向LCD传输图像
def lcd_xfer_image(width, height, data):
    buf = bytearray()
    buf += width.to_bytes(4, byteorder="little")
    buf += height.to_bytes(4, byteorder="little")
    buf += b"\x01\x00\x00\x00\x00\x00\x00\x00"
    buf += data
    device.write(0x01, buf)

# 屏幕录制函数
def record_screen():
    with mss.mss() as sct:
        # 获取屏幕大小
        screen = sct.monitors[1]  # 默认屏幕
        screen_width = screen['width']
        screen_height = screen['height']

        while True:
            # 捕获屏幕截图
            screenshot = sct.grab(screen)
            img = cv2.cvtColor(np.array(screenshot), cv2.COLOR_BGR2RGB)
            
            # 调整图像大小以适应LCD屏幕
            info = lcd_get_info()
            img_resized = cv2.resize(img, (info["width"], info["height"]))
            
            # 转换颜色格式到 ARGB8888
            img_resized = cv2.cvtColor(img_resized, cv2.COLOR_RGB2RGBA)
            
            # 将图像数据转换为字节流并传输到LCD
            data = img_resized.tobytes()
            lcd_xfer_image(info["width"], info["height"], data)

            # 暂停一小会，防止过快运行
            time.sleep(0.05)

def main():
    if not usb.core.find(idVendor=device_vid, idProduct=device_pid):
        load_fw()
        wait_for_device()
    open_device()

    # 开始屏幕录制并传输到 LCD
    record_screen()

if __name__ == "__main__":
    main()
