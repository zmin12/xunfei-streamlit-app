import streamlit as st
import requests
import PyPDF2
import json

# ===================== 页面基础配置 =====================
st.set_page_config(page_title="DeepCode - PDF代码生成", page_icon="🚀")
st.title("DeepCode - PDF代码生成")

# ===================== 核心函数 =====================
def extract_pdf_text(uploaded_file):
    """提取上传PDF文件的文本内容"""
    try:
        pdf_reader = PyPDF2.PdfReader(uploaded_file)
        text = ""
        for page in pdf_reader.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text.encode('utf-8', errors='ignore').decode('utf-8')
        return text, None
    except Exception as e:
        return "", f"PDF解析失败：{str(e)}"

def generate_code_from_pdf(pdf_text):
    """调用Hugging Face开源大模型生成代码（使用最新接口）"""
    hf_token = st.secrets.get("HUGGING_FACE_TOKEN", "")
    if not hf_token:
        return "", "❌ 请在Streamlit Secrets中配置HUGGING_FACE_TOKEN！"
    
    prompt = f"""
    请基于以下PDF内容，生成对应的可运行Python代码：
    PDF内容：
    {pdf_text[:2000]}
    
    生成要求：
    1. 代码语法完全正确，可直接复制运行
    2. 为关键逻辑添加详细注释
    3. 说明代码的功能和使用方法
    """.encode('utf-8').decode('utf-8')
    
    try:
        request_data = {
            "inputs": prompt,
            "parameters": {
                "temperature": 0.7,
                "max_new_tokens": 2048,
                "do_sample": True,
                "return_full_text": False
            },
            "model": "Qwen/Qwen-2-7B-Instruct"
        }
        
        # 使用最新的router.huggingface.co接口
        response = requests.post(
            url="https://router.huggingface.co/",
            headers={
                "Authorization": f"Bearer {hf_token}",
                "Content-Type": "application/json; charset=utf-8",
                "Accept": "application/json; charset=utf-8"
            },
            data=json.dumps(request_data, ensure_ascii=False).encode('utf-8'),
            timeout=60
        )
        
        response.encoding = 'utf-8'
        if response.status_code == 200:
            result = response.json()
            if "generated_text" in result:
                code_content = result["generated_text"].encode('utf-8').decode('utf-8')
                if "```python" in code_content:
                    code_content = code_content.split("```python")[1].split("```")[0]
                return code_content, None
            else:
                return "", f"模型返回格式异常：{str(result)}"
        elif response.status_code == 401:
            return "", "❌ Token无效或权限不足，请检查Token！"
        elif response.status_code == 503:
            return "", "⚠️ 模型暂时不可用，请1分钟后重试！"
        else:
            return "", f"调用失败：状态码{response.status_code}，响应：{response.text}"
    except requests.exceptions.Timeout:
        return "", "❌ 请求超时，免费模型响应较慢，请重试！"
    except Exception as e:
        return "", f"调用异常：{str(e)}"

# ===================== 页面交互 =====================
uploaded_file = st.file_uploader("📤 上传PDF文件", type="pdf")
generate_btn = st.button("🚀 生成代码", type="primary")

if generate_btn:
    if not uploaded_file:
        st.warning("⚠️ 请先上传PDF文件！")
    else:
        with st.spinner("🔍 正在解析PDF并生成代码...（免费模型响应较慢，请稍等）"):
            pdf_text, pdf_error = extract_pdf_text(uploaded_file)
            if pdf_error:
                st.error(pdf_error)
            else:
                if not pdf_text:
                    st.warning("⚠️ PDF中未提取到文本内容！")
                else:
                    code_result, api_error = generate_code_from_pdf(pdf_text)
                    if api_error:
                        st.error(api_error)
                    else:
                        st.success("✅ 代码生成成功！")
                        st.code(code_result, language="python")
