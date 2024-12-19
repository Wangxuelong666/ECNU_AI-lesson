import os
import shutil
import uuid
from typing import List
import gradio as gr
import pandas as pd
import subprocess

# 定义工作目录，与原 FastAPI 版本保持一致
BACKUP_WAV_DIR = 'backup/wxl'
RTTM_OUTPUT_DIR = 'exp/rttm'
EXCEL_OUTPUT_DIR = 'excel_all'

def ensure_empty_directories():
    """确保工作目录存在且为空"""
    for directory in [BACKUP_WAV_DIR, RTTM_OUTPUT_DIR, EXCEL_OUTPUT_DIR]:
        if os.path.exists(directory):
            shutil.rmtree(directory)
        os.makedirs(directory)

def run_diarization_script():
    """执行说话人分离处理脚本"""
    try:
        result = subprocess.run(
            ['./run_all.sh'],
            capture_output=True,
            text=True,
            check=True
        )
        return True, result.stdout
    except subprocess.CalledProcessError as e:
        return False, f"处理失败: {e.stderr}"

def merge_excel_files(session_id: str) -> str:
    """合并所有生成的 Excel 文件"""
    excel_files = [f for f in os.listdir(EXCEL_OUTPUT_DIR) if f.endswith('.xlsx')]
    
    if not excel_files:
        return None
    
    all_dataframes = []
    for file in excel_files:
        df = pd.read_excel(os.path.join(EXCEL_OUTPUT_DIR, file))
        df['源文件'] = file
        all_dataframes.append(df)
    
    merged_df = pd.concat(all_dataframes, ignore_index=True)
    final_excel_path = os.path.join(EXCEL_OUTPUT_DIR, f'{session_id}_merged_diarization.xlsx')
    merged_df.to_excel(final_excel_path, index=False)
    
    return final_excel_path

def process_audio(audio_files):
    """处理上传的音频文件并返回结果"""
    try:
        # 生成会话ID
        session_id = str(uuid.uuid4())
        
        # 清理工作目录
        ensure_empty_directories()
        
        # 保存上传的音频文件
        for audio_file in audio_files:
            if not audio_file.name.lower().endswith('.wav'):
                return None, "请只上传 WAV 格式的音频文件"
                
            file_path = os.path.join(BACKUP_WAV_DIR, os.path.basename(audio_file.name))
            shutil.copy(audio_file.name, file_path)
        
        # 执行处理脚本
        success, message = run_diarization_script()
        if not success:
            return None, message
        
        # 合并 Excel 文件
        final_excel_path = merge_excel_files(session_id)
        if not final_excel_path:
            return None, "未能生成结果文件"
            
        return final_excel_path, "处理完成！"
        
    except Exception as e:
        return None, f"发生错误: {str(e)}"

# 创建 Gradio 界面
def create_gradio_interface():
    with gr.Blocks(title="说话人分离系统") as demo:
        gr.Markdown("""
        # 说话人分离系统
        
        上传 WAV 格式的音频文件，系统将自动进行说话人分离分析，并生成分析报告。
        
        使用说明：
        1. 点击下方上传按钮选择一个或多个 WAV 文件
        2. 等待系统处理（处理时间取决于音频长度）
        3. 处理完成后将自动下载分析结果表格
        """)
        
        with gr.Row():
            audio_input = gr.File(
                file_count="multiple",
                label="上传音频文件",
                file_types=[".wav"]
            )
        
        with gr.Row():
            submit_btn = gr.Button("开始处理", variant="primary")
        
        output_file = gr.File(label="分析结果")
        status_output = gr.Textbox(label="处理状态")
        
        submit_btn.click(
            fn=process_audio,
            inputs=[audio_input],
            outputs=[output_file, status_output]
        )
    
    return demo

# 创建并启动应用
demo = create_gradio_interface()

# 本地调试时使用
if __name__ == "__main__":
    demo.launch(server_name="0.0.0.0", server_port=7860)
