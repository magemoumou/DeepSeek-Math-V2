# 🚀 DeepSeekMath-V2 vLLM兼容性配置指南

## 📋 环境配置

### 1. 环境变量配置（推荐方式）
```bash
# 设置vLLM推理引擎地址
export VLLM_BASE_URL="http://localhost:8000/v1"

# 设置API密钥（vLLM通常可以设置为EMPTY）
export VLLM_API_KEY="EMPTY"

# 可选：设置超时时间（毫秒）
export VLLM_TIMEOUT="300000"
```

### 2. 代码直接配置（备选方式）
```python
# 在代码中直接配置
api_model = APIModel(
    api_key="EMPTY",                    # vLLM通常不需要真实的API密钥
    base_url="http://localhost:8000/v1", # 你的vLLM推理引擎地址
    timeout=300000                     # 超时时间（毫秒）
)
```

## 🔧 vLLM推理引擎启动示例

### 基本启动命令
```bash
# 启动vLLM推理服务
python -m vllm.entrypoints.openai.api_server \
    --model deepseek-ai/deepseek-math-v2 \
    --host 0.0.0.0 \
    --port 8000 \
    --dtype auto \
    --max-model-len 128000
```

### 高级配置（推荐）
```bash
# 带GPU优化和批处理的启动命令
python -m vllm.entrypoints.openai.api_server \
    --model deepseek-ai/deepseek-math-v2 \
    --host 0.0.0.0 \
    --port 8000 \
    --dtype float16 \
    --max-model-len 128000 \
    --gpu-memory-utilization 0.9 \
    --max-num-batched-tokens 8192 \
    --max-num-seqs 256 \
    --disable-log-stats
```

## 🎯 使用示例

### 1. 基础使用（环境变量方式）
```bash
# 1. 设置环境变量
export VLLM_BASE_URL="http://localhost:8000/v1"
export VLLM_API_KEY="EMPTY"

# 2. 运行推理脚本
python inference/generate.py \
    --input_data_path inputs/IMO2025.json \
    --output_data_path outputs/IMO2025_results.jsonl \
    --temperature 1.0 \
    --top_p 0.95 \
    --max_tokens 128000 \
    --n 32
```

### 2. 命令行参数方式
```bash
# 直接通过命令行参数指定vLLM配置
python inference/generate_vllm_compatible.py \
    --input_data_path inputs/IMO2025.json \
    --output_data_path outputs/IMO2025_results.jsonl \
    --temperature 1.0 \
    --top_p 0.95 \
    --max_tokens 128000 \
    --n 32 \
    --num_processes 16 \
    --batch_size 16
```

### 3. 在Python代码中使用
```python
from inference.generate_vllm_compatible import APIModel

# 初始化vLLM客户端
api_model = APIModel()

# 准备测试数据
test_data = [{
    "prompt": "Prove that for any positive integer n, n^2 + n + 1 is always odd.",
    "problem_idx": "test-1"
}]

# 设置采样参数
sampling_params = {
    "temperature": 1.0,
    "top_p": 0.95,
    "max_tokens": 4096,
    "model": "default"
}

# 执行推理
results = api_model.generate(test_data, sampling_params)

# 输出结果
for result in results:
    print(f"输入: {result['prompt']}")
    print(f"输出: {result['output']}")
    print(f"完成原因: {result['finish_reason']}")
    print("-" * 50)
```

## 🔍 故障排除

### 常见问题1：连接超时
```bash
# 症状：连接vLLM服务超时
# 解决方案：
1. 检查vLLM服务是否正常运行
   curl http://localhost:8000/v1/models

2. 增加超时时间
   export VLLM_TIMEOUT="600000"  # 10分钟

3. 检查防火墙和网络配置
```

### 常见问题2：模型加载失败
```bash
# 症状：vLLM启动时报CUDA内存不足
# 解决方案：
1. 减小批处理大小
   --max-num-batched-tokens 4096
   --max-num-seqs 128

2. 使用更小的模型或量化
   --dtype float16
   --quantization awq

3. 减少GPU内存利用率
   --gpu-memory-utilization 0.8
```

### 常见问题3：推理质量异常
```python
# 症状：推理结果质量下降
# 解决方案：
# 1. 调整温度参数
sampling_params = {
    "temperature": 0.7,  # 降低温度提高确定性
    "top_p": 0.9,       # 降低top_p提高专注度
    "max_tokens": 8192,  # 适当增加最大token数
}

# 2. 检查prompt模板是否正确应用
# 3. 验证模型权重是否完整加载
```

## 📊 性能优化建议

### 1. 批处理优化
```bash
# 根据GPU内存调整批处理参数
--max-num-batched-tokens 16384  # 增加批处理token数
--max-num-seqs 512              # 增加并发序列数
```

### 2. 多进程优化
```bash
# 根据CPU核心数调整进程数
python inference/generate_vllm_compatible.py \
    --num_processes 32 \        # 增加进程数
    --batch_size 32 \          # 增加批大小
    ...其他参数
```

### 3. 模型参数优化
```python
# 针对数学推理优化的采样参数
sampling_params = {
    "temperature": 1.0,      # 保持创造性
    "top_p": 0.95,           # 保持多样性
    "max_tokens": 128000,    # 充分利用模型长度
    "presence_penalty": 0.1, # 轻微惩罚重复
    "frequency_penalty": 0.1,
}
```

## 🔗 相关链接

- [vLLM官方文档](https://docs.vllm.ai/)
- [OpenAI API兼容接口](https://docs.vllm.ai/en/latest/serving/openai_compatible_server.html)
- [DeepSeekMath-V2模型](https://huggingface.co/deepseek-ai/deepseek-math-v2)

## 📞 技术支持

如果遇到问题，请检查：
1. vLLM服务日志中的错误信息
2. 确保模型文件完整下载
3. 验证GPU驱动和CUDA版本兼容性
4. 检查网络连接和端口占用情况