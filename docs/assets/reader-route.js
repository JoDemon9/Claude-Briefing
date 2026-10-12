/* Compatibility routes are pinned to an edition in the generated route registry. */
(async()=>{'use strict';const out=document.querySelector('#reader-status');try{
 const controller=new AbortController(),timeout=setTimeout(()=>controller.abort(),10000);
 const root=new URL(document.querySelector('meta[name="briefing-root"]').content,location.href),routes=await fetch(new URL('data/reader-routes.json',root),{signal:controller.signal}).then(r=>{if(!r.ok)throw Error();return r.json()});
 clearTimeout(timeout);const route=routes[location.pathname.split('/').slice(-2).join('/')]||routes[location.pathname.split('/').pop()];
 const params=new URLSearchParams(location.search),edition=params.get('edition')||route?.edition_id,story=params.get('story')||'lead';
 const target=routes.articles?.[edition]?.[story];if(!target)throw Error();
 const url=new URL(target,root);if(url.origin!==root.origin||!url.pathname.startsWith(root.pathname+'articles/'))throw Error();
 const a=document.createElement('a');a.href=url.href;a.textContent='Άνοιγμα άρθρου';out.replaceChildren(a);location.replace(url.href);
 }catch{out.textContent='Το άρθρο δεν είναι διαθέσιμο για αυτήν την έκδοση. Επιστρέψτε στο αρχείο εκδόσεων.'}})();
