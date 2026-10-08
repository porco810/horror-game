const fs = require('node:fs');
const path = require('node:path');
const validator = require('gltf-validator');
const root = path.resolve(__dirname, '..');
const data = new Uint8Array(fs.readFileSync(path.join(root, 'web/assets/models/kuchikagura.glb')));
validator.validateBytes(data, {uri:'kuchikagura.glb', maxIssues:100}).then(report => {
  fs.writeFileSync(path.join(root, 'export/gltf_validation.json'), JSON.stringify(report, null, 2) + '\n');
  console.log(JSON.stringify({errors:report.issues.numErrors, warnings:report.issues.numWarnings,
    infos:report.issues.numInfos, messages:report.issues.messages}, null, 2));
  if (report.issues.numErrors) process.exitCode = 1;
}).catch(error => { console.error(error); process.exitCode = 1; });
