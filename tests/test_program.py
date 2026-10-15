import importlib.util
import json
from datetime import date
from pathlib import Path
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('program', Path(__file__).resolve().parents[1] / 'scripts/update_program.py')
p = importlib.util.module_from_spec(spec)
spec.loader.exec_module(p)


def activity(**extra):
    return dict(id='a', title='Minidisco', desc='Vanaf 8 jaar, neem 2 schoenen mee.', location='Animatie blokhut',
                ages=['8+'], start='19:00', end='19:30', image='', **extra)


class ProgramTests(unittest.TestCase):
    def test_source_change_invalidates_translation_but_schedule_change_does_not(self):
        item = activity()
        identity = p.fingerprint(item, {})
        self.assertEqual(identity, p.fingerprint({**item, 'id': 'different', 'start': '20:00'}, {}))
        self.assertNotEqual(identity, p.fingerprint({**item, 'desc': 'Vanaf 10 jaar.'}, {}))
        self.assertNotEqual(identity, p.fingerprint(item, {'term': 'new preference'}))

    def test_number_changes_and_invented_empty_fields_are_rejected(self):
        source = p.source_text(activity())
        p.validate_translation(source, {**source, 'desc': 'For ages 8 and up, bring 2 shoes.'})
        with self.assertRaises(ValueError):
            p.validate_translation(source, {**source, 'desc': 'For ages 6 and up, bring 2 shoes.'})
        with self.assertRaises(ValueError):
            p.validate_translation(source, {**source, 'ages': ['6+']})
        with self.assertRaises(ValueError):
            p.validate_translation({**source, 'location': ''}, source)

    def test_stale_translation_never_reused(self):
        item = activity()
        memory = {p.fingerprint(item, {}): {'en': p.source_text(item), 'de': p.source_text(item)}}
        changed = {**item, 'desc': 'Vanaf 10 jaar.'}
        built = p.build_languages({'2026-10-14': [changed]}, {}, memory, {}, {})
        self.assertNotIn('2026-10-14', built['en'])
        built = p.build_languages({'2026-10-14': [item]}, {}, memory, {}, {})
        self.assertEqual(built['en']['2026-10-14'][0]['start'], '19:00')

    def test_date_window_and_same_id_in_distinct_slots(self):
        xml = b'''<RECREATHEEK><DATUM date="2026-10-12"><ACTIVITEIT><TITEL>Old</TITEL></ACTIVITEIT></DATUM>
        <DATUM date="2026-10-13"><ACTIVITEIT><ACTIVITEITID>a</ACTIVITEITID><TIJD>10:00 UUR</TIJD><TITEL>A</TITEL></ACTIVITEIT>
        <ACTIVITEIT><ACTIVITEITID>a</ACTIVITEITID><TIJD>10:00 UUR</TIJD><TITEL>A</TITEL></ACTIVITEIT>
        <ACTIVITEIT><ACTIVITEITID>a</ACTIVITEITID><TIJD>11:00 UUR</TIJD><TITEL>A</TITEL></ACTIVITEIT></DATUM>
        <DATUM date="2026-10-22"/><DATUM date="2026-10-23"/></RECREATHEEK>'''
        days = p.parse_feed(xml, date(2026, 10, 14))
        self.assertEqual(set(days), {'2026-10-13', '2026-10-22'})
        self.assertEqual(len(days['2026-10-13']), 2)
        self.assertEqual(days['2026-10-13'][0]['start'], '10:00')

    def test_invalid_xml_and_entities_are_rejected(self):
        for xml in [b'<html/>', b'<!DOCTYPE x [<!ENTITY a "b">]><RECREATHEEK/>']:
            with self.assertRaises(ValueError):
                p.parse_feed(xml, date(2026, 10, 14))

    def test_french_factual_metadata_preserved(self):
        item = activity()
        french = {**item, 'title': 'Mini disco', 'ages': [], 'location': ''}
        built = p.build_languages({'2026-10-14': [item]}, {'2026-10-14': [french]}, {}, {}, {})
        self.assertEqual(built['fr']['2026-10-14'][0]['ages'], ['8+'])
        self.assertEqual(built['fr']['2026-10-14'][0]['location'], 'Animatie blokhut')

    def test_french_missing_title_repaired_without_overwriting_source(self):
        item = activity()
        french = {**item, 'title': '  ', 'desc': 'Description française conservée.'}
        nl, fr = {'2026-10-15': [item]}, {'2026-10-15': [french]}
        repairs = p.french_repairs(nl, fr, {})
        self.assertEqual(len(repairs), 1)
        _, _, fields, identity, source = repairs[0]
        self.assertEqual(fields, ['title'])
        self.assertEqual(source['desc'], '')
        memory = {identity: {'fr': {**source, 'title': 'Mini-discothèque'}}}
        built = p.build_languages(nl, fr, memory, {}, {})
        self.assertEqual(built['fr']['2026-10-15'][0]['title'], 'Mini-discothèque')
        self.assertEqual(built['fr']['2026-10-15'][0]['desc'], french['desc'])
        self.assertEqual(french['title'], '  ')
        self.assertEqual(identity, p.french_repairs(nl, fr, {})[0][3])
        french['title'] = 'Titre fourni par Recreatheek'
        self.assertEqual(p.french_repairs(nl, fr, {}), [])
        self.assertEqual(p.build_languages(nl, fr, memory, {}, {})['fr']['2026-10-15'][0]['title'], french['title'])

    def test_french_repair_changes_with_source_and_requires_cache(self):
        item = activity()
        french = {**item, 'title': ''}
        nl, fr = {'2026-10-15': [item]}, {'2026-10-15': [french]}
        identity = p.french_repairs(nl, fr, {})[0][3]
        with self.assertRaises(ValueError):
            p.build_languages(nl, fr, {}, {}, {})
        item['title'] = 'Nieuwe activiteit'
        self.assertNotEqual(identity, p.french_repairs(nl, fr, {})[0][3])
        french['start'] = '20:00'
        self.assertEqual(p.french_repairs(nl, fr, {}), [])

    def test_french_api_only_requests_french_and_preserves_empty_fields(self):
        source = {'title': 'Meeleef theater', 'desc': '', 'location': '', 'ages': []}
        target = {**source, 'title': 'Théâtre participatif'}
        result = {'status': 'completed', 'output': [{'content': [{'type': 'output_text', 'text': json.dumps({'translations': [{'id': 'fr:hash', 'fr': target}]})}]}]}
        with patch.object(p, 'fetch_bytes', return_value=json.dumps(result).encode()) as request:
            translated = p.translate_batch([{'id': 'fr:hash', 'source': source}], {}, 'dummy', ('fr',))
            self.assertEqual(translated['fr:hash']['fr'], target)
            payload = json.loads(request.call_args.args[1])
            self.assertEqual(payload['text']['format']['schema']['properties']['translations']['items']['required'], ['id', 'fr'])

    def test_api_contract_checks_each_id_and_completed_response(self):
        source = p.source_text(activity())
        result = {'status': 'completed', 'output': [{'content': [{'type': 'output_text', 'text': json.dumps({'translations': [{'id': 'hash', 'en': source, 'de': source}]})}]}]}
        with patch.object(p, 'fetch_bytes', return_value=json.dumps(result).encode()):
            self.assertEqual(set(p.translate_batch([{'id': 'hash', 'source': source}], {}, 'dummy')), {'hash'})
        result['status'] = 'incomplete'
        with patch.object(p, 'fetch_bytes', return_value=json.dumps(result).encode()):
            with self.assertRaises(ValueError):
                p.translate_batch([{'id': 'hash', 'source': source}], {}, 'dummy')


if __name__ == '__main__':
    unittest.main()
