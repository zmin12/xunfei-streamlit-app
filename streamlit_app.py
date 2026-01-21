# streamlit_app.py 顶部的导入区
import os
import datetime
import hashlib
import base64
import hmac
import requests


# 替换原来的.env读取代码，用Streamlit secrets获取配置
import streamlit as st

XUNFEI_APP_ID = st.secrets["XUNFEI_APP_ID"]
XUNFEI_API_KEY = st.secrets["XUNFEI_API_KEY"]
XUNFEI_API_SECRET = st.secrets["XUNFEI_API_SECRET"]

# ===================== 完整的call_xunfei函数 =====================
def call_xunfei(prompt):
    """
    调用讯飞Spark Pro API（严格按官方鉴权规范）
    参数: prompt - 发给大模型的提示词
    返回: (生成内容, 错误信息)
    """
    # 1. 固定配置（Spark Pro官方地址，一字不能改）
    host = "spark-api-open.xf-yun.com"
    path = "/v1/chat/completions"
    url = f"https://{host}{path}"

    # 2. 生成UTC时间（讯飞强制要求，格式不能错）
    now = datetime.datetime.now(datetime.timezone.utc)
    date = now.strftime("%a, %d %b %Y %H:%M:%S GMT")  # 必须是GMT格式

    # 3. 构造签名原始串（官方强制格式，顺序/换行/空格都不能改）
    signature_origin = f"host: {host}\ndate: {date}\nPOST {path} HTTP/1.1"
    
    # 4. 计算HMAC-SHA256签名（编码必须是utf-8，不能省略）
    signature_sha = hmac.new(
        XUNFEI_API_SECRET.encode('utf-8'),
        signature_origin.encode('utf-8'),
        digestmod=hashlib.sha256
    ).digest()
    signature = base64.b64encode(signature_sha).decode('utf-8')

    # 5. 构造Authorization头（headers参数必须包含host，顺序不能改）
    auth_str = (
        f'api_key="{XUNFEI_API_KEY}", '
        f'algorithm="hmac-sha256", '
        f'headers="host date request-line", '  # 必须包含host，和签名串对应
        f'signature="{signature}"'
    )
    authorization = base64.b64encode(auth_str.encode('utf-8')).decode('utf-8')

    # 6. 请求头（Host必须和签名中的host完全一致）
    headers = {
        "Content-Type": "application/json",
        "Host": host,
        "Date": date,
        "Authorization": authorization
    }

    # 7. 请求体（Spark Pro格式，model必须是spark-pro）
    payload = {
        "app_id": XUNFEI_APP_ID,
        "model": "spark-pro",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.7,
        "max_tokens": 2048
    }

    # 8. 发送请求（捕获所有可能的错误）
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=30)
        response.raise_for_status()
        result = response.json()
        
        if result.get("code") == 0 and result.get("choices"):
            return result["choices"][0]["message"]["content"], None
        else:
            return "", f"API返回错误：{result.get('message', '未知错误')}"
    
    except requests.exceptions.HTTPError as e:
        return "", f"401鉴权失败？核对配置！错误详情：{e.response.status_code} - {e.response.text}"
    except Exception as e:

        return "", f"请求异常：{str(e)}"

