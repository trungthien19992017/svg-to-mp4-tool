import {mkdir,copyFile,readFile,writeFile,access} from 'node:fs/promises';
import {fileURLToPath} from 'node:url';
import path from 'node:path';
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
const target=path.join(root,'src/SvgToMp4.Web/wwwroot/story/vendor');
await mkdir(target,{recursive:true});
const pkg=JSON.parse(await readFile(path.join(root,'node_modules/gsap/package.json'),'utf8'));
if(pkg.version!=='3.15.0')throw Error('Unexpected GSAP version');
for(const file of ['gsap.min.js','MotionPathPlugin.min.js','MorphSVGPlugin.min.js'])
    await copyFile(path.join(root,'node_modules/gsap/dist',file),path.join(target,file));
let licenseCopied=false;
for(const name of ['LICENSE','LICENSE.md','LICENSE.txt']){
    try{await access(path.join(root,'node_modules/gsap',name));await copyFile(path.join(root,'node_modules/gsap',name),path.join(target,'LICENSE.gsap'));licenseCopied=true;break;}catch{}
}
await writeFile(path.join(target,'NOTICE.gsap.txt'),`GSAP ${pkg.version}\n${pkg.license}\nhttps://gsap.com/community/standard-license/\nOriginal copyright/license headers are retained in all copied scripts.\n${licenseCopied?'Package license file copied.':'The package declares its license by URL; consult that license before distribution.'}\n`);
console.log('Local GSAP runtime ready: '+pkg.version);
