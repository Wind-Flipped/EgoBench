#!/bin/bash
export PYTHONUNBUFFERED=1

# Load API keys from .env file
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [ -f "$SCRIPT_DIR/.env" ]; then
    source "$SCRIPT_DIR/.env"
else
    echo "Error: .env file not found. Copy .env.example to .env and fill in your API keys."
    exit 1
fi
# python run/multi_agent.py --multi_agent_user --service_model_name kimi-k2.5 --summary_user --scenario retail --scenario_number 1 --user_mode easy
# python run/multi_agent.py --multi_agent_user --service_model_name kimi-k2.5 --summary_user --scenario retail --scenario_number 1 --user_mode static
# python run/multi_agent.py --multi_agent_user --service_model_name kimi-k2.5 --summary_user --scenario retail --scenario_number 1 --user_mode hard

# python run/multi_agent.py --multi_agent_user --service_model_name kimi-k2.5 --summary_user --scenario retail --scenario_number 2 --user_mode easy
# python run/multi_agent.py --multi_agent_user --service_model_name kimi-k2.5 --summary_user --scenario retail --scenario_number 2 --user_mode static
# python run/multi_agent.py --multi_agent_user --service_model_name kimi-k2.5 --summary_user --scenario retail --scenario_number 2 --user_mode hard

# python run/multi_agent.py --multi_agent_user --service_model_name kimi-k2.5 --summary_user --scenario retail --scenario_number 3 --user_mode easy
# python run/multi_agent.py --multi_agent_user --service_model_name kimi-k2.5 --summary_user --scenario retail --scenario_number 3 --user_mode static
# python run/multi_agent.py --multi_agent_user --service_model_name kimi-k2.5 --summary_user --scenario retail --scenario_number 3 --user_mode hard

# python run/multi_agent.py --multi_agent_user --service_model_name kimi-k2.5 --summary_user --scenario retail --scenario_number 4 --user_mode easy
# python run/multi_agent.py --multi_agent_user --service_model_name kimi-k2.5 --summary_user --scenario retail --scenario_number 4 --user_mode static
# python run/multi_agent.py --multi_agent_user --service_model_name kimi-k2.5 --summary_user --scenario retail --scenario_number 4 --user_mode hard

# python run/multi_agent.py --multi_agent_user --service_model_name kimi-k2.5 --summary_user --scenario retail --scenario_number 5 --user_mode easy
# python run/multi_agent.py --multi_agent_user --service_model_name kimi-k2.5 --summary_user --scenario retail --scenario_number 5 --user_mode static
# python run/multi_agent.py --multi_agent_user --service_model_name kimi-k2.5 --summary_user --scenario retail --scenario_number 5 --user_mode hard

# python run/multi_agent.py --multi_agent_user --service_model_name kimi-k2.5 --summary_user --scenario retail --scenario_number 6 --user_mode easy
# python run/multi_agent.py --multi_agent_user --service_model_name kimi-k2.5 --summary_user --scenario retail --scenario_number 6 --user_mode static
# python run/multi_agent.py --multi_agent_user --service_model_name kimi-k2.5 --summary_user --scenario retail --scenario_number 6 --user_mode hard

# python run/multi_agent.py --multi_agent_user --service_model_name kimi-k2.5 --summary_user --scenario retail --scenario_number 7 --user_mode easy
# python run/multi_agent.py --multi_agent_user --service_model_name kimi-k2.5 --summary_user --scenario retail --scenario_number 7 --user_mode static
# python run/multi_agent.py --multi_agent_user --service_model_name kimi-k2.5 --summary_user --scenario retail --scenario_number 7 --user_mode hard

# python run/multi_agent.py --multi_agent_user --service_model_name kimi-k2.5 --summary_user --scenario retail --scenario_number 8 --user_mode easy
# python run/multi_agent.py --multi_agent_user --service_model_name kimi-k2.5 --summary_user --scenario retail --scenario_number 8 --user_mode static
# python run/multi_agent.py --multi_agent_user --service_model_name kimi-k2.5 --summary_user --scenario retail --scenario_number 8 --user_mode hard

# python run/multi_agent.py --multi_agent_user --service_model_name kimi-k2.5 --summary_user --scenario retail --scenario_number 8 --user_mode easy
# python run/multi_agent.py --multi_agent_user --service_model_name kimi-k2.5 --summary_user --scenario retail --scenario_number 8 --user_mode static
# python run/multi_agent.py --multi_agent_user --service_model_name kimi-k2.5 --summary_user --scenario retail --scenario_number 8 --user_mode hard

# python run/multi_agent.py --multi_agent_user --service_model_name kimi-k2.5 --summary_user --scenario retail --scenario_number 9 --user_mode easy
# python run/multi_agent.py --multi_agent_user --service_model_name kimi-k2.5 --summary_user --scenario retail --scenario_number 9 --user_mode static
# python run/multi_agent.py --multi_agent_user --service_model_name kimi-k2.5 --summary_user --scenario retail --scenario_number 9 --user_mode hard

# python run/multi_agent.py --multi_agent_user --service_model_name kimi-k2.5 --summary_user --scenario retail --scenario_number 10 --user_mode easy
# python run/multi_agent.py --multi_agent_user --service_model_name kimi-k2.5 --summary_user --scenario retail --scenario_number 10 --user_mode static
# python run/multi_agent.py --multi_agent_user --service_model_name kimi-k2.5 --summary_user --scenario retail --scenario_number 10 --user_mode hard


# python run/multi_agent.py --multi_agent_user --service_model_name kimi-k2.5 --summary_user --scenario restaurant --scenario_number 1 --user_mode easy
# python run/multi_agent.py --multi_agent_user --service_model_name kimi-k2.5 --summary_user --scenario restaurant --scenario_number 1 --user_mode static
# python run/multi_agent.py --multi_agent_user --service_model_name kimi-k2.5 --summary_user --scenario restaurant --scenario_number 1 --user_mode hard

# python run/multi_agent.py --multi_agent_user --service_model_name kimi-k2.5 --summary_user --scenario restaurant --scenario_number 2 --user_mode easy
# python run/multi_agent.py --multi_agent_user --service_model_name kimi-k2.5 --summary_user --scenario restaurant --scenario_number 2 --user_mode static
# python run/multi_agent.py --multi_agent_user --service_model_name kimi-k2.5 --summary_user --scenario restaurant --scenario_number 2 --user_mode hard

# python run/multi_agent.py --multi_agent_user --service_model_name kimi-k2.5 --summary_user --scenario restaurant --scenario_number 3 --user_mode easy
# python run/multi_agent.py --multi_agent_user --service_model_name kimi-k2.5 --summary_user --scenario restaurant --scenario_number 3 --user_mode static
# python run/multi_agent.py --multi_agent_user --service_model_name kimi-k2.5 --summary_user --scenario restaurant --scenario_number 3 --user_mode hard

# python run/multi_agent.py --multi_agent_user --service_model_name kimi-k2.5 --summary_user --scenario restaurant --scenario_number 4 --user_mode easy
# python run/multi_agent.py --multi_agent_user --service_model_name kimi-k2.5 --summary_user --scenario restaurant --scenario_number 4 --user_mode static
# python run/multi_agent.py --multi_agent_user --service_model_name kimi-k2.5 --summary_user --scenario restaurant --scenario_number 4 --user_mode hard

# python run/multi_agent.py --multi_agent_user --service_model_name kimi-k2.5 --summary_user --scenario restaurant --scenario_number 5 --user_mode easy
# python run/multi_agent.py --multi_agent_user --service_model_name kimi-k2.5 --summary_user --scenario restaurant --scenario_number 5 --user_mode static
# python run/multi_agent.py --multi_agent_user --service_model_name kimi-k2.5 --summary_user --scenario restaurant --scenario_number 5 --user_mode hard

python run/multi_agent.py --multi_agent_user --service_model_name kimi-k2.5 --summary_user --scenario order --scenario_number 1 --user_mode easy
python run/multi_agent.py --multi_agent_user --service_model_name kimi-k2.5 --summary_user --scenario order --scenario_number 1 --user_mode static
python run/multi_agent.py --multi_agent_user --service_model_name kimi-k2.5 --summary_user --scenario order --scenario_number 1 --user_mode hard

python run/multi_agent.py --multi_agent_user --service_model_name kimi-k2.5 --summary_user --scenario order --scenario_number 2 --user_mode easy
python run/multi_agent.py --multi_agent_user --service_model_name kimi-k2.5 --summary_user --scenario order --scenario_number 2 --user_mode static
python run/multi_agent.py --multi_agent_user --service_model_name kimi-k2.5 --summary_user --scenario order --scenario_number 2 --user_mode hard

# python run/multi_agent.py --multi_agent_user --service_model_name kimi-k2.5 --summary_user --scenario kitchen --scenario_number 1 --user_mode easy --num_samples -1
# python run/multi_agent.py --multi_agent_user --service_model_name kimi-k2.5 --summary_user --scenario kitchen --scenario_number 1 --user_mode static --num_samples -1
# python run/multi_agent.py --multi_agent_user --service_model_name kimi-k2.5 --summary_user --scenario kitchen --scenario_number 1 --user_mode hard --num_samples -1

# python run/multi_agent.py --multi_agent_user --service_model_name kimi-k2.5 --summary_user --scenario kitchen --scenario_number 2 --user_mode easy --num_samples -1
# python run/multi_agent.py --multi_agent_user --service_model_name kimi-k2.5 --summary_user --scenario kitchen --scenario_number 2 --user_mode static --num_samples -1
# python run/multi_agent.py --multi_agent_user --service_model_name kimi-k2.5 --summary_user --scenario kitchen --scenario_number 2 --user_mode hard --num_samples -1

# python run/multi_agent.py --multi_agent_user --service_model_name kimi-k2.5 --summary_user --scenario kitchen --scenario_number 3 --user_mode easy --num_samples -1
# python run/multi_agent.py --multi_agent_user --service_model_name kimi-k2.5 --summary_user --scenario kitchen --scenario_number 3 --user_mode static --num_samples -1
# python run/multi_agent.py --multi_agent_user --service_model_name kimi-k2.5 --summary_user --scenario kitchen --scenario_number 3 --user_mode hard --num_samples -1

# python run/multi_agent.py --multi_agent_user --service_model_name kimi-k2.5 --summary_user --scenario kitchen --scenario_number 4 --user_mode easy --num_samples -1
# python run/multi_agent.py --multi_agent_user --service_model_name kimi-k2.5 --summary_user --scenario kitchen --scenario_number 4 --user_mode static --num_samples -1
# python run/multi_agent.py --multi_agent_user --service_model_name kimi-k2.5 --summary_user --scenario kitchen --scenario_number 4 --user_mode hard --num_samples -1