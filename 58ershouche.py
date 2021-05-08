import requests
from fake_useragent import UserAgent
import re
import base64
import sys
from fontTools.ttLib import TTFont
from lxml import etree
import pymysql
# Unicode => ASCII => hex
from unicode_to_hex import get_hex_back


# 继承重写TTFont，直接使用字节串数据，避免在动态字体加密中重复打开关闭woff文件
class MyTTFont(TTFont):
    """
    主要目的：实现直接读取字节串数据，避免每次存取文件
    fontTools-version: 4.22.0
    """
    def __init__(self, file_content, checkChecksums=0, fontNumber=-1, _tableCache=None):
        from fontTools.ttLib.sfnt import SFNTReader
        from io import BytesIO
        # 用content数据代替原码的open()
        file = BytesIO(file_content)
        super().__init__()
        # 继承父类的初始化，但是没有传值会影响后续赋值，
        self._tableCache = _tableCache
        self.reader = SFNTReader(file, checkChecksums, fontNumber=fontNumber)
        self.sfntVersion = self.reader.sfntVersion
        self.flavor = self.reader.flavor
        self.flavorData = self.reader.flavorData


class TongchengSpider:
    def __init__(self):
        # 匹配字体文件的base64数据正则
        self.regex = r"charset=utf-8;base64,(.*?)'\) format\('truetype'\)"
        self.pattern = re.compile(self.regex, re.S)
        # 存入mysql数据库
        self.db = pymysql.connect(
            host='192.168.31.63',
            port=3306,
            user='root',
            password='123456',
            database='ershouche'
        )
        self.cursor = self.db.cursor()
        self.ins = 'insert into carinfo(brand,detail,price) values(%s,%s,%s)'

    def get_requests_data(self, url):
        """简单封装了随机UA的get请求"""
        ua = UserAgent().chrome
        headers = {'User-Agent': ua}
        html = requests.get(url=url, headers=headers).text
        # print(html)
        return html

    # 提取网页中的base64_font数据
    def parse_font(self, html):
        """传入HTML text数据提取font文件的base64数据"""
        font_base64 = self.pattern.findall(html)
        if font_base64:
            font_base64 = font_base64[0].encode()
            # 返回base64解码后的字节串数据
            return base64.b64decode(font_base64)
        else:
            sys.exit('没有匹配到字体数据')

    # 创建价格字符到实际价格的映射
    def create_font_dict(self, font):
        """
        根据font对象创建字典，针对只有0-9且顺序排列的字体文件
        :param font:font对象
        :return:hex到font数字的映射
        """
        font_names = font.getGlyphOrder()
        font_dict = {}
        number = 0
        # 这种字体动态加密较为简单，虽然字体文件在变换，但是GlyphOder和字体的对应并没有改变
        for font_name in font_names[1:]:
            font_name = font_name[3:]
            font_dict[font_name] = str(number)
            number += 1
        return font_dict

    # 提取二手车页面中的品牌、车型、价格字符，以及字体还原
    def parse_ershouche_data(self, html, font_dict):
        p = etree.HTML(html)
        info_title = p.xpath('//li[@class="info"]/div/a')
        result_list = []
        for msg in info_title:
            car_brand = msg.xpath('.//span[@class="info_link"]/font/text()')[0]
            car_info = msg.xpath('.//span[@class="info_link"]/text()')[0].strip()
            car_price_obj = msg.xpath('.//div[@class="info--price"]/b/text()')[0]
            price_info = get_hex_back(car_price_obj)
            price_info = self.decode_real_price(price_info, font_dict) + '万元'
            result_list.append((car_brand, car_info, price_info))
        return result_list

    # 解析拼接出实际显示的价格数据
    def decode_real_price(self, price_info_dict, font_dict):
        """
        将网页源码中的16进制码转换为实际显示字体对应的数字
        :param price_info_dict: 整数部分和小数部分字典 {'int_part': ['2f'], 'decimal_part': ['2d']}
        :param font_dict: hex到font字体的查询字典 {'8D77': 0, '5143': 1,...}
        :return:拼接好的价格数据，不带单位，单位为：万元
        """
        # 获取整数和小数部分编码
        int_part_list = price_info_dict['int_part']
        decimal_part_list = price_info_dict['decimal_part']
        # 查询转换整数部分
        int_part = self.query_hex_codes(int_part_list, font_dict)
        # 如果list内元素为0而不是16进制码，代表没有数据，注意，实际价格若为0，也应该有编码查询到font字体的‘0’
        if not decimal_part_list[0]:
            return int_part
        else:
            # 查询转换小数部分
            decimal_part = self.query_hex_codes(decimal_part_list, font_dict)
            return int_part + '.' + decimal_part

    # 把一长串价格字符查找拼接成价格数字，不包含小数点
    def query_hex_codes(self, hex_list, font_dict):
        """
        遍历列表中的hex，查询对应的font字体
        :param hex_list: 网页源码中价格加密的hex
        :param font_dict: hex到font字体的映射
        :return:
        """
        price_str = ''
        for item in hex_list:
            price_slices = font_dict.get(item)
            price_str += price_slices
        return price_str

    def save_mysql(self,result_list):
        self.cursor.executemany(self.ins,result_list)
        self.db.commit()

    def run(self):
        # 以目标网站前5页内容为例
        for i in range(5):
            url = 'https://cd.58.com/ershouche/pn%s/' % (i+1)
            html = self.get_requests_data(url)
            # 构建出font查询字典：
            font_content = self.parse_font(html)
            font = MyTTFont(font_content)
            # 转为xml文件，重写的MyTTFont可以实现原有功能
            # font.saveXML('1.xml')
            font_dict = self.create_font_dict(font)
            # print(font_dict)
            font.close()
            result_list = self.parse_ershouche_data(html, font_dict)
            print(result_list)
            self.save_mysql(result_list)
        self.cursor.close()
        self.db.close()

if __name__ == '__main__':
    spider = TongchengSpider()
    spider.run()
