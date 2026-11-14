// Deploy as a Cloudflare Worker. Set TRADERA_APP_KEY as a Worker secret.
// Set TRADERA_APP_ID=7762 and ALLOWED_ORIGIN to your GitHub Pages origin.
export default {
  async fetch(request, env) {
    const origin = request.headers.get('Origin') || '';
    const allowed = env.ALLOWED_ORIGIN || '';
    const headers = { 'Content-Type': 'application/json', 'Cache-Control': 'no-store',
      'Access-Control-Allow-Origin': allowed, 'Vary': 'Origin' };
    if (request.method === 'OPTIONS') return new Response(null, {status:204, headers:{...headers,'Access-Control-Allow-Methods':'POST, OPTIONS','Access-Control-Allow-Headers':'Content-Type'}});
    if (request.method !== 'POST') return new Response(JSON.stringify({error:'Method not allowed'}),{status:405,headers});
    if (!allowed || origin !== allowed) return new Response(JSON.stringify({error:'Origin not allowed'}),{status:403,headers});
    if (!env.TRADERA_APP_KEY) return new Response(JSON.stringify({error:'API key not configured'}),{status:503,headers});
    let body;
    try { body = await request.json(); } catch { return new Response(JSON.stringify({error:'Invalid JSON'}),{status:400,headers}); }
    const query = typeof body.query === 'string' ? body.query.trim() : '';
    if (!query || query.length > 120) return new Response(JSON.stringify({error:'Invalid query'}),{status:400,headers});
    const url = 'https://api.tradera.com/v4/search?'+new URLSearchParams({query});
    try {
      const response = await fetch(url,{headers:{'X-App-Id':String(env.TRADERA_APP_ID||'7762'),'X-App-Key':env.TRADERA_APP_KEY,'Accept':'application/json'}});
      if (!response.ok) return new Response(JSON.stringify({error:'Tradera returned HTTP '+response.status}),{status:502,headers});
      const data = await response.json();
      const pick=(o,...keys)=>keys.map(k=>o?.[k]).find(v=>v!==undefined&&v!==null);
      let items=Array.isArray(data)?data:pick(data,'items','results','searchResults','itemList');
      if (!Array.isArray(items)) items=pick(items,'items','results');
      if (!Array.isArray(items)) return new Response(JSON.stringify({error:'Unexpected Tradera response'}),{status:502,headers});
      const listings=items.slice(0,50).map(item=>{
        const id=pick(item,'id','itemId','Id'), title=pick(item,'title','shortDescription','name');
        if (!id||!title) return null;
        let price=pick(item,'currentBid','price','buyItNowPrice');
        if (price && typeof price==='object') price=pick(price,'amount','value');
        const rawUrl=pick(item,'itemUrl','url','link');
        return {id:String(id),title:String(title),price:Number.isFinite(Number(price))?Number(price):null,
          currency:'SEK',url:typeof rawUrl==='string'&&rawUrl.startsWith('https://www.tradera.com/')?rawUrl:'https://www.tradera.com/item/'+id};
      }).filter(Boolean);
      return new Response(JSON.stringify({query,listings}),{headers});
    } catch { return new Response(JSON.stringify({error:'Tradera request failed'}),{status:502,headers}); }
  }
};
