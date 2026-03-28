import asyncio
import datetime
from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.star import Context, Star, register
from astrbot.api import logger, AstrBotConfig
from astrbot.core.message.message_event_result import MessageChain
from .jobs_tencent import get_filtered_tencent_jobs

# 工具函数：格式化岗位消息
def format_job_message(jobs):
    if not jobs:
        return "✅ 暂无符合条件的腾讯运营岗位（近2天更新+无学历年限要求）"
    msg = [f"🎯 腾讯符合条件的运营岗位（共{len(jobs)}个）"]
    for idx, job in enumerate(jobs, 1):
        msg.append(f"\n【{idx}】{job['岗位名']}")
        msg.append(f"📍 地点：{job['工作地点']}")
        msg.append(f"📅 更新：{job['更新时间']}")
        msg.append(f"🔗 链接：{job['详情链接']}")
    return "\n".join(msg)

# ===================== 插件注册（对标你的示例） =====================
@register("astrbot_plugin_tencent_job", "XieTiao", "腾讯运营岗位自动推送插件", "1.0.0", "")
class TencentJobPlugin(Star):
    def __init__(self, context: Context, config: AstrBotConfig):
        super().__init__(context)
        self.config = config
        # 配置项（和你的示例完全一致）
        self.groups = getattr(self.config, "groups", [])
        self.push_time = getattr(self.config, "push_time", "09:30")
        # 启动定时任务
        self._scheduler_task = asyncio.create_task(self._daily_scheduler())
        logger.info("✅ 腾讯岗位插件已加载")

    # ===================== 主动指令：/tencent_job =====================
    @filter.command("tencent_job")
    async def get_tencent_jobs(self, event: AstrMessageEvent):
        '''主动获取腾讯最新运营岗位'''
        logger.info("触发腾讯岗位指令!")
        try:
            job_list = await get_filtered_tencent_jobs()
            reply_msg = format_job_message(job_list)
            yield event.plain_result(reply_msg)
        except Exception as e:
            yield event.plain_result(f"❌ 获取失败：{str(e)}")

    # ===================== 管理员指令：/tencent_status =====================
    @filter.permission_type(filter.PermissionType.ADMIN)
    @filter.command("tencent_status")
    async def check_status(self, event: AstrMessageEvent):
        """查看插件状态（仅管理员）"""
        sleep_time = self._calculate_sleep_time()
        hours = int(sleep_time // 3600)
        minutes = int((sleep_time % 3600) // 60)
        yield event.plain_result(
            f"腾讯岗位插件运行中\n"
            f"推送时间：{self.push_time}\n"
            f"目标群组：{len(self.groups)} 个\n"
            f"下次推送：{hours}小时{minutes}分钟"
        )

    # ===================== 定时任务核心（完全对标你的示例） =====================
    def _calculate_sleep_time(self) -> float:
        now = datetime.datetime.now()
        hour, minute = map(int, self.push_time.split(":"))
        next_push = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
        if next_push <= now:
            next_push += datetime.timedelta(days=1)
        return (next_push - now).total_seconds()

    async def _send_to_groups(self):
        if not self.groups:
            logger.warning("未配置推送群组，跳过推送")
            return
        try:
            job_list = await get_filtered_tencent_jobs()
            if not job_list:
                logger.info("无新岗位，跳过推送")
                return
            
            msg = format_job_message(job_list)
            for group in self.groups:
                await self.context.send_message(group, MessageChain().message(msg))
                await asyncio.sleep(2)
            logger.info(f"已向 {len(self.groups)} 个群组推送岗位消息")
        except Exception as e:
            logger.error(f"推送失败：{str(e)}")

    async def _daily_scheduler(self):
        while True:
            try:
                sleep_time = self._calculate_sleep_time()
                logger.info(f"腾讯岗位定时任务：{sleep_time/3600:.2f} 小时后推送")
                await asyncio.sleep(sleep_time)
                await self._send_to_groups()
                await asyncio.sleep(60)
            except Exception as e:
                logger.error(f"定时任务出错：{str(e)}")
                await asyncio.sleep(300)

    # 插件卸载时停止任务
    async def terminate(self):
        if hasattr(self, "_scheduler_task"):
            self._scheduler_task.cancel()
        logger.info("🛑 腾讯岗位插件定时任务已停止")