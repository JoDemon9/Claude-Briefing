(() => {
 'use strict';
 const $=q=>document.querySelector(q), labels={'1M':'1 μήνας','3M':'3 μήνες','6M':'6 μήνες','12M':'1 έτος','60M':'5 έτη','ALL':'πλήρες ιστορικό'};
 let key='sp', range='6M', registry, theme='light';
 try{theme=localStorage.getItem('oracle-theme')==='dark'?'dark':'light'}catch(_){}
 document.documentElement.dataset.theme=theme;
 const status=message=>{const p=document.createElement('p');p.className='empty';p.textContent=message;$('#chart').replaceChildren(p)};
 function render(){
  const instrument=registry.instruments[key];
  $('#assetTitle').textContent=instrument.name;$('#ticker').textContent=instrument.symbol;
  $('#external').href=instrument.url;$('#marketInfo').textContent=instrument.info;
  for(const button of document.querySelectorAll('.asset')){
   const active=button.dataset.key===key;button.classList.toggle('active',active);button.setAttribute('aria-pressed',String(active));
  }
  for(const button of document.querySelectorAll('#ranges button')){
   const active=button.dataset.range===range;button.classList.toggle('active',active);button.setAttribute('aria-pressed',String(active));button.disabled=!instrument.embed;
  }
  if(!instrument.embed){
   status(instrument.reason+' Άνοιξε το πλήρες γράφημα στον παρακάτω σύνδεσμο και επίλεξε εκεί το διάστημα.');
   $('#desc').textContent='Ενσωμάτωση μη διαθέσιμη · έλεγχος '+registry.checked_at+' · '+instrument.symbol;
   return;
  }
  $('#desc').textContent='TradingView · '+labels[range]+' · δεδομένα παρόχου κατά τον χρόνο προβολής, με πιθανή καθυστέρηση.';
  const frame=document.createElement('iframe');frame.title='TradingView: '+instrument.name+' · '+labels[range];frame.referrerPolicy='origin';
  // Current provider format uses a JSON fragment, not the legacy widgetembed
  // query integration. The provider may choose its candle interval for the range. No alternate symbols here.
  const settings={symbol:instrument.symbol,interval:'D',range,theme,style:'1',locale:'en',width:'100%',height:'100%',timezone:'Etc/UTC',allow_symbol_change:false,hide_top_toolbar:true,hide_side_toolbar:true,save_image:false,withdateranges:false};
  frame.src='https://www.tradingview-widget.com/embed-widget/advanced-chart/?locale=en#'+encodeURIComponent(JSON.stringify(settings));
  frame.onerror=()=>status('Η σύνδεση με τον πάροχο απέτυχε. Χρησιμοποίησε τον σύνδεσμο πλήρους γραφήματος.');
  $('#chart').replaceChildren(frame);
 }
 $('#theme').onclick=()=>{theme=theme==='light'?'dark':'light';document.documentElement.dataset.theme=theme;try{localStorage.setItem('oracle-theme',theme)}catch(_){}if(registry)render()};
 document.querySelectorAll('.asset').forEach(button=>button.onclick=()=>{if(registry&&registry.instruments[button.dataset.key]){key=button.dataset.key;render()}});
 document.querySelectorAll('#ranges button').forEach(button=>button.onclick=()=>{if(registry&&labels[button.dataset.range]){range=button.dataset.range;render()}});
 fetch('assets/instruments.json').then(response=>{if(!response.ok)throw Error('registry');return response.json()}).then(data=>{registry=data;render()}).catch(()=>status('Η λίστα γραφημάτων δεν είναι διαθέσιμη. Άνοιξε τις πηγές δεδομένων παρακάτω.'));
})();
