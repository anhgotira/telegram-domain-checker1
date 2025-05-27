import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import time
from datetime import datetime
from telegram import Bot
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, Application
import asyncio
import random
import logging

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 常量配置
BOT_TOKEN = "7501103550:AAEJIxoD20_beODi1XN-0RCSlMJb4TwPveg"
DATAIMPULSE_API_URL = "https://api.dataimpulse.com/v1/user/proxy"
DATAIMPULSE_JWT_TOKEN = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJpc3MiOiJodHRwczpcL1wvYXBpLmRhdGFpbXB1bHNlLmNvbVwvcmVzZWxlc3VzZXJcL3Rva2VuXC9nZXQiLCJpYXQiOjE3NDgyMzEzMDEsImV4cCI6MTc0ODMxNzcwMSwibmJmIjoxNzQ4MjMxMzAxLCJqdGkiOiJGb0psTTJveVRJekJRRXRZIiwic3ViIjoxNDkzNDEsInBydiI6IjgwMTZkNDE2YWNhOTI4NjVmODhlNTg4MzQzOWM2OTkxZjM4MzRjZjUifQ.jAkSLkVJe64GWD5EY3Lamo4x6hw2Kbrb06Y2MgLvr8o"

# 4组 URL 列表及其对应的 Chat ID
URL_GROUPS = [
    {
        "urls": [
            "https://www.6733aa.com", "https://www.6733bb.com", "https://www.6733cc.com",
            "https://www.6733xx.com", "https://www.6733yy.com", "https://www.6733zz.com",
            "https://www.673301.com", "https://www.673303.com", "https://www.673304.com",
            "https://www.673305.com", "https://www.673306.com", "https://www.6733uu.com",
            "https://www.6733vv.com", "https://www.6733ww.com", "https://6733.game",
            "https://6733a.com", "https://6733c.com", "https://6733d.com", "https://6733z.com",
            "https://9276jogo.site", "https://9353jogo.site", "https://9376jogo.site"
        ],
        "chat_id": "-1002222479399"
    },
    {
        "urls": [
            "https://www.567br1.com", "https://www.567br2.com", "https://www.567br3.com",
            "https://www.567br4.com", "https://www.567br5.com", "https://www.567br555.com",
            "https://www.567br666.com", "https://www.567br777.com", "https://www.567br888.com",
            "https://www.567br999.com", "https://www.vip567br.com", "https://www.hot567br.com",
            "https://www.fun567br.com", "https://www.app567br.com", "https://www.567brgame.com",
            "https://agent567br1.com"
        ],
        "chat_id": "-4799328746"
    },
    {
        "urls": [
            "https://www.3537.com", "https://www.3537a.com", "https://www.3537b.com",
            "https://www.3537c.com", "https://www.3537d.com", "https://www.3537e.com",
            "https://www.3537p.com", "https://www.3537q.com", "https://www.3537s.com",
            "https://www.3537u.com", "https://www.3537v.com", "https://3537i.com",
            "https://3537i.com", "https://3537bet10.com"
        ],
        "chat_id": "-1002129824425"
    },
    {
        "urls": [
            "https://6167bet17.com", "https://6167.com", "https://6167aa.com",
            "https://6167bb.com", "https://6167cc.com", "https://6167dd.com",
            "https://6167ee.com", "https://6167ff.com", "https://6167000.com",
            "https://6167111.com", "https://6167222.com", "https://6167333.com",
            "https://6167444.com", "https://6167uu.com"
        ],
        "chat_id": "-1002090155242"
    }
]

# 最大5个运营商的 ASN 及对应名称
OPERATORS = [
    {"name": "Vivo", "asn": "AS27699"},
    {"name": "Claro", "asn": "AS28573"},
    {"name": "TIM", "asn": "AS26615"},
    {"name": "Oi", "asn": "AS7738"},
    {"name": "Algar Telecom", "asn": "AS16735"}
]

# DataImpulse 代理 URL，支持指定 ASN
PROXY_URLS = [
    {
        "operator": op["name"],
        "asn": op["asn"],
        "proxy": f"http://e940c7917396a4c4e8a3__cr.br;asn.16735,7738,26615,28573,27699:64a9117d4a15a2dc@gw.dataimpulse.com:823"
    }
    for op in OPERATORS
]

class ProxyManager:
    def __init__(self):
        self.proxy_pool = PROXY_URLS

    def _create_session(self) -> requests.Session:
        session = requests.Session()
        retries = Retry(total=5, backoff_factor=2, status_forcelist=[403, 407, 502, 503, 504])
        session.mount("http://", HTTPAdapter(max_retries=retries))
        session.mount("https://", HTTPAdapter(max_retries=retries))
        return session

    def _test_proxy_connection(self, proxy: dict, session: requests.Session) -> bool:
        proxy_dict = {"http": proxy["proxy"], "https": proxy["proxy"]}
        try:
            res = session.get("https://api.ipify.org/", proxies=proxy_dict, timeout=15)
            res.raise_for_status()
            logger.info(f"代理连接测试成功，IP: {res.text}")
            return True
        except Exception as e:
            logger.error(f"代理连接测试失败，错误: {str(e)}")
            return False

    async def get_brazilian_proxy_info(self, proxy: dict, session: requests.Session) -> tuple[str, bool, dict]:
        max_attempts = 10
        for attempt in range(max_attempts):
            proxy_dict = {"http": proxy["proxy"], "https": proxy["proxy"]}
            try:
                # 使用 DataImpulse API 获取代理信息
                headers = {
                    "Authorization": f"Bearer {DATAIMPULSE_JWT_TOKEN}",
                    "Accept": "application/json"
                }
                res = session.get(DATAIMPULSE_API_URL, headers=headers, timeout=15)
                res.raise_for_status()
                data = res.json()
                logger.info(f"DataImpulse API 响应: {data}")
                ip_info = {
                    'ip': data.get('ip', 'N/A'),
                    'country': data.get('country', 'N/A').upper(),
                    'org': proxy["operator"],
                    'city': data.get('city', 'N/A'),
                    'region': data.get('region', 'N/A'),
                    'timezone': data.get('timezone', 'N/A'),
                    'hostname': data.get('hostname', 'N/A'),
                    'asn': proxy["asn"]
                }
            except Exception as e:
                logger.warning(f"DataImpulse API 请求失败，错误: {str(e)}，回退到 ipify 和 ip-api")
                try:
                    res = session.get("https://api.ipify.org/", proxies=proxy_dict, timeout=15)
                    ip_address = res.text.strip()
                    res = session.get(f"http://ip-api.com/json/{ip_address}", proxies=proxy_dict, timeout=15)
                    data = res.json()
                    logger.info(f"ip-api.com API 响应: {data}")
                    ip_info = {
                        'ip': ip_address,
                        'country': data.get('countryCode', 'N/A'),
                        'org': proxy["operator"],
                        'city': data.get('city', 'N/A'),
                        'region': data.get('regionName', 'N/A'),
                        'timezone': data.get('timezone', 'N/A'),
                        'hostname': data.get('query', 'N/A'),
                        'asn': proxy["asn"]
                    }
                except Exception as e:
                    logger.error(f"获取代理 IP 信息失败: {str(e)}")
                    ip_info = {
                        'ip': 'N/A', 'country': 'N/A', 'org': proxy["operator"],
                        'city': 'N/A', 'region': 'N/A', 'timezone': 'N/A',
                        'hostname': 'N/A', 'asn': proxy["asn"]
                    }

            is_brazil_ip = ip_info['country'] == 'BR'
            if is_brazil_ip or attempt == max_attempts - 1:
                return ip_info, is_brazil_ip

            breath = random.uniform(2, 5)
            logger.warning(f"当前代理非巴西 IP，等待 {breath:.2f} 秒后重试...")
            await asyncio.sleep(breath)

        return ip_info, False

    async def check_url_with_proxy(self, url: str, proxy: dict) -> tuple[str, bool]:
        session = self._create_session()
        try:
            proxy_dict = {"http": proxy["proxy"], "https": proxy["proxy"]}
            ip_info, is_brazil_ip = await self.get_brazilian_proxy_info(proxy, session)
            if not is_brazil_ip:
                return f"⚠️ 代理非巴西 IP (ASN: {ip_info['asn']})", False

            headers = {
                "User-Agent": "Mozilla/5.0 (Linux; Android 10; SM-G975F) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.120 Mobile Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                "Connection": "keep-alive",
                "Accept-Language": "en-US,en;q=0.9",
            }

            try:
                res = session.get(url, proxies=proxy_dict, headers=headers, timeout=15)
                logger.info(f"请求 {url} 状态码: {res.status_code}")
                if res.status_code == 200:
                    return "", True  # 成功时不返回具体信息，仅计数
                else:
                    return f"❌ 运营商: {ip_info['org']} (ASN: {ip_info['asn']}) 失败 (状态码: {res.status_code})", False
            except Exception as e:
                logger.error(f"请求 {url} 失败，错误: {str(e)}")
                return f"❌ 运营商: {ip_info['org']} (ASN: {ip_info['asn']}) 失败 (错误: {str(e)})", False
        finally:
            session.close()

async def check_urls(proxy_manager: ProxyManager, urls: list, chat_id: str, bot: Bot) -> str:
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    message = f"🕒 检测报告 - {now}\n\n"

    # 遍历每个 URL
    for url in urls:
        logger.info(f"开始检测 URL: {url}")
        message += f"域名地址: {url}\n"
        used_asns = set()  # 记录已使用的 ASN，避免重复
        success_count = 0  # 记录成功次数
        first_city = None  # 记录第一个成功的城市
        failures = []  # 记录失败信息

        # 确保每个 URL 通过5个运营商检测，按顺序遍历
        for proxy in proxy_manager.proxy_pool:
            if proxy["asn"] in used_asns:
                continue  # 如果 ASN 已使用，跳过

            # 测试代理连接
            session = proxy_manager._create_session()
            try:
                if not proxy_manager._test_proxy_connection(proxy, session):
                    failures.append(f"⚠️ 运营商: {proxy['operator']} (ASN: {proxy['asn']}) 失败 (代理连接失败)")
                    used_asns.add(proxy["asn"])
                    continue

                # 检测 URL
                result, success = await proxy_manager.check_url_with_proxy(url, proxy)
                if success:
                    success_count += 1
                    if first_city is None:  # 记录第一个成功的城市
                        ip_info, _ = await proxy_manager.get_brazilian_proxy_info(proxy, session)
                        first_city = ip_info['city']
                else:
                    failures.append(result)

                used_asns.add(proxy["asn"])  # 记录已使用的 ASN
            except Exception as e:
                logger.error(f"检测 {url} 时发生错误: {str(e)}")
                failures.append(f"⚠️ 运营商: {proxy['operator']} (ASN: {proxy['asn']}) 失败 (错误: {str(e)})")
                used_asns.add(proxy["asn"])
            finally:
                session.close()

        # 格式化结果
        if success_count == len(OPERATORS):
            message += f"城市: {first_city} 检测成功 {success_count}/{len(OPERATORS)}\n"
        else:
            message += f"城市: {first_city if first_city else 'N/A'} 检测成功 {success_count}/{len(OPERATORS)}\n"
            for failure in failures:
                message += f"{failure}\n"

        message += "\n"  # 每个 URL 检测结果后加空行
        logger.info(f"完成检测 URL: {url}, 成功次数: {success_count}/{len(OPERATORS)}")

    # 异步发送消息，添加速率限制
    try:
        await bot.send_message(chat_id=chat_id, text=message)
        await asyncio.sleep(1)  # 每次发送后延迟1秒，避免触发速率限制
        logger.info(f"消息成功发送到 {chat_id}")
    except Exception as e:
        logger.error(f"发送消息到 {chat_id} 失败: {str(e)}")
        message = f"⚠️ 发送消息失败: {str(e)}"

    return message

async def manual_check(update, context: ContextTypes.DEFAULT_TYPE):
    proxy_manager = ProxyManager()
    bot = context.bot
    try:
        # 依次检测每组 URL 并发送到对应群组
        for group in URL_GROUPS:
            try:
                msg = await check_urls(proxy_manager, group["urls"], group["chat_id"], bot)
                logger.info(f"手动检测 - 消息发送到 {group['chat_id']}: {msg}")
            except Exception as e:
                logger.error(f"手动检测 {group['chat_id']} 时出错: {str(e)}")
                await bot.send_message(chat_id=group["chat_id"], text=f"⚠️ 手动检测出错: {str(e)}")
        logger.info("手动检测 - 消息发送成功")
        await update.message.reply_text("检测完成，结果已发送到对应群组！")
    except Exception as e:
        logger.error(f"手动检测 - 消息发送失败: {str(e)}")
        await update.message.reply_text(f"⚠️ 检测出错: {str(e)}")

async def run_scheduled(bot: Bot):
    proxy_manager = ProxyManager()
    try:
        # 依次检测每组 URL 并发送到对应群组
        for group in URL_GROUPS:
            try:
                msg = await check_urls(proxy_manager, group["urls"], group["chat_id"], bot)
                logger.info(f"定时检测 - 消息发送到 {group['chat_id']}: {msg}")
            except Exception as e:
                logger.error(f"定时检测 {group['chat_id']} 时出错: {str(e)}")
                await bot.send_message(chat_id=group["chat_id"], text=f"⚠️ 定时检测出错: {str(e)}")
        logger.info("定时检测 - 所有检测完成")
    except Exception as e:
        logger.error(f"定时检测 - 消息发送失败: {str(e)}")
        for group in URL_GROUPS:
            await bot.send_message(chat_id=group["chat_id"], text=f"⚠️ 定时检测出错: {str(e)}")

async def schedule_loop(app: Application):
    bot = app.bot
    while True:
        try:
            logger.info("开始定时检测")
            await run_scheduled(bot)
            logger.info("定时检测完成，等待下一次检测")
            await asyncio.sleep(7200)  # 每2小时运行一次 (7200秒)
        except Exception as e:
            logger.error(f"定时检测循环中发生错误: {str(e)}")
            await asyncio.sleep(60)  # 出错后等待1分钟再继续

async def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("check", manual_check))
    logger.info("✅ Bot 已启动，支持 /check 手动检测 + 每2小时自动检测")

    # 启动定时任务
    asyncio.create_task(schedule_loop(app))

    # 启动机器人
    await app.run()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        logger.error(f"程序启动失败: {str(e)}")
        raise