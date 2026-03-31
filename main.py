# main.py
import asyncio
import datetime
from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.star import Context, Star, register
from astrbot.api import logger, AstrBotConfig
from astrbot.core.message.message_event_result import MessageChain

from .jobs_tencent import get_filtered_tencent_jobs
from .jobs_dajiang import get_filtered_dji_jobs
from .jobs_wangyi import get_filtered_wangyi_jobs
from .jobs_bili import get_filtered_bili_jobs
from .jobs_yingjiao import get_filtered_yingjiao_jobs
from .jobs_xiaohongshu import get_filtered_xhs_jobs
from .jobs_bytedance import get_filtered_bytedance_jobs
from .jobs_mihoyo import get_filtered_mihoyo_jobs

# ===================== 【统一格式化函数】核心 =====================
def format_all_jobs(tencent_jobs, dji_jobs, wangyi_jobs, bili_jobs, yingjiao_jobs, xhs_jobs, bytedance_jobs, mihoyo_jobs, query_type="all"):
    """
    极简格式化：抽离重复逻辑，支持九种查询模式
    query_type: all / tencent / dji / wangyi / bili / yingjiao / xhs / bytedance / mihoyo
    """
    # 【抽离公共渲染函数】同一套渲染模板
    def render_company(title: str, jobs: list) -> str:
        if not jobs:
            return f"\n{title}\n暂无符合条件的岗位"
        items = [f"\n{title}"]
        for idx, job in enumerate(jobs, 1):
            items.append(f"{idx}. {job['岗位名']}\n {job['工作地点']} | {job['更新时间']}\n {job['详情链接']}")
        return "\n".join(items)

    t_count = len(tencent_jobs)
    d_count = len(dji_jobs)
    w_count = len(wangyi_jobs)
    b_count = len(bili_jobs)
    y_count = len(yingjiao_jobs)
    x_count = len(xhs_jobs)
    bt_count = len(bytedance_jobs)
    mihoyo_count = len(mihoyo_jobs)

    # 仅查询腾讯
    if query_type == "tencent":
        return render_company(f"🔵 腾讯岗位（共{t_count}个）", tencent_jobs) if t_count else "✅ 腾讯暂无符合条件的岗位"
    
    # 仅查询大疆
    if query_type == "dji":
        return render_company(f"🔵 大疆岗位（共{d_count}个）", dji_jobs) if d_count else "✅ 大疆暂无符合条件的岗位"
    
    # 仅查询网易
    if query_type == "wangyi":
        return render_company(f"🔵 网易岗位（共{w_count}个）", wangyi_jobs) if w_count else "✅ 网易暂无符合条件的岗位"
    
    # 仅查询B站
    if query_type == "bili":
        return render_company(f"🔵 B站岗位（共{b_count}个）", bili_jobs) if b_count else "✅ B站暂无符合条件的岗位"
    
    # 仅查询鹰角网络
    if query_type == "yingjiao":
        return render_company(f"🔵 鹰角网络岗位（共{y_count}个）", yingjiao_jobs) if y_count else "✅ 鹰角网络暂无符合条件的岗位"
    
    # 仅查询小红书
    if query_type == "xhs":
        return render_company(f"🔵 小红书岗位（共{x_count}个）", xhs_jobs) if x_count else "✅ 小红书暂无符合条件的岗位"
    
    # 仅查询字节跳动
    if query_type == "bytedance":
        return render_company(f"🔵 字节跳动岗位（共{bt_count}个）", bytedance_jobs) if bt_count else "✅ 字节跳动暂无符合条件的岗位"
    
    # 仅查询米哈游
    if query_type == "mihoyo":
        return render_company(f"🔵 米哈游岗位（共{mihoyo_count}个）", mihoyo_jobs) if mihoyo_count else "✅ 米哈游暂无符合条件的岗位"
    
    # 同时查询八家
    total = t_count + d_count + w_count + b_count + y_count + x_count + bt_count + mihoyo_count
    if total == 0:
        return "✅ 今日暂无符合条件的岗位\n🔵 腾讯：无\n🔵 大疆：无\n🔵 网易：无\n🔵 B站：无\n🔵 鹰角网络：无\n🔵 小红书：无\n🔵 字节跳动：无\n🔵 米哈游：无"
    
    return (
        f"🎯 最新符合条件岗位（总计{total}个）"
        + render_company(f"🔵 腾讯岗位（{t_count}个）", tencent_jobs)
        + render_company(f"🔵 大疆岗位（{d_count}个）", dji_jobs)
        + render_company(f"🔵 网易岗位（{w_count}个）", wangyi_jobs)
        + render_company(f"🔵 B站岗位（{b_count}个）", bili_jobs)
        + render_company(f"🔵 鹰角网络岗位（{y_count}个）", yingjiao_jobs)
        + render_company(f"🔵 小红书岗位（{x_count}个）", xhs_jobs)
        + render_company(f"🔵 字节跳动岗位（{bt_count}个）", bytedance_jobs)
        + render_company(f"🔵 米哈游岗位（{mihoyo_count}个）", mihoyo_jobs)
    )

@register("astrbot_plugin_job", "Dev", "腾讯+大疆+网易+B站+鹰角网络+小红书+字节跳动+米哈游岗位推送", "1.5", "")
class JobPlugin(Star):
    def __init__(self, context: Context, config: AstrBotConfig):
        super().__init__(context)
        self.config = config
        self.groups = getattr(config, "groups", [])
        self.push_time = getattr(config, "push_time", "09:30")
        self._scheduler_task = asyncio.create_task(self.schedule_loop())
        logger.info("✅ 腾讯+大疆+网易+B站+鹰角网络+小红书+字节跳动+米哈游岗位插件加载完成")

    # ===================== 指令 =====================
    @filter.command("job")
    async def get_all_jobs(self, event: AstrMessageEvent):
        logger.info("【指令触发】开始获取所有公司岗位信息")
        try:
            # 腾讯岗位
            logger.info("【执行中】正在爬取腾讯岗位数据...")
            tencent_jobs = await get_filtered_tencent_jobs()
            logger.info(f"【执行完成】腾讯岗位筛选完成，符合条件：{len(tencent_jobs)} 个")
            
            # 大疆岗位
            logger.info("【执行中】正在爬取大疆岗位数据...")
            dji_jobs = await asyncio.to_thread(get_filtered_dji_jobs)
            logger.info(f"【执行完成】大疆岗位筛选完成，符合条件：{len(dji_jobs)} 个")

            # 网易岗位
            logger.info("【执行中】正在爬取网易岗位数据...")
            wangyi_jobs = await get_filtered_wangyi_jobs()
            logger.info(f"【执行完成】网易岗位筛选完成，符合条件：{len(wangyi_jobs)} 个")
            
            # B站岗位
            logger.info("【执行中】正在爬取B站岗位数据...")
            bili_jobs = await asyncio.to_thread(get_filtered_bili_jobs)
            logger.info(f"【执行完成】B站岗位筛选完成，符合条件：{len(bili_jobs)} 个")
            
            # 鹰角网络岗位
            logger.info("【执行中】正在爬取鹰角网络岗位数据...")
            yingjiao_jobs = await asyncio.to_thread(get_filtered_yingjiao_jobs)
            logger.info(f"【执行完成】鹰角网络岗位筛选完成，符合条件：{len(yingjiao_jobs)} 个")

            # 小红书岗位
            logger.info("【执行中】正在爬取小红书岗位数据...")
            xhs_jobs = await asyncio.to_thread(get_filtered_xhs_jobs)
            logger.info(f"【执行完成】小红书岗位筛选完成，符合条件：{len(xhs_jobs)} 个")

            # 字节跳动岗位
            logger.info("【执行中】正在爬取字节跳动岗位数据...")
            bytedance_jobs = await asyncio.to_thread(get_filtered_bytedance_jobs)
            logger.info(f"【执行完成】字节跳动岗位筛选完成，符合条件：{len(bytedance_jobs)} 个")

            # 米哈游岗位
            logger.info("【执行中】正在爬取米哈游岗位数据...")
            mihoyo_jobs = await get_filtered_mihoyo_jobs()
            logger.info(f"【执行完成】米哈游岗位筛选完成，符合条件：{len(mihoyo_jobs)} 个")

            # 格式化输出
            result_msg = format_all_jobs(tencent_jobs, dji_jobs, wangyi_jobs, bili_jobs, yingjiao_jobs, xhs_jobs, bytedance_jobs, mihoyo_jobs)
            yield event.plain_result(result_msg)
            
        except Exception as e:
            logger.error(f"【错误】获取所有岗位失败：{str(e)}", exc_info=True)
            yield event.plain_result(f"❌ 失败：{str(e)}")

    @filter.command("tencent")
    async def get_tencent_jobs(self, event: AstrMessageEvent):
        logger.info("【指令触发】开始获取腾讯岗位信息")
        try:
            jobs = await get_filtered_tencent_jobs()
            logger.info(f"【执行完成】腾讯岗位筛选完成，符合条件：{len(jobs)} 个")
            yield event.plain_result(format_all_jobs(jobs, [], [], [], [], [], [], [], query_type="tencent"))
        except Exception as e:
            logger.error(f"【错误】获取腾讯岗位失败：{str(e)}", exc_info=True)
            yield event.plain_result(f"❌ 失败：{str(e)}")

    @filter.command("dji")
    async def get_dji_jobs(self, event: AstrMessageEvent):
        logger.info("【指令触发】开始获取大疆岗位信息")
        try:
            jobs = await asyncio.to_thread(get_filtered_dji_jobs)
            logger.info(f"【执行完成】大疆岗位筛选完成，符合条件：{len(jobs)} 个")
            yield event.plain_result(format_all_jobs([], jobs, [], [], [], [], [], [], query_type="dji"))
        except Exception as e:
            logger.error(f"【错误】获取大疆岗位失败：{str(e)}", exc_info=True)
            yield event.plain_result(f"❌ 失败：{str(e)}")

    @filter.command("wangyi")
    async def get_wangyi_jobs(self, event: AstrMessageEvent):
        logger.info("【指令触发】开始获取网易岗位信息")
        try:
            jobs = await get_filtered_wangyi_jobs()
            logger.info(f"【执行完成】网易岗位筛选完成，符合条件：{len(jobs)} 个")
            yield event.plain_result(format_all_jobs([], [], jobs, [], [], [], [], [], query_type="wangyi"))
        except Exception as e:
            logger.error(f"【错误】获取网易岗位失败：{str(e)}", exc_info=True)
            yield event.plain_result(f"❌ 失败：{str(e)}")

    @filter.command("bili")
    async def get_bili_jobs(self, event: AstrMessageEvent):
        logger.info("【指令触发】开始获取B站岗位信息")
        try:
            jobs = await asyncio.to_thread(get_filtered_bili_jobs)
            logger.info(f"【执行完成】B站岗位筛选完成，符合条件：{len(jobs)} 个")
            yield event.plain_result(format_all_jobs([], [], [], jobs, [], [], [], [], query_type="bili"))
        except Exception as e:
            logger.error(f"【错误】获取B站岗位失败：{str(e)}", exc_info=True)
            yield event.plain_result(f"❌ 失败：{str(e)}")

    @filter.command("yingjiao")
    async def get_yingjiao_jobs(self, event: AstrMessageEvent):
        logger.info("【指令触发】开始获取鹰角网络岗位信息")
        try:
            jobs = await asyncio.to_thread(get_filtered_yingjiao_jobs)
            logger.info(f"【执行完成】鹰角网络岗位筛选完成，符合条件：{len(jobs)} 个")
            yield event.plain_result(format_all_jobs([], [], [], [], jobs, [], [], [], query_type="yingjiao"))
        except Exception as e:
            logger.error(f"【错误】获取鹰角网络岗位失败：{str(e)}", exc_info=True)
            yield event.plain_result(f"❌ 失败：{str(e)}")

    @filter.command("xhs")
    async def get_xhs_jobs(self, event: AstrMessageEvent):
        logger.info("【指令触发】开始获取小红书岗位信息")
        try:
            jobs = await asyncio.to_thread(get_filtered_xhs_jobs)
            logger.info(f"【执行完成】小红书岗位筛选完成，符合条件：{len(jobs)} 个")
            yield event.plain_result(format_all_jobs([], [], [], [], [], jobs, [], [], query_type="xhs"))
        except Exception as e:
            logger.error(f"【错误】获取小红书岗位失败：{str(e)}", exc_info=True)
            yield event.plain_result(f"❌ 失败：{str(e)}")

    @filter.command("byte")
    async def get_bytedance_jobs(self, event: AstrMessageEvent):
        logger.info("【指令触发】开始获取字节跳动岗位信息")
        try:
            jobs = await asyncio.to_thread(get_filtered_bytedance_jobs)
            logger.info(f"【执行完成】字节跳动岗位筛选完成，符合条件：{len(jobs)} 个")
            yield event.plain_result(format_all_jobs([], [], [], [], [], [], jobs, [], query_type="bytedance"))
        except Exception as e:
            logger.error(f"【错误】获取字节跳动岗位失败：{str(e)}", exc_info=True)
            yield event.plain_result(f"❌ 失败：{str(e)}")

    @filter.command("mihoyo")
    async def get_mihoyo_jobs(self, event: AstrMessageEvent):
        logger.info("【指令触发】开始获取米哈游岗位信息")
        try:
            jobs = await get_filtered_mihoyo_jobs()
            logger.info(f"【执行完成】米哈游岗位筛选完成，符合条件：{len(jobs)} 个")
            yield event.plain_result(format_all_jobs([], [], [], [], [], [], [], jobs, query_type="mihoyo"))
        except Exception as e:
            logger.error(f"【错误】获取米哈游岗位失败：{str(e)}", exc_info=True)
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
                tencent_jobs = await get_filtered_tencent_jobs()
                dji_jobs = await asyncio.to_thread(get_filtered_dji_jobs)
                wangyi_jobs = await get_filtered_wangyi_jobs()
                bili_jobs = await asyncio.to_thread(get_filtered_bili_jobs)
                yingjiao_jobs = await asyncio.to_thread(get_filtered_yingjiao_jobs)
                xhs_jobs = await asyncio.to_thread(get_filtered_xhs_jobs)
                bytedance_jobs = await asyncio.to_thread(get_filtered_bytedance_jobs)
                mihoyo_jobs = await get_filtered_mihoyo_jobs()

                total = len(tencent_jobs) + len(dji_jobs) + len(wangyi_jobs) + len(bili_jobs) + len(yingjiao_jobs) + len(xhs_jobs) + len(bytedance_jobs) + len(mihoyo_jobs)
                logger.info(
                    f"【定时任务】筛选完成 | "
                    f"腾讯：{len(tencent_jobs)}个 | "
                    f"大疆：{len(dji_jobs)}个 | "
                    f"网易：{len(wangyi_jobs)}个 | "
                    f"B站：{len(bili_jobs)}个 | "
                    f"鹰角网络：{len(yingjiao_jobs)}个 | "
                    f"小红书：{len(xhs_jobs)}个 | "
                    f"字节跳动：{len(bytedance_jobs)}个 | "
                    f"米哈游：{len(mihoyo_jobs)}个 | "
                    f"总计：{total}个"
                )
                
                # 推送消息
                if self.groups:
                    msg = format_all_jobs(tencent_jobs, dji_jobs, wangyi_jobs, bili_jobs, yingjiao_jobs, xhs_jobs, bytedance_jobs, mihoyo_jobs)
                    for g in self.groups:
                        await self.context.send_message(g, MessageChain().message(msg))
                        await asyncio.sleep(1)
                    logger.info("【定时任务】岗位推送完成！")
                else:
                    logger.info("【定时任务】未配置推送群组，跳过推送")
                    
                await asyncio.sleep(60)
            except Exception as e:
                logger.error(f"【定时任务】执行错误：{e}", exc_info=True)
                await asyncio.sleep(300)

    # 卸载停止任务
    async def terminate(self):
        self._scheduler_task.cancel()
        logger.info("🛑 插件已停止运行")