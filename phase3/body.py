"""
SereneX Phase 3 — 身体控制系统（Body Control）
将意图转化为 Minecraft 动作序列，通过 Mineflayer 执行
"""
import subprocess
import json
import time
from dataclasses import dataclass
from typing import Optional


@dataclass
class BodyState:
    """Avatar 身体状态"""
    position: tuple[float, float, float] = (0, 0, 0)
    health: float = 20.0
    hunger: float = 20.0
    inventory: dict = None
    held_item: str = "空"
    is_moving: bool = False
    velocity: tuple[float, float, float] = (0, 0, 0)
    yaw: float = 0.0
    pitch: float = 0.0

    def __post_init__(self):
        if self.inventory is None:
            self.inventory = {}


@dataclass
class WorldState:
    """Minecraft 世界状态快照"""
    nearby_blocks: list[dict] = None
    nearby_entities: list[dict] = None
    time_of_day: str = "day"
    weather: str = "clear"
    biome: str = "unknown"
    block_under_feet: str = "air"

    def __post_init__(self):
        if self.nearby_blocks is None:
            self.nearby_blocks = []
        if self.nearby_entities is None:
            self.nearby_entities = []


class MinecraftBridge:
    """
    Python ↔ Mineflayer 的桥接层
    通过 Node.js 子进程调用 mineflayer API
    """

    def __init__(self, host: str = "localhost", port: int = 25565, mineflayer_script: str = None):
        self.host = host
        self.port = port
        self.script_path = mineflayer_script or "/workspace/SereneX/phase3/minecraft/bridge.js"
        self.running = False

    def _run_js(self, command: str, timeout: int = 10) -> dict:
        """通过 Node.js 执行 Mineflayer 命令"""
        try:
            result = subprocess.run(
                ["node", "-e", f"""
const{{ createMineflayer }}{{from'mineflayer'}};
const mineflayer = createMineflayer({{host:'{self.host}',port:{self.port}}});
mineflayer.once('spawn',()=>{{
  mineflayer.once('healthChanged',()=>{{}});
}});
{command}
setTimeout(()=>{{process.send(JSON.stringify({{ok:true}}));process.exit(0);}},{timeout*500});
"""],
                capture_output=True, text=True, timeout=timeout
            )
            return json.loads(result.stdout.strip())
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def get_world_state(self) -> WorldState:
        """获取当前世界状态"""
        # 简化版：通过 MCP 服务器查询（待接入真实服务器）
        return WorldState(
            time_of_day="day",
            weather="clear",
            biome="plains"
        )

    def execute_action(self, action: str, target: str = "") -> dict:
        """执行 Minecraft 动作"""
        actions = {
            "move_forward": "bot.setControlState('forward',true)",
            "move_back": "bot.setControlState('back',true)",
            "jump": "bot.setControlState('jump',true)",
            "look_at_block": f"bot.lookAt(bot.entity.position.offset(0,0,1))",
            "attack": "bot.attack(bot.nearestEntity())",
            "use_item": "bot.useItem()",
            "place_block": f"bot.placeBlock(bot.targetedBlock.offset(0,1,0),{{face:'top'}})",
            "collect": "bot.collectBlocks.reachUp()",
            "craft": "bot.craft()",
            "equip": "bot.equip(bot.inventory.slots[0],'hand')",
        }

        cmd = actions.get(action, f"// unknown action: {action}")
        return self._run_js(cmd)


class BodyController:
    """
    身体控制器：将 LLM 生成的意图 plan_steps 转化为 Minecraft 动作
    """

    def __init__(self, ch_name: str, bridge: Optional[MinecraftBridge] = None):
        self.ch_name = ch_name
        self.bridge = bridge or MinecraftBridge()
        self.body_state = BodyState()
        self.action_history: list[dict] = []

    def execute_plan(self, plan_steps: list[str], world_state: WorldState) -> dict:
        """
        执行动作计划
        plan_steps: ["走向那棵树", "砍树", "收集木材", ...]
        """
        results = []
        for step in plan_steps:
            result = self._step_to_action(step, world_state)
            results.append(result)
            self.action_history.append({
                "step": step,
                "action": result.get("action", ""),
                "success": result.get("ok", False),
                "timestamp": time.time()
            })
            time.sleep(1)  # 动作间隔

        return {
            "completed": len([r for r in results if r.get("ok")]),
            "total": len(plan_steps),
            "details": results
        }

    def _step_to_action(self, step: str, world_state: WorldState) -> dict:
        """将自然语言步骤转为 Minecraft action"""
        step_lower = step.lower()

        # 移动动作
        if "走" in step or "向" in step or "移动" in step_lower or "去" in step_lower:
            return self._execute_movement(step, world_state)

        # 砍/破坏
        elif "砍" in step or "破坏" in step_lower or "挖掘" in step_lower or "挖" in step_lower:
            return {"action": "Dig", "ok": True, "description": "开始挖掘"}

        # 收集/捡起
        elif "收集" in step or "捡" in step or "拿" in step_lower:
            return {"action": "Collect", "ok": True, "description": "收集物品"}

        # 建造
        elif "建造" in step_lower or "放置" in step_lower or "建" in step_lower:
            return {"action": "Place", "ok": True, "description": "放置方块"}

        # 观察/看
        elif "看" in step or "观察" in step_lower or "环顾" in step_lower:
            return {"action": "Look", "ok": True, "description": "环顾四周"}

        # 等待/休息
        elif "等待" in step_lower or "休息" in step_lower or "睡觉" in step_lower:
            return {"action": "Rest", "ok": True, "description": "原地休息"}

        # 交互
        elif "交互" in step_lower or "使用" in step_lower:
            return {"action": "UseItem", "ok": True, "description": "使用物品"}

        return {"action": "Unknown", "ok": False, "description": f"未知动作: {step}"}

    def _execute_movement(self, step: str, world_state: WorldState) -> dict:
        """处理移动指令"""
        # 从步骤中提取方向
        direction_map = {
            "北": ("forward", 0), "南": ("back", 0),
            "东": ("right", 0), "西": ("left", 0),
            "前": ("forward", 0), "后": ("back", 0),
        }

        for keyword, (control, _) in direction_map.items():
            if keyword in step:
                return {
                    "action": f"Move:{control}",
                    "ok": True,
                    "description": f"向{keyword}移动"
                }

        # 默认向前走
        return {"action": "Move:forward", "ok": True, "description": "向前移动"}

    def update_body_state(self, world_state: WorldState):
        """根据世界状态更新身体感知"""
        self.body_state.position = (0, 0, 0)  # 待从Minecraft读取真实位置
        self.body_state.block_under_feet = world_state.block_under_feet

    def get_available_actions(self) -> list[str]:
        """返回当前可执行的动作列表"""
        return [
            "move_forward", "move_back", "move_left", "move_right",
            "jump", "sprint", "crouch",
            "attack", "use_item", "place_block",
            "look_around", "collect_blocks",
            "craft_item", "equip_item",
            "dig", "inventory_show"
        ]

    def get_body_status_report(self) -> str:
        """生成身体状态报告（用于感知输入）"""
        return (
            f"位置：{self.body_state.position}；"
            f"生命值：{self.body_state.health:.0f}；"
            f"饥饿度：{self.body_state.hunger:.0f}；"
            f"手持：{self.body_state.held_item}；"
            f"脚下：{self.body_state.block_under_feet}"
        )
