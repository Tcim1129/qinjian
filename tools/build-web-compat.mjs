import { mkdirSync, existsSync } from 'node:fs';
import path from 'node:path';
import { spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const rootDir = path.resolve(__dirname, '..');
const webDir = path.join(rootDir, 'web');
const sourceDir = path.join(webDir, 'js');
const outDir = path.join(webDir, 'js-compat');

const entries = [
    'demo-fixtures.js',
    'api.js',
    'client-ai.js',
    'client-ai-worker.js',
    'app.js',
    'handmade.js',
];

function resolveEsbuildBinary() {
    const candidates = process.platform === 'win32'
        ? [
            path.join(rootDir, 'qinjian-app', 'qingjian app', 'node_modules', 'esbuild-windows-64', 'esbuild.exe'),
            path.join(rootDir, 'qinjian-app', 'qingjian app', 'node_modules', '.bin', 'esbuild.cmd'),
            path.join(rootDir, 'qinjian-app', 'qingjian app', 'node_modules', '.bin', 'esbuild'),
        ]
        : [
            path.join(rootDir, 'qinjian-app', 'qingjian app', 'node_modules', '.bin', 'esbuild'),
        ];

    const match = candidates.find((item) => existsSync(item));
    if (!match) {
        throw new Error('未找到可用的 esbuild，可先检查 qinjian-app/qingjian app/node_modules/.bin。');
    }
    return match;
}

function buildEntry(esbuildBin, entry) {
    const inputFile = path.join(sourceDir, entry);
    const outFile = path.join(outDir, entry);
    const args = [
        inputFile,
        '--target=es2018',
        '--charset=utf8',
        '--log-level=warning',
        `--outfile=${outFile}`,
    ];
    const result = spawnSync(
        esbuildBin,
        args,
        {
            cwd: rootDir,
            stdio: 'inherit',
            shell: false,
        },
    );

    if (result.status !== 0) {
        throw new Error(`构建失败：${entry}`);
    }
}

function main() {
    mkdirSync(outDir, { recursive: true });
    const esbuildBin = resolveEsbuildBinary();
    for (const entry of entries) {
        buildEntry(esbuildBin, entry);
    }
    console.log(`兼容脚本已生成到 ${outDir}`);
}

main();
