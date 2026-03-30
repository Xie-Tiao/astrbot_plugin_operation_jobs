# main.py
import asyncio
import datetime
from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.star import Context, Star, register
from astrbot.api import logger, AstrBotConfig
from astrbot.core.message.message_event_result import MessageChain

from .jobs_tencent import get_filtered_tencent_jobs
from .jobs_dajiang import get_filtered_dji_jobs

# ===================== 【统一格式化函数】核心 =====================
def format_all_jobs(tencent_jobs, dji_jobs):
    """统一格式化腾讯+大疆岗位，输出标准排版，明确标注无岗位的公司"""
    tencent_count = len(tencent_jobs)
    dji_count = len(dji_jobs)
    total = tencent_count + dji_count

    text = []

    # 情况1：两家都没有岗位
    if total == 0:
        return "✅ 今日暂无符合条件的岗位\n🔵 腾讯运营：无\n🔵 大疆运营：无"

    # 情况2：至少一家有岗位，先写总标题
    text.append(f"🎯 最新符合条件岗位（总计{total}个）")

    # 腾讯部分
    text.append("\n🔵 腾讯运营岗位")
    if tencent_count > 0:
        for i, job in enumerate(tencent_jobs, 1):
            text.append(f"{i}. {job['岗位名']}\n {job['工作地点']} | {job['更新时间']}\n {job['详情链接']}")
    else:
        text.append("暂无符合条件的岗位")

    # 大疆部分
    text.append("\n🔵 大疆运营岗位")
    if dji_count > 0:
        for i, job in enumerate(dji_jobs, 1):
            text.append(f"{i}. {job['岗位名']}\n {job['工作地点']} | {job['更新时间']}\n {job['详情链接']}")
    else:
        text.append("暂无符合条件的岗位")

    return "\n".join(text)

# 注册插件
@register("astrbot_plugin_job", "Dev", "腾讯+大疆岗位推送", "1.0", "")
class JobPlugin(Star):
    def __init__(self, context: Context, config: AstrBotConfig):
        super().__init__(context)
        self.config = config
        self.groups = getattr(config, "groups", [])
        self.push_time = getattr(config, "push_time", "09:30")
        self._scheduler_task = asyncio.create_task(self.schedule_loop())
        logger.info("✅ 腾讯+大疆岗位插件加载完成")

    # ===================== 指令 =====================
    @filter.command("job")
    async def get_all_jobs(self, event: AstrMessageEvent):
        logger.info("【指令触发】开始获取腾讯+大疆双公司岗位信息")
        try:
            # 腾讯岗位
            logger.info("【执行中】正在爬取腾讯岗位数据...")
            tencent_jobs = await get_filtered_tencent_jobs()
            logger.info(f"【执行完成】腾讯岗位筛选完成，符合条件：{len(tencent_jobs)} 个")
            
            # 大疆岗位
            logger.info("【执行中】正在爬取大疆岗位数据...")
            dji_jobs = await asyncio.to_thread(get_filtered_dji_jobs)
            logger.info(f"【执行完成】大疆岗位筛选完成，符合条件：{len(dji_jobs)} 个")

            logger.info(f"【汇总完成】双公司总计获取岗位：{len(tencent_jobs)+len(dji_jobs)} 个")
            yield event.plain_result(format_all_jobs(tencent_jobs, dji_jobs))
        except Exception as e:
            logger.error(f"【错误】获取岗位失败：{str(e)}")
            yield event.plain_result(f"❌ 获取岗位失败：{str(e)}")

    @filter.command("tencent")
    async def get_tencent_jobs(self, event: AstrMessageEvent):
        logger.info("【指令触发】开始获取腾讯岗位信息")
        try:
            jobs = await get_filtered_tencent_jobs()
            logger.info(f"【执行完成】腾讯岗位筛选完成，符合条件：{len(jobs)} 个")
            yield event.plain_result(format_all_jobs(jobs, []))
        except Exception as e:
            logger.error(f"【错误】获取腾讯岗位失败：{str(e)}")
            yield event.plain_result(f"❌ 失败：{str(e)}")

    @filter.command("dji")
    async def get_dji_jobs(self, event: AstrMessageEvent):
        logger.info("【指令触发】开始获取大疆岗位信息")
        try:
            jobs = await asyncio.to_thread(get_filtered_dji_jobs)
            logger.info(f"【执行完成】大疆岗位筛选完成，符合条件：{len(jobs)} 个")
            yield event.plain_result(format_all_jobs([], jobs))
        except Exception as e:
            logger.error(f"【错误】获取大疆岗位失败：{str(e)}")
            yield event.plain_result(f"❌ 失败：{str(e)}")

    # 管理员状态指令
    @filter.permission_type(filter.PermissionType.ADMIN)
    @filter.command("job_status")
    async def status(self, event: AstrMessageEvent):
        now = datetime.datetime.now()
        h, m = map(int, self.push_time.split(":"))
        next_t = now.replace(hour=h, minute=m, second=0)
        if next_t < now:
            next_t += datetime.timedelta(days=1)
        wait = int((next_t - now).total_seconds() / 60)
        yield event.plain_result(f"运行中\n推送时间：{self.push_time}\n下次推送：{wait}分钟后")

    # ===================== 定时推送 =====================
    async def schedule_loop(self):
        while True:
            try:
                now = datetime.datetime.now()
                h, m = map(int, self.push_time.split(":"))
                next_t = now.replace(hour=h, minute=m, second=0)
                if next_t < now:
                    next_t += datetime.timedelta(days=1)
                wait_sec = (next_t - now).total_seconds()
                
                logger.info(f"【定时任务】等待 {int(wait_sec/60)} 分钟后执行自动推送")
                await asyncio.sleep(wait_sec)
                
                logger.info("【定时任务】开始执行每日岗位自动推送")
                # 爬取数据
                tencent_jobs = await get_filtered_tencent_jobs()
                dji_jobs = await asyncio.to_thread(get_filtered_dji_jobs)

                total = len(tencent_jobs) + len(dji_jobs)
                logger.info(f"【定时任务】筛选完成 | 腾讯：{len(tencent_jobs)}个 | 大疆：{len(dji_jobs)}个 | 总计：{total}个")
                
                # 推送消息
                if self.groups:
                    msg = format_all_jobs(tencent_jobs, dji_jobs)
                    for g in self.groups:
                        await self.context.send_message(g, MessageChain().message(msg))
                        await asyncio.sleep(1)
                    logger.info("【定时任务】岗位推送完成！")
                else:
                    logger.info("【定时任务】未配置推送群组，跳过推送")
                    
                await asyncio.sleep(60)
            except Exception as e:
                logger.error(f"【定时任务】执行错误：{e}")
                await asyncio.sleep(300)

    # 卸载停止任务
    async def terminate(self):
        self._scheduler_task.cancel()
        logger.info("🛑 插件已停止运行")