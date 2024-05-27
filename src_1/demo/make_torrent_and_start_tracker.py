""" 兼顾做种，以及运行server文件 """

import os
import sys

# 这里是源代码的路径，可自行修改为对应的相对路径或绝对路径。
SRC_PATH = '../backend/'
sys.path.append(SRC_PATH)

from torrent import * #! 此处报错可忽略


full_file = './seed/test.mp4'
TRACKER_IP = '10.0.0.1'
TRACKER_PORT = 5000
# 制作种子文件，默认存到当前目录下
make_torrent_file(full_file,  tracker_ip = TRACKER_IP, tracker_port = TRACKER_PORT)
print("种子文件已经生成")

# 运行server端
os.system("python "+ SRC_PATH + "server.py")

