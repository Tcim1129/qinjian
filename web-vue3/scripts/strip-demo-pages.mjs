// 生产构建后清掉只给本地演示和设计参考用的静态文件。
// public/ 里的东西会被 vite 原样拷进 dist，这里在构建完成后剔除，本地 dev 仍然可以用它们。
import { rm } from 'node:fs/promises';
import { existsSync } from 'node:fs';
import path from 'node:path';

const dist = path.resolve(process.cwd(), 'dist');
const targets = [
  'preview-demo.html',
  'relationship-space-lab.html',
  'agent-demo-reference.png',
  'competition',
];

if (!existsSync(dist)) {
  console.error('没有找到 dist 目录，先跑 vite build。');
  process.exit(1);
}

for (const target of targets) {
  const full = path.join(dist, target);
  if (!existsSync(full)) continue;
  await rm(full, { recursive: true, force: true });
  console.log(`已从 dist 移除 ${target}`);
}
