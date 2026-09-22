// Optional developer preview: npm package playwright and its Chromium browser.
// The analytical pipeline itself has no Node or browser dependency.
const {chromium}=require('playwright');
const {resolve}=require('node:path');
const {pathToFileURL}=require('node:url');
const fs=require('node:fs/promises');
(async()=>{
 const source=resolve(process.argv[2]||'build/demo/report.html');
 const dest=resolve(process.argv[3]||'evidence/report-preview.png');
 const browser=await chromium.launch({headless:true});
 try {
   const page=await browser.newPage({viewport:{width:1440,height:1080},deviceScaleFactor:1});
   const errors=[];page.on('pageerror',e=>errors.push(e.message));
   await page.route(/^https?:\/\//,r=>r.abort());
   await page.goto(pathToFileURL(source).href,{waitUntil:'load'});
   const checks=await page.evaluate(()=>({title:document.title,tables:document.querySelectorAll('table').length,headings:document.querySelectorAll('h1,h2,h3').length,images:[...document.images].map(x=>({loaded:x.complete&&x.naturalWidth>0,source:x.getAttribute('src')})),scripts:document.scripts.length,overflow:document.documentElement.scrollWidth>innerWidth}));
   if(checks.scripts||checks.tables<5||checks.images.some(i=>!i.loaded)||errors.length)throw Error('Invalid report preview: '+JSON.stringify({checks,errors}));
   await fs.mkdir(require('node:path').dirname(dest),{recursive:true});
   await page.screenshot({path:dest});
   await fs.writeFile(dest.replace(/\.png$/,'.json'),JSON.stringify({checks,errors,passed:true},null,2)+'\n');
   console.log(JSON.stringify({output:dest,...checks,errors}));
 }finally{await browser.close();}
})().catch(e=>{console.error(e.message);process.exitCode=1;});
