// HTTP requests reach a real isolated Flask API; no API response fixtures.
// Only the Python harness substitutes the external paid AI provider.
import {chromium, expect} from '@playwright/test';
import http from 'node:http';
import {readFile, open} from 'node:fs/promises';
import {dirname, join} from 'node:path';
const proxy=http.createServer((req,res)=>{
 if(req.url.endsWith('/events')) {res.writeHead(503);res.end();return;}
 const upstream=http.request({hostname:'127.0.0.1',port:req.url.startsWith('/api/')?5099:3000,path:req.url,method:req.method,headers:req.headers},reply=>{
  res.writeHead(reply.statusCode,reply.headers);reply.pipe(res);
 });
 upstream.on('error',()=>{res.writeHead(502);res.end();});req.pipe(upstream);
});
await new Promise(resolve=>proxy.listen(3002,'127.0.0.1',resolve));
const browser = await chromium.launch({channel:'chrome',headless:true});
const page = await browser.newPage({viewport:{width:1440,height:900}});
const errors=[];
page.on('pageerror', e=>errors.push(e.message));
try {
 await page.goto('http://127.0.0.1:3002/');
 await expect(page.locator('.cursor-light')).toHaveCount(1);
 await page.goto('http://127.0.0.1:3002/register');
 await expect(page.locator('.cursor-light')).toHaveCount(0);
 await page.getByLabel('Your name').fill('Browser acceptance');
 await page.getByLabel('Email address').fill('browser-test@example.com');
 await page.locator('input[type=password]').fill('test-only-long-password');
 await page.getByRole('button',{name:'Create account',exact:true}).click();
 await expect(page.getByRole('heading',{name:'Your projects'})).toBeVisible({timeout:20000});
 await expect(page.locator('.cursor-light')).toHaveCount(0);
 console.log('PASS registration and authenticated dashboard; cursor only on home');
 await page.getByRole('link',{name:'Analyze your first repository'}).click();
 await page.getByLabel('Project name').fill('Browser flow fixture');
 const oversizedPath=join(dirname(process.env.FLOW_ZIP),'oversized.zip');
 const oversizedFile=await open(oversizedPath,'w');
 await oversizedFile.truncate(101*1024*1024); await oversizedFile.close();
 await page.getByLabel('Repository ZIP').setInputFiles(oversizedPath);
 await page.getByRole('button',{name:'Upload & preview'}).click();
 await expect(page.locator('.upload-flow').getByRole('alert')).toContainText('The upload limit is 100 MiB');
 console.log('PASS oversized ZIP rejected before upload');
 await page.getByLabel('Repository ZIP').setInputFiles(process.env.FLOW_ZIP);
 await page.getByRole('button',{name:'Upload & preview'}).click();
 await expect(page.getByRole('heading',{name:'Review your source'})).toBeVisible();
 await page.getByRole('button',{name:'main.py',exact:true}).click();
 await expect(page.locator('.source-preview')).toContainText('return 42');
 await page.getByLabel('I understand that supported sanitized source excerpts').check();
 await page.getByRole('button',{name:'Start indexing',exact:true}).click();
 await page.waitForURL('**/app/projects/*',{timeout:process.env.CODEBUDDY_LIVE_TEST === '1' ? 180000 : 45000});
 console.log('PASS ZIP upload, sanitized preview, Redis worker indexing, polling fallback');
 await page.getByLabel('Ask a question').fill('What does hello do?');
 await page.getByRole('button',{name:'Send question'}).click();
 if(process.env.CODEBUDDY_LIVE_TEST === '1') {
  await expect(page.locator('.answer .claim').first()).toContainText('42',{timeout:180000});
 } else {
  await expect(page.getByText('The supplied source defines a function.',{exact:true})).toBeVisible({timeout:process.env.CODEBUDDY_LIVE_TEST === '1' ? 180000 : 45000});
 }
 await page.getByRole('button',{name:/main.py:1/}).first().click();
 await expect(page.locator('.citation-highlight').first()).toBeVisible();
 console.log('PASS question, generated answer, citation-to-source navigation');
 await page.getByRole('button',{name:'Guide',exact:true}).click();
 await page.getByRole('button',{name:'Generate onboarding guide',exact:true}).click();
 await expect(page.getByRole('link',{name:'Download Markdown'})).toBeVisible({timeout:process.env.CODEBUDDY_LIVE_TEST === '1' ? 180000 : 45000});
 const downloadReady=page.waitForEvent('download');
 await page.getByRole('link',{name:'Download Markdown'}).click();
 const download=await downloadReady;
 const markdown=await readFile(await download.path(),'utf8');
 expect(markdown).toContain('main.py');
 expect(markdown).toContain('CodeBuddy onboarding guide');
 console.log('PASS guide generation and downloaded Markdown contents');
 await page.screenshot({path:process.env.CODEBUDDY_LIVE_TEST === '1' ? '../docs/screenshots/live-flow-test.png' : '../docs/screenshots/private-flow-test.png'});
 await page.reload();
 await expect(page.getByLabel('Ask a question')).toBeVisible({timeout:20000});
 await page.getByRole('button',{name:'Sign out',exact:true}).click();
 await page.waitForURL('**/login');
 await page.getByLabel('Email address').fill('browser-test@example.com');
 await page.locator('input[type=password]').fill('test-only-long-password');
 await page.getByRole('button',{name:'Sign in',exact:true}).click();
 await expect(page.getByRole('heading',{name:'Your projects'})).toBeVisible({timeout:20000});
 await expect(page.getByRole('heading',{name:'Browser flow fixture'})).toBeVisible();
 console.log('PASS sign-out, sign-in and persisted project');
 if(errors.length) throw new Error(errors.join('\n'));
 console.log('PASS persisted authenticated workspace; no browser errors');
} catch(e) {
 console.error(await page.locator('body').innerText());
 throw e;
} finally {await browser.close();proxy.closeAllConnections();await new Promise(resolve=>proxy.close(resolve));}
