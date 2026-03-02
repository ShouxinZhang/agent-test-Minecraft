/**
 * Minecraft Agent - 自动化研究脚本
 * 无需人类干预，Bot 自动执行预定义的研究任务
 */
const mineflayer = require('mineflayer');
const { pathfinder, Movements, goals } = require('mineflayer-pathfinder');
const vec3 = require('vec3');

const CONFIG = {
  host: 'localhost',
  port: 25565,
  username: 'ResearchBot',
  version: '1.20.4',
};

const bot = mineflayer.createBot(CONFIG);
bot.loadPlugin(pathfinder);

// === 研究任务队列 ===
const tasks = [];

function addTask(name, fn) {
  tasks.push({ name, fn });
}

async function runTasks() {
  console.log(`[研究] 共 ${tasks.length} 个任务`);
  for (let i = 0; i < tasks.length; i++) {
    const task = tasks[i];
    console.log(`\n[任务 ${i + 1}/${tasks.length}] ${task.name}`);
    const startTime = Date.now();
    try {
      await task.fn();
      const elapsed = ((Date.now() - startTime) / 1000).toFixed(1);
      console.log(`[完成] ${task.name} (${elapsed}s)`);
    } catch (err) {
      console.error(`[失败] ${task.name}: ${err.message}`);
    }
  }
  console.log('\n[研究] 所有任务完成！');
}

// === 定义研究任务 ===

// 任务1: 环境感知 - 收集周围环境信息
addTask('环境感知', async () => {
  const pos = bot.entity.position;
  console.log(`  位置: (${pos.x.toFixed(1)}, ${pos.y.toFixed(1)}, ${pos.z.toFixed(1)})`);
  console.log(`  游戏模式: ${bot.game.gameMode}`);
  console.log(`  时间: ${bot.time.timeOfDay}`);
  console.log(`  天气: ${bot.isRaining ? '下雨' : '晴天'}`);

  // 扫描周围方块
  const blockTypes = {};
  for (let x = -5; x <= 5; x++) {
    for (let y = -3; y <= 3; y++) {
      for (let z = -5; z <= 5; z++) {
        const block = bot.blockAt(pos.offset(x, y, z));
        if (block && block.name !== 'air') {
          blockTypes[block.name] = (blockTypes[block.name] || 0) + 1;
        }
      }
    }
  }
  console.log('  附近方块统计:', JSON.stringify(blockTypes, null, 2));

  // 扫描周围实体
  const entities = Object.values(bot.entities)
    .filter(e => e !== bot.entity && e.position.distanceTo(pos) < 32)
    .map(e => ({ type: e.name || e.username || 'unknown', pos: e.position }));
  console.log(`  附近实体 (${entities.length}):`, entities.map(e => e.type));
});

// 任务2: 寻路测试 - 测试自动导航能力
addTask('寻路测试', async () => {
  const mcData = require('minecraft-data')(bot.version);
  const movements = new Movements(bot, mcData);
  bot.pathfinder.setMovements(movements);

  const pos = bot.entity.position;
  const targets = [
    pos.offset(10, 0, 0),
    pos.offset(10, 0, 10),
    pos.offset(0, 0, 10),
    pos.offset(0, 0, 0),  // 回到原点
  ];

  for (const target of targets) {
    console.log(`  导航到 (${target.x.toFixed(0)}, ${target.z.toFixed(0)})...`);
    try {
      await bot.pathfinder.goto(new goals.GoalNear(target.x, target.y, target.z, 2));
      console.log(`  到达！当前位置: ${bot.entity.position}`);
    } catch {
      console.log('  导航失败，跳过');
    }
  }
});

// 任务3: 世界观察 - 持续观察记录
addTask('世界观察 (10秒)', async () => {
  return new Promise((resolve) => {
    const observations = [];
    const interval = setInterval(() => {
      const pos = bot.entity.position;
      observations.push({
        time: bot.time.timeOfDay,
        pos: { x: pos.x.toFixed(1), y: pos.y.toFixed(1), z: pos.z.toFixed(1) },
        health: bot.health,
        entities_nearby: Object.values(bot.entities).filter(e => e !== bot.entity && e.position.distanceTo(pos) < 16).length,
      });
    }, 2000);

    setTimeout(() => {
      clearInterval(interval);
      console.log(`  收集了 ${observations.length} 条观察记录`);
      observations.forEach((obs, i) => {
        console.log(`    [${i}] 时间:${obs.time} 位置:(${obs.pos.x},${obs.pos.y},${obs.pos.z}) 附近:${obs.entities_nearby}个实体`);
      });
      resolve();
    }, 10000);
  });
});

// === 启动 ===
bot.once('spawn', async () => {
  console.log('[研究] Bot 已进入游戏世界');
  console.log('[研究] 等待 3 秒后开始执行研究任务...');
  await new Promise(r => setTimeout(r, 3000));
  await runTasks();
  console.log('[研究] 研究结束，断开连接');
  bot.quit();
  process.exit(0);
});

bot.on('error', (err) => console.error('[错误]', err.message));
bot.on('end', () => console.log('[连接] 断开'));
