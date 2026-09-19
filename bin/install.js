#!/usr/bin/env node

const fs = require('fs');
const path = require('path');
const os = require('os');

console.log('🏛️  Installing arch-wiki AI Skill...\n');

const rootDir = path.join(__dirname, '..');
const skillFile = path.join(rootDir, 'SKILL.md');
const templateFile = path.join(rootDir, 'templates', 'build_html.py');
const overridesExample = path.join(rootDir, 'templates', 'arch_overrides.example.py');

if (!fs.existsSync(skillFile)) {
    console.error('❌ Error: SKILL.md not found in package root.');
    process.exit(1);
}

const homeDir = os.homedir();
const targets = [];

// 1. Antigravity Global Skills Path
const antigravityPath = path.join(homeDir, '.gemini', 'antigravity', 'skills', 'arch-wiki');
targets.push({ name: 'Antigravity AI Agent', path: antigravityPath });

// 2. Claude Code Skills Path
const claudePath = path.join(homeDir, '.claude', 'skills', 'arch-wiki');
targets.push({ name: 'Claude Code', path: claudePath });

// 3. Local Workspace Target (if run inside a project)
const cwdSkillPath = path.join(process.cwd(), '.skills', 'arch-wiki');
if (process.cwd() !== rootDir) {
    targets.push({ name: 'Local Project Workspace (.skills/arch-wiki)', path: cwdSkillPath });
}

let installedCount = 0;

targets.forEach(target => {
    try {
        if (!fs.existsSync(target.path)) {
            fs.mkdirSync(target.path, { recursive: true });
        }
        
        // Copy SKILL.md
        fs.copyFileSync(skillFile, path.join(target.path, 'SKILL.md'));
        
        // Copy build_html.py (and the override-hook example) if templates exist
        if (fs.existsSync(templateFile)) {
            const templatesDir = path.join(target.path, 'templates');
            if (!fs.existsSync(templatesDir)) {
                fs.mkdirSync(templatesDir, { recursive: true });
            }
            fs.copyFileSync(templateFile, path.join(templatesDir, 'build_html.py'));
            if (fs.existsSync(overridesExample)) {
                fs.copyFileSync(overridesExample, path.join(templatesDir, 'arch_overrides.example.py'));
            }
        }

        console.log(`✅ Installed arch-wiki to ${target.name}:`);
        console.log(`   └─ ${target.path}\n`);
        installedCount++;
    } catch (err) {
        console.warn(`⚠️ Could not write to ${target.name}: ${err.message}`);
    }
});

if (installedCount > 0) {
    console.log('🎉 arch-wiki Skill Installation Complete!');
    console.log('\n💡 Usage in AI Chat / Agent:');
    console.log('   Simply prompt your AI assistant:');
    console.log('   "Run arch-wiki skill to generate architecture documentation for this project"\n');
} else {
    console.error('❌ Skill installation failed. Please check folder permissions.');
}
