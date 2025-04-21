import json
import requests
import os
import time
from colorama import init, Fore, Style

# 初始化 colorama 模块，用于彩色输出
init(autoreset=True)

# LM Studio API 端点
LM_STUDIO_API_URL = "http://localhost:1234/v1/chat/completions"

# 存档文件夹路径
SAVE_FOLDER = "saves"
if not os.path.exists(SAVE_FOLDER):
    os.makedirs(SAVE_FOLDER)

# 初始化游戏状态
def init_game():
    save_files = [f for f in os.listdir(SAVE_FOLDER) if f.endswith('.json')]
    if save_files:
        print(Fore.YELLOW + "找到以下存档：")
        for i, file in enumerate(save_files, start=1):
            print(Fore.YELLOW + f"{i}. {file}")
        while True:
            choice = input(Fore.YELLOW + "请选择要加载的存档编号（输入 0 开始新游戏）：")
            if choice.isdigit():
                choice = int(choice)
                if choice == 0:
                    return new_game()
                elif 1 <= choice <= len(save_files):
                    try:
                        with open(os.path.join(SAVE_FOLDER, save_files[choice - 1]), 'r') as f:
                            return json.load(f)
                    except json.JSONDecodeError:
                        print(Fore.RED + "存档文件损坏，无法加载，请选择其他存档或开始新游戏。")
            else:
                print(Fore.RED + "输入无效，请重新输入。")
    return new_game()

    # 新增存档字段校验
    required_fields = [
        'location', 'experience', 'level', 'inventory',
        'completed_tasks', 'quests', 'stats'
    ]
    
    if not all(field in game_state for field in required_fields):
        print(Fore.RED + "存档缺少必要字段，已创建新游戏")
        return new_game()
    
    return game_state

# 创建新游戏
# 在常量区域新增
MAX_RETRY = 3  # 添加在 LM_STUDIO_API_URL 下方

# 修改 new_game 函数
def new_game():
    while True:
        player_name = input(Fore.YELLOW + "请输入你的名字: ").strip()
        if player_name:
            break
        print(Fore.RED + "名字不能为空，请重新输入。")
    
    # 动态生成职业系统（保留默认值作为后备）
    valid_classes = {"战士": {"攻击":10,"防御":8,"魔法":2},
                    "法师": {"攻击":3,"防御":4,"魔法":12},
                    "盗贼": {"攻击":7,"防御":5,"魔法":3}}
    
    # 尝试获取AI生成的职业
    for _ in range(MAX_RETRY):
        try:
            response = get_lm_response("生成5个幻想职业，格式：名称|攻击|防御|魔法|描述（用中文竖线分隔）")
            if response:
                new_classes = [line.split("|") for line in response.split("\n") if line]
                for parts in new_classes:
                    if len(parts) >=4 and parts[0] not in valid_classes:
                        valid_classes[parts[0]] = {
                            "攻击": max(1, min(15, int(parts[1]))),
                            "防御": max(1, min(15, int(parts[2]))),
                            "魔法": max(1, min(15, int(parts[3])))
                        }
                if len(valid_classes) > 3:  # 确保至少生成1个新职业
                    break
        except:
            continue

    # 职业选择界面
    while True:
        print(Fore.YELLOW + "\n可选职业：")
        classes = list(valid_classes.items())
        for i, (cls, stats) in enumerate(classes, 1):
            print(Fore.CYAN + f"{i}. {cls} (攻:{stats['攻击']} 防:{stats['防御']} 魔:{stats['魔法']})")
        
        choice = input(Fore.YELLOW + "请输入职业编号: ").strip()
        if choice.isdigit() and 1 <= int(choice) <= len(classes):
            player_class = classes[int(choice)-1][0]
            break
        print(Fore.RED + "无效的选择，请重新输入")

    return {
        "player_name": player_name,
        "player_class": player_class,
        "valid_classes": valid_classes,  # 新增字段保存所有职业
        "location": "新手村",
        "experience": 0,
        "level": 1,
        "gold": 0,
        "inventory": [],
        "completed_tasks": [],
        "quests": [],
        "stats": {
            "战士": {"攻击": 10, "防御": 8, "魔法": 2},
            "法师": {"攻击": 3, "防御": 4, "魔法": 12},
            "盗贼": {"攻击": 7, "防御": 5, "魔法": 3}
        }[player_class],
        "max_stats": {
            "攻击": 100,
            "防御": 100,
            "魔法": 100
        }
    }

# 保存游戏状态
def save_game(game_state):
    save_name = f"{game_state['player_name']}_save.json"
    save_path = os.path.join(SAVE_FOLDER, save_name)
    with open(save_path, 'w') as f:
        json.dump(game_state, f)

# 与 LM Studio 交互获取响应
def get_lm_response(prompt):
    headers = {
        "Content-Type": "application/json"
    }
    data = {
        "messages": [{"role": "user", "content": prompt}]
    }
    max_retries = 3
    for retry in range(max_retries):
        try:
            response = requests.post(LM_STUDIO_API_URL, headers=headers, json=data)
            response.raise_for_status()
            result = response.json()
            answer = result["choices"][0]["message"]["content"]
            # 过滤 <think> 相关内容
            import re
            answer = re.sub(r'<think>[^<]*</think>', '', answer)
            return answer
        except requests.RequestException as e:
            if retry < max_retries - 1:
                print(Fore.RED + f"请求出错，正在重试 ({retry + 1}/{max_retries}): {e}")
                time.sleep(2)
            else:
                print(Fore.RED + f"请求失败，可能是 LM Studio 未启动或 API 地址错误。你可以检查 LM Studio 是否正常运行，确认 API 地址 {LM_STUDIO_API_URL} 是否正确。")
    return None

# 处理任务系统
def handle_quests(game_state):
    if game_state["quests"]:
        print(Fore.YELLOW + "你当前有以下任务：")
        for i, quest in enumerate(game_state["quests"], start=1):
            print(Fore.YELLOW + f"{i}. {quest}")
        while True:
            choice = input(Fore.YELLOW + "请选择要处理的任务编号（输入 0 跳过）：")
            if choice.isdigit():
                choice = int(choice)
                if choice == 0:
                    break
                elif 1 <= choice <= len(game_state["quests"]):
                    quest = game_state["quests"].pop(choice - 1)
                    prompt = f"玩家要处理任务：{quest}，玩家属性为{game_state['stats']}。请描述任务完成情况和奖励。"
                    response = get_lm_response(prompt)
                    if response:
                        print(Fore.CYAN + response)
                        # 根据响应更新游戏状态
                        if "获得经验" in response:
                            exp_gained = int(response.split("获得经验")[1].split()[0])
                            game_state["experience"] += exp_gained
                            while game_state["experience"] >= game_state["level"] * 100:
                                game_state["experience"] -= game_state["level"] * 100
                                game_state["level"] += 1
                                print(Fore.GREEN + f"恭喜你，升级到了 {game_state['level']} 级！")
                                # 升级后提升属性
                                for stat in game_state["stats"]:
                                    game_state["stats"][stat] = min(game_state["stats"][stat] + 2, game_state["max_stats"][stat])
                        if "获得金币" in response:
                            gold_gained = int(response.split("获得金币")[1].split()[0])
                            game_state["gold"] += gold_gained
                        if "获得物品" in response:
                            item = response.split("获得物品")[1].split()[0]
                            game_state["inventory"].append(item)
                        game_state["completed_tasks"].append(quest)
                        save_game(game_state)
                    break
            else:
                print(Fore.RED + "输入无效，请重新输入。")
    else:
        print(Fore.YELLOW + "你目前没有任何任务。")

# 展示玩家信息
def show_player_info(game_state):
    # 基础信息区域
    print(Fore.YELLOW + f"\n╔{'═'*34}╗")
    print(Fore.YELLOW + f"║{Fore.CYAN}     玩家角色信息{Fore.YELLOW:>20}║")
    print(Fore.YELLOW + f"╠{'═'*12}╦{'═'*14}╦{'═'*6}╣")
    print(Fore.YELLOW + f"║ {Fore.CYAN}姓名：{Fore.GREEN}{game_state['player_name']:12} {Fore.YELLOW}║ {Fore.CYAN}等级：{Fore.GREEN}{game_state['level']:3} {Fore.YELLOW}║")
    print(Fore.YELLOW + f"╠{'═'*12}╬{'═'*14}╬{'═'*6}╣")
    print(Fore.YELLOW + f"║ {Fore.CYAN}职业：{Fore.GREEN}{game_state['player_class']:12} {Fore.YELLOW}║ {Fore.CYAN}金币：{Fore.GREEN}{game_state['gold']:3} {Fore.YELLOW}║")
    print(Fore.YELLOW + f"╠{'═'*12}╩{'═'*14}╩{'═'*6}╣")
    
    # 经验值进度条
    exp_percent = game_state['experience']/(game_state['level']*100)
    progress_bar = f"{Fore.GREEN}▓"*int(exp_percent*20) + f"{Fore.WHITE}░"*(20-int(exp_percent*20))
    print(Fore.YELLOW + f"║ {Fore.CYAN}经验值：{progress_bar} {Fore.YELLOW}║")
    print(Fore.YELLOW + f"╠{'═'*34}╣")
    
    # 属性区域
    stats_line = "║ "
    for i, (stat, value) in enumerate(game_state["stats"].items()):
        stats_line += f"{Fore.CYAN}{stat}：{Fore.GREEN}{value:2} "
        if (i+1) % 2 == 0 and i != len(game_state["stats"])-1:
            stats_line += f"{Fore.YELLOW}║\n╠{'─'*34}╣\n║ "
    stats_line += " "*(34 - len(stats_line)//2 + 5) + f"{Fore.YELLOW}║"
    print(Fore.YELLOW + stats_line)
    print(Fore.YELLOW + f"╠{'═'*34}╣")
    
    # 物品栏
    inv_count = len(game_state['inventory'])
    print(Fore.YELLOW + f"║ {Fore.CYAN}物品栏（{inv_count}件）{'·'*(28-len(f'物品栏（{inv_count}件）')*2)}║")
    if game_state["inventory"]:
        items = [f"{i+1}.{item}" for i, item in enumerate(game_state["inventory"])]
        for i in range(0, len(items), 3):
            line = "║ " + " ".join(f"{Fore.GREEN}{item:<10}" for item in items[i:i+3])
            print(line.ljust(35) + Fore.YELLOW + "║")
    else:
        print(Fore.YELLOW + f"║{Fore.WHITE}          暂无携带物品          {Fore.YELLOW}║")
    print(Fore.YELLOW + f"╠{'═'*34}╣")
    
    # 已完成任务
    task_count = len(game_state['completed_tasks'])
    print(Fore.YELLOW + f"║ {Fore.CYAN}已完成任务（{task_count}项）{'·'*(28-len(f'已完成任务（{task_count}项）')*2)}║")
    if game_state["completed_tasks"]:
        for i, task in enumerate(game_state["completed_tasks"], 1):
            print(Fore.YELLOW + f"║ {Fore.GREEN}{i:2}.{task[:20]:<29} {Fore.YELLOW}║")
    else:
        print(Fore.YELLOW + f"║{Fore.WHITE}          暂无完成任务          {Fore.YELLOW}║")
    print(Fore.YELLOW + f"╚{'═'*34}╝\n")

# 增加物品使用功能
def use_item(game_state):
    if game_state["inventory"]:
        print(Fore.YELLOW + "你拥有以下物品：")
        for i, item in enumerate(game_state["inventory"], start=1):
            print(Fore.YELLOW + f"{i}. {item}")
        while True:
            choice = input(Fore.YELLOW + "请选择要使用的物品编号（输入 0 取消）：")
            if choice.isdigit():
                choice = int(choice)
                if choice == 0:
                    break
                elif 1 <= choice <= len(game_state["inventory"]):
                    item = game_state["inventory"].pop(choice - 1)
                    prompt = f"玩家使用了物品：{item}，玩家属性为{game_state['stats']}。请描述使用物品后的效果，效果持续时间为 10 分钟，物品使用次数为 1 次。"
                    response = get_lm_response(prompt)
                    if response:
                        print(Fore.CYAN + response)
                        # 根据响应更新游戏状态
                        if "攻击提升" in response:
                            boost = int(response.split("攻击提升")[1].split()[0])
                            game_state["stats"]["攻击"] = min(game_state["stats"]["攻击"] + boost, game_state["max_stats"]["攻击"])
                        if "防御提升" in response:
                            boost = int(response.split("防御提升")[1].split()[0])
                            game_state["stats"]["防御"] = min(game_state["stats"]["防御"] + boost, game_state["max_stats"]["防御"])
                        if "魔法提升" in response:
                            boost = int(response.split("魔法提升")[1].split()[0])
                            game_state["stats"]["魔法"] = min(game_state["stats"]["魔法"] + boost, game_state["max_stats"]["魔法"])
                        save_game(game_state)
                    break
            else:
                print(Fore.RED + "输入无效，请重新输入。")
    else:
        print(Fore.YELLOW + "你没有任何物品可以使用。")

# 游戏主循环
def game_loop(game_state):
    print(Fore.GREEN + f"欢迎回来，{game_state['player_name']}！你现在位于 {game_state['location']}。")
    while True:
        print(Fore.YELLOW + "\n可用指令:")
        print(Fore.YELLOW + "1. 查看玩家信息：查看你的角色详细信息，包括等级、属性、物品栏等。")
        print(Fore.YELLOW + "2. 处理任务：查看并处理你当前接到的任务。")
        print(Fore.YELLOW + "3. 继续探索：在当前区域进行探索，可能会遇到新的任务或事件。")
        print(Fore.YELLOW + "4. 使用物品：使用你物品栏中的物品来提升属性。")
        print(Fore.YELLOW + "5. 保存并退出游戏：保存当前游戏进度并退出游戏。")
        while True:
            choice = input(Fore.YELLOW + "请输入指令编号: ")
            if choice.isdigit():
                choice = int(choice)
                if 1 <= choice <= 5:
                    break
            else:
                print(Fore.RED + "输入无效，请重新输入。")
        if choice == 1:
            show_player_info(game_state)
        elif choice == 2:
            handle_quests(game_state)
        elif choice == 3:
            current_location = game_state["location"]
            prompt = f"你是一名名为{game_state['player_name']}的{game_state['player_class']}，当前位于{current_location}，等级为{game_state['level']}，属性为{game_state['stats']}。请描述当前场景并给出一些可行的行动选项。"
            response = get_lm_response(prompt)
            if response:
                print(Fore.CYAN + response)
                while True:
                    action = input(Fore.YELLOW + "请输入你的行动（输入 '退出' 回到指令菜单）: ")
                    if action.lower() == '退出':
                        save_game(game_state)
                        break
                    
                    if not action:
                        print(Fore.RED + "行动不能为空，请重新输入。")
                        continue
                    
                    prompt = f"{response}\n玩家选择了: {action}，请描述接下来的情况。"
                    new_response = get_lm_response(prompt)
                    if new_response:
                        print(Fore.CYAN + new_response)
                        # 增强状态更新逻辑
                        state_updates = {
                            "location": game_state["location"],
                            "experience": game_state["experience"],
                            "inventory": game_state["inventory"],
                            "quests": game_state["quests"]
                        }
                        
                        # 解析经验值变化
                        if "获得经验" in new_response:
                            exp_gained = int(new_response.split("获得经验")[1].split()[0])
                            state_updates["experience"] += exp_gained
                        
                        # 解析物品获取
                        if "获得物品" in new_response:
                            item = new_response.split("获得物品")[1].split()[0]
                            state_updates["inventory"].append(item)
                        
                        # 解析任务更新
                        if "接受任务" in new_response or "发现任务" in new_response:
                            quest = new_response.split(":")[-1].strip()
                            if quest not in state_updates["quests"]:
                                state_updates["quests"].append(quest)
                        
                        # 更新游戏状态
                        game_state.update(state_updates)
                        
                        # 增强位置识别（支持更多动词和场景描述）
                        location_keywords = ["来到", "进入", "抵达", "到达", "移动至", "出现在"]
                        for keyword in location_keywords:
                            if keyword in new_response:
                                parts = new_response.split(keyword)
                                if len(parts) > 1:
                                    new_location = parts[1].split("。")[0].split("，")[0].strip()
                                    game_state["location"] = new_location
                                    break
                        
                        # 强制保存更新后的状态
                        save_game(game_state)
                        response = new_response
        elif choice == 4:
            use_item(game_state)
        elif choice == 5:
            save_game(game_state)
            print(Fore.GREEN + "游戏已保存，感谢游玩！")
            break

if __name__ == "__main__":
    game_state = init_game()
    game_loop(game_state)    