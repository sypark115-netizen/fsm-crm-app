const { chromium } = require(require('child_process').execSync('npm root -g').toString().trim()+'/playwright');
const path=require('path');
(async()=>{
  const dir=process.argv[2]||__dirname;
  const b=await chromium.launch();
  const p=await b.newPage({viewport:{width:1200,height:1400}});
  await p.goto('file://'+path.join(dir,'index.html'));
  await p.evaluate(()=>document.fonts.ready);
  // PNG: 카드 원본 크기로 한 장씩
  await p.addStyleTag({content:'.frame{width:1080px!important;height:1350px!important;aspect-ratio:auto!important;border-radius:0!important;box-shadow:none!important}.frame .card{transform:none!important}'});
  for(let i=1;i<=5;i++){
    const bb=await p.locator('#card-'+i+' .card').boundingBox();
    await p.screenshot({fullPage:true,clip:{x:Math.round(bb.x),y:Math.round(bb.y),width:1080,height:1350},path:path.join(dir,'export',`card-${i}.png`)});
  }
  await p.reload(); await p.evaluate(()=>document.fonts.ready);
  await p.pdf({path:path.join(dir,'export','cardnews-5pages.pdf'),width:'1080px',height:'1350px',printBackground:true,preferCSSPageSize:true});
  await b.close();
})();
