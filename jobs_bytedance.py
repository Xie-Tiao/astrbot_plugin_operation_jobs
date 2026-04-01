# jobs_bytedance.py
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException
from datetime import datetime, timedelta
import time

def get_filtered_bytedance_jobs():
    # ===================== 核心配置（可自定义修改） =====================
    TARGET_URL = "https://jobs.bytedance.com/experienced/position?keywords=&category=&location=CT_125%2CCT_128%2CCT_52&project=&type=&job_hot_flag=&current=1&limit=10&functionCategory=&tag="
    # 时间筛选：只保留近N天发布的岗位（0=不筛选，全量抓取）
    DAYS_THRESHOLD = 2
    KEYWORD_FILTER = ["运营"]
    EXCLUDE_KEYWORDS = ['硕士','四年', '4年', '五年', '5年', '六年', '6年', '七年', '7年', '八年', '8年', '九年', '9年', '十年', '10年']
    # 岗位详情链接前缀
    JOB_DETAIL_URL = "https://jobs.bytedance.com/experienced/position/{}/detail"
    # =================================================================

    # ===================== 浏览器配置（防检测 + 无界面模式） =====================
    edge_options = Options()
    edge_options.add_argument("--headless=new")
    edge_options.add_argument("--no-sandbox")
    edge_options.add_argument("--disable-dev-shm-usage") # 强制使用磁盘(/tmp)代替物理内存(/dev/shm)
    edge_options.add_argument('--blink-settings=imagesEnabled=false') # 不加载图片，极其省内存
    edge_options.add_argument("--incognito")
    edge_options.add_argument("--disable-blink-features=AutomationControlled")
    edge_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    edge_options.add_experimental_option("useAutomationExtension", False)

    # 对接Selenium Grid
    driver = webdriver.Remote(
        command_executor="http://192.168.2.53:4444/wd/hub",
        options=edge_options
    ) # type: ignore
    driver.set_page_load_timeout(60)
    driver.implicitly_wait(10)

    # ===================== 工具函数 =====================
    def convert_timestamp(timestamp_ms: int) -> str:
        """将毫秒时间戳转换为格式化日期字符串，且只保留年月日"""
        try:
            return datetime.fromtimestamp(timestamp_ms / 1000).strftime("%Y-%m-%d")
        except:
            return ""

    def is_job_valid(job):
        """岗位校验：时间筛选 + 关键词筛选"""
        # 1. 发布时间校验
        if DAYS_THRESHOLD > 0:
            try:
                publish_time = datetime.fromtimestamp(job.get("publish_time", 0) / 1000)
                threshold_time = datetime.now() - timedelta(days=DAYS_THRESHOLD)
                if publish_time < threshold_time:
                    return False
            except:
                pass
        
        # 2. 岗位类型关键词校验
        if KEYWORD_FILTER:
            job_category = job.get("job_category", {}).get("name", "").lower()
            print(job_category)
            if not any(keyword.lower() in job_category for keyword in KEYWORD_FILTER):
                return False
        
        return True

    # ===================== API接口拦截注入函数 =====================
    def inject_api_interceptor(driver_instance):
        driver_instance.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
            "source": """
                window.CAPTURE_API_DATA = null;
                // 拦截Fetch请求
                const rawFetch = window.fetch;
                window.fetch = async (...args) => {
                    const resp = await rawFetch(...args);
                    if(args[0].includes('/api/v1/search/job/posts')){
                        window.CAPTURE_API_DATA = await resp.clone().json();
                    }
                    return resp;
                };
                // 拦截XHR请求兜底
                const rawXHR = window.XMLHttpRequest;
                window.XMLHttpRequest = function(){
                    const xhr = new rawXHR();
                    xhr.addEventListener('load', ()=>{
                        if(xhr.responseURL.includes('/api/v1/search/job/posts')){
                            try{
                                window.CAPTURE_API_DATA = JSON.parse(xhr.responseText);
                            }catch{}
                        }
                    });
                    return xhr;
                };
            """
        })

    # ===================== 核心抓取流程 =====================
    job_list_collect = []
    page_num = 1
    stop_crawl = False

    # 首次注入接口拦截脚本
    inject_api_interceptor(driver)

    # 多页循环抓取
    while not stop_crawl:
        print(f"[字节跳动] 正在抓取第 {page_num} 页...")
        
        # 第一页直接访问，后续页点击翻页
        if page_num == 1:
            driver.get(TARGET_URL)
        time.sleep(4)

        # 获取页面捕获的API数据
        api_data = driver.execute_script("return window.CAPTURE_API_DATA")
        if not api_data or api_data.get("code") != 0:
            print("[字节跳动] API数据获取失败，终止抓取")
            break

        # 解析岗位列表
        data = api_data.get("data", {})
        job_list = data.get("job_post_list", [])
        if not job_list:
            print("[字节跳动] 当前页无岗位数据，终止抓取")
            break

        # 遍历校验岗位
        for job in job_list:
            # 时间过期直接终止全部抓取
            if DAYS_THRESHOLD > 0:
                try:
                    publish_time = datetime.fromtimestamp(job.get("publish_time", 0) / 1000)
                    threshold_time = datetime.now() - timedelta(days=DAYS_THRESHOLD)
                    if publish_time < threshold_time:
                        print("[字节跳动] 遇到过期岗位，停止全部抓取")
                        stop_crawl = True
                        break
                except:
                    pass

            # 校验通过则收集岗位信息
            if is_job_valid(job):
                job_id = job.get("id", "")
                job_info = {
                    "公司": "字节跳动",
                    "岗位名": job.get("title", ""),
                    "工作地点": job.get("city_info", {}).get("name", ""),
                    "详情链接": JOB_DETAIL_URL.format(job_id),
                    "更新时间": convert_timestamp(job.get("publish_time", 0)),
                    "岗位类型": job.get("job_category", {}).get("name", ""),
                    "岗位职责": job.get("description", ""),
                    "任职要求": job.get("requirement", ""),
                    "工作地址": job.get("job_post_info", {}).get("address", "")
                }
                job_list_collect.append(job_info)

        if stop_crawl:
            break

        # ===================== 翻页逻辑 =====================
        try:
            next_button = driver.find_element(
                By.XPATH,
                "//li[@title='下一页' and contains(@class, 'atsx-pagination-next') and @aria-disabled='false']"
            )
            # 重置捕获变量 + 点击下一页
            driver.execute_script("window.CAPTURE_API_DATA = null;")
            next_button.click()
            page_num += 1
            # 重新注入拦截脚本 + 等待加载
            inject_api_interceptor(driver)
            time.sleep(4)

        except NoSuchElementException:
            print("\n🏁 已到达最后一页，抓取结束！")
            break

    # 最终过滤：排除长年限、硕士
    result = [
        job for job in job_list_collect
        if not any(k in job["任职要求"] for k in EXCLUDE_KEYWORDS)
    ]

    # 关闭浏览器
    driver.quit()
    return result

# 测试代码
# if __name__ == "__main__":
#     jobs = get_filtered_bytedance_jobs()
#     print(f"\n✅ 字节跳动抓取完成 | 符合条件岗位：{len(jobs)} 个")
#     print("-" * 80)
#     for idx, job in enumerate(jobs, 1):
#         print(f"{idx}. {job['岗位名']} | {job['工作地点']} | {job['更新时间']}")
#         print(f"链接：{job['详情链接']}\n")