# Multi-Agent Customer Service Simulation Framework

A framework for evaluating multimodal LLM-based customer service agents through simulated multi-turn conversations. A user agent (simulated customer) interacts with a service agent (LLM under test) across four real-world service domains, while an automated evaluation pipeline measures tool-call accuracy and interaction quality.

## Architecture

The system operates as a **two-agent dialogue loop**:

1. **User Agent** — Simulates a customer with a specific task. In *easy* mode, the customer is cooperative and provides information step-by-step. In *hard* mode, the customer has low patience, gives vague or fragmented information, and may provide negative feedback. In *static* mode, the customer sends a single comprehensive request with no follow-up.

2. **Service Agent** — The LLM being evaluated. It receives tool definitions for the scenario, processes the user's request, invokes tools via structured JSON output, and responds in natural language. Tool calls are intercepted, executed against an in-memory scenario database, and the results are fed back into the conversation.

3. **Evaluation Pipeline** — After simulation, tool calls are compared against scenario ground truth using fuzzy matching to compute success metrics. Results feed into visualization and report generation scripts.

```
┌─────────────┐     message      ┌──────────────┐
│  User Agent  │ ───────────────▶ │ Service Agent │
│  (Qwen3.5)   │ ◀─────────────── │  (LLM under   │
│              │   response       │   test)       │
└─────────────┘                   └──────┬───────┘
                                         │ tool call (JSON)
                                         ▼
                                  ┌──────────────┐
                                  │ Scenario DB   │
                                  │ (in-memory)   │
                                  └──────────────┘
```

## Supported Scenarios

| Scenario | Description | Variants | Tools |
|----------|-------------|----------|-------|
| **retail** | Wine & retail product shopping | 10 environments | Product search, cart management, shopping lists, nutrition info, tax & discounts |
| **kitchen** | Kitchen & recipe assistance | 4 environments | Ingredient search, recipe lookup, nutrition, substitution, cooking instructions |
| **restaurant** | Restaurant ordering & menus | 5 environments | Dish/menu lookup, ordering, dietary info, set meals |
| **order** | Order tracking & delivery | 2 environments | Restaurant ordering, order tracking, delivery status |

Each scenario variant provides a different in-memory database configuration (product catalogs, menus, etc.) loaded from `tools/{scenario}/{scenario}_init.py`.

## Supported Models

| Model | Provider | API |
|-------|----------|-----|
| `glm-4.5v` / `glm-5v-turbo` | Zhipu AI | Zhipu AI SDK |
| `qwen3-vl-225b` | Alibaba Qwen | Custom endpoint |
| `Qwen3.5-397B-A17B` | Alibaba Qwen | OpenAI-compatible |
| `qwen3.6-plus` | Alibaba Qwen | OpenAI-compatible |
| `gemini-3.1-pro-preview` | Google | OpenAI-compatible proxy |
| `kimi-k2.5` | Moonshot | OpenAI-compatible |
| `mimo-v2-omni` | Xiaomi MiMo | OpenAI-compatible |
| `doubao-seed-2-0-pro-260215` | ByteDance Doubao | OpenAI-compatible |
| `manual` | — | Terminal input for manual testing |

## Project Structure

```
├── run/                          # Core simulation framework
│   ├── multi_agent.py            # Main entry point
│   ├── utils.py                  # LLM API calls, tool execution, message building
│   ├── prompts.py                # Prompt templates for all agents
│   └── apis/                     # LLM API wrappers
│       ├── unified.py            # Unified call_llm dispatcher
│       ├── zhipu.py              # Zhipu AI
│       ├── qwen.py               # Qwen
│       ├── qwen3_5.py            # Qwen3.5
│       ├── kimi.py               # Kimi
│       ├── mimo.py               # MiMo
│       └── doubao.py             # Doubao
├── tools/                        # Scenario databases & tool definitions
│   ├── retail/                   # RetailDB, retail_init.py, retail_tools.json
│   ├── kitchen/                  # KitchenDB, kitchen_init.py, kitchen_tools.json
│   ├── restaurant/               # RestaurantDB, restaurant_init.py, restaurant_tools.json
│   ├── order/                    # OrderDB, order_init.py, order_tools.json
│   ├── database_init.py          # DB initialization utilities
│   └── user_words.py             # Extra phrases for hard-mode user agent
├── scenarios/
│   └── final/                    # Production scenario definitions (JSON)
│       ├── retail1.json .. retail10.json
│       ├── kitchen1.json .. kitchen4.json
│       ├── restaurant1.json .. restaurant5.json
│       └── order1.json .. order2.json
├── analysis_scripts/             # Evaluation & visualization
│   ├── evaluate_interaction.py   # Core evaluation script
│   ├── print_eval.py             # Pretty-print evaluation results
│   ├── analyze_errors.py         # Error categorization
│   ├── analyze_tool_correctness.py
│   ├── visualize_results.py      # Chart generation
│   ├── plot_results.py           # Additional plotting
│   ├── generate_comprehensive_report.py
│   └── run_eval.sh               # Run evaluation across all models
├── results/                      # Raw simulation output per model
│   └── {model_name}/             # One subdirectory per evaluated model
├── eval_result/                  # Evaluation output per model
│   ├── {model_name}/             # {scenario}{number}_{mode}_eval.json
│   └── figures/                  # Generated charts (PNG, LaTeX)
├── run_all.sh                    # Launch all model runs in parallel
├── run_scenario.sh               # Configurable multi-model runner
├── run_glm.sh / run_qwen3.sh / … # Model-specific runners
└── requirements.txt
```

## Getting Started

### Prerequisites

- Python 3.10+
- API keys for the models you want to evaluate

### API Key Configuration

All API keys and base URLs are managed through environment variables. A `.env.example` file is provided as a template.

1. Copy the example file and fill in your keys:
   ```bash
   cp .env.example .env
   ```

2. Edit `.env` and replace the placeholder values with your actual API keys and endpoints:
   ```bash
   # Main API key for LLM platform models
   # Used by: Qwen3.5, Qwen3-VL, Gemini, DeepSeek, GLM-4.5V, Doubao, Qwen3.6, etc.
   export API_KEY="your-api-key-here"

   # Base URL for LLM API endpoints (Qwen, Doubao, Gemini, etc.)
   # Default: https://api.example.com/v1
   export LLM_API_BASE_URL="https://your-llm-api-endpoint.com/v1"

   # Kimi (Moonshot) API key
   # Used by: kimi-k2.5
   export KIMI_API_KEY="your-kimi-api-key-here"

   # Kimi API base URL (optional, defaults to Moonshot's official endpoint)
   export KIMI_API_BASE_URL="https://api.moonshot.cn/v1"

   # Xiaomi MiMo API key
   # Used by: mimo-v2-omni
   export MIMO_API_KEY="your-mimo-api-key-here"

   # MiMo API base URL (optional, defaults to Xiaomi's official endpoint)
   export MIMO_API_BASE_URL="https://api.xiaomimimo.com/v1"

   # Zhipu AI API key
   # Used by: glm-5v-turbo, glm-4.5v
   export ZHIPU_API_KEY="your-zhipu-api-key-here"
   ```

3. Source the `.env` file before running simulations:
   ```bash
   source .env
   ```

> **Note:** The shell scripts (`run_glm.sh`, `run_kimi.sh`, etc.) automatically source `.env` when executed. The `.env` file is excluded from version control via `.gitignore`.

| Environment Variable | Required | Default | Description |
|---------------------|----------|---------|-------------|
| `API_KEY` | Yes* | - | API key for Qwen, Gemini, DeepSeek, GLM, Doubao models |
| `LLM_API_BASE_URL` | No | `https://api.example.com/v1` | Base URL for LLM API endpoints |
| `KIMI_API_KEY` | Yes* | - | Moonshot Kimi API key |
| `KIMI_API_BASE_URL` | No | `https://api.moonshot.cn/v1` | Kimi API base URL |
| `MIMO_API_KEY` | Yes* | - | Xiaomi MiMo API key |
| `MIMO_API_BASE_URL` | No | `https://api.xiaomimimo.com/v1` | MiMo API base URL |
| `ZHIPU_API_KEY` | Yes* | - | Zhipu AI API key |

*Required only if using the corresponding models.

### Video URL Configuration

This framework requires video files for multimodal scenario simulations. You need to upload your own videos to publicly accessible URLs and configure them before running simulations.

#### Step 1: Upload Videos

Upload the required video files to your own cloud storage (e.g., Google Cloud Storage, AWS S3, Azure Blob, or any publicly accessible HTTPS URL). The scenarios require the following videos:

| Scenario | Required Videos |
|----------|----------------|
| **retail** | retail1.mp4 - retail10.mp4 |
| **kitchen** | kitchen1.mp4, deep_fried.mp4, Green Pepper Chicken.mp4, dumplings.mp4 |
| **restaurant** | restaurant1.mp4 - restaurant5.mp4 |
| **order** | afrikana_annie_1.mov, annie_butcher_1.mov, annie_meraki_1.mov, annie_pauhana_1.mov, sunny_annie_1.mov, afrikana_greek.mov, butcher_greek.mov, greek_annie_1.mov, meraki_greek.mov, pauhana_greek.mov, sunny_greek.mov |

#### Step 2: Configure URL Mappings

Edit `run/apis/unified.py` to update the video URL mappings with your public URLs:

1. **For standard models** (Qwen, GLM, Doubao, etc.): Update `_DEFAULT_CLOUD_URL_MAPPING`
   ```python
   _DEFAULT_CLOUD_URL_MAPPING = {
       "retail1.mp4": "https://your-domain.com/videos/retail1.mp4",
       "retail2.mp4": "https://your-domain.com/videos/retail2.mp4",
       # ... add all your video URLs
   }
   ```

2. **For Gemini models**: Update `_DEFAULT_GEMINI_URL_MAPPING`
   ```python
   _DEFAULT_GEMINI_URL_MAPPING = {
       "retail1.mp4": "gs://your-bucket/videos/retail1.mp4",
       # ... add all your video URLs
   }
   ```

3. **For Kimi models**: Update `_DEFAULT_KIMI_URL_MAPPING`
   ```python
   _DEFAULT_KIMI_URL_MAPPING = {
       "retail1.mp4": "ms://your-media-service/retail1",
       # ... add all your video URLs
   }
   ```

#### Step 3: Environment Variable Override (Optional)

Instead of editing the code, you can also set environment variables to provide URL mappings:

```bash
# Provide a JSON object mapping video filenames to URLs
export VIDEO_URL_MAPPING='{"retail1.mp4": "https://your-domain.com/retail1.mp4"}'
export GEMINI_URL_MAPPING='{"retail1.mp4": "gs://your-bucket/retail1.mp4"}'
export KIMI_URL_MAPPING='{"retail1.mp4": "ms://your-service/retail1"}'
```

> **Note:** Video URLs must be publicly accessible or use the appropriate protocol for your model provider (e.g., `gs://` for Google Cloud Storage with Gemini, `ms://` for Moonshot's media service).

### Installation

```bash
pip install -r requirements.txt
```

### Running a Simulation

```bash
# Set up API keys (required before first run)
cp .env.example .env   # then edit .env with your keys
source .env

# Run a single simulation
python run/multi_agent.py \
  --scenario retail \
  --scenario_number 1 \
  --user_mode easy \
  --service_model_name Qwen3.5-397B-A17B \
  --multi_agent_user \
  --summary_user

# Run with limited samples
python run/multi_agent.py \
  --scenario kitchen \
  --scenario_number 2 \
  --user_mode hard \
  --service_model_name glm-4.5v \
  --num_samples 10

# Rerun only previously failed scenarios
python run/multi_agent.py \
  --scenario restaurant \
  --scenario_number 1 \
  --user_mode easy \
  --service_model_name qwen3-vl-225b \
  --num_samples 0
```

### Key Arguments

| Argument | Values | Default | Description |
|----------|--------|---------|-------------|
| `--scenario` | `retail`, `kitchen`, `restaurant`, `order` | `retail` | Domain scenario |
| `--scenario_number` | int | `1` | Environment variant number |
| `--user_mode` | `easy`, `hard`, `static` | `easy` | User agent difficulty |
| `--service_model_name` | See [Supported Models](#supported-models) | `qwen3-vl-225b` | LLM to evaluate |
| `--multi_agent_user` | flag | off | Enable contradiction checker for user responses |
| `--summary_user` | flag | off | Enable dialogue summarization to manage context length |
| `--num_samples` | int | `0` | Limit scenarios per run (`0` = all) |

### Running Evaluation

```bash
# Evaluate a specific model
cd analysis_scripts
python evaluate_interaction.py --model_name glm-4.5v --num_samples 10

# Evaluate all models
bash run_eval.sh
```

### Batch Execution

```bash
# Run all models in parallel
bash run_all.sh

# Run a specific model across all scenarios and modes
bash run_glm.sh
bash run_qwen3.5.sh
```

## User Modes

### Easy Mode
The user agent acts as a cooperative customer who provides information step-by-step, responds clearly to questions, and signals completion with "STOP" when all requirements are met.

### Hard Mode
The user agent simulates a challenging customer with low patience, provides vague or incomplete information initially, may give negative feedback ("Bad Service Agent"), and passively introduces contradictions. Additional distractor phrases from `tools/user_words.py` are injected to increase difficulty.

### Static Mode
A single-turn interaction where the user agent sends one comprehensive request containing all requirements at once. The service agent must process everything without follow-up clarification.

## Evaluation

The evaluation pipeline in `analysis_scripts/evaluate_interaction.py` compares each service agent's tool calls against the scenario ground truth:

- **Tool-call matching** — Verifies that the correct tools were invoked with the correct parameters
- **Fuzzy matching** — Handles minor variations in parameter values (e.g., product names) using fuzzy string matching
- **Database verification** — Re-executes tool calls against the scenario database to verify result correctness
- **Success metrics** — Computes per-scenario and aggregate success rates across difficulty levels

### Visualization & Reports

```bash
# Generate charts and reports
cd analysis_scripts
python visualize_results.py
python plot_results.py
python generate_comprehensive_report.py
```

Output charts include success rates by difficulty/scenario, error distributions, token usage correlations, and dialogue round analysis. Charts are saved to `eval_result/figures/`.

## Output Format

Simulation results are saved to `results/{model_name}/{scenario}{number}_{mode}.json`:

```json
{
  "scenario_id": 0,
  "mode": "easy",
  "instruction": "...",
  "image_description": "...",
  "dialogue": [{"role": "user", "turn": 1, "content": "..."}, ...],
  "tool_calls": [{"turn": 1, "calls": [...], "results": [...]}],
  "rounds_count": 5,
  "input_tokens": 12345,
  "output_tokens": 6789,
  "tool_calls_count": 8,
  "user_response_time_seconds": 2.3,
  "agent_response_time_seconds": 5.1,
  "execution_time_seconds": 42.0,
  "user_performance": {...}
}
```

Evaluation results are saved to `eval_result/{model_name}/{scenario}{number}_{mode}_eval.json`.

## License

See [LEGAL.md](LEGAL.md) for legal information.
