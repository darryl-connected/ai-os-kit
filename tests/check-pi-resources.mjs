// Use Pi's actual default resource loader without creating a model session.
import { pathToFileURL } from 'node:url';
import { join } from 'node:path';

const [dist, cwd, agentDir] = process.argv.slice(2);
const { DefaultResourceLoader, SettingsManager } = await import(pathToFileURL(join(dist, 'index.js')));
// Same builtin registry and discovered skill naming used by Pi's interactive autocomplete.
const { BUILTIN_SLASH_COMMANDS } = await import(pathToFileURL(join(dist, 'core/slash-commands.js')));
const settingsManager = SettingsManager.inMemory({ packages: [], defaultProjectTrust: 'always' }, { projectTrusted: true });
if (!settingsManager.isProjectTrusted()) throw new Error('Fixture did not opt into its project resources');
const loader = new DefaultResourceLoader({
  cwd, agentDir, settingsManager, noExtensions: true, noPromptTemplates: true, noThemes: true,
});
await loader.reload();
const { skills, diagnostics } = loader.getSkills();
const commands = [
  ...BUILTIN_SLASH_COMMANDS.map(({ name }) => name),
  ...(settingsManager.getEnableSkillCommands() ? skills.map(({ name }) => `skill:${name}`) : []),
];
console.log(JSON.stringify({
  commands,
  trusted: settingsManager.isProjectTrusted(),
  skills: skills.map(({ name, filePath }) => ({ name, filePath })),
  diagnostics, instructions: loader.getAgentsFiles().agentsFiles,
  append: loader.getAppendSystemPrompt(),
}));
