with open("app.py", "w") as f:
    f.write('''
import os
import re
import requests
import streamlit as st
from groq import Groq

GROQ_API_KEY = st.secrets.get("GROQ_API_KEY", os.environ.get("GROQ_API_KEY", ""))
ETHERSCAN_API_KEY = st.secrets.get("ETHERSCAN_API_KEY", os.environ.get("ETHERSCAN_API_KEY", ""))
ETHERSCAN_BASE = "https://api.etherscan.io/v2/api"
client = Groq(api_key=GROQ_API_KEY)

# ── 多語言文字設定 ────────────────────────────────────────
LANG = {
    "zh": {
        "title": "Web3 診斷 AI 客服",
        "subtitle": "錢包 · 代幣 · 交易 · Swap 問題 — 即時診斷",
        "badge": "由 Groq LLaMA + Etherscan 驅動",
        "quick_title": "🚀 快速測試",
        "quick_desc": "點擊下方按鈕直接測試：",
        "btn1": "💸 代幣轉了沒看到",
        "btn2": "❌ 交易失敗怎麼辦",
        "btn3": "💼 查詢錢包餘額",
        "btn4": "🔴 代幣不見了",
        "btn5": "⛽ Gas 費太高怎麼辦",
        "btn6": "🔄 MetaMask 切換網路",
        "cap_title": "這個 Agent 能做什麼",
        "caps": ["✅ 查交易是否成功","✅ 查錢包 ETH 餘額","✅ 查 ERC-20 代幣紀錄",
                 "✅ 診斷 Swap 失敗原因","✅ 引導代幣匯入步驟","✅ 解釋 Gas / Slippage","✅ MetaMask 網路切換"],
        "clear": "🗑️ 清除對話",
        "placeholder": "輸入問題、交易 Hash 或錢包地址...",
        "spinner": "診斷中...",
        "welcome": "你好！我是 Web3 診斷 AI 客服 👋\n\n請告訴我你遇到的問題，或直接提供：\n- **交易 Hash**（0x + 64位）→ 查交易狀態\n- **錢包地址**（0x + 40位）→ 查餘額和代幣\n\n常見問題：代幣消失、交易失敗、Swap 卡住、Gas 費問題。",
        "q1": "我轉了代幣但錢包沒看到，交易是 0x5ed67f77ab4d242e81c8b20b55a06e2fb04c2f0b6c0a97fbf1e2614de51d852b7",
        "q2": "我的 Swap 交易失敗了，hash 是 0x462407e84d8a3df988a79e1fa1dc68cc8c3a6b9e5413087b7f4c1a9f912089a8",
        "q3": "幫我查這個地址的餘額：0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045",
        "q4": "我的 USDT 不見了，我的錢包地址是 0x722122dF12D4e14e13Ac3b6895a86e84145b6967",
        "q5": "Gas fee 很貴，我要怎麼省 Gas？",
        "q6": "我的 MetaMask 顯示錯誤網路，怎麼切換到 Ethereum mainnet？",
        "error": "抱歉，AI 回覆時發生錯誤：{e}\n請稍後再試。",
        "lang_toggle": "🌐 Switch to English",
    },
    "en": {
        "title": "Web3 Diagnostic AI Agent",
        "subtitle": "Wallet · Token · Transaction · Swap Issues — Instant Diagnosis",
        "badge": "Powered by Groq LLaMA + Etherscan",
        "quick_title": "🚀 Quick Test",
        "quick_desc": "Click a button to test instantly:",
        "btn1": "💸 Sent tokens but not visible",
        "btn2": "❌ Transaction failed",
        "btn3": "💼 Check wallet balance",
        "btn4": "🔴 Tokens disappeared",
        "btn5": "⛽ Gas fee too high",
        "btn6": "🔄 Switch MetaMask network",
        "cap_title": "What This Agent Can Do",
        "caps": ["✅ Check transaction status","✅ Check ETH balance","✅ Check ERC-20 token history",
                 "✅ Diagnose Swap failures","✅ Guide token import","✅ Explain Gas / Slippage","✅ MetaMask network switching"],
        "clear": "🗑️ Clear chat",
        "placeholder": "Enter question, Transaction Hash, or wallet address...",
        "spinner": "Diagnosing...",
        "welcome": "Hi! I am your Web3 Diagnostic AI Agent 👋\\n\\nTell me your issue or provide:\\n- **Transaction Hash** (0x + 64 chars) → Check transaction status\\n- **Wallet Address** (0x + 40 chars) → Check balance and tokens\\n\\nCommon issues: tokens missing, failed transaction, Swap stuck, Gas fee problems.",
        "q1": "I sent tokens but they are not showing in my wallet. Tx: 0x5ed67f77ab4d242e81c8b20b55a06e2fb04c2f0b6c0a97fbf1e2614de51d852b7",
        "q2": "My Swap transaction failed. Hash: 0x462407e84d8a3df988a79e1fa1dc68cc8c3a6b9e5413087b7f4c1a9f912089a8",
        "q3": "Check balance for this address: 0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045",
        "q4": "My USDT disappeared. Wallet: 0x722122dF12D4e14e13Ac3b6895a86e84145b6967",
        "q5": "Gas fees are very expensive. How can I save on Gas?",
        "q6": "MetaMask shows wrong network. How do I switch to Ethereum mainnet?",
        "error": "Sorry, an error occurred: {e}\\nPlease try again.",
        "lang_toggle": "🌐 切換為中文",
    }
}

SYSTEM_PROMPT = """You are a senior Web3 Customer Success technical consultant specializing in diagnosing wallet and token issues.
Your capabilities: check transaction status, check wallet balance and ERC-20 tokens, diagnose Web3 issues.
Common issues: tokens disappeared, transaction failed, Swap failed, Gas too high, wrong network.
Response style: concise, professional, plain language, always end with a Next Step recommendation.
Language: Respond in the same language as the user (Chinese or English)."""

# ── 工具函數 ──────────────────────────────────────────────
def check_transaction(tx_hash):
    try:
        resp = requests.get(ETHERSCAN_BASE, params={
            "chainid":"1","module":"proxy","action":"eth_getTransactionReceipt",
            "txhash":tx_hash,"apikey":ETHERSCAN_API_KEY}, timeout=10)
        result = resp.json().get("result")
        if not result:
            return f"Transaction {tx_hash[:16]}... not found. May be pending or hash is incorrect."
        status = result.get("status")
        block = int(result.get("blockNumber","0x0"),16)
        gas = int(result.get("gasUsed","0x0"),16)
        if status=="0x1":
            return f"Status: SUCCESS | Block: {block} | Gas Used: {gas:,}\nTransaction confirmed successfully."
        elif status=="0x0":
            return f"Status: FAILED | Block: {block} | Gas Used: {gas:,}\nTransaction reverted. Common causes: insufficient gas, high slippage, or insufficient allowance."
        return f"Status unknown: {status}"
    except Exception as e:
        return f"Error: {e}"

def check_balance(address):
    try:
        resp = requests.get(ETHERSCAN_BASE, params={
            "chainid":"1","module":"account","action":"balance",
            "address":address,"tag":"latest","apikey":ETHERSCAN_API_KEY}, timeout=10)
        result = resp.json().get("result")
        if not result: return f"Cannot retrieve balance for {address[:16]}..."
        eth = int(result)/1e18
        return f"Address: {address}\nETH Balance: {eth:.6f} ETH\nNote: This does not include ERC-20 tokens. Import token contract address to see tokens."
    except Exception as e:
        return f"Error: {e}"

def check_tokens(address):
    try:
        resp = requests.get(ETHERSCAN_BASE, params={
            "chainid":"1","module":"account","action":"tokentx",
            "address":address,"page":1,"offset":5,"sort":"desc","apikey":ETHERSCAN_API_KEY}, timeout=10)
        result = resp.json().get("result",[])
        if not isinstance(result,list) or not result:
            return f"No ERC-20 transfers found for {address[:16]}..."
        lines=[f"Recent ERC-20 transfers for {address[:16]}...:"]
        for tx in result[:5]:
            sym=tx.get("tokenSymbol","?"); dec=int(tx.get("tokenDecimal",18))
            val=int(tx.get("value",0))/(10**dec); contract=tx.get("contractAddress","")
            lines.append(f"- {sym}: {val:.4f} | Contract: {contract}")
        lines.append("Import the contract address above to see tokens in your wallet.")
        return "\n".join(lines)
    except Exception as e:
        return f"Error: {e}"

def run_tools(msg):
    results=[]
    txs=re.findall(r"0x[a-fA-F0-9]{64}",msg)
    addrs=re.findall(r"0x[a-fA-F0-9]{40}(?![a-fA-F0-9])",msg)
    for tx in txs:
        results.append(f"[Transaction Check]\n{check_transaction(tx)}")
    for addr in addrs:
        if addr not in [t[:42] for t in txs]:
            results.append(f"[Wallet Balance]\n{check_balance(addr)}")
            results.append(f"[Token History]\n{check_tokens(addr)}")
    return "\n\n".join(results)

# ── UI ────────────────────────────────────────────────────
st.set_page_config(page_title="Web3 AI Agent", page_icon="🤖", layout="centered")

if "lang" not in st.session_state:
    st.session_state.lang = "zh"
if "messages" not in st.session_state:
    st.session_state.messages = []

L = LANG[st.session_state.lang]

st.markdown("""
<style>
.header-box{background:linear-gradient(135deg,#0A2342,#1B4F8A);padding:20px 28px;border-radius:10px;margin-bottom:20px;color:white}
.header-box h1{font-size:20px;margin:0;font-weight:700}
.header-box p{font-size:13px;margin:4px 0 0;opacity:.8}
.badge{background:#1B4F8A;color:#FFD700;padding:3px 10px;border-radius:20px;font-size:11px;font-weight:600;display:inline-block;margin-top:8px}
</style>
""", unsafe_allow_html=True)

st.markdown(f"""
<div class="header-box">
  <h1>🤖 {L["title"]}</h1>
  <p>{L["subtitle"]}</p>
  <span class="badge">{L["badge"]}</span>
</div>
""", unsafe_allow_html=True)

with st.sidebar:
    if st.button(L["lang_toggle"], use_container_width=True):
        st.session_state.lang = "en" if st.session_state.lang == "zh" else "zh"
        st.session_state.messages = []
        st.rerun()

    st.markdown(f"### {L['quick_title']}")
    st.markdown(L["quick_desc"])

    for key, btn_label in [("q1",L["btn1"]),("q2",L["btn2"]),("q3",L["btn3"]),
                            ("q4",L["btn4"]),("q5",L["btn5"]),("q6",L["btn6"])]:
        if st.button(btn_label, use_container_width=True):
            st.session_state.quick_input = L[key]

    st.divider()
    st.markdown(f"### {L['cap_title']}")
    for cap in L["caps"]:
        st.markdown(cap)
    st.divider()
    st.caption("Etherscan API | Groq LLaMA 3.1")
    if st.button(L["clear"], use_container_width=True):
        st.session_state.messages = []
        st.rerun()

if not st.session_state.messages:
    st.session_state.messages.append({"role":"assistant","content":L["welcome"]})

if "quick_input" in st.session_state:
    quick = st.session_state.pop("quick_input")
    st.session_state.messages.append({"role":"user","content":quick})

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

if prompt := st.chat_input(L["placeholder"]):
    st.session_state.messages.append({"role":"user","content":prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner(L["spinner"]):
            tool_data = run_tools(prompt)
            msgs = [{"role":"system","content":SYSTEM_PROMPT}]
            for m in st.session_state.messages[:-1]:
                msgs.append({"role":m["role"],"content":m["content"]})
            content = prompt + (f"\n\n[Tool Results]:\n{tool_data}" if tool_data else "")
            msgs.append({"role":"user","content":content})
            try:
                resp = client.chat.completions.create(
                    model="llama-3.1-8b-instant", messages=msgs,
                    temperature=0.3, max_tokens=1000)
                reply = resp.choices[0].message.content
            except Exception as e:
                reply = L["error"].format(e=e)
            st.markdown(reply)
            st.session_state.messages.append({"role":"assistant","content":reply})
''')
print("✅ app.py 完成")
