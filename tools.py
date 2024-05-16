import re

def get_port_from_url(url):
    match = re.search(r':(\d+)/', url)  # 查找冒号后面跟着数字，后面紧接着斜杠的模式
    if match:
        return int(match.group(1))  # 转换找到的数字为整数
    else:
        raise ValueError("Invalid URL, port not found.")


'''
# 示例用法
announce_url = 'http://127.0.0.1:6881/announce'
server_port = get_port_from_url(announce_url)
print(server_port)  # 应该输出 6881
'''