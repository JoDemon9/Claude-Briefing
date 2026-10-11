(() => {
 'use strict';
 const input=document.getElementById('search'), cards=[...document.querySelectorAll('.edition')];
 const results=document.getElementById('articleResults'), status=document.getElementById('searchStatus');
 const empty=document.getElementById('noResults'); let entries=[], ready=false;
 const norm=value=>String(value||'').toLocaleLowerCase('el').normalize('NFD').replace(/[\u0300-\u036f]/g,'');
 function render() {
  const query=norm(input.value.trim()), dates=new Set(); results.replaceChildren();
  const matches=query.length>=2 ? entries.filter(item=>norm(item.date+' '+item.title+' '+item.text+' '+item.section).includes(query)) : [];
  for(const item of matches) dates.add(item.date);
  let visible=0;
  for(const card of cards) { const show=!query || norm(card.textContent+' '+card.dataset.filter).includes(query) || dates.has(card.dataset.filter); card.hidden=!show; card.style.display=show?'':'none'; visible+=Number(show); }
  for(const item of matches.slice(0,30)) {
   if(!/^briefings\/\d{4}-\d{2}-\d{2}\.html#[a-z0-9-]+$/.test(item.url)) continue;
   const link=document.createElement('a'); link.href=item.url;
   const meta=document.createElement('small');meta.textContent=item.date+' · '+item.section;
   const title=document.createElement('h3');title.textContent=item.title;
   const summary=document.createElement('p');summary.textContent=item.snippet;
   link.append(meta,title,summary);results.append(link);
  }
  status.textContent=query ? (ready ? `${matches.length} άρθρα · ${visible} εκδόσεις${matches.length>30?' · εμφανίζονται τα πρώτα 30':''}` : 'Η αναζήτηση θεμάτων δεν είναι διαθέσιμη. Αναζήτηση στις ημερομηνίες και τους τίτλους εκδόσεων.') : '';
  empty.classList.toggle('show',visible===0 && matches.length===0);
 }
 input.addEventListener('input',render);
 fetch('search-index.json').then(response=>{if(!response.ok)throw Error('index');return response.json()}).then(data=>{entries=data;ready=true;render()}).catch(()=>{status.textContent='Η αναζήτηση θεμάτων δεν είναι διαθέσιμη. Οι εκδόσεις παραμένουν προσβάσιμες.'});
})();
