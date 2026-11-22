// Deploy as a Cloudflare Worker behind Cloudflare Access (email OTP).
// Secrets: GITHUB_TOKEN (fine-grained Actions:write), ACCESS_TEAM_DOMAIN, ACCESS_AUD.
// Environment: ALLOWED_ORIGIN=https://atomicnumber36.github.io
const categories = new Set(['nintendo','playstation','xbox','sega']);
let keyCache;
async function verifyAccess(request, env) {
  const jwt = request.headers.get('Cf-Access-Jwt-Assertion');
  if (!jwt) return false;
  const [h,p,s] = jwt.split('.');
  if (!h || !p || !s) return false;
  const decode = x => JSON.parse(atob(x.replace(/-/g,'+').replace(/_/g,'/')));
  const header=decode(h), payload=decode(p);
  const team=env.ACCESS_TEAM_DOMAIN;
  if (!team || !env.ACCESS_AUD || payload.iss !== 'https://'+team || ![].concat(payload.aud||[]).includes(env.ACCESS_AUD) || payload.exp*1000<=Date.now()) return false;
  const keys=await fetch('https://'+team+'/cdn-cgi/access/certs').then(r=>r.json());
  const jwk=keys.keys.find(k=>k.kid===header.kid);
  if (!jwk || header.alg!=='RS256') return false;
  const key=await crypto.subtle.importKey('jwk',jwk,{name:'RSASSA-PKCS1-v1_5',hash:'SHA-256'},false,['verify']);
  const bytes=x=>Uint8Array.from(atob(x.replace(/-/g,'+').replace(/_/g,'/')),c=>c.charCodeAt(0));
  return crypto.subtle.verify('RSASSA-PKCS1-v1_5',key,bytes(s),new TextEncoder().encode(h+'.'+p));
}
export default {
  async fetch(request,env){
    const origin=env.ALLOWED_ORIGIN||'https://atomicnumber36.github.io';
    const headers={'Access-Control-Allow-Origin':origin,'Access-Control-Allow-Headers':'Content-Type','Access-Control-Allow-Methods':'POST,OPTIONS','Vary':'Origin','Content-Type':'application/json'};
    if(request.method==='OPTIONS')return new Response(null,{status:204,headers});
    if(request.method!=='POST'||new URL(request.url).pathname!=='/import')return new Response('Not found',{status:404,headers});
    if(request.headers.get('Origin')!==origin)return new Response('Forbidden origin',{status:403,headers});
    if(!await verifyAccess(request,env))return new Response(JSON.stringify({error:'Login required'}),{status:401,headers});
    let input;try{input=await request.json()}catch{return new Response('Invalid JSON',{status:400,headers})}
    const selected=input.categories,days=Number(input.days);
    if(!Array.isArray(selected)||selected.length<1||selected.length>4||new Set(selected).size!==selected.length||selected.some(x=>!categories.has(x))||![1,3,7,14,30].includes(days))return new Response('Invalid selection',{status:400,headers});
    const r=await fetch('https://api.github.com/repos/Atomicnumber36/marginspotter/actions/workflows/tradera-sync.yml/dispatches',{method:'POST',headers:{Authorization:'Bearer '+env.GITHUB_TOKEN,Accept:'application/vnd.github+json','X-GitHub-Api-Version':'2022-11-28','User-Agent':'MarginSpotter-import'},body:JSON.stringify({ref:'main',inputs:{categories:selected.join(','),days:String(days)}})});
    return new Response(JSON.stringify({ok:r.status===204}),{status:r.status===204?202:502,headers});
  }
};