import {build} from 'esbuild';
import fs from 'node:fs';
import path from 'node:path';

const result=await build({entryPoints:['frontend/google-auth.js'],bundle:true,format:'iife',platform:'browser',target:'es2022',minify:true,legalComments:'eof',metafile:true,write:false});
const packages=new Set();
for(const input of Object.keys(result.metafile.inputs)) {
  if(!input.includes('node_modules/'))continue;
  let directory=path.dirname(path.resolve(input));
  while(directory!==path.dirname(directory)) {
    const manifest=path.join(directory,'package.json');
    if(fs.existsSync(manifest) && JSON.parse(fs.readFileSync(manifest,'utf8')).name) {packages.add(directory);break;}
    directory=path.dirname(directory);
  }
}
const licenses=[];
for(const directory of [...packages].sort()) {
  const name=JSON.parse(fs.readFileSync(path.join(directory,'package.json'),'utf8')).name;
  const files=fs.readdirSync(directory).filter(file=>/^licen[cs]e(?:\.|$)/i.test(file));
  if(!files.length)throw Error('Missing license for '+name);
  licenses.push(name+'\n'+files.map(file=>fs.readFileSync(path.join(directory,file),'utf8')).join('\n'));
}
fs.writeFileSync('web/assets/google-auth.js',result.outputFiles[0].text+'\n/*! Third-party licenses\n'+licenses.join('\n\n').replaceAll('*/','* /')+'\n*/\n');
console.log('Google auth bundle built with third-party licenses.');
