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
def format_all_jobs(tencent_jobs, dji_jobs, query_type="all"):
    """
    极简格式化：抽离重复逻辑，支持三种查询模式
    query_type: all / tencent / dji
    """
    # 【抽离公共渲染函数】同一套渲染模板
    def render_company(title: str, jobs: list) -> str:
        if not jobs:
            return f"\n{title}\n暂无符合条件的岗位"
        items = [f"\n{title}"]
        for idx, job in enumerate(jobs, 1):
            items.append(f"{idx}. {job['岗位名']}\n {job['工作地点']} | {job['更新时间']}\n {job['详情链接']}")
        return "\n".join(items)

    t_count, d_count = len(tencent_jobs), len(dji_jobs)

    # 仅查询腾讯
    if query_type == "tencent":
        return render_company(f"🔵 腾讯运营岗位（共{t_count}个）", tencent_jobs) if t_count else "✅ 腾讯运营暂无符合条件的岗位"
    
    # 仅查询大疆
    if query_type == "dji":
        return render_company(f"🔵 大疆运营岗位（共{d_count}个）", dji_jobs) if d_count else "✅ 大疆运营暂无符合条件的岗位"
    
    # 同时查询两家（默认）
    total = t_count + d_count
    if total == 0:
        return "✅ 今日暂无符合条件的岗位\n🔵 腾讯运营：无\n🔵 大疆运营：无"
    
    return (
        f"🎯 最新符合条件岗位（总计{total}个）"
        + render_company("🔵 腾讯运营岗位", tencent_jobs)
        + render_company("🔵 大疆运营岗位", dji_jobs)
    )

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
            yield event.plain_result(format_all_jobs(tencent_jobs, dji_jobs, query_type="all"))
        except Exception as e:
            logger.error(f"【错误】获取岗位失败：{str(e)}")
            yield event.plain_result(f"❌ 获取岗位失败：{str(e)}")

    @filter.command("tencent")
    async def get_tencent_jobs(self, event: AstrMessageEvent):
        logger.info("【指令触发】开始获取腾讯岗位信息")
        try:
            jobs = await get_filtered_tencent_jobs()
            logger.info(f"【执行完成】腾讯岗位筛选完成，符合条件：{len(jobs)} 个")
            yield event.plain_result(format_all_jobs(jobs, [], query_type="tencent"))
        except Exception as e:
            logger.error(f"【错误】获取腾讯岗位失败：{str(e)}")
            yield event.plain_result(f"❌ 失败：{str(e)}")

    @filter.command("dji")
    async def get_dji_jobs(self, event: AstrMessageEvent):
        logger.info("【指令触发】开始获取大疆岗位信息")
        try:
            jobs = await asyncio.to_thread(get_filtered_dji_jobs)
            logger.info(f"【执行完成】大疆岗位筛选完成，符合条件：{len(jobs)} 个")
            yield event.plain_result(format_all_jobs([], jobs, query_type="dji"))
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