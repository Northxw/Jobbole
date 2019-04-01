import hashlib

def get_md5(url):
    # 判断URL的编码
    if isinstance(url, str):
        url = url.encode('utf-8')
    m = hashlib.md5()
    m.update(url)
    return m.hexdigest()

if __name__ == "__main__":
    # URL：传入函数之前先做UTF8编码
    print(get_md5("http://jobbole.com".encode("utf-8")))