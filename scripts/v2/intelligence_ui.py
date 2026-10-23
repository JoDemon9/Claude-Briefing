"""Progressive reading controls; the complete newspaper remains usable without JS."""
from bs4 import BeautifulSoup

LABELS = {'NEW':'Νέο', 'UPDATED':'Ενημερώθηκε', 'REVERSAL':'Ανατροπή',
          'CORRECTION':'Διόρθωση', 'UNCHANGED':'Προηγούμενο πλαίσιο', 'UNKNOWN':'Χωρίς ταξινόμηση μεταβολής'}


def decorate(b, doc, edition, day=None):
    if edition.get('intelligence_contract') != 1:
        return
    doc.html['data-intelligence'] = '1'
    doc.html['data-reading-mode'] = 'standard'
    for card in doc.select('[data-intelligence-story]'):
        findings = card.select_one('.story-findings')
        if findings:
            findings['open'] = ''
        parent = card.select_one('.lead-copy') or card.select_one('.story-content')
        status = card.get('data-change-status', 'UNKNOWN')
        badge = doc.new_tag('span', attrs={'class':'intelligence-status'})
        badge.string = LABELS[status]
        heading = parent.select_one('h2,h3')
        if heading:
            heading.insert_before(badge)
        tags = card.get('data-driver-tags','').split()
        if tags:
            row = doc.new_tag('nav', attrs={'class':'driver-tags','aria-label':'Κοινοί παράγοντες'})
            for tag in tags:
                link = doc.new_tag('a', href=b.BASE+'search.html?tag='+tag, attrs={'data-driver-tag':tag,'aria-pressed':'false'})
                link.string = '#'+tag
                row.append(link)
            heading.insert_after(row)
    controls = BeautifulSoup('''<div class="intelligence-controls" hidden data-intelligence-controls>
      <div role="group" aria-label="Τρόπος ανάγνωσης"><button type="button" data-reading-mode="executive" aria-pressed="false">30″ Επισκόπηση</button><button type="button" data-reading-mode="standard" aria-pressed="true">Σάρωση</button><button type="button" data-reading-mode="full" aria-pressed="false">Πλήρης ανάλυση</button></div>
      <label><input type="checkbox" data-delta-only> Μόνο μεταβολές</label><label>Σύγκριση με <select data-delta-baseline></select></label>
      <button type="button" data-clear-filters>Όλα τα θέματα</button><a data-tag-archive hidden>Σχετικά στο αρχείο ↗</a><span role="status" data-filter-status></span>
    </div>''', 'html.parser').div
    select = controls.select_one('select')
    options = []
    if day:
        options = [(e['id'], e['published_at']) for e in day['editions'][:-1]]
    elif edition.get('baseline'):
        ref = edition['baseline']
        baseline, _ = b.load_module('baseline').load(b.ROOT, ref, edition['published_at'])
        options = [(baseline['id'], baseline['published_at'])]
    for eid, at in options:
        option = doc.new_tag('option', value=at)
        option.string = eid
        select.append(option)
    if not options:
        option = doc.new_tag('option', value='')
        option.string = 'Δεν ορίστηκε βάση'
        select.append(option)
        select['disabled'] = ''
        controls.select_one('[data-delta-only]')['disabled'] = ''
    sticky = doc.select_one('.stickybar > .wrap')
    if sticky:
        sticky.append(controls)
    else:
        doc.select_one('main').insert(0, controls)
