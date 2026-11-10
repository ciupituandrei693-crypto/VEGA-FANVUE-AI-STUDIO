"""Optional offline UI browser smoke test. Mocks API, does NOT test real iPhone/Android."""
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT=Path(__file__).resolve().parents[1]
html=(ROOT/'web/index.html').read_text(encoding='utf-8').replace('<script src="/assets/app.js" defer></script>','')
css=(ROOT/'web/style.css').read_text(encoding='utf-8')
js=(ROOT/'web/app.js').read_text(encoding='utf-8')
shim=r'''
const mem = new Map([['vega_token','fake-offline-demo-token']]);
Object.defineProperty(window,'sessionStorage',{configurable:true,value:{getItem:k=>mem.get(k)||null,setItem:(k,v)=>mem.set(k,v),removeItem:k=>mem.delete(k)}});
const MODELS=['Aria Vale','Maya Solis','Elena Hart','Nova Quinn','Selene Voss','Claudia Rose','Irina Sky','Liora Maren','Evelyn Frost'].map((name,i)=>({id:['aria','maya','elena','nova','selene','claudia','irina','liora','evelyn'][i],name,niche:'fashion',voice:'creativă',accent:'rose'}));
let profiles=MODELS.map(m=>({...m,model_id:m.id,visual_prompt:'',negative_prompt:'',personality:'',voice_profile:'',reference_media_id:null}));
let packs=[];let metrics=[];
window.fetch=async function(input,opts={}){
 const url=String(input);const meth=opts.method||'GET';let data;
 if(url==='/api/setup-state')data={configured:true};
 else if(url==='/api/me')data={username:'demo'};
 else if(url==='/api/models')data=MODELS;
 else if(url==='/api/posts')data=[];
 else if(url==='/api/media')data=[];
 else if(url==='/api/dashboard')data={models:9,posts:0,review:0,approved:0,scheduled:0,media:0,events:[]};
 else if(url==='/api/settings')data={paused:true};
 else if(url==='/api/characters'&&meth==='GET')data=profiles;
 else if(url.startsWith('/api/characters/')&&meth==='PUT'){let id=url.split('/').pop(),p=profiles.find(x=>x.model_id===id);Object.assign(p,JSON.parse(opts.body));data={ok:true};}
 else if(url.startsWith('/api/production/prompt/'))data={prompt:'original fictional character',negative:'',reference_media_id:null};
 else if(url==='/api/ollama/status')data={available:false,models:[]};
 else if(url==='/api/editorial/packs'&&meth==='GET')data=packs;
 else if(url==='/api/editorial/packs'&&meth==='POST'){let f=JSON.parse(opts.body);data={id:'mock1',source:'template',state:'draft',output:{hooks:['a','b','c'],caption:'Draft AI virtual',hashtags:'#AI',cta:'Hello'}};packs.push({...data,...f,data_json:'',created_at:new Date().toISOString()});}
 else if(url==='/api/connectors')data={platforms:['Fanvue','Instagram','TikTok','X','Reddit'].map(x=>({platform:x,state:'unconfigured',note:''})),connected_accounts:0,live_posting:false};
 else if(url==='/api/deliveries')data=[];
 else if(url==='/api/analytics')data={sample_size:metrics.length,totals:{subscribers:0,impressions:0,clicks:0,gross_cents:0,cost_cents:0,net_cents:0},by_model:[],warning:'Date introduse manual.'};
 else if(url==='/api/analytics/manual'&&meth==='POST'){metrics.push(JSON.parse(opts.body));data={saved:true};}
 else if(url==='/api/backup/status')data={files:[]};
 else if(url==='/api/security/report')data={kill_switch_enabled:true,active_sessions:1,lan_mode:false,external_server:false};
 else data={};
 return {ok:true,status:200,json:async()=>data,blob:async()=>new Blob()};
};
'''

with sync_playwright() as p:
    browser=p.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox'])
    try:
        for width,height,name in [(1365,860,'desktop'),(390,844,'mobile')]:
            page=browser.new_page(viewport={'width':width,'height':height},is_mobile=(name=='mobile'))
            page.set_default_timeout(4000)
            print('Start',name,flush=True)
            errors=[]
            page.on('pageerror',lambda e: errors.append(str(e)))
            page.set_content(html,wait_until='domcontentloaded')
            page.add_style_tag(content=css)
            page.add_script_tag(content=shim)
            page.add_script_tag(content=js)
            page.locator('#app-shell').wait_for(state='visible',timeout=10000)
            def open_nav(view):
                print('nav',name,view,flush=True)
                if name=='mobile':
                    page.locator('#mobile-menu').click()
                    print('sidebar open?',page.locator('.sidebar').get_attribute('class'),flush=True)
                page.locator(f'button[data-view="{view}"]').click()
            open_nav('characters')
            page.locator('#v09-character-form').wait_for()
            page.locator('textarea[name="visual_prompt"]').fill('Adult fictional original persona')
            page.locator('#v09-character-form button[type="submit"]').click()
            open_nav('editorial')
            page.locator('#v09-pack-form').wait_for()
            page.locator('input[name="topic"]').fill('Fashion de seară')
            page.locator('#v09-pack-form button[type="submit"]').click()
            page.get_by_text('Doar draft').wait_for(timeout=5000)
            open_nav('integrations')
            page.locator('#v09-connectors').get_by_text('Fanvue').wait_for()
            open_nav('insights')
            page.locator('#v09-metric-form').wait_for()
            open_nav('backup')
            page.locator('#v09-security').get_by_text('Raport securitate').wait_for()
            page.wait_for_timeout(300)  # Allow mobile sidebar close transition to complete.
            page.screenshot(path=f'/mnt/data/VEGA_v09_preview_{name}.png',full_page=True)
            if errors:raise AssertionError(f'{name} JS errors: {errors}')
            print(f'Offline browser preview {name}: OK; all v0.9 views; 0 JS errors')
            page.close()
    finally:
        browser.close()
