"""
针对HTML中&#x开头的转义序列，在xpath获取text()后，或者etree.tostring(xpathselector).decode('utf-8')后，
会默有转义序列html.unescape()的效果，在字体加密中需要的是原序列，这里转换回16进制；

以下代码案列实现：'+./¥' ==> '002B' . '002F', '00A5'
为方便字体解密时候使用，组织成字典形式：
{'int_part': ['4E01'], 'decimal_part': [0]}
"""

def singlestr_to_hex(single_str):
    """将单个字符串转换为16进制"""
    # 现将字符转换为ASCII值，在将ASCII转换为16进制
    return hex(ord(single_str))

# 将价格数据拆分为小数和整数分别转码
def get_hex_back(multi_str):
    """将售价xxx.xxx类型的编码转换为16进制码，返回字典"""
    price_info = multi_str.split('.')
    int_part = price_info[0]
    # 有些售价信息没有小数点，需要判断：
    try:
        decimal_part = price_info[1]
    except Exception as e:
        decimal_part = 0
    # 构造存放16进制信息的字典
    price_code = {}
    # 分别对整数和小数部分进行转换
    price_code['int_part'] = decode_part(int_part)
    price_code['decimal_part'] = decode_part(decimal_part)
    return price_code

# 对单独的某一部分字符进行转码
def decode_part(str_part):
    """遍历字符串，将字符转换为16进制码存放在列表返回"""
    if str_part:
        result = []
        for single_str in str_part:
            hex_code = singlestr_to_hex(single_str)[2:]
            # 转换格式：2f => 002F
            hex_code = hex_code.rjust(4, '0').upper()
            result.append(hex_code)
    else:
        return [0]
    return result

if __name__ == '__main__':
    #  示例：将售价转换回16进制（后续逻辑会用16进制码查找对应字体）
    a = '+./¥'
    result = get_hex_back(a)  # => {'int_part': ['002B'], 'decimal_part': ['002F', '00A5']}
    print(result)

