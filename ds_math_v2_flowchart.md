## 🎯 DeepSeekMath-V2三重验证机制Mermaid流程图

```mermaid
flowchart TD
    %% 定义样式类
    classDef codeControl fill:#4285F4,stroke:#1a73e8,stroke-width:2px,color:#fff
    classDef modelInfer fill:#EA4335,stroke:#d33b2c,stroke-width:2px,color:#fff
    classDef dataProcess fill:#34A853,stroke:#137333,stroke-width:2px,color:#fff
    classDef storage fill:#9AA0A6,stroke:#80868b,stroke-width:2px,color:#fff
    classDef decision fill:#FBBC04,stroke:#f29900,stroke-width:2px,color:#000
    classDef contrast fill:#673AB7,stroke:#512DA8,stroke-width:3px,color:#fff

    %% 开始节点
    Start([开始]):::codeControl
    
    %% 第一轮：证明生成
    Start --> LoadData[加载IMO竞赛题目数据]:::codeControl
    LoadData --> FormatGenInput[准备证明生成输入格式]:::dataProcess
    FormatGenInput --> CheckRound1{是否为第一轮?}:::decision
    
    CheckRound1 -->|是| UseRawData[使用原始题目数据]:::dataProcess
    CheckRound1 -->|否| UseRefinement[使用历史精炼数据]:::dataProcess
    
    UseRawData --> ApplyGenTemplate[应用proof_generation模板]:::dataProcess
    UseRefinement --> ApplyGenTemplate
    
    ApplyGenTemplate --> CreateGenCmd[构建生成命令参数]:::codeControl
    CreateGenCmd --> ExecGenCmd[执行生成命令]:::codeControl
    
    %% 关键模型推理调用 - 证明生成
    ExecGenCmd --> ModelGenCall[模型推理调用 #1<br/>generate.py:24<br/>AsyncOpenAI.chat.completions.create]:::modelInfer
    ModelGenCall --> GenAsyncProcess[异步批量处理<br/>温度:1.0, max_tokens:128K]:::modelInfer
    
    GenAsyncProcess --> SaveGenResult[保存生成结果到<br/>proof_gen_R{N}/output.jsonl]:::storage
    
    %% 第二轮：证明验证
    SaveGenResult --> PrepVerifInput[准备验证输入数据<br/>提取证明内容]:::dataProcess
    PrepVerifInput --> ApplyVerifTemplate[应用proof_verification模板]:::dataProcess
    
    ApplyVerifTemplate --> CreateVerifCmd[构建验证命令参数]:::codeControl
    CreateVerifCmd --> ExecVerifCmd[执行验证命令]:::codeControl
    
    %% 关键模型推理调用 - 证明验证
    ExecVerifCmd --> ModelVerifCall[模型推理调用 #2<br/>generate.py:24<br/>AsyncOpenAI.chat.completions.create]:::modelInfer
    ModelVerifCall --> VerifAsyncProcess[异步批量处理<br/>温度:1.0, max_tokens:64K]:::modelInfer
    
    VerifAsyncProcess --> SaveVerifResult[保存验证结果到<br/>proof_verification_R{N}/output.jsonl]:::storage
    
    %% 第三轮：元验证
    SaveVerifResult --> CheckScore{验证评分<br/><0.75?}:::decision
    
    CheckScore -->|是| PrepMetaInput[准备元验证输入数据]:::dataProcess
    CheckScore -->|否| SkipMeta[跳过元验证]:::codeControl
    
    PrepMetaInput --> ApplyMetaTemplate[应用meta_verification模板]:::dataProcess
    ApplyMetaTemplate --> CreateMetaCmd[构建元验证命令参数]:::codeControl
    CreateMetaTemplate --> ExecMetaCmd[执行元验证命令]:::codeControl
    
    %% 关键模型推理调用 - 元验证
    ExecMetaCmd --> ModelMetaCall[模型推理调用 #3<br/>generate.py:24<br/>AsyncOpenAI.chat.completions.create]:::modelInfer
    ModelMetaCall --> MetaAsyncProcess[异步批量处理<br/>温度:1.0, max_tokens:64K]:::modelInfer
    
    MetaAsyncProcess --> SaveMetaResult[保存元验证结果到<br/>meta_verification_R{N}/output.jsonl]:::storage
    
    %% 多轮迭代控制
    SaveMetaResult --> UpdatePool[更新证明池数据<br/>保存高质量证明]:::storage
    SkipMeta --> UpdatePool
    
    UpdatePool --> CheckRound{是否达到<br/>最大轮次?}:::decision
    CheckRound -->|否| IncrementRound[轮次计数器+1<br/>R = R + 1]:::codeControl
    IncrementRound --> PrepVerifInput
    
    CheckRound -->|是| FinalOutput[输出最终结果<br/>高质量数学证明]:::storage
    
    %% 与常规LLM对比部分
    subgraph 常规LLM推理 ["🔄 常规LLM推理流程（对比参考）"]
        direction TB
        ConventionalInput[输入问题]:::contrast
        ConventionalPrompt[简单prompt]:::contrast
        ConventionalModel[单次模型调用]:::contrast
        ConventionalOutput[直接输出答案]:::contrast
        
        ConventionalInput --> ConventionalPrompt --> ConventionalModel --> ConventionalOutput
    end
    
    %% 连接线到对比区域
    Start -.->|"对比"| ConventionalInput
    FinalOutput -.->|"质量提升"| ConventionalOutput
    
    %% 批处理和并行说明
    BatchNote[💡 每轮都支持<br/>并行处理: 32-320个进程<br/>批量大小: 160个样本]:::codeControl
    ModelGenCall -.-> BatchNote
    ModelVerifCall -.-> BatchNote  
    ModelMetaCall -.-> BatchNote
    
    %% 关键差异标注
    KeyDiff1[🔍 关键差异 #1<br/>单次调用 vs 三重验证]:::contrast
    KeyDiff2[🔍 关键差异 #2<br/>无质量控制 vs 严格评分筛选]:::contrast
    KeyDiff3[🔍 关键差异 #3<br/>无迭代优化 vs 多轮精炼]:::contrast
    
    ModelGenCall -.-> KeyDiff1
    CheckScore -.-> KeyDiff2
    CheckRound -.-> KeyDiff3

    %% 样式应用
    class Start,LoadData,FormatGenInput,CreateGenCmd,ExecGenCmd,CreateVerifCmd,ExecVerifCmd,CreateMetaCmd,ExecMetaCmd,IncrementRound codeControl
    class ModelGenCall,ModelVerifCall,ModelMetaCall,GenAsyncProcess,VerifAsyncProcess,MetaAsyncProcess modelInfer
    class UseRawData,UseRefinement,ApplyGenTemplate,PrepVerifInput,ApplyVerifTemplate,PrepMetaInput,ApplyMetaTemplate,UpdatePool dataProcess
    class SaveGenResult,SaveVerifResult,SaveMetaResult,FinalOutput storage
    class CheckRound1,CheckScore,CheckRound decision
    class ConventionalInput,ConventionalPrompt,ConventionalModel,ConventionalOutput,KeyDiff1,KeyDiff2,KeyDiff3 contrast
```

---

## 📊 关键差异总结

### 🔥 模型推理接口调用环节
1. **证明生成**: `generate.py:24` - `self.client.chat.completions.create()`
2. **证明验证**: `generate.py:24` - 相同API，不同模板  
3. **元验证**: `generate.py:24` - 相同API，不同模板

### 🎯 与常规LLM的核心差异

| 维度 | 常规LLM | DeepSeekMath-V2 |
|------|---------|-----------------|
| **调用次数** | 1次 | 3次（每轮） |
| **质量控制** | ❌ 无 | ✅ 严格评分筛选 |
| **迭代优化** | ❌ 无 | ✅ 多轮精炼 |
| **并行处理** | ❌ 单次 | ✅ 32-320进程并行 |
| **数据格式** | ❌ 简单文本 | ✅ 结构化JSONL |
| **验证机制** | ❌ 无验证 | ✅ 三重验证体系 |

### 💡 技术洞察

DeepSeekMath-V2的巧妙之处在于：**用相同的模型API接口，通过不同的prompt模板和代码逻辑控制，实现了复杂的验证流程**。这种设计既保持了系统的简洁性，又实现了强大的功能。