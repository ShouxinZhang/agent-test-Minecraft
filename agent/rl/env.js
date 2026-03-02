/**
 * Minecraft RL 环境 - Gym-like 接口
 * 任务：从起点导航到目标点，寻找最短路径
 *
 * 状态空间：离散化的 (dx, dy, dz) 相对目标的偏移
 * 动作空间：6 个方向移动 (前/后/左/右/跳/下蹲前进)
 * 奖励：
 *   - 每步 -1（鼓励最短路径）
 *   - 到达目标 +100
 *   - 靠近目标 +距离差 * 5
 *   - 远离目标 -距离差 * 5
 *   - 掉入虚空 / 超时 -50
 */
const mineflayer = require('mineflayer');
const vec3 = require('vec3');

// 动作定义
const ACTIONS = {
  FORWARD:  0,   // +Z
  BACK:     1,   // -Z
  LEFT:     2,   // -X
  RIGHT:    3,   // +X
  JUMP_FWD: 4,   // 跳跃前进
  SNEAK_FWD: 5,  // 下蹲前进（可下边缘）
};
const ACTION_NAMES = ['前进', '后退', '左移', '右移', '跳跃前进', '下蹲前进'];
const NUM_ACTIONS = Object.keys(ACTIONS).length;

class MinecraftPathEnv {
  constructor(config = {}) {
    this.host = config.host || 'localhost';
    this.port = config.port || 25565;
    this.version = config.version || '1.20.4';
    this.username = config.username || `RLBot_${Math.floor(Math.random() * 1000)}`;

    // 任务参数
    this.goalPos = config.goalPos || null;       // 目标位置 (运行时设置)
    this.startPos = config.startPos || null;     // 起始位置
    this.maxSteps = config.maxSteps || 200;      // 每回合最大步数
    this.reachDist = config.reachDist || 2.0;    // 到达判定距离
    this.gridSize = config.gridSize || 1.0;      // 状态离散化精度

    // 内部状态
    this.bot = null;
    this.stepCount = 0;
    this.prevDist = Infinity;
    this.done = false;
    this.connected = false;
  }

  /**
   * 连接到 Minecraft 服务器
   */
  async connect() {
    return new Promise((resolve, reject) => {
      this.bot = mineflayer.createBot({
        host: this.host,
        port: this.port,
        username: this.username,
        version: this.version,
      });

      this.bot.once('spawn', () => {
        this.connected = true;
        console.log(`[Env] ${this.username} 已连接，位置: ${this.bot.entity.position}`);
        resolve();
      });

      this.bot.on('error', (err) => {
        if (!this.connected) reject(err);
      });
    });
  }

  /**
   * 重置环境，开始新回合
   */
  async reset(goalPos, startPos) {
    if (goalPos) this.goalPos = vec3(goalPos.x, goalPos.y, goalPos.z);
    if (startPos) this.startPos = vec3(startPos.x, startPos.y, startPos.z);

    this.stepCount = 0;
    this.done = false;

    // 传送到起点
    if (this.startPos) {
      this.bot.chat(`/tp ${this.username} ${this.startPos.x} ${this.startPos.y} ${this.startPos.z}`);
      await this._wait(500);
    }

    this.prevDist = this._distToGoal();
    return this._getState();
  }

  /**
   * 执行一个动作，返回 { state, reward, done, info }
   */
  async step(action) {
    if (this.done) throw new Error('Episode already done, call reset()');

    this.stepCount++;
    const posBefore = this.bot.entity.position.clone();

    // 执行动作
    await this._executeAction(action);
    await this._wait(350);  // 等待服务器更新

    // 停止所有移动
    this._stopMovement();

    const posAfter = this.bot.entity.position.clone();
    const dist = this._distToGoal();
    const distDelta = this.prevDist - dist;

    // 计算奖励
    let reward = -1;  // 时间惩罚

    if (dist <= this.reachDist) {
      // 到达目标
      reward = 100;
      this.done = true;
    } else if (posAfter.y < -60) {
      // 掉入虚空
      reward = -50;
      this.done = true;
    } else if (this.stepCount >= this.maxSteps) {
      // 超时
      reward = -50;
      this.done = true;
    } else {
      // 距离变化奖励
      reward += distDelta * 5;

      // 原地不动惩罚
      const moved = posBefore.distanceTo(posAfter);
      if (moved < 0.1) {
        reward -= 3;
      }
    }

    this.prevDist = dist;

    const state = this._getState();
    const info = {
      pos: posAfter,
      dist: dist,
      steps: this.stepCount,
      action: ACTION_NAMES[action],
    };

    return { state, reward, done: this.done, info };
  }

  /**
   * 获取离散化状态 - 相对目标的偏移量
   */
  _getState() {
    const pos = this.bot.entity.position;
    const dx = Math.round((pos.x - this.goalPos.x) / this.gridSize);
    const dy = Math.round((pos.y - this.goalPos.y) / this.gridSize);
    const dz = Math.round((pos.z - this.goalPos.z) / this.gridSize);

    // 附近方块信息（前方是否有障碍）
    const blockFront = this.bot.blockAt(pos.offset(0, 0, 1));
    const blockAbove = this.bot.blockAt(pos.offset(0, 1, 0));
    const isBlockedFront = blockFront && blockFront.name !== 'air';
    const isBlockedAbove = blockAbove && blockAbove.name !== 'air';

    return `${dx},${dy},${dz},${isBlockedFront ? 1 : 0},${isBlockedAbove ? 1 : 0}`;
  }

  /**
   * 执行具体动作
   */
  async _executeAction(action) {
    this._stopMovement();

    switch (action) {
      case ACTIONS.FORWARD:
        this.bot.setControlState('forward', true);
        break;
      case ACTIONS.BACK:
        this.bot.setControlState('back', true);
        break;
      case ACTIONS.LEFT:
        this.bot.setControlState('left', true);
        break;
      case ACTIONS.RIGHT:
        this.bot.setControlState('right', true);
        break;
      case ACTIONS.JUMP_FWD:
        this.bot.setControlState('forward', true);
        this.bot.setControlState('jump', true);
        break;
      case ACTIONS.SNEAK_FWD:
        this.bot.setControlState('forward', true);
        this.bot.setControlState('sneak', true);
        break;
    }
  }

  _stopMovement() {
    ['forward', 'back', 'left', 'right', 'jump', 'sneak'].forEach(ctrl => {
      this.bot.setControlState(ctrl, false);
    });
  }

  _distToGoal() {
    return this.bot.entity.position.distanceTo(this.goalPos);
  }

  _wait(ms) {
    return new Promise(r => setTimeout(r, ms));
  }

  async disconnect() {
    if (this.bot) {
      this.bot.quit();
      this.connected = false;
    }
  }
}

module.exports = { MinecraftPathEnv, ACTIONS, ACTION_NAMES, NUM_ACTIONS };
