import os
import json
import pickle
import math
import argparse
import asyncio
import aiohttp

from tqdm import tqdm
from multiprocessing import Queue, Process
from time import time, sleep

# vLLM兼容的APIModel类（独立版本）
class APIModel:
    def __init__(self):
        """
        初始化APIModel，支持vLLM本地推理引擎
        通过环境变量配置：
        - VLLM_API_KEY: API密钥（可选，默认为"EMPTY"）
        - VLLM_BASE_URL: vLLM推理引擎地址（如：http://localhost:8000/v1）
        """
        self.api_key = os.getenv("VLLM_API_KEY", "EMPTY")
        self.base_url = os.getenv("VLLM_BASE_URL", "http://localhost:8000/v1")
        self.timeout = 300  # 5分钟超时
        
        # 验证配置
        if not self.base_url:
            raise ValueError("必须设置VLLM_BASE_URL环境变量或通过代码配置base_url")
        
        print(f"🔧 初始化vLLM客户端:")
        print(f"   Base URL: {self.base_url}")
        print(f"   API Key: {self.api_key[:10]}..." if len(self.api_key) > 10 else f"   API Key: {self.api_key}")

    async def generate_one(self, prompt, sampling_params):
        """
        单次生成调用，兼容vLLM API格式
        
        Args:
            prompt: 消息列表格式的prompt
            sampling_params: 采样参数字典
            
        Returns:
            (output_string, finish_reason) 元组
        """
        try:
            # 构建vLLM兼容的请求体
            request_body = {
                "model": sampling_params.get("model", "default"),
                "messages": prompt,
                "temperature": sampling_params.get("temperature", 1.0),
                "top_p": sampling_params.get("top_p", 0.95),
                "max_tokens": sampling_params.get("max_tokens", 128000),
                "stream": False,
            }
            
            # 清理None值
            request_body = {k: v for k, v in request_body.items() if v is not None}
            
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}"
            }
            
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=self.timeout)) as session:
                async with session.post(
                    f"{self.base_url}/chat/completions",
                    headers=headers,
                    json=request_body
                ) as response:
                    
                    if response.status != 200:
                        error_text = await response.text()
                        raise Exception(f"vLLM API错误: {response.status} - {error_text}")
                    
                    result = await response.json()
                    
                    # 处理vLLM响应格式
                    choice = result["choices"][0]
                    message = choice["message"]
                    
                    # 提取推理内容和主要内容
                    reasoning_content = message.get("reasoning_content", "").strip()
                    content = message.get("content", "").strip()
                    
                    # 构建与原始格式兼容的输出
                    output_string = f"<think>\n{reasoning_content}"
                    if content:
                        output_string = reasoning_content + f"\n</think>\n{content}"
                    
                    finish_reason = choice.get("finish_reason", "stop").lower()
                    
                    return output_string.strip(), finish_reason
                    
        except Exception as e:
            print(f"❌ 生成错误: {e}")
            # 返回错误时的默认值
            return f"<think>\n推理错误: {str(e)}\n</think>\n", "error"

    async def generate_all(self, data):
        """批量异步生成"""
        tasks = [self.generate_one(task['prompt'], task['sampling_params']) for task in data]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 处理异常结果
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                print(f"❌ 任务 {i} 失败: {result}")
                processed_results.append((f"<think>\n错误: {str(result)}\n</think>\n", "error"))
            else:
                processed_results.append(result)
        
        return processed_results

    def generate(self, input_data, sampling_params):
        """同步生成接口"""
        data = []
        for item in input_data:
            if "messages" not in item:
                messages = [{
                    "role": "user",
                    "content": item["prompt"],
                }]
            else:
                messages = item['messages']
            
            data.append({
                'prompt': messages,
                'sampling_params': sampling_params
            })

        outputs = asyncio.run(self.generate_all(data))
        output_data = []
        
        assert len(input_data) == len(outputs), f"输入输出数量不匹配: {len(input_data)} vs {len(outputs)}"
        
        for item, (output_string, finish_reason) in zip(input_data, outputs):
            output_data.append({
                **item,
                "output": output_string,
                "finish_reason": finish_reason,
            })
        
        return output_data

    def mp_generate(self, input_queue: Queue, output_queue: Queue, sampling_params):
        """多进程生成接口"""
        while True:
            batch_idx, input_data = input_queue.get()
            if input_data is None:
                output_queue.put((batch_idx, None))
                break
            
            try:
                output_data = self.generate(input_data, sampling_params)
                output_queue.put((batch_idx, output_data))
            except Exception as e:
                print(f"❌ 批量生成错误: {e}")
                error_output = [{
                    **item,
                    "output": f"<think>\n批量生成错误: {str(e)}\n</think>\n",
                    "finish_reason": "error",
                } for item in input_data]
                output_queue.put((batch_idx, error_output))


def mp_generate_loop(input_queue, output_queue, sampling_params):
    """多进程生成循环"""
    api_model = APIModel()
    sleep(5)  # 初始化延迟
    api_model.mp_generate(input_queue, output_queue, sampling_params)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--input_data_path", required=True)
    parser.add_argument("--output_data_path", required=True)
    parser.add_argument("--num_processes", default=16, type=int)
    parser.add_argument("--batch_size", default=16, type=int)
    parser.add_argument("--temperature", required=True, type=float)
    parser.add_argument("--top_p", required=True, type=float)
    parser.add_argument("--max_tokens", required=True, type=int)
    parser.add_argument("--n", required=True, type=int)
    
    args, _ = parser.parse_known_args()
    
    input_data_path, output_data_path = args.input_data_path, args.output_data_path
    os.makedirs(os.path.dirname(output_data_path), exist_ok=True)

    num_processes = args.num_processes
    batch_size = args.batch_size
    temperature = args.temperature
    top_p = args.top_p
    max_tokens = args.max_tokens
    n = args.n

    # 元数据处理（保持原有逻辑）
    meta_data_path = f"{output_data_path}.meta"
    if not os.path.exists(meta_data_path):
        meta_data = {"n": n, "batch_size": batch_size, "complete_batches": []}
        with open(meta_data_path, "wb") as f:
            pickle.dump(meta_data, f)
    with open(meta_data_path, "rb") as f:
        meta_data = pickle.load(f)
    meta_data["complete_batches"] = set(meta_data["complete_batches"])

    assert n == meta_data["n"] and batch_size == meta_data["batch_size"], \
        f"params n or batch_size are different from previous running setting({n}, {batch_size}) != ({meta_data['n']}, {meta_data['batch_size']}), you need to delete {output_data_path} & {meta_data_path} to clear existing results"

    sampling_params = dict(
        temperature=temperature,
        top_p=top_p,
        max_tokens=max_tokens,
        model="default"  # vLLM需要指定模型名称
    )

    input_queue, output_queue = Queue(), Queue()
    fr = open(input_data_path, "r", encoding="utf-8")
    fw = open(output_data_path, "a+", encoding="utf-8")

    processes = []
    
    for i in range(num_processes):
        process = Process(target=mp_generate_loop, args=(input_queue, output_queue, sampling_params))
        process.start()
        processes.append(process)

    submit_batch = []
    num_input = 0
    num_skip = 0
    batch_idx = 0

    for line in tqdm(fr, desc="Waiting Input"):
        item = json.loads(line)
        for i in range(n):
            submit_batch.append(item)
            if len(submit_batch) >= batch_size:
                if batch_idx not in meta_data["complete_batches"]:
                    num_input += batch_size
                    input_queue.put((batch_idx, submit_batch))
                else:
                    num_skip += batch_size
                batch_idx += 1
                submit_batch = []
    if len(submit_batch) > 0:
        if batch_idx not in meta_data["complete_batches"]:
            input_queue.put((batch_idx, submit_batch))
            num_input += len(submit_batch)
        else:
            num_skip += len(submit_batch)
    print(f"Total Input Samples: {num_input} (Skip {num_skip} Samples)")
    fr.close()

    for i in range(num_processes):
        input_queue.put((None, None))

    remain_processes = num_processes
    num_output = 0
    with tqdm(desc="Waiting Output", total=num_input) as pbar:
        while remain_processes > 0:
            batch_idx, output_data = output_queue.get()
            if output_data is None:
                remain_processes -= 1
                continue
            for item in output_data:
                print(json.dumps(item, ensure_ascii=False), file=fw, flush=True)
                num_output += 1
                pbar.update(1)
            meta_data["complete_batches"].add(batch_idx)
            with open(meta_data_path, "wb") as f:
                pickle.dump(meta_data, f)
            fw.flush()
    print(f"Total Output Samples: {num_output}")
    fw.close()
    [process.join() for process in processes]