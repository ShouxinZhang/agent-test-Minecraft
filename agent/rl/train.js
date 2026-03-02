/**
 * RL 最短路径训练脚本
 *
 * 训练流程：
 * 1. 连接 Minecraft 服务器
 * 2. 在服务器上建立训练场地（平坦地面 + 目标标记）
 * 3. 进行多轮训练，Q-Learning 逐步学习最短路径
 * 4. 定期保存 Q 表和训练统计
 *
 * 用法：node train.js [episodes] [--resume]
 */
const { MinecraftPathEnv, ACTION_NAMES } = require('./env');
const { QLearningAgent } = require('./q_agent');
const fs = require('fs');
const path = require('path');

// === 训练配置 ===
const TOTAL_EPISODES = parseInt(process.argv[2]) || 50;
const RESUME = process.argv.includes('--resume');
const SAVE_DIR = path.join(__dirname, 'checkpoints');
const Q_TABLE_PATH = path.join(SAVE_DIR, 'q_table.json');
const LOG_PATH = path.join(SAVE_DIR, 'train_log.json');

// 训练场景：从起点到达目标点（直线距离约 20 格）
const SCENARIOS = [
  { name: '直线导航', start: { x: 100, y: 150, z: -40 }, goal: { x: 120, y: 150, z: -40 } },
  { name: '对角导航', start: { x: 100, y: 150, z: -40 }, goal: { x: 115, y: 150, z: -25 } },
  { name: '短距离', start: { x: 100, y: 150, z: -40 }, goal: { x: 108, y: 150, z: -40 } },
];

async function setupArena(env) {
  console.log('[训练] 设置训练场地...');
  // 用命令方块在目标位置放置标记（金块）
  for (const s of SCENARIOS) {
    env.bot.chat(`/setblock ${s.goal.x} ${s.goal.y - 1} ${s.goal.z} gold_block`);
    // 确保起点附近是平坦的
    env.bot.chat(`/fill ${s.start.x - 2} ${s.start.y - 1} ${s.start.z - 2} ${s.start.x + 2} ${s.start.y - 1} ${s.start.z + 2} stone`);
    // 确保路径区域平坦
    const minX = Math.min(s.start.x, s.goal.x) - 3;
    const maxX = Math.max(s.start.x, s.goal.x) + 3;
    const minZ = Math.min(s.start.z, s.goal.z) - 3;
    const maxZ = Math.max(s.start.z, s.goal.z) + 3;
    env.bot.chat(`/fill ${minX} ${s.start.y - 1} ${minZ} ${maxX} ${s.start.y - 1} ${maxZ} stone`);
    // 清除路径上方的障碍
    env.bot.chat(`/fill ${minX} ${s.start.y} ${minZ} ${maxX} ${s.start.y + 3} ${maxZ} air`);
  }
  await new Promise(r => setTimeout(r, 1000));
  console.log('[训练] 场地设置完成');
}

async function train() {
  console.log('=== Minecraft RL 最短路径训练 ===');
  console.log(`  回合数: ${TOTAL_EPISODES}`);
  console.log(`  续训: ${RESUME}`);
  console.log(`  场景: ${SCENARIOS.map(s => s.name).join(', ')}`);

  // 创建保存目录
  if (!fs.existsSync(SAVE_DIR)) fs.mkdirSync(SAVE_DIR, { recursive: true });

  // 初始化环境和 Agent
  const env = new MinecraftPathEnv({
    username: 'RLTrainer',
    maxSteps: 150,
    reachDist: 2.5,
    gridSize: 1.0,
  });

  const agent = new QLearningAgent({
    alpha: 0.15,
    gamma: 0.95,
    epsilon: RESUME ? undefined : 1.0,
    epsilonMin: 0.05,
    epsilonDecay: 0.99,
  });

  // 加载已有 Q 表
  if (RESUME) agent.load(Q_TABLE_PATH);

  // 连接服务器
  console.log('[训练] 连接服务器...');
  await env.connect();
  await new Promise(r => setTimeout(r, 2000));

  // 设置训练场地
  await setupArena(env);

  // 训练日志
  const trainLog = [];
  let bestReward = -Infinity;
  let bestSteps = Infinity;

  // === 训练循环 ===
  for (let ep = 1; ep <= TOTAL_EPISODES; ep++) {
    // 随机选择场景
    const scenario = SCENARIOS[ep % SCENARIOS.length];
    const state0 = await env.reset(scenario.goal, scenario.start);
    await new Promise(r => setTimeout(r, 500));

    let state = state0;
    let totalReward = 0;
    let trajectory = [];

    // 回合循环
    while (!env.done) {
      const action = agent.chooseAction(state);
      const { state: nextState, reward, done, info } = await env.step(action);

      agent.update(state, action, reward, nextState, done);

      trajectory.push({ s: state, a: ACTION_NAMES[action], r: reward.toFixed(1) });
      totalReward += reward;
      state = nextState;
    }

    agent.decayEpsilon();

    // 记录
    const epLog = {
      episode: ep,
      scenario: scenario.name,
      steps: env.stepCount,
      reward: totalReward.toFixed(1),
      epsilon: agent.epsilon.toFixed(4),
      states: Object.keys(agent.qTable).length,
      reached: totalReward > 50,
    };
    trainLog.push(epLog);

    // 打印进度
    const reachedStr = epLog.reached ? '✅ 到达' : '❌ 未到达';
    console.log(
      `[Episode ${ep}/${TOTAL_EPISODES}] ${scenario.name} | ` +
      `步数: ${env.stepCount} | 奖励: ${totalReward.toFixed(1)} | ` +
      `${reachedStr} | ε: ${agent.epsilon.toFixed(3)} | Q表: ${Object.keys(agent.qTable).length}个状态`
    );

    // 记录最优
    if (epLog.reached && env.stepCount < bestSteps) {
      bestSteps = env.stepCount;
      bestReward = totalReward;
      console.log(`  🏆 新最短路径！${bestSteps} 步`);
    }

    // 定期保存
    if (ep % 10 === 0 || ep === TOTAL_EPISODES) {
      agent.save(Q_TABLE_PATH);
      fs.writeFileSync(LOG_PATH, JSON.stringify(trainLog, null, 2));
      console.log(`[保存] 检查点已保存 (Episode ${ep})`);
    }
  }

  // === 训练总结 ===
  console.log('\n========== 训练总结 ==========');
  console.log(`总回合数: ${TOTAL_EPISODES}`);
  console.log(`Q 表状态数: ${Object.keys(agent.qTable).length}`);
  console.log(`最终 ε: ${agent.epsilon.toFixed(4)}`);
  console.log(`最短到达步数: ${bestSteps === Infinity ? '未到达' : bestSteps}`);

  const reached = trainLog.filter(l => l.reached).length;
  console.log(`到达率: ${reached}/${TOTAL_EPISODES} (${(reached / TOTAL_EPISODES * 100).toFixed(1)}%)`);

  // 按场景统计
  for (const s of SCENARIOS) {
    const scenarioLogs = trainLog.filter(l => l.scenario === s.name);
    const scenarioReached = scenarioLogs.filter(l => l.reached).length;
    const avgSteps = scenarioLogs.filter(l => l.reached).reduce((sum, l) => sum + l.steps, 0) / (scenarioReached || 1);
    console.log(`  ${s.name}: 到达 ${scenarioReached}/${scenarioLogs.length}, 平均步数: ${avgSteps.toFixed(1)}`);
  }

  // 最终保存
  agent.save(Q_TABLE_PATH);
  fs.writeFileSync(LOG_PATH, JSON.stringify(trainLog, null, 2));

  await env.disconnect();
  console.log('[训练] 完成！');
  process.exit(0);
}

train().catch(err => {
  console.error('[训练错误]', err);
  process.exit(1);
});
