# main.py
import asyncio
import datetime
from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.star import Context, Star, register
from astrbot.api import logger, AstrBotConfig
from astrbot.core.message.message_event_result import MessageChain
from .jobs_tencent import get_filtered_tencent_jobs

# 格式化消息
def format_msg(jobs):
    if not jobs:
        return "✅ 暂无符合条件的腾讯运营岗位"
    text = [f"🎯 腾讯运营岗位（共{len(jobs)}个）"]
    for i, job in enumerate(jobs, 1):
        text.append(f"\n{i}. {job['岗位名']}\n📍{job['工作地点']} | 📅{job['更新时间']}\n🔗{job['详情链接']}")
    return "\n".join(text)

# 注册插件
@register("astrbot_plugin_tencent_job", "Dev", "腾讯岗位推送", "1.0", "")
class TencentJobPlugin(Star):
    def __init__(self, context: Context, config: AstrBotConfig):
        super().__init__(context)
        self.config = config
        self.groups = getattr(config, "groups", [])
        self.push_time = getattr(config, "push_time", "09:30")
        self._scheduler_task = asyncio.create_task(self.schedule_loop())
        logger.info("✅ 腾讯岗位插件加载完成")

    # 指令：/tencent
    @filter.command("tencent")
    async def get_jobs(self, event: AstrMessageEvent):
        try:
            # 【修复】正常 await 异步函数，无报错
            jobs = await get_filtered_tencent_jobs()
            yield event.plain_result(format_msg(jobs))
        except Exception as e:
            yield event.plain_result(f"❌ 失败：{str(e)}")

    # 管理员状态指令
    @filter.permission_type(filter.PermissionType.ADMIN)
    @filter.command("tencent_status")
    async def status(self, event: AstrMessageEvent):
        now = datetime.datetime.now()
        h, m = map(int, self.push_time.split(":"))
        next_t = now.replace(hour=h, minute=m, second=0)
        if next_t < now:
            next_t += datetime.timedelta(days=1)
        wait = int((next_t - now).total_seconds() / 60)
        yield event.plain_result(f"运行中\n推送时间：{self.push_time}\n下次推送：{wait}分钟后")

    # 定时推送
    async def schedule_loop(self):
        while True:
            try:
                now = datetime.datetime.now()
                h, m = map(int, self.push_time.split(":"))
                next_t = now.replace(hour=h, minute=m, second=0)
                if next_t < now:
                    next_t += datetime.timedelta(days=1)
                await asyncio.sleep((next_t - now).total_seconds())
                
                # 推送逻辑
                jobs = await get_filtered_tencent_jobs()
                if jobs and self.groups:
                    msg = format_msg(jobs)
                    for g in self.groups:
                        await self.context.send_message(g, MessageChain().message(msg))
                        await asyncio.sleep(1)
                await asyncio.sleep(60)
            except Exception as e:
                logger.error(f"定时任务错误：{e}")
                await asyncio.sleep(300)

    # 卸载停止任务
    async def terminate(self):
        self._scheduler_task.cancel()
        logger.info("🛑 插件已停止")