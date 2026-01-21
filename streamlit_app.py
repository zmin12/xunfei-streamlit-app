import streamlit as st
import requests
import PyPDF2

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
                text += page_text
        return text, None
    except Exception as e:
        return "", f"PDF解析失败：{str(e)}"

def generate_code_from_pdf(pdf_text, hf_token):
    """调用Hugging Face开源大模型生成代码"""
    # 校验Token
    if not hf_token or hf_token == "你的Hugging Face Token":
        return "", "❌ 请先替换代码中的Hugging Face Token！"
    
    # 构造生成代码的提示词
    prompt = f"""
    请基于以下PDF内容，生成对应的可运行Python代码：
    PDF内容：
    {pdf_text[:2000]}  # 限制长度避免超出模型上下文
    
    生成要求：
    1. 代码语法完全正确，可直接复制运行
    2. 为关键逻辑添加详细注释
    3. 说明代码的功能和使用方法
    """
    
    try:
        # 调用Qwen-2-7B-Instruct开源模型（免费、稳定）
        response = requests.post(
            url="https://api-inference.huggingface.co/models/Qwen/Qwen-2-7B-Instruct",
            headers={
                "Authorization": f"Bearer {hf_token}",
                "Content-Type": "application/json"
            },
            json={
                "inputs": prompt,
                "parameters": {
                    "temperature": 0.7,  # 生成多样性
                    "max_new_tokens": 2048,  # 最大生成长度
                    "do_sample": True
                }
            },
            timeout=60  # 延长超时时间，适配免费模型响应速度
        )
        
        # 处理响应结果
        if response.status_code == 200:
            result = response.json()
            if isinstance(result, list) and len(result) > 0:
                code_content = result[0]["generated_text"]
                # 清理多余的提示词内容，只保留代码部分
                if "```python" in code_content:
                    code_content = code_content.split("```python")[1].split("```")[0]
                return code_content, None
            else:
                return "", f"模型返回格式异常：{result}"
        elif response.status_code == 401:
            return "", "❌ Token无效或权限不足，请检查Token是否正确！"
        elif response.status_code == 503:
            return "", "⚠️ 模型暂时不可用，请1分钟后重试！"
        else:
            return "", f"调用失败：状态码{response.status_code}，响应：{response.text}"
    except requests.exceptions.Timeout:
        return "", "❌ 请求超时，免费模型响应较慢，请重试！"
    except Exception as e:
        return "", f"调用异常：{str(e)}"

# ===================== 页面交互 =====================
# 1. 替换这里的Token！！！
YOUR_HF_TOKEN = "hf_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"  # 把这里替换成你的Token

# 2. 文件上传组件
uploaded_file = st.file_uploader("📤 上传PDF文件", type="pdf")

# 3. 生成代码按钮
generate_btn = st.button("🚀 生成代码", type="primary")

# 4. 按钮点击逻辑
if generate_btn:
    if not uploaded_file:
        st.warning("⚠️ 请先上传PDF文件！")
    else:
        with st.spinner("🔍 正在解析PDF并生成代码...（免费模型响应较慢，请稍等）"):
            # 提取PDF文本
            pdf_text, pdf_error = extract_pdf_text(uploaded_file)
            if pdf_error:
                st.error(pdf_error)
            else:
                if not pdf_text:
                    st.warning("⚠️ PDF中未提取到文本内容！")
                else:
                    # 调用模型生成代码
                    code_result, api_error = generate_code_from_pdf(pdf_text, YOUR_HF_TOKEN)
                    if api_error:
                        st.error(api_error)
                    else:
                        st.success("✅ 代码生成成功！")
                        st.code(code_result, language="python")
