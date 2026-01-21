import streamlit as st
import openai
import PyPDF2  # 用于解析PDF内容

# 1. 页面基础配置
st.set_page_config(page_title="DeepCode - PDF代码生成", page_icon="🚀")
st.title("DeepCode - PDF代码生成")

# 2. 从Streamlit Secrets读取OpenAI API密钥
openai.api_key = st.secrets.get("OPENAI_API_KEY", "")

# 3. PDF文本提取函数
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

# 4. 调用OpenAI API生成代码
def generate_code_from_pdf(pdf_text):
    """调用OpenAI API基于PDF内容生成代码"""
    # 校验API密钥
    if not openai.api_key:
        return "", "❌ 请配置OpenAI API密钥（在Streamlit Secrets中设置OPENAI_API_KEY）"
    
    # 构造提示词
    prompt = f"""
    请基于以下PDF内容，生成对应的可运行代码：
    PDF内容：
    {pdf_text[:2000]}  # 限制文本长度，避免超出API令牌限制
    
    要求：
    1. 代码语法正确，可直接运行
    2. 给出详细的注释说明
    3. 说明代码的功能和使用方法
    """
    
    try:
        # 调用OpenAI的gpt-3.5-turbo模型
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=2048
        )
        return response.choices[0].message["content"], None
    except Exception as e:
        return "", f"API调用失败：{str(e)}"

# 5. 核心交互组件
uploaded_file = st.file_uploader("📤 上传PDF文件", type="pdf")
generate_btn = st.button("🚀 生成代码", type="primary")

# 6. 按钮点击逻辑
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
                    # 生成代码
                    code_result, api_error = generate_code_from_pdf(pdf_text)
                    if api_error:
                        st.error(api_error)
                    else:
                        st.success("✅ 代码生成成功！")
                        st.code(code_result, language="python")
