import streamlit as st
import datetime
import hashlib
import base64
import hmac
import requests

# 1. 页面基础标题
st.title("DeepCode - PDF代码生成")

# 2. 从Streamlit Secrets读取讯飞配置
XUNFEI_APP_ID = st.secrets.get("XUNFEI_APP_ID", "")
XUNFEI_API_KEY = st.secrets.get("XUNFEI_API_KEY", "")
XUNFEI_API_SECRET = st.secrets.get("XUNFEI_API_SECRET", "")

# 3. 讯飞API调用函数
def call_xunfei(prompt):
    if not all([XUNFEI_APP_ID, XUNFEI_API_KEY, XUNFEI_API_SECRET]):
        return "", "❌ 讯飞配置不完整，请检查Secrets配置"
    
    host = "spark-api-open.xf-yun.com"
    path = "/v1/chat/completions"
    url = f"https://{host}{path}"

    # 生成UTC时间和签名
    now = datetime.datetime.now(datetime.timezone.utc)
    date = now.strftime("%a, %d %b %Y %H:%M:%S GMT")
    signature_origin = f"host: {host}\ndate: {date}\nPOST {path} HTTP/1.1"
    signature_sha = hmac.new(
        XUNFEI_API_SECRET.encode('utf-8'),
        signature_origin.encode('utf-8'),
        digestmod=hashlib.sha256
    ).digest()
    signature = base64.b64encode(signature_sha).decode('utf-8')

    # 构造Authorization头
    auth_str = (
        f'api_key="{XUNFEI_API_KEY}", '
        f'algorithm="hmac-sha256", '
        f'headers="host date request-line", '
        f'signature="{signature}"'
    )
    authorization = base64.b64encode(auth_str.encode('utf-8')).decode('utf-8')

    headers = {
        "Content-Type": "application/json",
        "Host": host,
        "Date": date,
        "Authorization": authorization
    }

    payload = {
        "app_id": XUNFEI_APP_ID,
        "model": "spark-pro",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.7,
        "max_tokens": 2048
    }

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=30)
        response.raise_for_status()
        result = response.json()
        
        if result.get("code") == 0 and result.get("choices"):
            return result["choices"][0]["message"]["content"], None
        else:
            return "", f"API返回错误：{result.get('message', '未知错误')}"
    except Exception as e:
        return "", f"请求异常：{str(e)}"

# 4. 核心交互组件（文件上传+生成按钮）
uploaded_file = st.file_uploader("📤 上传PDF文件", type="pdf")
generate_btn = st.button("🚀 生成代码", type="primary")

# 5. 按钮点击逻辑
if generate_btn:
    if not uploaded_file:
        st.warning("请先上传PDF文件！")
    else:
        # 读取PDF文件（简单处理，若需完整解析可补充PyPDF2依赖）
        st.info("正在读取PDF文件并调用讯飞API...")
        # 这里简化处理，实际可补充PDF文本提取逻辑
        prompt = f"基于以下PDF文件内容生成相关代码：{uploaded_file.name}"
        code_result, error = call_xunfei(prompt)
        
        if error:
            st.error(error)
        else:
            st.success("代码生成成功！")
            st.code(code_result, language="python")
