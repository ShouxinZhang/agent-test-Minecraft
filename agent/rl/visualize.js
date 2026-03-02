/**
 * 训练统计可视化 - 在终端输出训练曲线（ASCII）
 * 用法: node visualize.js
 */
const fs = require('fs');
const path = require('path');

const LOG_PATH = path.join(__dirname, 'checkpoints', 'train_log.json');

function asciiPlot(title, data, width = 60, height = 15) {
  if (data.length === 0) return;

  const min = Math.min(...data);
  const max = Math.max(...data);
  const range = max - min || 1;

  console.log(`\n  ${title}`);
  console.log(`  ${'─'.repeat(width + 6)}`);

  for (let row = height - 1; row >= 0; row--) {
    const threshold = min + (range * row) / (height - 1);
    const label = threshold.toFixed(1).padStart(8);
    let line = `${label} │`;

    for (let col = 0; col < width; col++) {
      const idx = Math.floor((col / width) * data.length);
      const val = data[idx];
      if (val >= threshold) {
        line += '█';
      } else {
        line += ' ';
      }
    }
    console.log(line);
  }

  console.log(`${''.padStart(9)}└${'─'.repeat(width)}`);
  console.log(`${''.padStart(10)}Episode 1${' '.repeat(width - 15)}Episode ${data.length}`);
}

function movingAverage(data, window = 5) {
  const result = [];
  for (let i = 0; i < data.length; i++) {
    const start = Math.max(0, i - window + 1);
    const slice = data.slice(start, i + 1);
    result.push(slice.reduce((a, b) => a + b, 0) / slice.length);
  }
  return result;
}

function main() {
  if (!fs.existsSync(LOG_PATH)) {
    console.log('未找到训练日志，请先运行 train.js');
    process.exit(1);
  }

  const log = JSON.parse(fs.readFileSync(LOG_PATH, 'utf-8'));
  console.log('=== Minecraft RL 训练统计 ===');
  console.log(`总回合数: ${log.length}`);

  const rewards = log.map(l => parseFloat(l.reward));
  const steps = log.map(l => l.steps);
  const epsilons = log.map(l => parseFloat(l.epsilon));
  const reached = log.map(l => l.reached ? 1 : 0);

  // 基本统计
  const reachRate = reached.filter(x => x).length / reached.length * 100;
  const avgReward = rewards.reduce((a, b) => a + b, 0) / rewards.length;
  const reachedSteps = log.filter(l => l.reached).map(l => l.steps);
  const avgSteps = reachedSteps.length ? reachedSteps.reduce((a, b) => a + b, 0) / reachedSteps.length : 0;
  const minSteps = reachedSteps.length ? Math.min(...reachedSteps) : 'N/A';

  console.log(`\n到达率: ${reachRate.toFixed(1)}%`);
  console.log(`平均奖励: ${avgReward.toFixed(1)}`);
  console.log(`平均到达步数: ${avgSteps.toFixed(1)}`);
  console.log(`最短到达步数: ${minSteps}`);

  // 绘制曲线
  asciiPlot('奖励曲线 (每回合)', movingAverage(rewards, 5));
  asciiPlot('步数曲线 (每回合)', movingAverage(steps, 5));

  // 按场景统计
  console.log('\n  === 分场景统计 ===');
  const scenarios = [...new Set(log.map(l => l.scenario))];
  for (const s of scenarios) {
    const sLogs = log.filter(l => l.scenario === s);
    const sReached = sLogs.filter(l => l.reached);
    const sAvgSteps = sReached.length
      ? sReached.reduce((sum, l) => sum + l.steps, 0) / sReached.length
      : 'N/A';
    console.log(`  ${s}: 到达 ${sReached.length}/${sLogs.length} (${(sReached.length / sLogs.length * 100).toFixed(0)}%), 平均步数: ${typeof sAvgSteps === 'number' ? sAvgSteps.toFixed(1) : sAvgSteps}`);
  }
}

main();
