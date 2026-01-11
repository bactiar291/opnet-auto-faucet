import asyncio
import aiohttp
import json
import sys
import time
import re
import random
import datetime
from typing import Dict, Optional, Tuple, List
import urllib.parse

CAPTCHA_API_FILE = "cap.txt"
PROXY_FILE = "proxy.txt"
WALLET_FILE = "wallet.txt"
FAUCET_URL = "https://faucet.opnet.org/"
CLAIM_API_URL = "https://x.opnet.org/api/claim-faucet"
HCAPTCHA_SITEKEY = "4978ba10-9ffc-45fa-b97c-009e780023ee"
TURNSTILE_SITEKEY = "0x4AAAAAAAhNx1-1PPe0Oqfz"

SCTG_SERVERS = [
    "https://sctg.xyz",
    "https://ru.sctg.xyz", 
    "https://api.sctg.xyz"
]

class FaucetClaimer:
    def __init__(self):
        self.session = None
        self.user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        self.api_key = None
        self.sctg_server = None
        self.load_api_key()
        self.select_sctg_server()
    
    def load_api_key(self):
        """Load API key dari cap.txt"""
        try:
            with open(CAPTCHA_API_FILE, 'r') as f:
                lines = [line.strip() for line in f if line.strip()]
                if lines:
                    self.api_key = lines[0]
                    print(f"âœ… API key loaded: {self.api_key[:12]}...")
                    print(f"ðŸ”‘ Service: {'SCTG' if 'sctg' in self.api_key.lower() else 'Unknown'}")
                else:
                    print(f"âŒ File {CAPTCHA_API_FILE} kosong!")
                    sys.exit(1)
        except FileNotFoundError:
            print(f"âŒ File {CAPTCHA_API_FILE} tidak ditemukan!")
            print(f"ðŸ’¡ Buat file {CAPTCHA_API_FILE} berisi API key SCTG")
            print(f"   Format: your_sctg_api_key_here")
            sys.exit(1)
    
    def select_sctg_server(self):
        """Pilih server SCTG yang tersedia"""
        self.sctg_server = SCTG_SERVERS[0]  
        print(f"ðŸŒ Menggunakan SCTG server: {self.sctg_server}")
    
    async def init_session(self, proxy_url: str = None):
        """Initialize aiohttp session dengan atau tanpa proxy"""
        headers = {
            'User-Agent': self.user_agent,
            'Accept': '*/*',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Cache-Control': 'no-cache',
        }
        
        if proxy_url:
            print(f"ðŸ”— Menggunakan proxy: {proxy_url[:60]}...")
            from aiohttp import ClientSession
            connector = aiohttp.TCPConnector(ssl=False)
            self.session = ClientSession(headers=headers, connector=connector)
        else:
            from aiohttp import ClientSession
            connector = aiohttp.TCPConnector(ssl=False)
            self.session = ClientSession(headers=headers, connector=connector)
    
    async def close(self):
        """Close session"""
        if self.session and not self.session.closed:
            await self.session.close()
    
    async def test_sctg_connection(self) -> bool:
        """Test koneksi ke server SCTG"""
        print("\nðŸ” Testing koneksi ke SCTG...")
        try:
            test_url = f"{self.sctg_server}/ping"
            async with self.session.get(test_url, timeout=10) as resp:
                status = resp.status
                if status == 200:
                    print("âœ… SCTG server merespon")
                    return True
                else:
                    print(f"âš ï¸  SCTG status: {status}")
                    return False
        except Exception as e:
            print(f"âŒ Tidak bisa connect ke SCTG: {str(e)[:100]}")
            for server in SCTG_SERVERS[1:]:
                try:
                    self.sctg_server = server
                    print(f"ðŸ”„ Coba server: {server}")
                    test_url = f"{server}/ping"
                    async with self.session.get(test_url, timeout=10) as resp:
                        if resp.status == 200:
                            print(f"âœ… Server {server} bekerja")
                            return True
                except:
                    continue
            return False
    
    async def solve_hcaptcha_sctg(self) -> Optional[str]:
        """
        Solve hCaptcha menggunakan SCTG API
        Dokumentasi SCTG: https://sctg.xyz/api.html
        """
        print(f"\nðŸ”„ Menyelesaikan hCaptcha via SCTG...")
        print(f"ðŸ“¡ Server: {self.sctg_server}")
        
        if not self.api_key:
            print("âŒ API key tidak tersedia!")
            return None
        
        in_url = f"{self.sctg_server}/in.php"
        res_url = f"{self.sctg_server}/res.php"
        
        params = {
            'key': self.api_key,
            'method': 'hcaptcha',
            'sitekey': HCAPTCHA_SITEKEY,
            'pageurl': FAUCET_URL,
            'json': 1,
            'soft_id': 3721  
        }
        
        print(f"ðŸ“¤ Mengirim hCaptcha ke SCTG...")
        print(f"   Sitekey: {HCAPTCHA_SITEKEY}")
        print(f"   Page URL: {FAUCET_URL}")
        
        for attempt in range(3):  
            try:
                print(f"\n   ðŸŽ¯ Attempt {attempt + 1}/3...")
                
                async with self.session.post(in_url, data=params, timeout=60) as resp:
                    resp_text = await resp.text()
                    print(f"   ðŸ“¥ Response: {resp_text}")
                    
                    try:
                        result = json.loads(resp_text)
                        
                        if result.get('status') == 1:
                            request_id = result.get('request')
                            print(f"   âœ… Request diterima, ID: {request_id}")
                            
                            print(f"   â³ Menunggu solusi dari human solver...")
                            print(f"   ðŸ’¡ Ini bisa memakan waktu 30-120 detik")
                            
                            poll_params = {
                                'key': self.api_key,
                                'action': 'get',
                                'id': request_id,
                                'json': 1
                            }
                            
                            for poll_attempt in range(90):  
                                await asyncio.sleep(2)
                                
                                if poll_attempt % 15 == 0:  
                                    elapsed = poll_attempt * 2
                                    print(f"   â±ï¸  Menunggu... ({elapsed} detik)")
                                
                                try:
                                    async with self.session.get(res_url, params=poll_params, timeout=20) as poll_resp:
                                        poll_text = await poll_resp.text()
                                        
                                        try:
                                            poll_result = json.loads(poll_text)
                                            
                                            if poll_result.get('status') == 1:
                                                token = poll_result.get('request')
                                                print(f"\n   ðŸŽ‰ hCaptcha berhasil diselesaikan!")
                                                print(f"   ðŸŽ« Token: {token[:60]}...")
                                                
                                                with open('sctg_hcaptcha_token.txt', 'w') as f:
                                                    f.write(token)
                                                    f.write(f"\n\nRequest ID: {request_id}")
                                                    f.write(f"\nTime: {time.ctime()}")
                                                
                                                return token
                                            elif poll_result.get('request') == 'CAPCHA_NOT_READY':
                                                continue
                                            else:
                                                error = poll_result.get('request', 'Unknown')
                                                if poll_attempt % 30 == 0:
                                                    print(f"   âš ï¸  Status: {error}")
                                                continue
                                        except json.JSONDecodeError:
                                            if 'OK|' in poll_text:
                                                token = poll_text.split('|')[1]
                                                print(f"\n   ðŸŽ‰ hCaptcha solved! Token: {token[:60]}...")
                                                return token
                                            continue
                                except Exception as e:
                                    if poll_attempt % 30 == 0:
                                        print(f"   âš ï¸  Poll error: {str(e)[:50]}")
                                    continue
                            
                            print("   âŒ Timeout menunggu solusi (3 menit)")
                            return None
                            
                        else:
                            error_msg = result.get('request', result.get('error_text', 'Unknown error'))
                            print(f"   âŒ Error SCTG: {error_msg}")
                            
                            if "ERROR_WRONG_USER_KEY" in error_msg:
                                print("   ðŸ’¡ API key salah! Periksa file cap.txt")
                                return None
                            elif "ERROR_ZERO_BALANCE" in error_msg:
                                print("   ðŸ’¡ Saldo SCTG habis!")
                                return None
                            elif "ERROR_KEY_DOES_NOT_EXIST" in error_msg:
                                print("   ðŸ’¡ API key tidak terdaftar di SCTG")
                                return None
                            
                            if attempt == 1:
                                print("   ðŸ”„ Coba tanpa parameter json...")
                                params.pop('json', None)
                            
                            await asyncio.sleep(3)
                            continue
                            
                    except json.JSONDecodeError:
                        if resp_text.startswith('OK|'):
                            request_id = resp_text.split('|')[1]
                            print(f"   âœ… Request diterima (plain), ID: {request_id}")
                            print("   âš ï¸  Format plain text, perlu implementasi polling")
                            await asyncio.sleep(2)
                            continue
                        else:
                            print(f"   âŒ Response tidak valid: {resp_text[:100]}")
                            await asyncio.sleep(3)
                            continue
                            
            except asyncio.TimeoutError:
                print(f"   â° Timeout attempt {attempt + 1}")
                await asyncio.sleep(5)
            except Exception as e:
                print(f"   âŒ Error: {str(e)[:100]}")
                await asyncio.sleep(3)
        
        print("   âŒ Gagal menyelesaikan hCaptcha setelah 3 percobaan")
        return None
    
    async def solve_turnstile_sctg(self, sitekey: str) -> Optional[str]:
        """
        Solve Cloudflare Turnstile menggunakan SCTG API
        """
        print(f"\nðŸŒ€ Menyelesaikan Turnstile via SCTG...")
        print(f"   Sitekey: {sitekey}")
        
        if not self.api_key:
            return None
        
        in_url = f"{self.sctg_server}/in.php"
        res_url = f"{self.sctg_server}/res.php"
        
        params = {
            'key': self.api_key,
            'method': 'turnstile',
            'sitekey': sitekey,
            'pageurl': FAUCET_URL,
            'json': 1,
            'action': 'managed'  
        }
        
        try:
            print("   ðŸ“¤ Mengirim Turnstile ke SCTG...")
            async with self.session.post(in_url, data=params, timeout=45) as resp:
                resp_text = await resp.text()
                print(f"   ðŸ“¥ Response: {resp_text}")
                
                try:
                    result = json.loads(resp_text)
                    
                    if result.get('status') == 1:
                        request_id = result.get('request')
                        print(f"   âœ… Request Turnstile diterima, ID: {request_id}")
                        
                        poll_params = {
                            'key': self.api_key,
                            'action': 'get',
                            'id': request_id,
                            'json': 1
                        }
                        
                        for poll_attempt in range(60):  
                            await asyncio.sleep(2)
                            
                            if poll_attempt % 10 == 0:
                                print(f"   â³ Tunggu Turnstile... ({poll_attempt * 2}s)")
                            
                            async with self.session.get(res_url, params=poll_params, timeout=15) as poll_resp:
                                poll_text = await poll_resp.text()
                                
                                try:
                                    poll_result = json.loads(poll_text)
                                    
                                    if poll_result.get('status') == 1:
                                        token = poll_result.get('request')
                                        print(f"   âœ… Turnstile solved! Token: {token[:50]}...")
                                        return token
                                    elif poll_result.get('request') == 'CAPCHA_NOT_READY':
                                        continue
                                except:
                                    if 'OK|' in poll_text:
                                        token = poll_text.split('|')[1]
                                        print(f"   âœ… Turnstile solved (plain)! Token: {token[:50]}...")
                                        return token
                                    continue
                        
                        print("   âŒ Timeout Turnstile")
                        return None
                    else:
                        error = result.get('request', 'Unknown error')
                        print(f"   âŒ Error Turnstile: {error}")
                        return None
                        
                except json.JSONDecodeError:
                    if resp_text.startswith('OK|'):
                        request_id = resp_text.split('|')[1]
                        print(f"   âš ï¸  Plain text response, ID: {request_id}")
                        print(f"   â„¹ï¸  Untuk plain text, butuh implementasi polling berbeda")
                        return None
                    else:
                        print(f"   âŒ Invalid response: {resp_text}")
                        return None
                
        except Exception as e:
            print(f"   âŒ Error solving Turnstile: {str(e)[:100]}")
            return None
    
    async def claim_faucet_api(self, wallet_address: str, hcaptcha_token: str, turnstile_token: str = "") -> Dict:
        """
        Kirim klaim ke API faucet
        """
        print("\nðŸŽ¯ Mengirim klaim ke API faucet...")
        
        payload = {
            "walletAddress": wallet_address,
            "hCaptcha": hcaptcha_token,
            "cloudflareCaptcha": turnstile_token if turnstile_token else ""
        }
        
        print(f"ðŸ“¤ Payload yang dikirim:")
        print(f"   Wallet: {wallet_address}")
        print(f"   hCaptcha Token: {hcaptcha_token[:60]}...")
        if turnstile_token:
            print(f"   Turnstile Token: {turnstile_token[:60]}...")
        
        try:
            headers = {
                'User-Agent': self.user_agent,
                'Content-Type': 'application/json',
                'Accept': 'application/json',
                'Origin': 'https://faucet.opnet.org',
                'Referer': 'https://faucet.opnet.org/',
                'X-Requested-With': 'XMLHttpRequest'
            }
            
            print(f"   ðŸš€ Mengirim ke: {CLAIM_API_URL}")
            async with self.session.post(
                CLAIM_API_URL,
                json=payload,
                headers=headers,
                timeout=45
            ) as resp:
                
                response_text = await resp.text()
                status_code = resp.status
                print(f"\nðŸ“¥ Response API (Status {status_code}):")
                print(f"   {response_text[:200]}...")
                
                try:
                    result = json.loads(response_text)
                    return {
                        "success": result.get('success', False),
                        "message": result.get('message', 'No message'),
                        "txHash": result.get('txHash'),
                        "amount": result.get('amount'),
                        "raw": response_text
                    }
                except json.JSONDecodeError:
                    if 'success' in response_text.lower() or 'txhash' in response_text.lower():
                        return {
                            "success": True,
                            "message": "Klaim berhasil (manual parse)",
                            "raw": response_text
                        }
                    else:
                        return {
                            "success": False,
                            "message": f"Invalid JSON: {response_text[:150]}",
                            "raw": response_text
                        }
                    
        except asyncio.TimeoutError:
            print("   âŒ Timeout saat mengirim klaim")
            return {"success": False, "message": "API timeout"}
        except Exception as e:
            print(f"   âŒ Error calling API: {str(e)[:100]}")
            return {"success": False, "message": str(e)}
    
    async def process_wallet(self, wallet_address: str, proxy_url: str = None) -> Dict:
        """
        Proses utama untuk klaim faucet dengan SCTG
        """
        print(f"\n{'='*60}")
        print(f"ðŸš€ FAUCET CLAIMER dengan SCTG SOLVER")
        print(f"ðŸ“ Wallet: {wallet_address}")
        print(f"{'='*60}")
        
        try:
            await self.init_session(proxy_url)
            
            if not await self.test_sctg_connection():
                print("âš ï¸  Masalah koneksi SCTG, tetap lanjut...")
            
            print(f"\n{'='*60}")
            print("ðŸŽ¯ STEP 1: SOLVE hCAPTCHA DENGAN SCTG")
            print(f"{'='*60}")
            
            hcaptcha_token = await self.solve_hcaptcha_sctg()
            if not hcaptcha_token:
                return {
                    "success": False, 
                    "message": "Gagal solve hCaptcha dengan SCTG",
                    "solver": "SCTG",
                    "step": "hCaptcha"
                }
            
            turnstile_token = ""
            use_turnstile = True  
            
            if use_turnstile and TURNSTILE_SITEKEY:
                print(f"\n{'='*60}")
                print("ðŸŽ¯ STEP 2: SOLVE TURNSTILE DENGAN SCTG")
                print(f"{'='*60}")
                
                turnstile_token = await self.solve_turnstile_sctg(TURNSTILE_SITEKEY)
                if not turnstile_token:
                    print("âš ï¸  Gagal solve Turnstile, lanjut tanpa...")
            
            print(f"\n{'='*60}")
            print("ðŸŽ¯ STEP 3: KLAIM FAUCET")
            print(f"{'='*60}")
            
            result = await self.claim_faucet_api(wallet_address, hcaptcha_token, turnstile_token)
            result["solver"] = "SCTG"
            result["wallet"] = wallet_address
            result["timestamp"] = time.time()
            
            return result
            
        except Exception as e:
            print(f"\nâŒ ERROR PROSES: {str(e)}")
            import traceback
            traceback.print_exc()
            return {
                "success": False, 
                "message": f"Error proses: {str(e)}",
                "solver": "SCTG",
                "error": str(e)
            }
        finally:
            await self.close()

def load_wallets() -> List[str]:
    """Load wallets dari wallet.txt"""
    wallets = []
    try:
        with open(WALLET_FILE, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    wallets.append(line)
        if wallets:
            print(f"ðŸ“Š Ditemukan {len(wallets)} wallet")
            for i, wallet in enumerate(wallets, 1):
                print(f"   {i}. {wallet}")
        else:
            print(f"âŒ File {WALLET_FILE} kosong!")
            sys.exit(1)
    except FileNotFoundError:
        print(f"âŒ File {WALLET_FILE} tidak ditemukan!")
        print(f"ðŸ’¡ Buat file {WALLET_FILE} berisi daftar wallet")
        print(f"   Format: satu wallet per baris")
        sys.exit(1)
    
    return wallets

def load_proxies() -> List[str]:
    """Load proxies dari proxy.txt"""
    proxies = []
    try:
        with open(PROXY_FILE, 'r') as f:
            proxies = [line.strip() for line in f if line.strip()]
        if proxies:
            print(f"ðŸ“Š Ditemukan {len(proxies)} proxy")
        else:
            print("â„¹ï¸ proxy.txt kosong, jalankan tanpa proxy")
    except FileNotFoundError:
        print("â„¹ï¸ proxy.txt tidak ditemukan, jalankan tanpa proxy")
    
    return proxies

def validate_wallet(address: str) -> bool:
    """Validasi format wallet address"""
    patterns = [
        r'^bc1[ac-hj-np-z02-9]{11,87}$',  
        r'^[13][a-km-zA-HJ-NP-Z1-9]{25,34}$',  
        r'^bcrt1[ac-hj-np-z02-9]{11,87}$',  
    ]
    
    for pattern in patterns:
        if re.match(pattern, address):
            return True
    return False

def format_time(seconds: int) -> str:
    """Format detik menjadi HH:MM:SS"""
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60
    return f"{hours:02d}:{minutes:02d}:{secs:02d}"

async def countdown_timer(seconds: int, message: str = "Menunggu"):
    """Tampilkan countdown timer"""
    print(f"\nâ° {message} {format_time(seconds)}")
    
    for remaining in range(seconds, 0, -1):
        if remaining % 60 == 0 or remaining <= 10:  
            print(f"   â³ {message}: {format_time(remaining)}")
        await asyncio.sleep(1)
    
    print(f"âœ… {message} selesai!")

async def process_all_wallets(wallets: List[str], proxies: List[str] = None):
    """Proses semua wallet dalam loop"""
    cycle_count = 1
    total_wait_time = 86460  
    
    while True:
        print(f"\n{'='*70}")
        print(f"ðŸš€ SIKLUS #{cycle_count}")
        print(f"ðŸ“… {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'='*70}")
        
        for i, wallet in enumerate(wallets, 1):
            print(f"\nðŸ“ Memproses wallet {i}/{len(wallets)}")
            
            proxy_url = None
            if proxies:
                proxy_index = (cycle_count - 1 + i - 1) % len(proxies)
                proxy_url = proxies[proxy_index]
                print(f"ðŸ”— Proxy terpilih: {proxy_url[:70]}...")
            
            if not validate_wallet(wallet):
                print(f"âš ï¸  Format wallet tidak valid: {wallet}")
                print(f"   Lanjut ke wallet berikutnya...")
                continue
            
            claimer = FaucetClaimer()
            result = await claimer.process_wallet(wallet, proxy_url)
            
            print(f"\nðŸ“Š Hasil untuk {wallet}:")
            if result.get('success'):
                print(f"âœ… SUKSES: {result.get('message')}")
                if result.get('amount'):
                    print(f"ðŸ’° Amount: {result.get('amount')}")
            else:
                print(f"âŒ GAGAL: {result.get('message')}")
            
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            result_file = f"result_{wallet[-8:]}_{timestamp}.json"
            with open(result_file, 'w', encoding='utf-8') as f:
                result['timestamp_str'] = time.ctime()
                result['cycle'] = cycle_count
                json.dump(result, f, indent=2, ensure_ascii=False)
            
            if i < len(wallets):
                wait_between = 30  
                print(f"\nâ³ Tunggu {wait_between} detik sebelum wallet berikutnya...")
                await asyncio.sleep(wait_between)
        
        print(f"\n{'='*70}")
        print(f"âœ… SIKLUS #{cycle_count} SELESAI")
        print(f"â° Waktu: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'='*70}")
        
        cycle_count += 1
        
        print(f"\nâ³ Menunggu untuk siklus berikutnya...")
        print(f"   Interval: 24 jam 1 menit ({total_wait_time} detik)")
        
        await countdown_timer(total_wait_time, "Siklus berikutnya dalam")

async def main():
    """Main function"""
    print("="*70)
    print("ðŸ¤– FAUCET CLAIMER v5.0 - MULTI WALLET LOOP")
    print("="*70)
    print("Fitur:")
    print("âœ… Baca wallet dari wallet.txt")
    print("âœ… Loop dengan jeda 24 jam 1 menit")
    print("âœ… Countdown timer berjalan")
    print("âœ… Auto solve hCaptcha + Turnstile")
    print("="*70)
    
    print("\nðŸ” Memeriksa file...")
    
    try:
        with open(CAPTCHA_API_FILE, 'r') as f:
            content = f.read().strip()
            if not content:
                print(f"âŒ File {CAPTCHA_API_FILE} kosong!")
                print(f"ðŸ’¡ Isi dengan API key SCTG dari https://sctg.xyz")
                sys.exit(1)
            else:
                print(f"âœ… {CAPTCHA_API_FILE}: OK")
    except FileNotFoundError:
        print(f"âŒ File {CAPTCHA_API_FILE} tidak ditemukan!")
        sys.exit(1)
    
    wallets = load_wallets()
    
    proxies = load_proxies()
    
    print(f"\nðŸ”§ KONFIGURASI:")
    print(f"   - Jumlah Wallet: {len(wallets)}")
    print(f"   - Jumlah Proxy: {len(proxies) if proxies else 'Tidak ada'}")
    print(f"   - Interval: 24 jam 1 menit")
    print(f"   - Auto Solve: hCaptcha + Turnstile")
    
    print("\nâš ï¸  PERINGATAN:")
    print("   - Pastikan API key SCTG valid dan saldo cukup")
    print("   - Bot akan berjalan terus sampai dihentikan (Ctrl+C)")
    print("   - Hasil akan disimpan di file result_*.json")
    
    confirm = input("\nðŸš€ Jalankan bot? (y/n): ").lower()
    if confirm != 'y':
        print("âŒ Dibatalkan oleh user")
        sys.exit(0)
    
    try:
        await process_all_wallets(wallets, proxies)
    except KeyboardInterrupt:
        print("\n\nâš ï¸  Bot dihentikan oleh user (Ctrl+C)")
        print("ðŸ’¾ Menyimpan status terakhir...")
        
        with open('last_status.json', 'w') as f:
            status = {
                "stopped_at": time.ctime(),
                "total_wallets": len(wallets),
                "timestamp": time.time()
            }
            json.dump(status, f, indent=2)
        
        print("âœ… Status disimpan di last_status.json")
        print("ðŸ‘‹ Sampai jumpa!")
    except Exception as e:
        print(f"\nâŒ ERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    print("\n" + "="*70)
    print("ðŸ¤– SCTG FAUCET BOT - MULTI WALLET LOOP")
    print("ðŸŒ https://sctg.xyz")
    print("="*70)
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\nðŸ‘‹ Program dihentikan")
    except Exception as e:
        print(f"\nâŒ ERROR SYSTEM: {e}")
        import traceback
        traceback.print_exc()
