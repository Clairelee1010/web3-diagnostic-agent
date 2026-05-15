import os
import re
import requests
import streamlit as st
from groq import Groq

GROQ_API_KEY = st.secrets.get("GROQ_API_KEY", os.environ.get("GROQ_API_KEY", ""))
ETHERSCAN_API_KEY = st.secrets.get("ETHERSCAN_API_KEY", os.environ.get("ETHERSCAN_API_KEY", ""))
ETHERSCAN_BASE = "https://api.etherscan.io/v2/api"

client = Groq(api_key=GROQ_API_KEY)

# ── Web3 診斷工具函數 ──────────────────────────────────────

def check_transaction(tx_hash: str) -> str:
    try:
        resp = requests.get(ETHERSCAN_BASE, params={
            "chainid": "1", "module": "proxy",
            "action": "eth_getTransactionReceipt",
            "txhash": tx_hash, "apikey": ETHERSCAN_API_KEY
        }, timeout=10)
        data = resp.json()
        result = data.get("result")
        if not result:
            return f"Transaction {tx_hash[:16]}... not found. It may still be pending or the hash is incorrect."
        status = result.get("status")
        block = int(result.get("blockNumber", "0x0"), 16)
        gas_used = int(result.get("gasUsed", "0x0"), 16)
        if status == "0x1":
            return (f"Transaction Status: SUCCESS\n"
                    f"Block Number: {block}\n"
                    f"Gas Used: {gas_used:,}\n"
                    f"The transaction was confirmed successfully.")
        elif status == "0x0":
            return (f"Transaction Status: FAILED\n"
                    f"Block Number: {block}\n"
                    f"Gas Used: {gas_used:,}\n"
                    f"The transaction was reverted. Common reasons: insufficient gas, slippage too high, or insufficient token allowance.")
        else:
            return f"Transaction found but status unknown. Raw status: {status}"
    except Exception as e:
        return f"Error checking transaction: {e}"


def check_token_balance(address: str) -> str:
    try:
        resp = requests.get(ETHERSCAN_BASE, params={
            "chainid": "1", "module": "account",
            "action": "balance", "address": address,
            "tag": "latest", "apikey": ETHERSCAN_API_KEY
        }, timeout=10)
        data = resp.json()
        result = data.get("result")
        if not result:
            return f"Could not retrieve balance for {address[:16]}..."
        eth_balance = int(result) / 1e18
        return (f"Wallet Address: {address}\n"
                f"ETH Balance: {eth_balance:.6f} ETH\n"
                f"Note: ETH balance does not include ERC-20 tokens. "
                f"To see tokens, import the token contract address in your wallet.")
    except Exception as e:
        return f"Error checking balance: {e}"


def check_erc20_tokens(address: str) -> str:
    try:
        resp = requests.get(ETHERSCAN_BASE, params={
            "chainid": "1", "module": "account",
            "action": "tokentx", "address": address,
            "startblock": 0, "endblock": 99999999,
            "page": 1, "offset": 5, "sort": "desc",
            "apikey": ETHERSCAN_API_KEY
        }, timeout=10)
        data = resp.json()
        result = data.get("result", [])
        if not isinstance(result, list) or not result:
            return f"No ERC-20 token transfers found for {address[:16]}..."
        lines = [f"Recent ERC-20 Token Transfers for {address[:16]}...:"]
        for tx in result[:5]:
            symbol = tx.get("tokenSymbol", "Unknown")
            name = tx.get("tokenName", "Unknown")
            decimals = int(tx.get("tokenDecimal", 18))
            value = int(tx.get("value", 0)) / (10 ** decimals)
            from_addr = tx.get("from", "")[:16]
            to_addr = tx.get("to", "")[:16]
            contract = tx.get("contractAddress", "")
            lines.append(f"- {symbol} ({name}): {value:.4f}")
            lines.append(f"  From: {from_addr}... To: {to_addr}...")
            lines.append(f"  Contract: {contract}")
        lines.append("\nIf tokens are not visible in your wallet, import the contract address shown above.")
        return "\n".join(lines)
    except Exception as e:
        return f"Error checking token transfers: {e}"


def detect_and_run_tools(user_message: str) -> str:
    tool_results = []
    tx_hashes = re.findall(r"0x[a-fA-F0-9]{64}", user_message)
    addresses = re.findall(r"0x[a-fA-F0-9]{40}(?![a-fA-F0-9])", user_message)
    for tx in tx_hashes:
        result = check_transaction(tx)
        tool_results.append(f"[Transaction Check]\n{result}")
    for addr in addresses:
        if addr not in [t[:42] for t in tx_hashes]:
            balance_result = check_token_balance(addr)
            token_result = check_erc20_tokens(addr)
            tool_results.append(f"[Wallet Balance]\n{balance_result}")
            tool_results.append(f"[Token History]\n{token_result}")
    return "\n\n".join(tool_results) if tool_results else ""


SYSTEM_PROMPT = """You are a senior Web3 Customer Success technical consultant specializing in diagnosing wallet and token issues.

Your capabilities:
1. Check transaction status (success/failed/pending) using transaction hashes
2. Check wallet ETH balance and ERC-20 token history
3. Diagnose common Web3 issues

Common issues you handle:
- "My tokens disappeared" → Check if transaction succeeded, guide user to import token contract
- "Transaction failed" → Explain revert reasons (gas, slippage, allowance)
- "I sent tokens but wallet shows nothing" → Check transaction + guide token import
- "Swap failed on Uniswap/DEX" → Diagnose slippage, gas, or approval issues
- "Wrong network" → Guide network switching in MetaMask

Response style:
- Be concise and professional
- Use plain language, avoid excessive jargon
- Always end with a clear "Next Step" recommendation
- If tool data is provided, analyze it and explain what it means for the user
- If no tool data, ask for the transaction hash or wallet address to diagnose

Language: Respond in the same language as the user (Chinese or English)."""

# ── Streamlit UI ──────────────────────────────────────────

st.set_page_config(
    page_title="Web3 診斷 AI 客服",
    page_icon="🤖",
    layout="centered"
)

st.markdown("""
<style>
  .header-box {
    background: linear-gradient(135deg, #0A2342 0%, #1B4F8A 100%);
    padding: 20px 28px; border-radius: 10px; margin-bottom: 20px; color: white;
  }
  .header-box h1 { font-size: 20px; margin: 0; font-weight: 700; }
  .header-box p  { font-size: 13px; margin: 4px 0 0; opacity: 0.8; }
  .tool-badge {
    background: #1B4F8A; color: #FFD700; padding: 3px 10px;
    border-radius: 20px; font-size: 11px; font-weight: 600;
    display: inline-block; margin-top: 8px;
  }
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="header-box">
  <h1>🤖 Web3 Diagnostic AI Agent</h1>
  <p>Wallet · Token · Transaction · Swap Issues — Instant Diagnosis</p>
  <span class="tool-badge">Powered by Groq LLaMA + Etherscan</span>
</div>
""", unsafe_allow_html=True)

# 側邊欄
with st.sidebar:
    st.markdown("### 🚀 快速測試")
    st.markdown("點擊下方按鈕直接測試：")

    if st.button("💸 代幣轉了沒看到", use_container_width=True):
        st.session_state.quick_input = "我轉了代幣但錢包沒看到，交易是 0x5ed67f77ab4d242e81c8b20b55a06e2fb04c2f0b6c0a97fbf1e2614de51d852b7"

    if st.button("❌ 交易失敗怎麼辦", use_container_width=True):
        st.session_state.quick_input = "我的 Swap 交易失敗了，hash 是 0x462407e84d8a3df988a79e1fa1dc68cc8c3a6b9e5413087b7f4c1a9f912089a8"

    if st.button("💼 查詢錢包餘額", use_container_width=True):
        st.session_state.quick_input = "幫我查這個地址的餘額：0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045"

    if st.button("🔴 代幣不見了", use_container_width=True):
        st.session_state.quick_input = "我的 USDT 不見了，我的錢包地址是 0x722122dF12D4e14e13Ac3b6895a86e84145b6967"

    if st.button("⛽ Gas 費太高怎麼辦", use_container_width=True):
        st.session_state.quick_input = "Gas fee 很貴，我要怎麼省 Gas？"

    if st.button("🔄 MetaMask 切換網路", use_container_width=True):
        st.session_state.quick_input = "我的 MetaMask 顯示錯誤網路，怎麼切換到 Ethereum mainnet？"

    st.divider()
    st.markdown("### 這個 Agent 能做什麼")
    st.markdown("""
- ✅ 查交易是否成功
- ✅ 查錢包 ETH 餘額
- ✅ 查 ERC-20 代幣紀錄
- ✅ 診斷 Swap 失敗原因
- ✅ 引導代幣匯入步驟
- ✅ 解釋 Gas / Slippage
- ✅ MetaMask 網路切換
    """)
    st.divider()
    st.caption("Data: Etherscan API | AI: Groq LLaMA 3.1")
    if st.button("🗑️ 清除對話", use_container_width=True):
        st.session_state.messages = []
        st.rerun()

# 初始化對話
if "messages" not in st.session_state:
    st.session_state.messages = []
    st.session_state.messages.append({
        "role": "assistant",
        "content": (
            "你好！我是 Web3 診斷 AI 客服 👋\n\n"
            "請告訴我你遇到的問題，或直接提供：\n"
            "- **交易 Hash**（0x + 64位）→ 我幫你查交易狀態\n"
            "- **錢包地址**（0x + 40位）→ 我幫你查餘額和代幣\n\n"
            "常見問題：代幣消失、交易失敗、Swap 卡住、Gas 費問題、網路切換。"
        )
    })

# 快速輸入處理
if "quick_input" in st.session_state:
    quick = st.session_state.pop("quick_input")
    st.session_state.messages.append({"role": "user", "content": quick})

# 顯示對話歷史
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# 輸入框
if prompt := st.chat_input("輸入問題、交易 Hash 或錢包地址..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("診斷中..."):
            tool_data = detect_and_run_tools(prompt)
            messages_for_llm = [{"role": "system", "content": SYSTEM_PROMPT}]
            for m in st.session_state.messages[:-1]:
                messages_for_llm.append({"role": m["role"], "content": m["content"]})
            user_content = prompt
            if tool_data:
                user_content += f"\n\n[Diagnostic Tool Results]:\n{tool_data}"
            messages_for_llm.append({"role": "user", "content": user_content})
            try:
                response = client.chat.completions.create(
                    model="llama-3.1-8b-instant",
                    messages=messages_for_llm,
                    temperature=0.3,
                    max_tokens=1000,
                )
                reply = response.choices[0].message.content
            except Exception as e:
                reply = f"抱歉，AI 回覆時發生錯誤：{e}\n請稍後再試。"

            st.markdown(reply)
            st.session_state.messages.append({"role": "assistant", "content": reply})
