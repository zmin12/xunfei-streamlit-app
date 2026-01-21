import streamlit as st
import requests
import datetime
import hashlib
import base64
import hmac
import json
import PyPDF2

# ===================== 核心配置 =====================
# 页面基础设置
st.set_page_config(page_title="DeepCode - PDF代码生成", page_icon="🚀")
st.title("DeepCode - PDF代码生成")

# 从Streamlit Secrets读取讯飞配置
XUNFEI_APP_ID = st.secrets.get("XUNFEI_APP_ID", "")
XUNFEI_API_KEY = st.secrets.get("XUNFEI_API_KEY", "")
XUNFEI_API_SECRET = st.secrets.get("XUNFEI_API_SECRET", "")

# ===================== 工具函数 =====================
def extract_pdf_text(uploaded_file):
    """提取PDF文本内容"""
    try:
        pdf_reader = PyPDF2.PdfReader(uploaded_file)
        text = ""
        for page in pdf_reader.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text
        return text, None
    except Exception as e:
        return "", f"PDF解析失败：{str(e)}"

def get_ws_auth_url():
    """生成讯飞API的鉴权URL（修复401核心）"""
    if not all([XUNFEI_APP_ID, XUNFEI_API_KEY, XUNFEI_API_SECRET]):
        return "", "❌ 讯飞配置不完整，请检查Secrets中的APP_ID/API_KEY/API_SECRET"
    
    # 1. 生成时间戳
    now = datetime.datetime.now(datetime.timezone.utc)
    date = now.strftime("%a, %d %b %Y %H:%M:%S GMT")
    
    # 2. 构造签名原始串
    signature_origin = f"host: spark-api.xf-yun.com\ndate: {date}\nGET /v1.1/chat HTTP/1.1"
    
    # 3. HMAC-SHA256签名
    signature_sha = hmac.new(XUNFEI_API_SECRET.encode('utf-8'), 
                             signature_origin.encode('utf-8'), 
                             digestmod=hashlib.sha256).digest()
    signature_b64 = base64.b64encode(signature_sha).decode('utf-8')
    
    # 4. 构造Authorization
    authorization_origin = f'api_key="{XUNFEI_API_KEY}", algorithm="hmac-sha256", headers="host date request-line", signature="{signature_b64}"'
    authorization_b64 = base64.b64encode(authorization_origin.encode('utf-8')).decode('utf-8')
    
    # 5. 拼接最终URL
    url = f"wss://spark-api.xf-yun.com/v1.1/chat?authorization={authorization_b64}&date={date}&host=spark-api.xf-yun.com"
    return url, None

def call_xunfei_api(pdf_text):
    """调用讯飞星火API生成代码"""
    # 1. 获取鉴权URL
    auth_url, auth_error = get_ws_auth_url()
    if auth_error:
        return "", auth_error
    
    # 2. 构造请求数据
    messages = [
        {
            "role": "user",
            "content": f"""基于以下PDF内容生成可运行的代码：
            {pdf_text[:2000]}
            要求：
            1. 代码语法正确，可直接运行
            2. 附带详细注释
            3. 说明代码功能和使用方法
            """
        }
    ]
    
    data = {
        "header": {
            "app_id": XUNFEI_APP_ID,
            "uid": "deepcode_user"
        },
        "parameter": {
            "chat": {
                "domain": "general",
                "temperature": 0.7,
                "max_tokens": 2048
            }
        },
        "payload": {
            "message": {
                "text": messages
            }
        }
    }
    
    # 3. 发送请求（使用HTTP接口兼容WS，降低复杂度）
    try:
        # 改用HTTP接口（比WebSocket更稳定，适合新手）
        response = requests.post(
            url="https://spark-api.xf-yun.com/v1.1/chat",
            headers={
                "Content-Type": "application/json",
                "Authorization": auth_url.split("?")[1].split("&")[0].split("=")[1],
                "Date": auth_url.split("&")[1].split("=")[1],
                "Host": "spark-api.xf-yun.com"
            },
            json=data,
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            if result.get("header", {}).get("code") == 0:
                code_content = result["payload"]["choices"]["text"][0]["content"]
                return code_content, None
            else:
                return "", f"讯飞API返回错误：{result.get('header', {}).get('message', '未知错误')}"
        else:
            return "", f"API请求失败，状态码：{response.status_code}，响应：{response.text}"
    except Exception as e:
        return "", f"API调用异常：{str(e)}"

# ===================== 页面交互 =====================
# 1. 文件上传
uploaded_file = st.file_uploader("📤 上传PDF文件", type="pdf")

# 2. 生成按钮
generate_btn = st.button("🚀 生成代码", type="primary")

# 3. 按钮点击逻辑
if generate_btn:
    if not uploaded_file:
        st.warning("⚠️ 请先上传PDF文件！")
    else:
        with st.spinner("🔍 正在解析PDF并生成代码..."):
            # 提取PDF文本
            pdf_text, pdf_error = extract_pdf_text(uploaded_file)
            if pdf_error:
                st.error(pdf_error)
            else:
                if not pdf_text:
                    st.warning("⚠️ PDF中未提取到文本内容！")
                else:
                    # 调用讯飞API
                    code_result, api_error = call_xunfei_api(pdf_text)
                    if api_error:
                        st.error(api_error)
                    else:
                        st.success("✅ 代码生成成功！")
                        st.code(code_result, language="python")
