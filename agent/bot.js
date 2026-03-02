/**
 * Minecraft Agent 基础 Bot
 * 使用 Mineflayer 连接到离线模式的 PaperMC 服务器
 * 提供基础的 agent 行为框架
 */
const mineflayer = require('mineflayer');
const { pathfinder, Movements, goals } = require('mineflayer-pathfinder');
const collectBlock = require('mineflayer-collectblock').plugin;
const vec3 = require('vec3');

// === 配置 ===
const CONFIG = {
  host: 'localhost',
  port: 25565,
  username: 'AgentBot',       // 离线模式，任意用户名
  version: '1.20.4',
};

// === 创建 Bot ===
const bot = mineflayer.createBot(CONFIG);

// 加载插件
bot.loadPlugin(pathfinder);
bot.loadPlugin(collectBlock);

// === 事件处理 ===
bot.once('spawn', () => {
  console.log(`[Agent] 已连接到服务器，位置: ${bot.entity.position}`);
  console.log(`[Agent] 游戏模式: ${bot.game.gameMode}`);
  console.log(`[Agent] 生物群系: ${bot.entity.position}`);

  // 初始化寻路
  const mcData = require('minecraft-data')(bot.version);
  const movements = new Movements(bot, mcData);
  bot.pathfinder.setMovements(movements);

  console.log('[Agent] 寻路模块已初始化');
  console.log('[Agent] Bot 准备就绪！输入命令进行控制...');
});

bot.on('chat', (username, message) => {
  if (username === bot.username) return;
  console.log(`[聊天] <${username}> ${message}`);

  // 简单命令系统
  const args = message.split(' ');
  const cmd = args[0].toLowerCase();

  switch (cmd) {
    case 'come':
      comeToPlayer(username);
      break;
    case 'goto':
      if (args.length >= 4) {
        gotoPosition(parseInt(args[1]), parseInt(args[2]), parseInt(args[3]));
      }
      break;
    case 'look':
      lookAround();
      break;
    case 'inventory':
      showInventory();
      break;
    case 'dig':
      digBelow();
      break;
    case 'status':
      showStatus();
      break;
    case 'explore':
      exploreRandomly();
      break;
    case 'help':
      showHelp();
      break;
  }
});

bot.on('health', () => {
  console.log(`[状态] 生命: ${bot.health} | 饱食: ${bot.food}`);
});

bot.on('death', () => {
  console.log('[Agent] Bot 死亡，等待重生...');
});

bot.on('error', (err) => {
  console.error('[错误]', err.message);
});

bot.on('end', () => {
  console.log('[Agent] 连接断开');
});

// === Agent 行为函数 ===

async function comeToPlayer(username) {
  const player = bot.players[username];
  if (!player || !player.entity) {
    bot.chat('我看不到你，离近一点！');
    return;
  }
  const goal = new goals.GoalNear(player.entity.position.x, player.entity.position.y, player.entity.position.z, 2);
  bot.chat(`正在向 ${username} 移动...`);
  try {
    await bot.pathfinder.goto(goal);
    bot.chat('我到了！');
  } catch (err) {
    bot.chat('找不到路径过去...');
  }
}

async function gotoPosition(x, y, z) {
  bot.chat(`正在前往 (${x}, ${y}, ${z})...`);
  try {
    await bot.pathfinder.goto(new goals.GoalBlock(x, y, z));
    bot.chat('到达目标位置！');
  } catch (err) {
    bot.chat('无法到达该位置');
  }
}

function lookAround() {
  const entities = Object.values(bot.entities).filter(e => e !== bot.entity);
  const nearby = entities
    .map(e => ({ name: e.name || e.username || 'unknown', dist: e.position.distanceTo(bot.entity.position) }))
    .filter(e => e.dist < 32)
    .sort((a, b) => a.dist - b.dist)
    .slice(0, 10);

  bot.chat(`附近实体 (${nearby.length}): ${nearby.map(e => `${e.name}(${e.dist.toFixed(1)}m)`).join(', ') || '无'}`);

  // 打印附近方块信息
  const pos = bot.entity.position;
  const blockBelow = bot.blockAt(pos.offset(0, -1, 0));
  console.log(`[环境] 脚下方块: ${blockBelow?.name || 'unknown'}`);
}

function showInventory() {
  const items = bot.inventory.items();
  if (items.length === 0) {
    bot.chat('背包是空的');
  } else {
    const itemList = items.map(i => `${i.name}x${i.count}`).join(', ');
    bot.chat(`背包: ${itemList}`);
  }
}

async function digBelow() {
  const blockBelow = bot.blockAt(bot.entity.position.offset(0, -1, 0));
  if (blockBelow && bot.canDigBlock(blockBelow)) {
    bot.chat(`正在挖掘 ${blockBelow.name}...`);
    try {
      await bot.dig(blockBelow);
      bot.chat('挖掘完成！');
    } catch (err) {
      bot.chat('挖掘失败');
    }
  } else {
    bot.chat('脚下没有可挖掘的方块');
  }
}

function showStatus() {
  const pos = bot.entity.position;
  bot.chat(`位置: (${pos.x.toFixed(1)}, ${pos.y.toFixed(1)}, ${pos.z.toFixed(1)}) | 生命: ${bot.health} | 饱食: ${bot.food}`);
}

async function exploreRandomly() {
  const pos = bot.entity.position;
  const dx = Math.floor(Math.random() * 40) - 20;
  const dz = Math.floor(Math.random() * 40) - 20;
  const target = pos.offset(dx, 0, dz);
  bot.chat(`探索中... 目标: (${target.x.toFixed(0)}, ${target.z.toFixed(0)})`);
  try {
    await bot.pathfinder.goto(new goals.GoalNear(target.x, target.y, target.z, 3));
    bot.chat('探索到达！');
  } catch (err) {
    bot.chat('探索路径受阻');
  }
}

function showHelp() {
  bot.chat('命令: come | goto x y z | look | inventory | dig | status | explore | help');
}

console.log('[Agent] 正在连接到 Minecraft 服务器...');
