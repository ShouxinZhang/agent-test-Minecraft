/**
 * Q-Learning Agent
 * 使用 ε-greedy 策略的表格型 Q-Learning
 * 支持保存/加载 Q 表
 */
const fs = require('fs');
const path = require('path');
const { NUM_ACTIONS } = require('./env');

class QLearningAgent {
  constructor(config = {}) {
    this.alpha = config.alpha || 0.1;          // 学习率
    this.gamma = config.gamma || 0.99;         // 折扣因子
    this.epsilon = config.epsilon || 1.0;      // 探索率
    this.epsilonMin = config.epsilonMin || 0.05;
    this.epsilonDecay = config.epsilonDecay || 0.995;
    this.numActions = config.numActions || NUM_ACTIONS;

    this.qTable = {};  // { state: [q_values] }
    this.trainSteps = 0;
  }

  /**
   * 获取某状态的 Q 值数组，不存在则初始化为 0
   */
  _getQ(state) {
    if (!this.qTable[state]) {
      this.qTable[state] = new Array(this.numActions).fill(0);
    }
    return this.qTable[state];
  }

  /**
   * ε-greedy 策略选择动作
   */
  chooseAction(state, explore = true) {
    if (explore && Math.random() < this.epsilon) {
      return Math.floor(Math.random() * this.numActions);
    }
    const qValues = this._getQ(state);
    // 选最大 Q 值对应的动作（相同时随机选）
    const maxQ = Math.max(...qValues);
    const bestActions = qValues
      .map((q, i) => ({ q, i }))
      .filter(x => Math.abs(x.q - maxQ) < 1e-8)
      .map(x => x.i);
    return bestActions[Math.floor(Math.random() * bestActions.length)];
  }

  /**
   * Q-Learning 更新
   */
  update(state, action, reward, nextState, done) {
    const qValues = this._getQ(state);
    const nextQValues = this._getQ(nextState);

    const target = done
      ? reward
      : reward + this.gamma * Math.max(...nextQValues);

    qValues[action] += this.alpha * (target - qValues[action]);
    this.trainSteps++;
  }

  /**
   * 衰减探索率
   */
  decayEpsilon() {
    this.epsilon = Math.max(this.epsilonMin, this.epsilon * this.epsilonDecay);
  }

  /**
   * 保存 Q 表到文件
   */
  save(filepath) {
    const data = {
      qTable: this.qTable,
      epsilon: this.epsilon,
      trainSteps: this.trainSteps,
      stateCount: Object.keys(this.qTable).length,
    };
    fs.writeFileSync(filepath, JSON.stringify(data, null, 2));
    console.log(`[Agent] Q表已保存: ${Object.keys(this.qTable).length} 个状态, ε=${this.epsilon.toFixed(4)}`);
  }

  /**
   * 从文件加载 Q 表
   */
  load(filepath) {
    if (!fs.existsSync(filepath)) {
      console.log('[Agent] 未找到已有 Q 表，从零开始训练');
      return false;
    }
    const data = JSON.parse(fs.readFileSync(filepath, 'utf-8'));
    this.qTable = data.qTable;
    this.epsilon = data.epsilon;
    this.trainSteps = data.trainSteps || 0;
    console.log(`[Agent] Q表已加载: ${Object.keys(this.qTable).length} 个状态, ε=${this.epsilon.toFixed(4)}`);
    return true;
  }

  /**
   * 打印统计信息
   */
  stats() {
    return {
      states: Object.keys(this.qTable).length,
      epsilon: this.epsilon.toFixed(4),
      trainSteps: this.trainSteps,
    };
  }
}

module.exports = { QLearningAgent };
