from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from datetime import date, timedelta
import time
import re

def get_filtered_yingjiao_jobs():
    # ===================== 核心配置 字段&规则1:1对齐大疆 =====================
    BASE_URL = "https://jobs.hypergryph.com/apply/hypergryph/26325/#/jobs?page=1&commitment%5B0%5D=%E5%85%A8%E8%81%8C&zhineng%5B0%5D=46432&pageSize=15"
    BASE_DETAIL_DOMAIN = "https://jobs.hypergryph.com/apply/hypergryph/26325/"
    EXCLUDE_KEYWORDS = ['硕士', '三年', '3年','四年', '4年', '五年', '5年', '六年', '6年', '七年', '7年', '八年', '8年', '九年', '9年', '十年', '10年']
    
    # ===================== 浏览器配置 完全复用大疆配置 =====================
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")

    driver = webdriver.Remote(
        command_executor="http://192.168.2.53:4444/wd/hub",
        options=options
    ) # type: ignore
    driver.set_page_load_timeout(60)

    # ===================== 工具函数 格式&规则对齐大疆 =====================
    def get_valid_dates():
        """和大疆完全一致：获取近2天的日期，格式统一为YYYY年MM月DD日"""
        today = date.today()
        yesterday = today - timedelta(days=8)
        return [today.strftime("%Y年%m月%d日"), yesterday.strftime("%Y年%m月%d日")]

    def convert_date(date_str: str) -> str:
        """适配鹰角固定格式：发布于 2026-03-25 → 转换为和大疆一致的YYYY年MM月DD日格式"""
        try:
            clean_date = re.search(r'(\d{4}-\d{1,2}-\d{1,2})', date_str)
            if clean_date:
                return date.fromisoformat(clean_date.group(1)).strftime("%Y年%m月%d日")
            return date_str
        except:
            return date_str

    def parse_job_requirement_only(html):
        """【精简版】仅提取岗位要求，不处理职位描述，适配列表页直接提取"""
        # 移除HTML标签，保留文本结构
        html = re.sub(r'<p.*?>', '\n', html)
        html = re.sub(r'</p>', '', html)
        html = re.sub(r'<ol.*?>', '\n', html)
        html = re.sub(r'</ol>', '', html)
        html = re.sub(r'<li.*?>', '\n', html)
        html = re.sub(r'</li>', '', html)
        html = re.sub(r'<br.*?>', '\n', html)
        html = re.sub(r'<.*?>', '', html)
        
        # 清理空白字符
        lines = [line.strip() for line in html.split('\n') if line.strip()]
        pure_text = '\n'.join(lines)
        
        # 所有可能的要求类关键词，全场景兼容
        req_keywords = ["任职要求","岗位要求","任职资格","职责要求","工作要求","职位要求"]
        
        # 定位要求关键词的起始位置
        req_start = -1
        for key in req_keywords:
            pos = pure_text.find(key)
            if pos != -1:
                req_start = pos + len(key)
                break
        
        # 仅提取要求内容，不处理职位描述
        job_req = ""
        if req_start != -1:
            job_req = pure_text[req_start:].strip()
        
        # 清理空行，保证格式整洁
        job_req = '\n'.join([line for line in job_req.split('\n') if line.strip()])
        return job_req

    # ===================== 核心流程 简化提取，列表页一次性完成 =====================
    valid_dates = get_valid_dates()
    
    # 1. 打开列表页，等待SPA页面完全渲染
    driver.get(BASE_URL)
    time.sleep(5)
    job_items = driver.find_elements(By.CSS_SELECTOR, ".container-aOp138AX_X.normal-TBuWTpDMcE.list-oR2doUijv4")
    raw_jobs = []

    for item in job_items:
        try:
            # 滚动确保元素可见，避免提取失败
            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", item)
            time.sleep(0.5)

            # 1. 提取详情页链接（仅保留URL，不跳转访问）
            job_a_tag = item.find_element(By.CSS_SELECTOR, "a.link-txmgVOCVz9")
            detail_href = job_a_tag.get_attribute("href")
            # 兜底兼容相对路径，自动补全域名
            detail_url = BASE_DETAIL_DOMAIN + detail_href if detail_href.startswith("#") else detail_href

            # 2. 提取基础信息
            job_name = item.find_element(By.CSS_SELECTOR, ".title-u2qk9xX9Ie.target-color-container").text.strip()
            update_time_raw = item.find_element(By.CSS_SELECTOR, ".published-at-PQ5IBWmbJV").text.strip()
            
            # 3. 精准提取工作地点（固定三栏结构，取第三个节点）
            info_nodes = item.find_elements(By.CSS_SELECTOR, ".info-tPG_0QGbhl .sd-foundation-body-secondary-1Z7H-")
            city = info_nodes[2].text.strip() if len(info_nodes) >=3 else "上海市"

            # 4. 列表页直接提取岗位要求，无需跳转详情页
            desc_elem = item.find_element(By.CLASS_NAME, "job-description-WwRmovZt9o")
            inner_html = desc_elem.get_attribute("innerHTML")
            job_requirement = parse_job_requirement_only(inner_html)

            # 组装基础信息，字段和大疆完全对齐
            raw_jobs.append({
                "公司": "鹰角网络",
                "岗位名": job_name,
                "工作地点": city,
                "详情链接": detail_url,
                "更新时间": convert_date(update_time_raw),
                "岗位要求": job_requirement
            })
            print(f"✅ 提取成功: {job_name}")
        except Exception as e:
            # 单个岗位解析失败不中断整体流程
            continue

    # 2. 第一层筛选：仅保留近2天更新的岗位，和大疆逻辑完全一致
    filtered_by_date = [j for j in raw_jobs if j["更新时间"] in valid_dates]

    # 3. 第二层筛选：排除含学历/年限关键词的岗位，和大疆逻辑完全一致
    final_jobs = [j for j in filtered_by_date if not any(k in j["岗位要求"] for k in EXCLUDE_KEYWORDS)]

    driver.quit()
    return final_jobs

# 测试运行
# if __name__ == "__main__":
#     result = get_filtered_yingjiao_jobs()
#     print(f"✅ 鹰角网络筛选完成，符合条件岗位：{len(result)}")
#     for job in result:
#         print(job)