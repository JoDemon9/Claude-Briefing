"""Focused maintenance preview for reading modes, tabs, filters, no-JS and print."""
import copy
import importlib.util
import json
import os
from pathlib import Path
import unittest
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

ROOT=Path(__file__).resolve().parents[1]


def module(name):
    spec=importlib.util.spec_from_file_location('reading_browser_'+name,ROOT/'scripts/v2'/(name+'.py'))
    value=importlib.util.module_from_spec(spec);spec.loader.exec_module(value);return value


def fixture():
    build=module('build');edition=json.loads((ROOT/'content/editions/2026-10-23-evening.json').read_text(encoding='utf-8'))
    articles=[json.loads((ROOT/'content'/path).read_text(encoding='utf-8')) for path in edition['articles'][:2]]
    for index,article in enumerate(articles):
        article.update(id='fixture-'+str(index),story_id='fixture-story-'+str(index),image=None,
                       change_status='NEW' if index==0 else 'UPDATED',driver_tags=['energy' if index==0 else 'cyber'])
    articles[0]['mechanics_and_incentives']='Fixture mechanism, not published analysis.'
    articles[0]['scenarios']={'base_case':'Fixture base','alternative_case':'Fixture alternative','tail_risk':'Fixture tail','watch_next':'Fixture watch'}
    text='<html lang="el"><head><meta name="viewport" content="width=device-width,initial-scale=1">'+''.join('<link rel="stylesheet" href="/assets/'+name+'">' for name in ('newspaper.css','accessibility.css','newspaper-ui.css'))+'<script defer src="/assets/reading.js"></script></head><body><div class="stickybar"><div class="wrap"></div></div><main class="wrap" id="main"><section class="executive-scan">Fixture executive synthesis</section>'+''.join(build.card(edition,a,i==0) for i,a in enumerate(articles))+'<section class="section compact-markets" id="markets"><div class="core-quotes">Fixture compact data</div></section></main></body></html>'
    doc=BeautifulSoup(text,'html.parser')
    morning='2026-10-23T07:36:00+03:00'
    cards=doc.select('[data-intelligence-story]')
    cards[0]['data-change-times']=json.dumps([morning]);cards[1]['data-change-times']=json.dumps(['2026-10-23T14:00:00+03:00'])
    module('intelligence_ui').decorate(build,doc,edition,{'editions':[{'id':'2026-10-23-morning','published_at':morning},{'id':edition['id'],'published_at':edition['published_at']}]})
    return str(doc)


class IntelligenceBrowserTests(unittest.TestCase):
    def test_modes_tabs_filters_and_static_fallback(self):
        text=fixture()
        with sync_playwright() as playwright:
            browser=playwright.chromium.launch(headless=True)
            for width,js in ((390,True),(1440,False),(1440,True)):
                with self.subTest(width=width,javascript=js):
                    context=browser.new_context(java_script_enabled=js,viewport={'width':width,'height':950},reduced_motion='reduce')
                    def route(request):
                        path=request.request.url.removeprefix('http://oracle.test/')
                        if path=='preview':return request.fulfill(body=text,content_type='text/html')
                        asset=ROOT/'docs'/path
                        if path.startswith('assets/') and asset.is_file():return request.fulfill(path=str(asset))
                        return request.abort()
                    context.route('**/*',route)
                    page=context.new_page();errors=[];page.on('pageerror',lambda error:errors.append(str(error)))
                    page.goto('http://oracle.test/preview',wait_until='load')
                    self.assertTrue(page.locator('.hero .abstract').is_visible())
                    if js:
                        self.assertTrue(page.locator('[data-intelligence-controls]').is_visible())
                        page.locator('button[data-reading-mode="full"]').click()
                        self.assertTrue(page.locator('.hero .card-analysis').evaluate('(node)=>node.open'))
                        tabs=page.locator('.hero [role=tab]')
                        tabs.first.focus();page.keyboard.press('ArrowRight')
                        self.assertEqual(tabs.nth(1).get_attribute('aria-selected'),'true')
                        self.assertTrue(page.locator('[data-scenario-panel="alternative_case"]').is_visible())
                        page.locator('button[data-reading-mode="executive"]').click()
                        self.assertFalse(page.locator('.hero').is_visible())
                        self.assertTrue(page.locator('.executive-scan').is_visible())
                        page.locator('button[data-reading-mode="standard"]').click()
                        page.locator('.intelligence-filters > summary').click()
                        page.locator('[data-delta-only]').check()
                        self.assertFalse(page.locator('.hero').is_visible())
                        self.assertTrue(page.locator('.newscard').is_visible())
                        page.locator('[data-clear-filters]').click()
                        page.locator('[data-driver-tag="energy"]').click()
                        self.assertFalse(page.locator('.newscard').is_visible())
                        self.assertIn('tag=energy',page.locator('[data-tag-archive]').get_attribute('href'))
                        self.assertLess(page.locator('.stickybar').bounding_box()['height'],130)
                        page.evaluate("window.dispatchEvent(new Event('beforeprint'))")
                        page.emulate_media(media='print')
                        self.assertTrue(page.locator('.newscard').is_visible())
                        self.assertEqual(page.locator('[data-scenario-panel]:visible').count(),3)
                        page.emulate_media(media='screen')
                    else:
                        self.assertFalse(page.locator('[data-intelligence-controls]').is_visible())
                        page.locator('.hero .card-analysis > summary').click()
                        self.assertEqual(page.locator('[data-scenario-panel]:visible').count(),3)
                    self.assertFalse(page.evaluate('document.documentElement.scrollWidth>innerWidth+1'))
                    self.assertFalse(errors,errors)
                    context.close()
            browser.close()


if __name__=='__main__':unittest.main()
