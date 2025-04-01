from web3 import Web3, HTTPProvider
import json
import time
import secrets
import random
import colorama
from colorama import Fore, Style
import concurrent.futures
import threading
import re

colorama.init(autoreset=True)

print("Transfer Native Balance EVM Multiple Chain")
print("Transfer All Native Balance From Custom/Specific Address To Single Address")
print("Make Sure Already Input PrivateKey Custom/Specific Address On pvkeylist.txt !")
print("")

# Global variables
web3 = None
chainId = None
recipient = None
lock = threading.Lock()

# Initialize log files
def initialize_logs():
    open('log_success.txt', 'w').close()
    open('log_fail.txt', 'w').close()
    open('log_empty.txt', 'w').close()

def log_result(wallet_address, private_key, status):
    """
    Log only private key to appropriate log file
    status: 'success', 'fail', or 'empty'
    """
    # Ensure private key has 0x prefix
    if not str(private_key).startswith('0x'):
        private_key = f"0x{private_key}"
    
    filename = f"log_{status}.txt"
    
    with lock:
        with open(filename, 'a') as log_file:
            log_file.write(f"{private_key}\n")

def connect_web3():
    global web3, chainId
    web3 = Web3(Web3.HTTPProvider('https://evmrpc-testnet.0g.ai'))
    chainId = web3.eth.chain_id

    if web3.is_connected():
        print("Web3 Connected...\n")
    else:
        print("Error Connecting Please Try Again...")
        exit()

def TransferNative(sender, senderkey, recipient, index, total_wallets, max_retries=100000):
    # Convert private key to string format with '0x' prefix
    private_key_str = senderkey.hex() if hasattr(senderkey, 'hex') else str(senderkey)
    if not private_key_str.startswith('0x'):
        private_key_str = f"0x{private_key_str}"
    
    retries = 0
    while retries <= max_retries:
        try:
            with lock:
                if retries == 0:
                    print(f"\nProcessing Wallet {index}/{total_wallets}...")
                else:
                    print(f"\nRetry #{retries} for Wallet {index}/{total_wallets}...")
            
            gasPrice = web3.eth.gas_price
            nonce = web3.eth.get_transaction_count(sender)

            # Get balance before estimating gas
            balance = web3.eth.get_balance(sender)
            mainbalance = web3.from_wei(balance, 'ether')
            
            # Check if balance is zero or too low
            if balance == 0 or mainbalance < 0.0001:  # Threshold for "empty"
                with lock:
                    print(f"{Fore.LIGHTYELLOW_EX}💵 Empty balance!{Style.RESET_ALL} ⟠ {Fore.LIGHTGREEN_EX}Wallet balance : {mainbalance} ETH{Style.RESET_ALL}")
                log_result(sender, private_key_str, "empty")
                return

            try:
                gasAmount = web3.eth.estimate_gas({
                    'chainId': chainId,
                    'from': sender,
                    'to': recipient,
                    'value': balance,
                    'gasPrice': gasPrice,
                    'nonce': nonce
                })
            except Exception as gas_error:
                with lock:
                    print(f"Gas estimation error: {gas_error}")
                
                if retries == max_retries:
                    log_result(sender, private_key_str, "fail")
                    return
                retries += 1
                time.sleep(random.uniform(2, 5))  # Wait before retry
                continue
            
            totalfee_gwei = gasPrice * gasAmount
            totalfee_ether = web3.from_wei(totalfee_gwei, 'ether')
            
            totalsend = mainbalance - totalfee_ether

            if totalsend <= 0:
                with lock:
                    print(f"{Fore.LIGHTYELLOW_EX}💵 Balance too low for gas !{Style.RESET_ALL} ⟠ {Fore.LIGHTGREEN_EX}Wallet balance : {mainbalance} ETH{Style.RESET_ALL} ⛽ {Fore.LIGHTRED_EX}Fee: {totalfee_ether} ETH{Style.RESET_ALL}")
                log_result(sender, private_key_str, "empty")
                return

            if totalsend > 2**256 - 1:
                with lock:
                    print(f"Error: The amount to send exceeds the maximum allowed wei value.")
                log_result(sender, private_key_str, "fail")
                return

            auto_tx = {
                'chainId': chainId,
                'from': sender,
                'gas': gasAmount,
                'to': recipient,
                'value': web3.to_wei(totalsend, 'ether'),
                'gasPrice': gasPrice,
                'nonce': nonce
            }

            fixamount = '%.18f' % float(totalsend)
            with lock:
                print(f'{Fore.LIGHTBLUE_EX}Transferring....{Style.RESET_ALL}')
            
            try:
                tx_hash = web3.eth.send_raw_transaction(web3.eth.account.sign_transaction(auto_tx, senderkey).raw_transaction)
                txid = str(web3.to_hex(tx_hash))
                transaction_receipt = web3.eth.wait_for_transaction_receipt(tx_hash)
                
                with lock:
                    print('')
                    print(f'{Fore.LIGHTGREEN_EX}Transfer{Style.RESET_ALL} {fixamount} {Fore.LIGHTGREEN_EX}Native ETH from{Style.RESET_ALL} {sender} {Fore.LIGHTGREEN_EX}to{Style.RESET_ALL} {recipient} {Fore.LIGHTGREEN_EX}Successful!{Style.RESET_ALL}')
                    print(f'{Fore.LIGHTRED_EX}TX-ID :{Style.RESET_ALL} {txid}')
                
                # Log successful transfer
                log_result(sender, private_key_str, "success")
                return
                
            except Exception as tx_error:
                with lock:
                    print(f"Transaction Error: {tx_error}")
                
                if retries == max_retries:
                    # Log failed transfer after all retries
                    log_result(sender, private_key_str, "fail")
                    return
                
                retries += 1
                time.sleep(random.uniform(2, 5))  # Wait before retry
                
        except Exception as e:
            with lock:
                print(f"Error: {e}")
            
            if retries == max_retries:
                log_result(sender, private_key_str, "fail")
                return
            
            retries += 1
            time.sleep(random.uniform(2, 5))  # Wait before retry

def process_wallet(pvkeylist, index, total_wallets):
    try:
        sender = web3.eth.account.from_key(pvkeylist)
        TransferNative(sender.address, sender.key, recipient, index, total_wallets)
    except Exception as e:
        with lock:
            print(f"Error processing wallet: {e}")
        # Just log the private key
        log_result("Invalid_Address", pvkeylist, "fail")

def main():
    global recipient
    
    # Initialize log files
    initialize_logs()
    
    connect_web3()
    
    recipient = web3.to_checksum_address(input("Input Recipient Main EVM Address : "))
    num_threads = int(input("Enter the number of threads to use: "))
    max_retries = int(input("Enter maximum retries per transaction (recommended 3-5): "))
    
    with open('pvkeylist.txt', 'r') as file:
        local_data = file.read().splitlines()
    
    total_wallets = len(local_data)
    
    print(f"\nTotal wallets to process: {total_wallets}")
    print(f"Using {num_threads} threads")
    print(f"Max retries per transaction: {max_retries}")
    print("Starting transfers...\n")
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=num_threads) as executor:
        futures = [executor.submit(process_wallet, pvkeylist, index, total_wallets) 
                   for index, pvkeylist in enumerate(local_data, start=1)]
        
        concurrent.futures.wait(futures)
    
    # Print summary
    with open('log_success.txt', 'r') as f:
        success_count = len(f.readlines())
    with open('log_fail.txt', 'r') as f:
        fail_count = len(f.readlines())
    with open('log_empty.txt', 'r') as f:
        empty_count = len(f.readlines())
    
    print("\n" + "="*50)
    print(f"TRANSFER SUMMARY:")
    print(f"Successful transfers: {success_count}")
    print(f"Failed transfers: {fail_count}")
    print(f"Empty wallets: {empty_count}")
    print("="*50)

if __name__ == '__main__':
    main()
