import requests
from bs4 import BeautifulSoup
import time
import pandas as pd
import re
import os


class AllCuisinesCrawler:
    def __init__(self):
        self.base_url = "https://home.meishichina.com"
        # 八大菜系的URL映射
        self.cuisine_urls = {
            "鲁菜": "https://home.meishichina.com/recipe/lucai/",
            "川菜": "https://home.meishichina.com/recipe/chuancai/",
            "粤菜": "https://home.meishichina.com/recipe/yuecai/",
            "苏菜": "https://home.meishichina.com/recipe/sucai/",
            "闽菜": "https://home.meishichina.com/recipe/mincai/",
            "浙菜": "https://home.meishichina.com/recipe/zhecai/",
            "徽菜": "https://home.meishichina.com/recipe/huicai/",
            "湘菜": "https://home.meishichina.com/recipe/xiangcai/"
        }
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }

    def get_page_content(self, url):
        """获取页面内容"""
        try:
            response = requests.get(url, headers=self.headers, timeout=10)
            response.encoding = 'utf-8'
            if response.status_code == 200:
                return response.text
            else:
                print(f"请求失败，状态码：{response.status_code}")
                return None
        except Exception as e:
            print(f"请求出错：{e}")
            return None

    def parse_food_list(self, html):
        """解析菜品列表页面"""
        soup = BeautifulSoup(html, 'html.parser')
        food_items = []

        # 查找菜品列表项
        items = soup.find_all('div', class_='detail')

        for item in items:
            try:
                # 获取菜名和链接
                name_tag = item.find('a')
                if name_tag:
                    food_name = name_tag.get_text().strip()
                    food_link = name_tag.get('href')

                    # 确保链接是完整的URL
                    if food_link and not food_link.startswith('http'):
                        food_link = self.base_url + food_link

                    food_items.append({
                        'name': food_name,
                        'link': food_link
                    })
            except Exception as e:
                print(f"解析菜品项时出错：{e}")
                continue

        return food_items

    def extract_taste_info(self, html):
        """提取口味信息"""
        soup = BeautifulSoup(html, 'html.parser')

        # 查找所有包含分类信息的div
        category_divs = soup.find_all('div', class_='recipeCategory_sub_R')
        for div in category_divs:
            # 查找所有的li元素
            lis = div.find_all('li')
            for li in lis:
                # 查找包含"口味"的span
                taste_span = li.find('span', class_='category_s2')
                if taste_span and '口味' in taste_span.get_text():
                    # 找到前一个兄弟节点，即包含口味值的span
                    taste_value_span = taste_span.find_previous_sibling('span', class_='category_s1')
                    if taste_value_span:
                        # 提取a标签的title属性
                        a_tag = taste_value_span.find('a')
                        if a_tag and a_tag.get('title'):
                            return a_tag['title']
                        elif a_tag:
                            return a_tag.get_text().strip()

        return "未知"

    def extract_all_ingredients(self, html):
        """提取所有原料信息并合并为一列"""
        soup = BeautifulSoup(html, 'html.parser')
        all_ingredients = []

        try:
            # 查找所有fieldset（主料、辅料、调料）
            fieldsets = soup.find_all('fieldset', class_='particulars')

            for fieldset in fieldsets:
                # 提取该类别下的所有食材
                ingredients_list = fieldset.find('ul')
                if ingredients_list:
                    items = ingredients_list.find_all('li')
                    for item in items:
                        # 提取食材名称和数量
                        name_span = item.find('span', class_='category_s1')
                        amount_span = item.find('span', class_='category_s2')

                        if name_span and amount_span:
                            # 提取食材名称
                            a_tag = name_span.find('a')
                            if a_tag:
                                name = a_tag.get_text().strip()
                            else:
                                name = name_span.get_text().strip()

                            amount = amount_span.get_text().strip()
                            ingredient = f"{name} {amount}"
                            all_ingredients.append(ingredient)

            # 将所有原料合并为一个字符串
            if all_ingredients:
                return '，'.join(all_ingredients)
            else:
                return "未知"
        except Exception as e:
            print(f"提取原料信息出错: {e}")
            return "未知"

    def crawl_cuisine(self, cuisine_name, cuisine_url):
        """爬取单个菜系的前10页"""
        print(f"\n开始爬取{cuisine_name}前10页...")

        max_pages = 10
        page = 1
        cuisine_data = []

        while page <= max_pages:
            if page == 1:
                page_url = cuisine_url
            else:
                page_url = f"{cuisine_url}page/{page}/"

            print(f"  正在处理第 {page}/{max_pages} 页...")

            page_html = self.get_page_content(page_url)
            if not page_html:
                print(f"  无法获取第 {page} 页内容，跳过")
                page += 1
                continue

            # 解析当前页的菜品列表
            food_items = self.parse_food_list(page_html)

            if not food_items:
                print(f"  第 {page} 页没有找到菜品，停止爬取")
                break

            print(f"  第 {page} 页找到 {len(food_items)} 个菜品")

            # 获取每个菜品的详细信息
            for i, item in enumerate(food_items):
                print(f"    进度: {i + 1}/{len(food_items)} - {item['name']}")
                detail_html = self.get_page_content(item['link'])

                if detail_html:
                    taste = self.extract_taste_info(detail_html)
                    ingredients = self.extract_all_ingredients(detail_html)
                else:
                    taste = "未知"
                    ingredients = "未知"

                cuisine_data.append({
                    '菜名': item['name'],
                    '口味': taste,
                    '原料': ingredients
                })

                # 添加延迟，避免请求过快
                time.sleep(0.3)

            page += 1

        print(f"  {cuisine_name}爬取完成，共获取 {len(cuisine_data)} 个菜品")
        return cuisine_data

    def save_cuisine_data(self, cuisine_name, cuisine_data):
        """保存单个菜系数据到CSV文件"""
        if not cuisine_data:
            print(f"  {cuisine_name}没有数据可保存")
            return

        # 创建DataFrame并保存为CSV
        df = pd.DataFrame(cuisine_data)

        # 创建菜系文件夹
        folder_name = "八大菜系数据"
        if not os.path.exists(folder_name):
            os.makedirs(folder_name)

        # 保存为CSV
        csv_filename = f"{folder_name}/{cuisine_name}数据.csv"
        df.to_csv(csv_filename, index=False, encoding='utf-8-sig')
        print(f"  {cuisine_name}数据已保存到 {csv_filename}，共 {len(cuisine_data)} 条记录")

    def print_sample_results(self, cuisine_name, cuisine_data):
        """打印单个菜系的前5个菜品信息"""
        if not cuisine_data:
            return

        print(f"\n  {cuisine_name}前5个菜品信息:")
        for i, item in enumerate(cuisine_data[:5]):
            print(f"    {i + 1}. {item['菜名']}")
            print(f"       口味: {item['口味']}")
            print(f"       原料: {item['原料'][:50]}...")  # 只显示前50个字符

    def crawl_all_cuisines(self):
        """爬取所有八大菜系"""
        print("开始爬取八大菜系数据...")

        # 创建总数据文件夹
        if not os.path.exists("八大菜系数据"):
            os.makedirs("八大菜系数据")

        # 爬取每个菜系
        for cuisine_name, cuisine_url in self.cuisine_urls.items():
            cuisine_data = self.crawl_cuisine(cuisine_name, cuisine_url)
            self.save_cuisine_data(cuisine_name, cuisine_data)
            self.print_sample_results(cuisine_name, cuisine_data)

            # 菜系之间添加较长延迟
            print(f"  等待2秒后处理下一个菜系...")
            time.sleep(2)

        print("\n所有菜系爬取完成！")
        print("数据已分别保存到'八大菜系数据'文件夹中")


def main():
    crawler = AllCuisinesCrawler()
    crawler.crawl_all_cuisines()


if __name__ == "__main__":
    main()