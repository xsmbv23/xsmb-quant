from bs4 import BeautifulSoup
from data_foundation.forensic_crawler import extract_full_27, tails27, validate_full_27


def test_extracts_full_27_not_tails():
    html = '''<table>
      <tr><td>ĐB</td><td>12345</td></tr>
      <tr><td>G1</td><td>67890</td></tr>
      <tr><td>G2</td><td>11111 22222</td></tr>
      <tr><td>G3</td><td>12345 23456 34567 45678 56789 67890</td></tr>
      <tr><td>G4</td><td>1111 2222 3333 4444</td></tr>
      <tr><td>G5</td><td>11111 22222 33333 44444 55555 66666</td></tr>
      <tr><td>G6</td><td>111 222 333</td></tr>
      <tr><td>G7</td><td>11 22 33 44</td></tr>
    </table>'''
    table = BeautifulSoup(html, 'html.parser').table
    full = extract_full_27(table)
    assert full is not None and len(full) == 27
    assert full[0] == '12345' and full[1] == '67890'
    assert full[2:4] == ['11111', '22222']
    assert tails27(full)[0] == '45' and tails27(full)[1] == '90'


def test_rejects_wrong_structure():
    try:
        validate_full_27(['12345'] * 26)
    except ValueError as exc:
        assert '27' in str(exc)
    else:
        raise AssertionError('expected strict 27-prize rejection')
