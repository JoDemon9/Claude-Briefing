"""Shared frontend layout. Preserve reviewed text, publication identity and URLs."""
from datetime import date
from bs4 import BeautifulSoup

MONTHS=('Ιανουαρίου','Φεβρουαρίου','Μαρτίου','Απριλίου','Μαΐου','Ιουνίου','Ιουλίου','Αυγούστου','Σεπτεμβρίου','Οκτωβρίου','Νοεμβρίου','Δεκεμβρίου')
DAYS=('Δευτέρα','Τρίτη','Τετάρτη','Πέμπτη','Παρασκευή','Σάββατο','Κυριακή')
HUB='https://jodemon9.github.io/oracle-briefing/'

def summary(b, paragraphs, label, story_links=None):
    topics={'Πρώτο θέμα':('📰','lead'),'Επίδομα τέκνου':('👨‍👩‍👧','family'),'Κύπρος':('🇨🇾','cyprus'),'Διεθνή':('🌍','world'),'Αγορές':('📈','markets'),'Αθλητισμός':('🏆','sports'),'Λεμεσός':('🌤️','weather')}
    items=[]
    for index,paragraph in enumerate(paragraphs):
        topic,separator,text=paragraph.partition(':')
        known=separator and topic in topics
        emoji,kind=topics[topic] if known else ('📰','news')
        heading=b.esc(topic)+':' if known else f'{index+1:02}'
        body=b.esc(text.lstrip() if known else paragraph)
        links=(story_links or [])[index] if story_links and index<len(story_links) else []
        actions='<div class="summary-story-links">'+''.join('<a href="'+b.esc(link['url'])+'">'+b.esc(link['label'])+' '+b.icon('arrow')+'</a>' for link in links)+'</div>' if links else ''
        items.append('<li class="summary-point summary-'+kind+'"><div class="summary-topic"><span aria-hidden="true">'+emoji+'</span><b>'+heading+'</b></div><p>'+body+'</p>'+actions+'</li>')
    return '<details class="day-summary" id="summary"><summary>'+b.emblem('summary')+'<span class="summary-heading">'+b.esc(label)+'<small>'+str(len(paragraphs))+' σημεία · Η γρήγορη ματιά σου</small></span></summary><ol class="summary-points">'+''.join(items)+'</ol></details>'

def changes(b, records):
    markers={'Πλαίσιο':'🧭','Προσθήκη':'＋','Εξέλιξη':'↗','Διόρθωση':'✎'}
    items=''.join('<li class="edition-change"><span class="change-kind"><span aria-hidden="true">'+markers.get(c['kind'],'•')+'</span> '+b.esc(c['kind'])+'</span><p>'+b.esc(c['text'])+'</p></li>' for c in records)
    return '<section class="edition-changes" id="edition-changes"><div class="sectionhead"><h2>'+b.emblem('changes')+'Τι άλλαξε</h2><span>Από την προηγούμενη έκδοση</span></div>'+('<ul class="edition-change-list">'+items+'</ul>' if items else '<p>Δεν έχει καταγραφεί ουσιαστική αλλαγή.</p>')+'</section>'

def date_label(value):
    day=date.fromisoformat(value)
    return f'{DAYS[day.weekday()]} {day.day} {MONTHS[day.month-1]} {day.year}'

def mobile_publication(doc, edition, day):
    """Compact native mobile navigation, derived from the same edition records."""
    bar=doc.select_one('.publication-bar')
    if not bar or bar.select_one('.mobile-editions'):return
    intro=bar.select_one('.introbar');desk=bar.select_one('.edition-desk')
    if not intro or not desk:return
    value=date.fromisoformat((day or edition)['date'])
    calendar=doc.new_tag('time',attrs={'class':'mobile-publication-date','datetime':value.isoformat(),'title':date_label(value.isoformat())})
    calendar.string=f'{DAYS[value.weekday()]} {value.day:02}/{value.month:02}'
    intro.insert(0,calendar)
    menu=doc.new_tag('details',attrs={'class':'mobile-editions'})
    toggle=doc.new_tag('summary')
    edition_name={'morning':'Πρωινή','midday':'Μεσημεριανή','evening':'Βραδινή'}[edition['type']]
    toggle.string=f'Εκδόσεις · {len(day["editions"])}/3' if day else edition_name
    toggle['aria-label']='Επιλογή εκδόσεων' if day else edition_name+' έκδοση · Επιλογή εκδόσεων'
    menu.append(toggle)
    panel=doc.new_tag('div',attrs={'class':'mobile-edition-panel'})
    label=doc.new_tag('strong');label.string='Εφημερίδα ημέρας' if day else edition_name+' έκδοση'
    panel.append(label)
    if edition.get('scheduled_slot') and not day:
        scheduled=doc.new_tag('p');scheduled.string='Προγραμματισμός: '+edition['scheduled_slot'];panel.append(scheduled)
    links=BeautifulSoup(str(desk),'html.parser').nav
    links['class']=['mobile-edition-links']
    for node in links.select('b,.participating-caption'):node.decompose()
    for node in links.select('[aria-current]'):
        node['data-current-edition']='true';del node['aria-current']
    panel.append(links)
    home=doc.new_tag('a',href=HUB);home.string='Κύρια εφημερίδα ↗';panel.append(home)
    archive=doc.new_tag('a',href='../daily/index.html');archive.string='Αρχείο ημερών';panel.append(archive)
    menu.append(panel);bar.append(menu)

def decorate(b, text, edition, day=None):
    doc=BeautifulSoup(text,'html.parser')
    main=doc.select_one('main.wrap')
    if not main:return text
    if not doc.select_one('.hub-guide'):
        guide=doc.new_tag('section',attrs={'class':'hub-guide','aria-label':'Κύρια εφημερίδα και αρχείο'})
        identity=doc.new_tag('div',attrs={'class':'hub-identity'})
        title=doc.new_tag('strong');title.string='🗞️ Η κύρια εφημερίδα ημέρας' if day else '☀️ Πρωινό στιγμιότυπο' if edition['type']=='morning' else '🕑 Μεσημεριανό στιγμιότυπο' if edition['type']=='midday' else '🌙 Βραδινό στιγμιότυπο'
        identity.append(title)
        note=doc.new_tag('p');note.string='Τα κύρια νέα σε μία σελίδα · Πρωί, μεσημέρι και βράδυ όταν δημοσιευτούν.' if day else 'Δες τη συνολική εικόνα και τις εκδόσεις της ημέρας στην κύρια εφημερίδα.'
        identity.append(note);guide.append(identity)
        links=doc.new_tag('nav',attrs={'class':'hub-links','aria-label':'Εφημερίδα ημέρας'})
        home=doc.new_tag('a',href=HUB,attrs={'class':'hub-home'});home.string='Κύρια εφημερίδα ↗';links.append(home)
        archive=doc.new_tag('a',href='../daily/index.html');archive.string='Αρχείο ημερών';links.append(archive)
        guide.append(links);main.insert(0,guide)
        brand=doc.select_one('.masthead .brand h1')
        if brand:
            anchor=doc.new_tag('a',href=HUB,attrs={'aria-label':'The Oracle Sovereign · Κύρια εφημερίδα ημέρας'})
            for child in list(brand.contents):anchor.append(child.extract())
            brand.append(anchor)
    nav=doc.select_one('.navs')
    if nav and doc.select_one('#opportunities') and not nav.select_one('a[href="#opportunities"]'):
        anchor=doc.new_tag('a',href='#opportunities');anchor.string='Επιδοτήσεις & δικαιώματα'
        markets=nav.select_one('a[href="#markets"]')
        if markets:markets.insert_before(anchor)
        else:nav.append(anchor)
    if nav and not doc.select_one('.section-menu'):
        # One complete native menu replaces the horizontally clipped mobile links.
        links=BeautifulSoup(str(nav),'html.parser').nav
        links['class']=['section-menu-list'];links['aria-label']='Όλες οι ενότητες'
        known={a.get('href') for a in links.select('a')}
        for panel in doc.select('.edition-panel'):
            target='#'+panel['id']
            if target in known:continue
            heading=BeautifulSoup(str(panel.h2),'html.parser')
            for marker in heading.select('.section-emblem'):marker.decompose()
            anchor=doc.new_tag('a',href=target);anchor.string=heading.get_text(' ',strip=True)
            links.append(anchor)
        menu=doc.new_tag('details',attrs={'class':'section-menu'})
        summary=doc.new_tag('summary')
        summary.append(BeautifulSoup(b.icon('news'),'html.parser'));summary.append('Ενότητες')
        menu.append(summary);menu.append(links);nav.insert_before(menu)
    tools=doc.select_one('.stickybar .tools')
    if tools and not tools.select_one('.utility-menu'):
        menu=doc.new_tag('details',attrs={'class':'utility-menu'})
        summary=doc.new_tag('summary',attrs={'aria-label':'Περισσότερες επιλογές'})
        symbol=doc.new_tag('span',attrs={'class':'utility-symbol','aria-hidden':'true'});symbol.string='⋯';summary.append(symbol)
        label=doc.new_tag('span',attrs={'class':'utility-label'});label.string='Περισσότερα';summary.append(label)
        menu.append(summary)
        items=doc.new_tag('div',attrs={'class':'utility-list'})
        for node in tools.select('[data-print],a[aria-label="Ροή ειδήσεων"]'):
            items.append(node.extract())
        menu.append(items);tools.append(menu)
        button=tools.select_one('[data-theme-toggle]')
        if button:button.string='◐ Θέμα'
    intro=doc.select_one('.introbar');desk=doc.select_one('.edition-desk')
    if intro and desk and not doc.select_one('.publication-bar'):
        bar=doc.new_tag('section',attrs={'class':'publication-bar','aria-label':'Ημερομηνία και δημοσιευμένες εκδόσεις'})
        intro.insert_before(bar)
        label='Εφημερίδα ημέρας' if day else b.TYPES[edition['type']]+' έκδοση'
        intro.b.clear();intro.b.append(label+' · ')
        calendar_date=doc.new_tag('time',attrs={'class':'publication-date','datetime':(day or edition)['date']});calendar_date.string=date_label((day or edition)['date']);intro.b.append(calendar_date)
        given=(day or edition)['updated_at' if day else 'published_at']
        zone=(day or edition)['timezone']
        stamp=b.stamp(given,zone)
        time=doc.new_tag('time',attrs={'datetime':given,'title':stamp});time.string=stamp.partition(' · ')[2] or stamp
        intro.span.clear();intro.span.append('Ενημέρωση: ' if day else 'Δημοσίευση: ');intro.span.append(time)
        if not day and edition.get('scheduled_slot'):
            slot=doc.new_tag('span',attrs={'class':'scheduled-slot'});slot.string='Προγραμματισμός: '+edition['scheduled_slot'];intro.append(slot)
        bar.append(intro.extract());bar.append(desk.extract())
        if edition.get('reading_review',{}).get('version')==2 and edition.get('analysis_revision_at'):
            note=doc.new_tag('p',attrs={'class':'revision-note editorial-revision'})
            note.string='Συντακτική αναθεώρηση: '+b.stamp(edition['analysis_revision_at'],edition['timezone'])+'. Οι ειδήσεις και οι πηγές διατηρούν τους αρχικούς χρόνους τους.'
            bar.insert_after(note)
        if day:
            caption=doc.new_tag('span',attrs={'class':'participating-caption'});caption.string='Συμμετέχουν στην ημέρα:';desk.insert(0,caption)
        for node in desk.find_all('span',recursive=False):
            if 'participating-caption' in node.get('class',[]):continue
            original=node.get('aria-label') or node.get('title') or node.get_text(' ',strip=True)
            node['title']=original;node['aria-label']=original
            slot=node.get_text(' ',strip=True).partition(' · ')[0]
            node.clear();node.append(slot)
            state=doc.new_tag('small',attrs={'class':'slot-state'});state.string='Μη διαθέσιμη';node.append(state)
        if day and day['missing_slots']:
            note=doc.select_one('main > .revision-note')
            status=doc.new_tag('span',attrs={'class':'edition-count'});status.string=f'{len(day["editions"])}/3 εκδόσεις'
            if note:
                about=doc.select_one('.edition-about')
                if about:about.append(note.extract())
            intro.append(status)
    mobile_publication(doc,edition,day)
    for label in doc.select('.reading-layer,.reading-time'):label.decompose()
    # Reuse the existing sources disclosure for the edition references as well.
    for card in doc.select('[data-story-id]'):
        history=card.select_one('.story-history')
        sources=card.select_one('.lead-copy > .sources-disclosure,.story-content > .sources-disclosure')
        if history and sources and history!=sources:
            sources['class']=list(dict.fromkeys(sources.get('class',[])+['article-meta']))
            sources.summary.clear();sources.summary.append(BeautifulSoup(b.icon('book'),'html.parser'));sources.summary.append('Πηγές και εκδόσεις')
            body=sources.select_one('.disclosure-body')
            heading=doc.new_tag('h4');heading.string='Προηγούμενες αναφορές'
            body.append(heading)
            for anchor in list(history.select('a')):body.append(anchor.extract())
            history.decompose()
    # DEC-006: concise controls share one row; their native panels span below it.
    for card in doc.select('.hero,.newscard'):
        parent=card.select_one('.lead-copy') or card.select_one('.story-content')
        if not parent or parent.select_one('.article-actions'):continue
        analysis=parent.select_one(':scope > .card-analysis,:scope > section.lead-analysis')
        if analysis and analysis.name=='section':
            analysis.name='details';analysis['class']=['card-analysis','lead-analysis']
            analysis.h3.name='summary'
        reader=parent.select_one(':scope > .story-actions')
        sources=parent.select_one(':scope > .sources-disclosure')
        if not reader or not sources:continue
        actions=doc.new_tag('div',attrs={'class':'article-actions'+(' two-actions' if not analysis else '')})
        reader.insert_before(actions)
        for node,label in [(analysis,'Ανάλυση'),(reader,'Άρθρο'),(sources,'Πηγές')]:
            if not node:continue
            control=node.select_one('a') if node==reader else node.summary
            original=control.get_text(' ',strip=True)
            control['aria-label']=original;control['title']=original
            control.clear();control.append(label)
            actions.append(node.extract())
    for caption in doc.select('figure[data-editorial-image] figcaption'):caption.decompose()
    footer=doc.select_one('.day-footer,.footer')
    if footer and not footer.select_one('.image-credits-link'):
        link=doc.new_tag('a',href=b.BASE+'photo-credits.html',attrs={'class':'image-credits-link'})
        link.string='Συντελεστές εικόνων';footer.append(link)
    b.load_module('intelligence_ui').decorate(b, doc, edition, day)
    return str(doc)
