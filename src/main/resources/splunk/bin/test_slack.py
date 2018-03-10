import unittest
from slack import build_alert_attachment, build_fields_attachment

class TestAttachments(unittest.TestCase):
    def test_build_alert_attachment_does_not_raise(self):
        build_alert_attachment(dict(configuration=dict()))

    def test_build_fields_attachment_does_not_raise(self):
        build_fields_attachment(dict(configuration=dict()))

    def test_build_fields_attachment(self):
        result = build_fields_attachment(dict(
            configuration=dict(fields='foo, bar*'),
            result=dict(
                foo='YOLO',
                bar1='hi',
                bar2='there',
                other='nix',
            ),
        ))
        self.assertEqual(result, [
            {'short': True, 'title': 'foo', 'value': 'YOLO'},
            {'short': True, 'title': 'bar1', 'value': 'hi'},
            {'short': True, 'title': 'bar2', 'value': 'there'},
        ])

if __name__ == '__main__':
    unittest.main()
