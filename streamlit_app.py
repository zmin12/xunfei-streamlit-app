import streamlit as st
from transformers import pipeline, AutoTokenizer, AutoModelForCausalLM
import PyPDF2
import torch

# ===================== 页面基础配置 =====================
st.set_page_config(page_title="DeepCode - PDF代码生成", page_icon="🚀")
st.title("DeepCode - PDF代码生成")

# ===================== 加载本地模型（首次运行自动下载） =====================
@st.cache_resource
def load_model():
    try:
        # 使用轻量级开源模型（适合Streamlit Cloud资源）
        model_name = "distilgpt2"
        tokenizer = AutoTokenizer.from_pretrained(model_name)
        model = AutoModelForCausalLM.from_pretrained(model_name)
        
        # 添加pad token（distilgpt2默认没有）
        tokenizer.pad_token = tokenizer.eos_token
        
        # 初始化文本生成pipeline
        generator = pipeline(
            "text-generation",
            model=model,
            tokenizer=tokenizer,
            device_map="auto",  # 自动使用GPU（如果可用）
            max_new_tokens=1024,
            temperature=0.7,
            do_sample=True
        )
        return generator, None
    except Exception as e:
        return None, f"模型加载失败：{str(e)}"

# ===================== 核心函数 =====================
def extract_pdf_text(uploaded_file):
    """提取PDF文本内容"""
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

def generate_code_from_pdf(pdf_text, generator):
    """使用本地模型生成代码"""
    if not generator:
        return "", "❌ 模型加载失败，请刷新页面重试！"
    
    if not pdf_text:
        return "", "⚠️ PDF中未提取到文本内容！"
    
    # 构造提示词
    prompt = f"""
    基于以下PDF内容生成可运行的Python代码：
    {pdf_text[:1000]}  # 限制长度适配模型
    
    要求：
    1. 代码语法正确
    2. 带详细注释
    3. 说明功能
    """
    
    try:
        # 生成代码
        result = generator(
            prompt,
            max_new_tokens=1024,
            temperature=0.7,
            top_p=0.95,
            repetition_penalty=1.1
        )
        
        # 提取生成的代码
        code_content = result[0]["generated_text"].split(prompt)[-1]
        if "```python" in code_content:
            code_content = code_content.split("```python")[1].split("```")[0]
        return code_content, None
    except Exception as e:
        return "", f"生成异常：{str(e)}"

# ===================== 页面交互 =====================
# 1. 加载模型
generator, load_error = load_model()
if load_error:
    st.error(load_error)

# 2. 文件上传
uploaded_file = st.file_uploader("📤 上传PDF文件", type="pdf")

# 3. 生成按钮
generate_btn = st.button("🚀 生成代码", type="primary", disabled=not generator)

# 4. 按钮逻辑
if generate_btn and generator:
    if not uploaded_file:
        st.warning("⚠️ 请先上传PDF文件！")
    else:
        with st.spinner("🔍 正在解析PDF并生成代码...（首次运行稍慢）"):
            pdf_text, pdf_error = extract_pdf_text(uploaded_file)
            if pdf_error:
                st.error(pdf_error)
            else:
                code_result, gen_error = generate_code_from_pdf(pdf_text, generator)
                if gen_error:
                    st.error(gen_error)
                else:
                    st.success("✅ 代码生成成功！")
                    st.code(code_result, language="python")
