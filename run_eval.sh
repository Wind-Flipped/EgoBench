
# # python evaluate_interaction.py --scenario retail --scenario_number 1 --user_mode hard
# python evaluate_interaction.py --scenario retail --scenario_number 1 --user_mode easy
# python evaluate_interaction.py --scenario_number 1 --user_mode static
# # python evaluate_interaction.py --scenario_number 2 --user_mode hard
# python evaluate_interaction.py --scenario_number 2 --user_mode easy
# python evaluate_interaction.py --scenario_number 2 --user_mode static
# # python evaluate_interaction.py --scenario_number 3 --user_mode hard
# python evaluate_interaction.py --scenario_number 3 --user_mode easy
# python evaluate_interaction.py --scenario_number 3 --user_mode static
# # python evaluate_interaction.py --scenario_number 4 --user_mode hard
# # python evaluate_interaction.py --scenario_number 4 --user_mode easy
# # python evaluate_interaction.py --scenario_number 4 --user_mode static
# python evaluate_interaction.py --scenario_number 6 --user_mode easy
# python evaluate_interaction.py --scenario_number 6 --user_mode static
# python evaluate_interaction.py --scenario_number 7 --user_mode easy
# python evaluate_interaction.py --scenario_number 7 --user_mode static
# python evaluate_interaction.py --scenario_number 8 --user_mode easy
# python evaluate_interaction.py --scenario_number 8 --user_mode static
# gemini-3.1-pro-preview doubao-seed-2-0-pro-260215

python evaluate_interaction.py --model_name Qwen3.5-397B-A17B --num_samples 10
python evaluate_interaction.py --model_name glm-4.5v --num_samples 10
python evaluate_interaction.py --model_name gemini-3.1-pro-preview --num_samples 10
python evaluate_interaction.py --model_name mimo-v2-omni --num_samples 10
python evaluate_interaction.py --model_name kimi-k2.5 --num_samples 10
python evaluate_interaction.py --model_name qwen3.6-plus --num_samples 10
python evaluate_interaction.py --model_name glm-5v-turbo --num_samples 10
python evaluate_interaction.py --model_name doubao-seed-2-0-pro-260215 --num_samples 10
python evaluate_interaction.py --model_name qwen3-vl-225b --num_samples 10