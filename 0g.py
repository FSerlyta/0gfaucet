import requests
import time
from colorama import init, Fore
from web3 import Web3

# Inisialisasi Colorama
init(autoreset=True)

API_KEY = 'APIKEY 2CAPTCHA'  # Ganti dengan API key 2Captcha Anda
HCAPTCHA_SITEKEY = '1230eb62-f50c-4da4-a736-da5c3c342e8e'
FAUCET_URL = 'https://992dkn4ph6.execute-api.us-west-1.amazonaws.com/'
MAX_RETRIES = 2

# Wallet utama Anda (gunakan private key untuk mengirimkan transaksi)
MAIN_WALLET_PRIVATE_KEY = 'YOUR_MAIN_WALLET_PRIVATE_KEY'
MAIN_WALLET_ADDRESS = 'YOUR_MAIN_WALLET_ADDRESS'

# URL RPC Ethereum
WEB3_PROVIDER = 'https://mainnet.infura.io/v3/YOUR_INFURA_PROJECT_ID'
w3 = Web3(Web3.HTTPProvider(WEB3_PROVIDER))

def read_addresses():
    with open('wallet.txt', 'r') as file:
        addresses = file.read().splitlines()
    return addresses

def read_proxies():
    with open('proxy.txt', 'r') as file:
        proxies = file.read().splitlines()
    return proxies

def blur_proxy(proxy):
    if proxy:
        parts = proxy.split(':')
        if len(parts) == 4:  # Format: ip:port:username:password
            return f"{parts[0]}:****:****:****"
        elif len(parts) == 2:  # Format: ip:port
            return f"{parts[0]}:****"
    return "****"

def solve_hcaptcha(proxy):
    captcha_url = 'http://2captcha.com/in.php'
    params = {
        'key': API_KEY,
        'method': 'hcaptcha',
        'sitekey': HCAPTCHA_SITEKEY,
        'pageurl': FAUCET_URL,
        'json': 1
    }

    print(Fore.YELLOW + "Mengirim permintaan ke 2Captcha API untuk menyelesaikan hCaptcha...")
    try:
        response = requests.get(captcha_url, params=params, proxies={'http': proxy, 'https': proxy})
        response_data = response.json()

        if response_data.get('status') == 1:
            captcha_id = response_data.get('request')
            print(Fore.GREEN + f"Captcha ID diterima: {captcha_id}")

            result_url = 'http://2captcha.com/res.php'
            params_result = {
                'key': API_KEY,
                'action': 'get',
                'id': captcha_id,
                'json': 1
            }

            print(Fore.YELLOW + "Menunggu penyelesaian captcha...")
            time.sleep(10)
            while True:
                response_result = requests.get(result_url, params=params_result, proxies={'http': proxy, 'https': proxy})
                result_data = response_result.json()

                if result_data.get('status') == 1:
                    captcha_token = result_data.get('request')
                    print(Fore.GREEN + "hCaptcha berhasil diselesaikan!")
                    return captcha_token
                elif result_data.get('request') == 'CAPCHA_NOT_READY':
                    print(Fore.YELLOW + "Captcha belum siap, menunggu...")
                    time.sleep(5)
                else:
                    print(Fore.RED + f"Gagal menyelesaikan captcha: {result_data}")
                    return None
        else:
            print(Fore.RED + f"Gagal memulai penyelesaian captcha: {response_data}")
            return None
    except Exception as e:
        print(Fore.RED + f"Terjadi kesalahan: {e}")
        return None

def claim_faucet(address, hcaptcha_token, proxy):
    headers = {
        'Accept': 'application/json, text/plain, */*',
        'Content-Type': 'application/json',
        'Origin': 'https://hub.0g.ai',
        'Referer': 'https://hub.0g.ai/',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36'
    }
    payload = {
        'address': address,
        'hcaptchaToken': hcaptcha_token,
        'token': 'A0GI'
    }
    proxies = {
        'http': proxy,
        'https': proxy
    }

    print(Fore.CYAN + f"Mengirim permintaan claim faucet untuk address {address}...")
    try:
        response = requests.post(FAUCET_URL, json=payload, headers=headers, proxies=proxies)
        if response.status_code == 200:
            response_data = response.json()
            print(Fore.GREEN + "Claim faucet berhasil!")
            print(Fore.GREEN + "Response:", response_data)

            tx_hash = response_data.get('message')
            if tx_hash:
                # Buat link explorer
                explorer_url = f"https://chainscan-newton.0g.ai/tx/{tx_hash}"
                print(Fore.BLUE + f"Link Explorer: {explorer_url}")

                # Kirim A0GI ke wallet utama
                send_to_main_wallet(tx_hash)

                with open('log.txt', 'a') as log_file:
                    log_file.write(f"Address: {address}, Proxy: {proxy}, Tx Hash: {tx_hash}, Explorer: {explorer_url}\n")
            else:
                print(Fore.RED + "Hash transaksi tidak ditemukan dalam respons.")
            return True
        else:
            print(Fore.RED + f"Gagal claim faucet. Status code: {response.status_code}")
            print(Fore.RED + "Response:", response.text)
            return False
    except Exception as e:
        print(Fore.RED + f"Terjadi kesalahan saat mengirim permintaan: {e}")
        return False

def send_to_main_wallet(tx_hash):
    # Persiapkan transaksi untuk mengirim A0GI ke wallet utama
    nonce = w3.eth.getTransactionCount(MAIN_WALLET_ADDRESS)

    # Konfigurasi transaksi (ganti sesuai dengan token yang digunakan)
    tx = {
        'to': MAIN_WALLET_ADDRESS,
        'value': w3.toWei(0.01, 'ether'),  # Ganti sesuai dengan jumlah yang ingin Anda kirimkan
        'gas': 2000000,
        'gasPrice': w3.toWei('20', 'gwei'),
        'nonce': nonce
    }

    # Tandatangani transaksi
    signed_tx = w3.eth.account.signTransaction(tx, MAIN_WALLET_PRIVATE_KEY)

    # Kirim transaksi
    try:
        tx_hash = w3.eth.sendRawTransaction(signed_tx.rawTransaction)
        print(Fore.GREEN + f"Transaksi berhasil dikirim, hash transaksi: {tx_hash.hex()}")
    except Exception as e:
        print(Fore.RED + f"Gagal mengirim transaksi: {e}")

def main():
    addresses = read_addresses()
    proxies = read_proxies()

    if len(addresses) == 0:
        print(Fore.RED + "Tidak ada address yang ditemukan di address.txt.")
        return
    if len(proxies) == 0:
        print(Fore.RED + "Tidak ada proxy yang ditemukan di proxy.txt.")
        return

    if len(addresses) != len(proxies):
        print(Fore.RED + "Jumlah address dan proxy tidak sama. Pastikan setiap address memiliki proxy yang sesuai.")
        return

    for i, address in enumerate(addresses):
        proxy = proxies[i]
        retry_count = 0

        while retry_count < MAX_RETRIES:
            print(Fore.YELLOW + f"\nMemproses address {address} (Line {i + 1}) dengan proxy {blur_proxy(proxy)} (Percobaan {retry_count + 1})...")

            hcaptcha_token = solve_hcaptcha(proxy)
            if not hcaptcha_token:
                print(Fore.RED + f"Tidak dapat melanjutkan untuk address {address} tanpa token hCaptcha.")
                break

            success = claim_faucet(address, hcaptcha_token, proxy)
            if success:
                break
            else:
                retry_count += 1
                if retry_count < MAX_RETRIES:
                    print(Fore.YELLOW + f"Percobaan gagal. Mencoba lagi ({retry_count + 1}/{MAX_RETRIES})...")
                    time.sleep(5)
                else:
                    print(Fore.RED + f"Gagal claim faucet untuk address {address} setelah {MAX_RETRIES} percobaan.")

        time.sleep(10)

if __name__ == "__main__":
    main()
