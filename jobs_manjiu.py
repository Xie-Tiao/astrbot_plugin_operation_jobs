from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from datetime import date, timedelta, datetime
import time

def get_filtered_manjiu_jobs():
    # ===================== 核心配置 =====================
    BASE_URL = "https://ooia5293gn.jobs.feishu.cn/index/position/list?keywords=&category=&location=CT_125&project=&type=&job_hot_flag=&current=1&limit=10&functionCategory=7510139416967448895&tag="
    TARGET_API_KEY = "/api/v1/search/job/posts"
    DETAIL_URL_PREFIX = "https://ooia5293gn.jobs.feishu.cn/index/position/"
    EXCLUDE_KEYWORDS = ['硕士', '四年', '4年', '五年', '5年', '六年', '6年', '七年', '7年', '八年', '8年', '九年', '9年', '十年', '10年']
    
    # ===================== 浏览器配置 (复用小红书的Remote Grid) =====================
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument('--blink-settings=imagesEnabled=false')
    options.add_argument("--disable-gpu")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])

    driver = webdriver.Remote(
        command_executor="http://192.168.2.53:4444/wd/hub",
        options=options
    ) # type: ignore
    driver.set_page_load_timeout(60)

    # ===================== 工具函数 =====================
    def get_valid_dates():
        today = date.today()
        yesterday = today - timedelta(days=1)
        return [today.strftime("%Y年%m月%d日"), yesterday.strftime("%Y年%m月%d日")]

    def convert_timestamp(timestamp_ms):
        try:
            if timestamp_ms:
                return datetime.fromtimestamp(timestamp_ms / 1000).strftime("%Y年%m月%d日")
            return ""
        except:
            return ""

    # ===================== 核心流程 =====================
    valid_dates = get_valid_dates()
    job_list_collect = []

    # 页面加载前注入拦截脚本
    def inject_api_interceptor(driver_instance):
        driver_instance.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
            "source": f"""
                window.CAPTURE_API_DATA = null;
                // 拦截 Fetch
                const rawFetch = window.fetch;
                window.fetch = async (...args) => {{
                    const resp = await rawFetch(...args);
                    if(args[0].includes('{TARGET_API_KEY}')){{
                        window.CAPTURE_API_DATA = await resp.clone().json();
                    }}
                    return resp;
                }};
                // 拦截 XHR (备用)
                const rawXHR = window.XMLHttpRequest;
                window.XMLHttpRequest = function(){{
                    const xhr = new rawXHR();
                    xhr.addEventListener('load', ()=>{{
                        if(xhr.responseURL.includes('{TARGET_API_KEY}')){{
                            try{{ window.CAPTURE_API_DATA = JSON.parse(xhr.responseText); }}catch{{}}
                        }}
                    }});
                    return xhr;
                }};
            """
        })

    try:
        inject_api_interceptor(driver)
        print("[蛮啾] 正在加载页面...")
        driver.get(BASE_URL)
        time.sleep(3)

        # 获取API数据
        api_data = driver.execute_script("return window.CAPTURE_API_DATA")
        if not api_data:
            print("[蛮啾] 未能捕获到API数据")
        else:
            job_list = api_data.get("data", {}).get("job_post_list", [])
            if job_list:
                for job in job_list:
                    try:
                        publish_time = convert_timestamp(job.get("publish_time"))
                        
                        # 仅保留近两天发布的岗位
                        if publish_time not in valid_dates:
                            continue
                        
                        job_id = job.get("id", "")
                        job_title = job.get("title", "")
                        job_location = job.get("city_list", [{}])[0].get("name", "")
                        job_description = job.get("description", "").strip()
                        job_requirement = job.get("requirement", "").strip()
                        job_detail_url = f"{DETAIL_URL_PREFIX}{job_id}/detail" if job_id else ""

                        job_info = {
                            "公司": "蛮啾网络",
                            "岗位名": job_title,
                            "工作地点": job_location,
                            "详情链接": job_detail_url,
                            "更新时间": publish_time,
                            "岗位职责": job_description,
                            "岗位要求": job_requirement
                        }
                        job_list_collect.append(job_info)
                    except Exception:
                        continue
    except Exception as e:
        print(f"[蛮啾] 程序运行出错：{str(e)}")
    finally:
        driver.quit()

    # 最终过滤：排除长年限、硕士
    result = [
        job for job in job_list_collect
        if not any(k in job["岗位要求"] for k in EXCLUDE_KEYWORDS)
    ]

    return result

if __name__ == "__main__":
    jobs = get_filtered_manjiu_jobs()
    print(f"\n✅ 蛮啾网络抓取完成 | 符合条件岗位：{len(jobs)} 个")
    print("-" * 80)
    for idx, job in enumerate(jobs, 1):
        print(f"{idx}. {job['岗位名']} | {job['工作地点']} | {job['更新时间']}")
        print(f"链接：{job['详情链接']}\n")