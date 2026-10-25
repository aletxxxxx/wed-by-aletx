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
    version: str
    api_level: int

class DeviceGenerator:
    DEVICES = [
        DeviceInfo("Pixel 6", "12", 31),
        DeviceInfo("Pixel 5", "11", 30),
        DeviceInfo("Samsung Galaxy S21", "13", 33),
        DeviceInfo("Oppo Reno 8", "12", 31),
        DeviceInfo("Xiaomi Mi 11", "12", 31),
    ]
    
    @classmethod
    def random_device(cls) -> DeviceInfo:
        return random.choice(cls.DEVICES)

class Signature:
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
            "X-Khronos": str(unix_timestamp)
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
        """Giá»¯ nguyÃªn session hiá»u quáº£ cá»§a báº¡n"""
        timeout = aiohttp.ClientTimeout(total=30, connect=10)
        connector = aiohttp.TCPConnector(
            limit=0,
            limit_per_host=0,
            keepalive_timeout=30,
            enable_cleanup_closed=True
        )
        
        self.session = aiohttp.ClientSession(
            timeout=timeout,
            connector=connector,
            headers={'User-Agent': 'com.ss.android.ugc.trill/400304'},
            cookie_jar=aiohttp.DummyCookieJar()
        )
    
    async def close_session(self):
        if self.session:
            await self.session.close()
    
    def get_video_id(self, url: str) -> Optional[str]:
        """ThÃªm fallback methods tá»« code cá»§a tÃ´i"""
        try:
            # Method 1: Direct patterns tá»« URL
            patterns_url = [
                r'/video/(\d+)',
                r'tiktok\.com/@[^/]+/(\d+)',
                r'(\d{18,19})'
            ]
            
            for pattern in patterns_url:
                match = re.search(pattern, url)
                if match:
                    video_id = match.group(1)
                    logger.info(f"â Found Video ID from URL: {video_id}")
                    return video_id
            
            # Method 2: Request page (cá»§a báº¡n)
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
                    logger.info(f"â Found Video ID from page: {video_id}")
                    return video_id
            
            logger.error("â No video ID found")
            return None
                
        except Exception as e:
            logger.error(f"â Error getting video ID: {e}")
            return None
    
    def generate_request_data(self, video_id: str) -> Tuple[str, Dict, Dict, Dict]:
        """Giá»¯ nguyÃªn method hiá»u quáº£ cá»§a báº¡n"""
        device = DeviceGenerator.random_device()
        
        params = (
            f"channel=googleplay&aid=1233&app_name=musical_ly&version_code=400304"
            f"&device_platform=android&device_type={device.model.replace(' ', '+')}"
            f"&os_version={device.version}&device_id={random.randint(600000000000000, 699999999999999)}"
            f"&os_api={device.api_level}&app_language=vi&tz_name=Asia%2FHo_Chi_Minh"
        )
        
        url = f"https://api16-core-c-alisg.tiktokv.com/aweme/v1/aweme/stats/?{params}"
        
        data = {
            "item_id": video_id,
            "play_delta": 1,
            "action_time": int(time.time())
        }
        
        cookies = {"sessionid": secrets.token_hex(16)}
        
        headers = {
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
            "User-Agent": "com.ss.android.ugc.trill/400304",
            "Accept-Encoding": "gzip",
            "Connection": "keep-alive"
        }
        
        return url, data, cookies, headers
    
    async def send_view_request(self, video_id: str, semaphore: asyncio.Semaphore) -> bool:
        """ThÃªm retry mechanism nháº¹"""
        async with semaphore:
            for attempt in range(2):  # Retry 1 láº§n
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
                            if attempt == 0:  # Chá» retry náº¿u lá»i server
                                await asyncio.sleep(0.01)
                                continue
                            self.failed_requests += 1
                            return False
                            
                except Exception as e:
                    if attempt == 0:
                        await asyncio.sleep(0.01)
                        continue
                    self.failed_requests += 1
                    return False
    
    async def view_sender(self, video_id: str, task_id: int, semaphore: asyncio.Semaphore):
        """Tá»i Æ°u delay algorithm"""
        consecutive_success = 0
        base_delay = 0.001
        
        while self.is_running:
            success = await self.send_view_request(video_id, semaphore)
            
            if success:
                consecutive_success += 1
                # Giáº£m delay náº¿u nhiá»u request thÃ nh cÃ´ng liÃªn tiáº¿p
                if consecutive_success > 100:
                    delay = base_delay * 0.5
                elif consecutive_success > 50:
                    delay = base_delay * 0.7
                else:
                    delay = base_delay
            else:
                consecutive_success = 0
                delay = base_delay * 2  # TÄng delay náº¿u tháº¥t báº¡i
            
            # Adaptive delay based on current speed
            current_speed = self.calculate_stats()["views_per_second"]
            if current_speed > 500:
                delay *= 1.5
            elif current_speed > 1000:
                delay *= 2
            
            await asyncio.sleep(delay + random.uniform(0, 0.002))
    
    def calculate_stats(self) -> Dict[str, float]:
        """ThÃªm peak speed tracking"""
        elapsed = time.time() - self.start_time
        views_per_second = self.count / elapsed if elapsed > 0 else 0
        
        # Update peak speed
        if views_per_second > self.peak_speed:
            self.peak_speed = views_per_second
        
        views_per_minute = views_per_second * 60
        views_per_hour = views_per_minute * 60
        
        success_rate = (self.successful_requests / (self.successful_requests + self.failed_requests)) * 100 if (self.successful_requests + self.failed_requests) > 0 else 0
        
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
        """ThÃªm hiá»n thá» peak speed"""
        stats = self.calculate_stats()
        print(f"\n{'='*60}")
        print(f"ð THá»NG KÃ HIá»U SUáº¤T - OPTIMIZED VERSION")
        print(f"{'='*60}")
        print(f"ð Tá»ng view: {stats['total_views']:,}")
        print(f"â° Thá»i gian: {stats['elapsed_time']:.1f}s")
        print(f"ð Tá»c Äá» hiá»n táº¡i: {stats['views_per_second']:.1f} view/s")
        print(f"ð Tá»c Äá» cao nháº¥t: {stats['peak_speed']:.1f} view/s")
        print(f"ð Dá»± kiáº¿n: {stats['views_per_minute']:,.0f} view/phÃºt")
        print(f"ðââï¸ Dá»± kiáº¿n: {stats['views_per_hour']:,.0f} view/giá»")
        print(f"â Request thÃ nh cÃ´ng: {stats['successful_requests']:,}")
        print(f"â Request tháº¥t báº¡i: {stats['failed_requests']:,}")
        print(f"ð¯ Tá»· lá» thÃ nh cÃ´ng: {stats['success_rate']:.1f}%")
        print(f"{'='*60}")
    
    async def run_optimized(self, video_url: str):
        """Tá»i Æ°u sá» lÆ°á»£ng tasks tá»± Äá»ng"""
        print("ð Äang láº¥y Video ID...")
        video_id = self.get_video_id(video_url)
        
        if not video_id:
            print("â KhÃ´ng thá» láº¥y Video ID. Kiá»m tra láº¡i URL!")
            return
        
        # Tá»± Äá»ng detect sá» tasks tá»i Æ°u
        cpu_count = os.cpu_count() or 1
        if cpu_count <= 2:
            optimal_workers = 2000  # Low-end CPU
        elif cpu_count <= 4:
            optimal_workers = 5000  # Mid-range CPU  
        else:
            optimal_workers = 8000  # High-end CPU
        
        print(f"â Video ID: {video_id}")
        print(f"ð» CPU Cores: {cpu_count}")
        print(f"ð¯ Sá» tasks tá»i Æ°u: {optimal_workers:,}")
        print("â¡ TÃ­nh nÄng má»i: Auto-retry, Adaptive delay, Peak tracking")
        print("ð Äang khá»i cháº¡y... (Nháº¥n Ctrl+C Äá» dá»«ng)")
        
        await asyncio.sleep(2)
        
        await self.init_session()
        self.is_running = True
        self.start_time = time.time()
        
        # Semaphore linh hoáº¡t
        semaphore = asyncio.Semaphore(min(3000, optimal_workers // 3))
        
        try:
            tasks = []
            for i in range(optimal_workers):
                task = asyncio.create_task(self.view_sender(video_id, i, semaphore))
                tasks.append(task)
            
            logger.info(f"â ÄÃ£ khá»i táº¡o {len(tasks):,} tasks")
            
            last_display = 0
            while self.is_running:
                await asyncio.sleep(0.5)
                
                current_time = time.time()
                if current_time - last_display >= 2:
                    stats = self.calculate_stats()
                    print(
                        f"\râ ÄÃ£ gá»­i: {stats['total_views']:,} | "
                        f"Tá»c Äá»: {stats['views_per_second']:.1f} view/s | "
                        f"Peak: {stats['peak_speed']:.1f} view/s | "
                        f"ThÃ nh cÃ´ng: {stats['success_rate']:.1f}% | "
                        f"Thá»i gian: {stats['elapsed_time']:.1f}s", 
                        end="", flush=True
                    )
                    last_display = current_time
                    
        except KeyboardInterrupt:
            print("\n\nð Äang dá»«ng bot...")
        except Exception as e:
            logger.error(f"â Lá»i khÃ´ng mong muá»n: {e}")
        finally:
            self.is_running = False
            
            logger.info("ð Äang dá»«ng cÃ¡c tasks...")
            for task in tasks:
                task.cancel()
            
            await asyncio.gather(*tasks, return_exceptions=True)
            await self.close_session()
            self.display_stats()

def signal_handler(sig, frame):
    print("\n\nð Nháº­n tÃ­n hiá»u dá»«ng...")
    sys.exit(0)

def display_banner():
    """Giao diá»n má»i - Äáº¹p hÆ¡n"""
    os.system("cls" if os.name == "nt" else "clear")
    
    banner = """
    ââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââ
    â                      ð  VIEW BOT PRO                    â
    â                    aletsion bot v1.0                     â
    â                                                          â
    â    âââââââââââââââ  ââââââââââââ âââââââ âââ  âââ        â
    â    âââââââââââââââ âââââââââââââââââââââââââ ââââ        â
    â       âââ   ââââââââââ    âââ   âââ   ââââââââââ         â
    â       âââ   ââââââââââ    âââ   âââ   ââââââââââ         â
    â       âââ   ââââââ  âââ   âââ   ââââââââââââ  âââ        â
    â       âââ   ââââââ  âââ   âââ    âââââââ âââ  âââ        â
    â                                                          â
    â              â¡ PhiÃªn báº£n hiá»u suáº¥t tá»i Æ°u hÃ³a           â
    ââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââ
    
    ð TÃNH NÄNG:
    â Tá»± Äá»ng phÃ¡t hiá»n ID video
    â Há» thá»ng thá»­ láº¡i thÃ´ng minh
    â Kiá»m soÃ¡t tá»c Äá» thÃ­ch á»©ng
    â PhÃ¢n tÃ­ch thá»i gian thá»±c
    â Theo dÃµi hiá»u suáº¥t tá»i Äa
    â Kiáº¿n trÃºc Äa luá»ng
    
    â ï¸ KHUYáº¾N CÃO: Chá» dÃ nh cho má»¥c ÄÃ­ch giÃ¡o dá»¥c
    """      
    
    print(banner)

def get_user_input():
    """Giao diá»n input má»i"""
    print("\n" + "â" * 60)
    print("ð¯ CONFIGURATION SETUP")
    print("â" * 60)
    
    video_url = input("\nð¥ Please enter Spy video URL: ").strip()
    
    if not video_url:
        print("â URL cannot be empty!")
        return None
        
    if not video_url.startswith(('http://', 'https://')):
        print("â Invalid URL format! Please include http:// or https://")
        return None
    
    # Test internet connection
    print("\nð Checking internet connection...", end="")
    try:
        requests.get("https://www.google.com", timeout=5)
        print(" â Connected")
    except:
        print(" â No internet connection!")
        return None
    
    return video_url

async def main_optimized():
    """HÃ m main vá»i giao diá»n má»i"""
    display_banner()
    
    signal.signal(signal.SIGINT, signal_handler)
    
    video_url = get_user_input()
    if not video_url:
        return
    
    print("\nð® STARTING BOT...")
    print("â" * 60)
    print("ð¡ Tip: Press Ctrl+C to stop the bot at any time")
    print("â³ Initializing...")
    
    bot = OptimizedTikTokViewBot()
    
    try:
        await bot.run_optimized(video_url)
    except Exception as e:
        logger.error(f"â Bot execution error: {e}")
        print(f"\nð¥ Critical error occurred: {e}")
    finally:
        await bot.close_session()
        
    print("\n" + "â" * 60)
    print("ð BOT SESSION COMPLETED")
    print("â" * 60)
    print("Thank you for using Spy View Bot Pro!")
    print("Follow for more tools and updates! ð¨âð»")

if __name__ == "__main__":
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    
    asyncio.set_event_loop(asyncio.new_event_loop())
    
    try:
        asyncio.run(main_optimized())
    except KeyboardInterrupt:
        print("\n\nð Program terminated by user. Goodbye!")
    except Exception as e:
        print(f"\nð¥ Unexpected error: {e}")
