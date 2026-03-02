/**
 * RL 评估脚本 - 使用训练好的 Q 表进行最短路径评估
 *
 * 功能：
 * 1. 加载训练好的 Q 表
 * 2. 用贪心策略（无探索）评估路径
 * 3. 打印路径轨迹和对比最优距离
 *
 * 用法：node eval.js
 */
const { MinecraftPathEnv, ACTION_NAMES, NUM_ACTIONS } = require('./env');
const { QLearningAgent } = require('./q_agent');
const fs = require('fs');
const path = require('path');

const Q_TABLE_PATH = path.join(__dirname, 'checkpoints', 'q_table.json');

const EVAL_SCENARIOS = [
  { name: '直线导航', start: { x: 100, y: 150, z: -40 }, goal: { x: 120, y: 150, z: -40 } },
  { name: '对角导航', start: { x: 100, y: 150, z: -40 }, goal: { x: 115, y: 150, z: -25 } },
  { name: '短距离', start: { x: 100, y: 150, z: -40 }, goal: { x: 108, y: 150, z: -40 } },
];

async function evaluate() {
  console.log('=== Minecraft RL 最短路径评估 ===\n');

  const agent = new QLearningAgent();
  if (!agent.load(Q_TABLE_PATH)) {
    console.log('错误: 未找到训练好的 Q 表，请先运行 train.js');
    process.exit(1);
  }

  const env = new MinecraftPathEnv({
    username: 'RLEvaluator',
    maxSteps: 200,
    reachDist: 2.5,
  });

  console.log('[评估] 连接服务器...');
  await env.connect();
  await new Promise(r => setTimeout(r, 2000));

  for (const scenario of EVAL_SCENARIOS) {
    console.log(`\n--- 场景: ${scenario.name} ---`);
    const directDist = Math.sqrt(
      (scenario.goal.x - scenario.start.x) ** 2 +
      (scenario.goal.z - scenario.start.z) ** 2
    );
    console.log(`  直线距离: ${directDist.toFixed(1)} 格`);

    const state0 = await env.reset(scenario.goal, scenario.start);
    await new Promise(r => setTimeout(r, 500));

    let state = state0;
    let totalReward = 0;
    const trajectory = [];

    while (!env.done) {
      // 贪心策略（不探索）
      const action = agent.chooseAction(state, false);
      const { state: nextState, reward, done, info } = await env.step(action);

      trajectory.push({
        step: env.stepCount,
        action: ACTION_NAMES[action],
        pos: `(${info.pos.x.toFixed(1)}, ${info.pos.y.toFixed(1)}, ${info.pos.z.toFixed(1)})`,
        dist: info.dist.toFixed(1),
        reward: reward.toFixed(1),
      });

      totalReward += reward;
      state = nextState;
    }

    // 打印轨迹
    console.log(`  总步数: ${env.stepCount}`);
    console.log(`  总奖励: ${totalReward.toFixed(1)}`);
    console.log(`  到达: ${totalReward > 50 ? '✅' : '❌'}`);
    console.log(`  效率: ${(directDist / env.stepCount).toFixed(2)} 格/步 (理想 ≈ 1.0)`);
    console.log('  轨迹:');
    trajectory.forEach(t => {
      console.log(`    步${t.step}: ${t.action.padEnd(6)} → ${t.pos} (距离: ${t.dist}, R: ${t.reward})`);
    });
  }

  await env.disconnect();
  console.log('\n[评估] 完成！');
  process.exit(0);
}

evaluate().catch(err => {
  console.error('[评估错误]', err);
  process.exit(1);
});
