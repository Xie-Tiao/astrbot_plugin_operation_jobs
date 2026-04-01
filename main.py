import asyncio, datetime
from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.star import Context, Star, register
from astrbot.api import logger, AstrBotConfig
from astrbot.core.message.message_event_result import MessageChain

from . import jobs_tencent, jobs_dajiang, jobs_wangyi, jobs_bili, jobs_yingjiao, jobs_xiaohongshu, jobs_bytedance, jobs_mihoyo, jobs_taotian, jobs_aliguoji, jobs_aliyun, jobs_feizhu, jobs_qianwen, jobs_lingxihuyu, jobs_alijiankang, jobs_hujing, jobs_gaode

# ===================== 配置与映射 =====================
# 这里的顺序决定了“查询全部”时的显示顺序
COMPANY_MAP = {
    "tencent":   {"name": "腾讯",   "func": jobs_tencent.get_filtered_tencent_jobs, "sync": False},
    "dji":       {"name": "大疆",   "func": jobs_dajiang.get_filtered_dji_jobs,     "sync": True},
    "wangyi":    {"name": "网易",   "func": jobs_wangyi.get_filtered_wangyi_jobs,    "sync": False},
    "bili":      {"name": "B站",    "func": jobs_bili.get_filtered_bili_jobs,       "sync": True},
    "yingjiao":  {"name": "鹰角",   "func": jobs_yingjiao.get_filtered_yingjiao_jobs,"sync": True},
    "xhs":       {"name": "小红书", "func": jobs_xiaohongshu.get_filtered_xhs_jobs, "sync": True},
    "byte":      {"name": "字节",   "func": jobs_bytedance.get_filtered_bytedance_jobs,"sync": True},
    "mihoyo":    {"name": "米哈游", "func": jobs_mihoyo.get_filtered_mihoyo_jobs,    "sync": False},
    "taotian":   {"name": "淘天",   "func": jobs_taotian.get_filtered_taotian_jobs,  "sync": True},
    "aliguoji":  {"name": "阿里国际", "func": jobs_aliguoji.get_filtered_aliguoji_jobs,  "sync": True},
    "aliyun":    {"name": "阿里云", "func": jobs_aliyun.get_filtered_aliyun_jobs,  "sync": True},
    "feizhu":    {"name": "飞猪",   "func": jobs_feizhu.get_filtered_feizhu_jobs,  "sync": True},
    "qianwen":   {"name": "千问",   "func": jobs_qianwen.get_filtered_qianwen_jobs,  "sync": True},
    "lingxihuyu": {"name": "灵犀互娱", "func": jobs_lingxihuyu.get_filtered_lingxihuyu_jobs,  "sync": True},
    "alijiankang": {"name": "阿里健康", "func": jobs_alijiankang.get_filtered_alijiankang_jobs,  "sync": True},
    "hujing":    {"name": "虎鲸文娱", "func": jobs_hujing.get_filtered_hujing_jobs,  "sync": True},
    "gaode":     {"name": "高德地图", "func": jobs_gaode.get_filtered_gaode_jobs,  "sync": True},
}

@register("astrbot_plugin_job", "Dev", "精简版多平台岗位推送", "2.0")
class JobPlugin(Star):
    def __init__(self, context: Context, config: AstrBotConfig):
        super().__init__(context)
        self.groups = getattr(config, "groups", [])
        self.push_time = getattr(config, "push_time", "09:30")
        self._scheduler_task = asyncio.create_task(self.schedule_loop())

    def _format_unit(self, title: str, jobs: list) -> str:
        """渲染单个公司的岗位列表"""
        if not jobs: return f"\n🔵 {title}\n暂无岗位"
        items = [f"\n🔵 {title}（{len(jobs)}个）"]
        items.extend([f"{i}. {j['岗位名']}\n {j['工作地点']} | {j['更新时间']}\n {j['详情链接']}" for i, j in enumerate(jobs, 1)])
        return "\n".join(items)

    async def _fetch_job(self, key: str) -> list:
        """统一的抓取逻辑，根据 sync 标识自动选择调用方式"""
        conf = COMPANY_MAP[key]
        try:
            if conf["sync"]:
                return await asyncio.to_thread(conf["func"])
            return await conf["func"]()
        except Exception as e:
            logger.error(f"抓取 {conf['name']} 失败: {e}")
            return []

    # ===================== 指令逻辑 =====================
    @filter.command("job")
    async def job_handler(self, event: AstrMessageEvent, company: str = "all"):
        """
        单一指令入口：
        /job         -> 查询全部
        /job tencent -> 仅查询腾讯
        """
        if company != "all" and company not in COMPANY_MAP:
            yield event.plain_result(f"❌ 未知公司。可选: {', '.join(COMPANY_MAP.keys())}")
            return

        yield event.plain_result("🚀 正在查询，请稍候...")
        
        results = []
        target_keys = COMPANY_MAP.keys() if company == "all" else [company]
        
        total_count = 0
        for key in target_keys:
            logger.info(f"开始抓取 {COMPANY_MAP[key]['name']} 岗位")
            jobs = await self._fetch_job(key)
            total_count += len(jobs)
            results.append(self._format_unit(COMPANY_MAP[key]["name"], jobs))
            await asyncio.sleep(0.1)

        header = f"🎯 最新符合条件岗位（总计{total_count}个）\n" if company == "all" else ""
        yield event.plain_result(header + "".join(results))

    @filter.permission_type(filter.PermissionType.ADMIN)
    @filter.command("job_status")
    async def status(self, event: AstrMessageEvent):
        yield event.plain_result(f"运行中\n推送时间：{self.push_time}")

    async def schedule_loop(self):
        while True:
            try:
                now = datetime.datetime.now()
                h, m = map(int, self.push_time.split(":"))
                target = now.replace(hour=h, minute=m, second=0, microsecond=0)
                if target <= now: target += datetime.timedelta(days=1)
                
                await asyncio.sleep((target - now).total_seconds())
                
                # 执行自动推送
                all_content = []
                total = 0
                for key in COMPANY_MAP:
                    logger.info(f"定时任务：开始抓取 {COMPANY_MAP[key]['name']} 岗位")
                    jobs = await self._fetch_job(key)
                    total += len(jobs)
                    all_content.append(self._format_unit(COMPANY_MAP[key]["name"], jobs))
                    await asyncio.sleep(0.5) # 降低瞬时 CPU 占用
                
                if self.groups:
                    msg = f"📢 每日岗位自动推送（总计{total}个）\n" + "".join(all_content)
                    for g in self.groups:
                        await self.context.send_message(g, MessageChain().message(msg))
                        await asyncio.sleep(1)
            except Exception as e:
                logger.error(f"定时任务异常: {e}")
                await asyncio.sleep(60)

    # 卸载停止任务
    async def terminate(self):
        self._scheduler_task.cancel()
        logger.info("🛑 插件已停止运行")