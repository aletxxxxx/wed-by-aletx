import aiohttp
import asyncio
import random
import requests
import re
import time
import secrets
import os
import signal
import sys
import uuid
from hashlib import md5
from time import time as T
from typing import Dict, Tuple, Optional, List
from dataclasses import dataclass
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@dataclass
class DeviceInfo:
    model: str
    brand: str
    version: str
    api_level: int
    resolution: str
    dpi: int

class DeviceGenerator:
    DEVICES = [
        DeviceInfo("Pixel 6", "Google", "12", 31, "1080*2400", 420),
        DeviceInfo("Pixel 5", "Google", "11", 30, "1080*2340", 440),
        DeviceInfo("SM-G991B", "samsung", "13", 33, "1080*2400", 480),
        DeviceInfo("SM-A525F", "samsung", "12", 31, "1080*2400", 420),
        DeviceInfo("Redmi Note 11", "Xiaomi", "12", 31, "1080*2400", 440),
        DeviceInfo("CPH2381", "OPPO", "12", 31, "1080*2400", 480),
        DeviceInfo("V2055", "vivo", "12", 31, "1080*2400", 420),
        DeviceInfo("M2101K6G", "Xiaomi", "12", 31, "1080*2400", 440),
    ]
    
    @classmethod
    def random_device(cls) -> DeviceInfo:
        return random.choice(cls.DEVICES)

class Signature:
    """Giữ nguyên thuật toán cũ, chỉ clean + ổn định hơn"""
    KEY = [0xDF, 0x77, 0xB9, 0x40, 0xB9, 0x9B, 0x84, 0x83, 0xD1, 0xB9, 
           0xCB, 0xD1, 0xF7, 0xC2, 0xB9, 0x85, 0xC3, 0xD0, 0xFB, 0xC3]
    
    def __init__(self, params: str, data: str, cookies: str):
        self.params = params
        self.data = data
        self.cookies = cookies
    
    def _md5_hash(self, data: str) -> str:
        return md5(data.encode()).hexdigest()
    
    def _reverse_byte(self, n: int) -> int:
        return int(f"{n:02x}"[1:] + f"{n:02x}"[0], 16)
    
    def generate(self) -> Dict[str, str]:
        g = self._md5_hash(self.params)
        g += self._md5_hash(self.data) if self.data else "0" * 32
        g += self._md5_hash(self.cookies) if self.cookies else "0" * 32
        g += "0" * 32
        
        unix_timestamp = int(T())
        payload = []
        
        for i in range(0, 12, 4):
            chunk = g[8 * i:8 * (i + 1)]
            for j in range(4):
                payload.append(int(chunk[j * 2:(j + 1) * 2], 16))
        
        payload.extend([0x0, 0x6, 0xB, 0x1C])
        payload.extend([
            (unix_timestamp & 0xFF000000) >> 24,
            (unix_timestamp & 0x00FF0000) >> 16,
            (unix_timestamp & 0x0000FF00) >> 8,
            (unix_timestamp & 0x000000FF)
        ])
        
        encrypted = [a ^ b for a, b in zip(payload, self.KEY)]
        
        for i in range(0x14):
            C = self._reverse_byte(encrypted[i])
            D = encrypted[(i + 1) % 0x14]
            F = int(bin(C ^ D)[2:].zfill(8)[::-1], 2)
            H = ((F ^ 0xFFFFFFFF) ^ 0x14) & 0xFF
            encrypted[i] = H
        
        signature = "".join(f"{x:02x}" for x in encrypted)
        
        return {
            "X-Gorgon": "840280416000" + signature,
            "X-Khronos": str(unix_timestamp),
            "x-ss-req-ticket": str(int(unix_timestamp * 1000)),
        }

class OptimizedTikTokViewBot:
    def __init__(self):
        self.count = 0
        self.start_time = 0
        self.is_running = False
        self.session = None
        self.successful_requests = 0
        self.failed_requests = 0
        self.peak_speed = 0
        
    async def init_session(self):
        """Session tối ưu, keepalive mạnh"""
        timeout = aiohttp.ClientTimeout(total=20, connect=8)
        connector = aiohttp.TCPConnector(
            limit=0,
            limit_per_host=0,
            keepalive_timeout=60,
            enable_cleanup_closed=True,
            ttl_dns_cache=300,
        )
        
        self.session = aiohttp.ClientSession(
            timeout=timeout,
            connector=connector,
            headers={'User-Agent': 'com.ss.android.ugc.trill/400304 (Linux; U; Android 12; vi_VN; Pixel 6; Build/SP2A.220505.002; Cronet/58.0.2991.0)'},
            cookie_jar=aiohttp.DummyCookieJar()
        )
    
    async def close_session(self):
        if self.session:
            await self.session.close()
    
    def get_video_id(self, url: str) -> Optional[str]:
        """Hỗ trợ short link vt / vm / t.tiktok.com"""
        try:
            if any(x in url for x in ("vt.tiktok.com", "vm.tiktok.com", "t.tiktok.com")):
                try:
                    resp = requests.get(
                        url,
                        headers={
                            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                        },
                        allow_redirects=True,
                        timeout=15,
                    )
                    url = resp.url
                    logger.info(f"✅ Expanded short URL → {url}")
                except Exception as e:
                    logger.error(f"❌ Failed to expand short URL: {e}")
                    return None

            patterns_url = [
                r'/video/(\d+)',
                r'tiktok\.com/@[^/]+/video/(\d+)',
                r'tiktok\.com/@[^/]+/(\d+)',
                r'(\d{18,19})'
            ]
            
            for pattern in patterns_url:
                match = re.search(pattern, url)
                if match:
                    video_id = match.group(1)
                    logger.info(f"✅ Found Video ID from URL: {video_id}")
                    return video_id
            
            response = requests.get(
                url, 
                headers={
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                    'Accept-Language': 'en-US,en;q=0.5',
                    'Accept-Encoding': 'gzip, deflate',
                    'Connection': 'keep-alive',
                    'Upgrade-Insecure-Requests': '1',
                }, 
                timeout=15
            )
            response.raise_for_status()
            
            patterns_page = [
                r'"video":\{"id":"(\d+)"',
                r'"id":"(\d+)"',
                r'video/(\d+)',
                r'(\d{19})',
                r'"aweme_id":"(\d+)"'
            ]
            
            for pattern in patterns_page:
                match = re.search(pattern, response.text)
                if match:
                    video_id = match.group(1)
                    logger.info(f"✅ Found Video ID from page: {video_id}")
                    return video_id
            
            logger.error("❌ No video ID found")
            return None
                
        except Exception as e:
            logger.error(f"❌ Error getting video ID: {e}")
            return None
    
    def generate_request_data(self, video_id: str) -> Tuple[str, Dict, Dict, Dict]:
        """Device dày hơn + params chuẩn hơn"""
        device = DeviceGenerator.random_device()
        
        device_id = str(random.randint(7000000000000000000, 7999999999999999999))
        iid = str(random.randint(7000000000000000000, 7999999999999999999))
        openudid = secrets.token_hex(8)
        cdid = str(uuid.uuid4())
        
        params = (
            f"channel=googleplay&aid=1233&app_name=musical_ly&version_code=400304"
            f"&version_name=40.3.4&manifest_version_code=2024003040"
            f"&update_version_code=2024003040"
            f"&device_platform=android&device_type={device.model.replace(' ', '+')}"
            f"&device_brand={device.brand}&os_version={device.version}"
            f"&device_id={device_id}&iid={iid}&openudid={openudid}&cdid={cdid}"
            f"&os_api={device.api_level}&resolution={device.resolution.replace('*', '%2A')}"
            f"&dpi={device.dpi}&app_language=vi&language=vi&region=VN"
            f"&sys_region=VN&carrier_region=VN&timezone_name=Asia%2FHo_Chi_Minh"
            f"&ac=wifi&ac2=wifi&ssmix=a&host_abi=arm64-v8a"
        )
        
        # Random host để phân tán
        host = random.choice([
            "api16-core-c-alisg.tiktokv.com",
            "api16-core-c-useast1a.tiktokv.com",
            "api19-core-c-useast1a.tiktokv.com",
            "api21-core-c-alisg.tiktokv.com",
        ])
        
        url = f"https://{host}/aweme/v1/aweme/stats/?{params}"
        
        data = {
            "item_id": video_id,
            "play_delta": 1,
            "action_time": int(time.time()),
            "aweme_type": 0,
        }
        
        cookies = {
            "sessionid": secrets.token_hex(16),
            "install_id": iid,
        }
        
        headers = {
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
            "User-Agent": f"com.ss.android.ugc.trill/400304 (Linux; U; Android {device.version}; vi_VN; {device.model}; Build/SP2A.220505.002; Cronet/58.0.2991.0)",
            "Accept-Encoding": "gzip",
            "Connection": "keep-alive",
            "sdk-version": "2",
            "passport-sdk-version": "19",
        }
        
        return url, data, cookies, headers
    
    async def send_view_request(self, video_id: str, semaphore: asyncio.Semaphore) -> bool:
        """Retry nhẹ + không spam sleep"""
        async with semaphore:
            for attempt in range(2):
                try:
                    url, data, cookies, base_headers = self.generate_request_data(video_id)
                    
                    sig = Signature(url.split('?')[1], str(data), str(cookies)).generate()
                    headers = {**base_headers, **sig}
                    
                    async with self.session.post(
                        url, 
                        data=data, 
                        headers=headers, 
                        cookies=cookies,
                        ssl=False
                    ) as response:
                        
                        if response.status == 200:
                            self.count += 1
                            self.successful_requests += 1
                            return True
                        else:
                            if attempt == 0:
                                await asyncio.sleep(0.005)
                                continue
                            self.failed_requests += 1
                            return False
                            
                except Exception:
                    if attempt == 0:
                        await asyncio.sleep(0.005)
                        continue
                    self.failed_requests += 1
                    return False
    
    async def view_sender(self, video_id: str, task_id: int, semaphore: asyncio.Semaphore):
        """Delay nới — không tự phanh khi tốc độ cao"""
        base_delay = 0.0003
        
        while self.is_running:
            success = await self.send_view_request(video_id, semaphore)
            
            if success:
                delay = base_delay + random.uniform(0, 0.001)
            else:
                delay = base_delay * 3 + random.uniform(0, 0.005)
            
            await asyncio.sleep(delay)
    
    def calculate_stats(self) -> Dict[str, float]:
        elapsed = time.time() - self.start_time
        views_per_second = self.count / elapsed if elapsed > 0 else 0
        
        if views_per_second > self.peak_speed:
            self.peak_speed = views_per_second
        
        views_per_minute = views_per_second * 60
        views_per_hour = views_per_minute * 60
        
        total_req = self.successful_requests + self.failed_requests
        success_rate = (self.successful_requests / total_req) * 100 if total_req > 0 else 0
        
        return {
            "total_views": self.count,
            "elapsed_time": elapsed,
            "views_per_second": views_per_second,
            "views_per_minute": views_per_minute,
            "views_per_hour": views_per_hour,
            "success_rate": success_rate,
            "successful_requests": self.successful_requests,
            "failed_requests": self.failed_requests,
            "peak_speed": self.peak_speed
        }
    
    def display_stats(self):
        stats = self.calculate_stats()
        print(f"\n{'='*60}")
        print(f"📊 THỐNG KÊ HIỆU SUẤT - PATCHED VERSION")
        print(f"{'='*60}")
        print(f"👀 Tổng view: {stats['total_views']:,}")
        print(f"⏱️ Thời gian: {stats['elapsed_time']:.1f}s")
        print(f"🚀 Tốc độ hiện tại: {stats['views_per_second']:.1f} view/s")
        print(f"🏆 Tốc độ cao nhất: {stats['peak_speed']:.1f} view/s")
        print(f"📈 Dự kiến: {stats['views_per_minute']:,.0f} view/phút")
        print(f"🏃‍♂️ Dự kiến: {stats['views_per_hour']:,.0f} view/giờ")
        print(f"✅ Request thành công: {stats['successful_requests']:,}")
        print(f"❌ Request thất bại: {stats['failed_requests']:,}")
        print(f"🎯 Tỷ lệ thành công: {stats['success_rate']:.1f}%")
        print(f"{'='*60}")
    
    async def run_optimized(self, video_url: str):
        print("🔄 Đang lấy Video ID...")
        video_id = self.get_video_id(video_url)
        
        if not video_id:
            print("❌ Không thể lấy Video ID. Kiểm tra lại URL!")
            return
        
        cpu_count = os.cpu_count() or 1
        # Worker vừa phải — ổn định hơn 8000 task ảo
        if cpu_count <= 2:
            optimal_workers = 1200
        elif cpu_count <= 4:
            optimal_workers = 2500
        else:
            optimal_workers = 4000
        
        print(f"✅ Video ID: {video_id}")
        print(f"💻 CPU Cores: {cpu_count}")
        print(f"🎯 Số tasks: {optimal_workers:,}")
        print("⚡ Patch: short-link + device dày + delay nới + multi-host")
        print("🚀 Đang khởi chạy... (Nhấn Ctrl+C để dừng)")
        
        await asyncio.sleep(1.5)
        
        await self.init_session()
        self.is_running = True
        self.start_time = time.time()
        
        semaphore = asyncio.Semaphore(min(2000, optimal_workers // 2))
        
        try:
            tasks = []
            for i in range(optimal_workers):
                task = asyncio.create_task(self.view_sender(video_id, i, semaphore))
                tasks.append(task)
            
            logger.info(f"✅ Đã khởi tạo {len(tasks):,} tasks")
            
            last_display = 0
            while self.is_running:
                await asyncio.sleep(0.4)
                
                current_time = time.time()
                if current_time - last_display >= 1.5:
                    stats = self.calculate_stats()
                    print(
                        f"\r✅ Đã gửi: {stats['total_views']:,} | "
                        f"Tốc độ: {stats['views_per_second']:.1f} view/s | "
                        f"Peak: {stats['peak_speed']:.1f} view/s | "
                        f"Thành công: {stats['success_rate']:.1f}% | "
                        f"Thời gian: {stats['elapsed_time']:.1f}s", 
                        end="", flush=True
                    )
                    last_display = current_time
                    
        except KeyboardInterrupt:
            print("\n\n🛑 Đang dừng bot...")
        except Exception as e:
            logger.error(f"❌ Lỗi không mong muốn: {e}")
        finally:
            self.is_running = False
            
            logger.info("🛑 Đang dừng các tasks...")
            for task in tasks:
                task.cancel()
            
            await asyncio.gather(*tasks, return_exceptions=True)
            await self.close_session()
            self.display_stats()

def signal_handler(sig, frame):
    print("\n\n🛑 Nhận tín hiệu dừng...")
    sys.exit(0)

def display_banner():
    os.system("cls" if os.name == "nt" else "clear")
    
    banner = """
    ╔══════════════════════════════════════════════════════════╗
    ║                      🚀  VIEW BOT PRO                    ║
    ║                 aletsion bot v1.1 PATCHED                ║
    ║                                                          ║
    ║    ████████╗██╗██╗  ██╗████████╗ ██████╗ ██╗  ██╗        ║
    ║    ╚══██╔══╝██║██║ ██╔╝╚══██╔══╝██╔═══██╗██║ ██╔╝        ║
    ║       ██║   ██║█████╔╝    ██║   ██║   ██║█████╔╝         ║
    ║       ██║   ██║██╔═██╗    ██║   ██║   ██║██╔═██╗         ║
    ║       ██║   ██║██║  ██╗   ██║   ╚██████╔╝██║  ██╗        ║
    ║       ╚═╝   ╚═╝╚═╝  ╚═╝   ╚═╝    ╚═════╝ ╚═╝  ╚═╝        ║
    ║                                                          ║
    ║         ⚡ Short-link + Device dày + Delay nới           ║
    ╚══════════════════════════════════════════════════════════╝
    
    📊 TÍNH NĂNG:
    ✅ Tự động phát hiện ID video (kể cả vt.tiktok.com)
    ✅ Device fingerprint dày hơn (iid / openudid / cdid)
    ✅ Multi-host phân tán
    ✅ Delay không tự phanh
    ✅ Worker ổn định theo CPU
    ✅ Retry nhẹ + stats real-time
    
    ⚠️ KHUYẾN CÁO: Chỉ dành cho mục đích giáo dục
    """      
    print(banner)

def get_user_input():
    print("\n" + "═" * 60)
    print("🎯 CONFIGURATION SETUP")
    print("═" * 60)
    
    video_url = input("\n📥 Nhập link video (hỗ trợ short link): ").strip()
    
    if not video_url:
        print("❌ URL không được để trống!")
        return None
        
    if not video_url.startswith(('http://', 'https://')):
        print("❌ URL không hợp lệ! Cần có http:// hoặc https://")
        return None
    
    print("\n🔍 Kiểm tra kết nối...", end="")
    try:
        requests.get("https://www.google.com", timeout=5)
        print(" ✅ OK")
    except:
        print(" ❌ Không có mạng!")
        return None
    
    return video_url

async def main_optimized():
    display_banner()
    
    signal.signal(signal.SIGINT, signal_handler)
    
    video_url = get_user_input()
    if not video_url:
        return
    
    print("\n🎮 STARTING BOT...")
    print("═" * 60)
    print("💡 Tip: Nhấn Ctrl+C để dừng bất cứ lúc nào")
    print("⏳ Đang khởi tạo...")
    
    bot = OptimizedTikTokViewBot()
    
    try:
        await bot.run_optimized(video_url)
    except Exception as e:
        logger.error(f"❌ Bot execution error: {e}")
        print(f"\n💥 Lỗi nghiêm trọng: {e}")
    finally:
        await bot.close_session()
        
    print("\n" + "═" * 60)
    print("🎉 BOT SESSION COMPLETED")
    print("═" * 60)
    print("Cảm ơn đã dùng Spy View Bot Pro!")
    print("Follow for more tools! 👨‍💻")

if __name__ == "__main__":
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    
    asyncio.set_event_loop(asyncio.new_event_loop())
    
    try:
        asyncio.run(main_optimized())
    except KeyboardInterrupt:
        print("\n\n👋 Đã dừng bởi người dùng. Tạm biệt!")
    except Exception as e:
        print(f"\n💥 Lỗi không mong muốn: {e}")