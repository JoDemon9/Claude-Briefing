(() => {
 'use strict';
 const $=query=>document.querySelector(query);
 const element=(tag,cls,text)=>{const node=document.createElement(tag);if(cls)node.className=cls;if(text!==undefined)node.textContent=text;return node};
 const params=new URLSearchParams(location.search), id=params.get('story')||'lead';
 const validDate=value=>/^\d{4}-\d{2}-\d{2}$/.test(value||'');
 const external=value=>{try{const u=new URL(value);return ['http:','https:'].includes(u.protocol)&&!u.username&&!u.password}catch(_){return false}};
 function error(message){$('#loading').hidden=true;$('#readerError').hidden=false;$('#readerError').textContent=message}
 if(!/^(lead|cyprus-\d+|world-\d+)$/.test(id)){error('Άγνωστο άρθρο.');return}
 $('#print').onclick=()=>window.print();
 $('#share').onclick=async()=>{try{await navigator.clipboard.writeText(location.href);$('#share').textContent='Αντιγράφηκε ✓'}catch(_){prompt('Σύνδεσμος άρθρου',location.href)}};
 async function load(){
  let edition=params.get('edition');
  if(edition&&!validDate(edition))throw Error('Μη έγκυρη ημερομηνία.');
  // Original public story-only links refer to the October edition. A bare
  // reader URL opens the latest edition; all generated links include a date.
  if(!edition&&params.has('story'))edition='2026-10-11';
  if(!edition){const response=await fetch('editions.json');if(!response.ok)throw Error('Το αρχείο δεν είναι διαθέσιμο.');edition=(await response.json()).latest}
  if(!validDate(edition))throw Error('Άγνωστη έκδοση.');
  const response=await fetch(`articles/${edition}.json`);if(!response.ok)throw Error('Η έκδοση δεν είναι διαθέσιμη.');
  const data=await response.json(), article=data.articles.find(item=>item.id===id);
  if(!article || data.date!==edition)throw Error('Το άρθρο δεν υπάρχει σε αυτήν την έκδοση.');
  const editionURL=[`briefings/${edition}.html`,`morning/${edition}.html`].includes(data.content_url)?data.content_url:`briefings/${edition}.html`;
  document.querySelectorAll('[data-edition-link]').forEach(link=>link.href=`${editionURL}#${article.anchor}`);
  document.title=article.title+' · The Oracle Sovereign';$('#category').textContent=article.category+' / '+edition;
  $('#headline').textContent=article.title;$('#subhead').textContent=article.summary||'Δημοσιευμένο άρθρο.';
  if(article.image && (/^assets\/[a-z0-9.-]+$/.test(article.image.src) || external(article.image.src))){
   $('#photo').src=article.image.src;$('#photo').alt=article.image.alt;$('#photoCaption').textContent=article.image.caption;
   if(article.image.width&&article.image.height){$('#photo').width=Number(article.image.width);$('#photo').height=Number(article.image.height)}
  }else $('.photo').hidden=true;
  article.paragraphs.forEach((paragraph,index)=>{const text=index===0&&paragraph.startsWith(article.summary)?paragraph.slice(article.summary.length).trim():paragraph;if(text)$('#factual').append(element('p','',text))});
  for(const paragraph of article.analysis)$('#analysis').append(element('p','',paragraph));
  if(!article.analysis.length)$('#analysis').append(element('p','','Δεν έχει δημοσιευθεί πρόσθετη ανάλυση για αυτό το άρθρο.'));
  $('#timeline').append(element('p','','Δεν έχει δημοσιευθεί ξεχωριστό τεκμηριωμένο χρονολόγιο για αυτό το άρθρο.'));
  $('#counterpoint').textContent='Ο αντίλογος, όταν υπάρχει στην έκδοση, περιλαμβάνεται στην παραπάνω ανάλυση.';
  $('#opinion').textContent='Οι ερμηνείες και προβλέψεις αποτελούν συντακτική ανάλυση. Δεν προστίθενται νέοι ισχυρισμοί σε αυτήν τη σελίδα.';
  const sources=article.sources.filter(item=>external(item.url));
  const hosts=new Set(sources.map(item=>new URL(item.url).hostname.replace(/^www\./,'')));
  $('#sourceBadge').textContent=hosts.size+' διακριτοί ιστότοποι πηγών';
  $('#auditLabel').textContent='Η παράθεση πηγών δεν αποτελεί αυτόματη ανεξάρτητη επιβεβαίωση.';
  $('#sourceWarning').textContent=`${sources.length} σύνδεσμοι από τη δημοσιευμένη έκδοση. Δεν έχει διενεργηθεί νέα επαλήθευση προσβασιμότητας ή έλεγχος κάθε ισχυρισμού.`;
  for(const source of sources){const link=element('a','',source.name);link.href=source.url;link.target='_blank';link.rel='noopener noreferrer';$('#bottomSources').append(link)}
  for(const item of data.articles.filter(item=>item.id!==id).slice(0,5)){const link=element('a','',item.title);link.href=`reader.html?edition=${edition}&story=${encodeURIComponent(item.id)}`;$('#related').append(link)}
  $('#loading').hidden=true;$('#content').hidden=false;
 }
 load().catch(reason=>error('Δεν ήταν δυνατή η φόρτωση: '+reason.message));
})();
