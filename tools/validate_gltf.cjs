const fs = require('node:fs');
const path = require('node:path');
const validator = require('gltf-validator');
const root = path.resolve(__dirname, '..');
const assets = {kuchikagura:'kuchikagura.glb', glasses:'pursuer_glasses.glb', cropped:'pursuer_cropped.glb'};
const args = process.argv.slice(2);
if (args.length && args[0] !== '--asset') {
  console.error('Usage: node tools/validate_gltf.cjs [--asset kuchikagura glasses cropped]');
  process.exit(1);
}
const selected = args.length ? args.slice(1) : Object.keys(assets);
if (!selected.length || selected.some(name => !assets[name])) {
  console.error('Choose kuchikagura, glasses, or cropped.');
  process.exit(1);
}
async function main() {
  const reports = {};
  for (const name of selected) {
    const uri = assets[name];
    const data = new Uint8Array(fs.readFileSync(path.join(root, 'web/assets/models', uri)));
    const report = await validator.validateBytes(data, {uri, maxIssues:100});
    reports[name] = report;
    console.log(JSON.stringify({asset:uri, errors:report.issues.numErrors, warnings:report.issues.numWarnings,
      infos:report.issues.numInfos, messages:report.issues.messages}, null, 2));
    if (report.issues.numErrors) process.exitCode = 1;
  }
  if (reports.kuchikagura) {
    fs.writeFileSync(path.join(root, 'export/gltf_validation.json'), JSON.stringify(reports.kuchikagura, null, 2) + '\n');
  }
  const references = Object.fromEntries(Object.entries(reports).filter(([name]) => name !== 'kuchikagura'));
  if (Object.keys(references).length) {
    const result = {status:Object.values(references).some(r => r.issues.numErrors) ? 'failed':'passed',
      both_reference_characters:!!(references.glasses && references.cropped), assets:references};
    fs.writeFileSync(path.join(root, 'export/reference_gltf_validation.json'), JSON.stringify(result, null, 2) + '\n');
  }
}
main().catch(error => { console.error(error); process.exitCode = 1; });
