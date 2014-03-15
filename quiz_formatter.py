#! /usr/bin/python
# by pts@fazekas.hu at Sat Mar 15 17:01:14 CET 2014
# works on Python 2.4, 2.5, 2.6 and 2.7.

import cgi
import json  # Needs Python 2.6 or the json module installed.
import os
import os.path
import re
import sys

TEMPLATE = r'''
<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01 Transitional//EN"
    "http://www.w3.org/TR/html4/loose.dtd">
<html><head>
<meta http-equiv="content-type" content="text/html; charset=UTF-8">
<title>%(title_html)s</title>
<style type="text/css">
body {
  background:#eef;
  color:#000;
  margin:1ex;
  padding:0px;
  font-family:serif;
  font-size:12pt;
}
h1.top {
  margin-top:0px;
  margin-bottom:1ex;
}
div.entry {
  background:#fff;
  border:1px solid #000;
  margin-top:2ex;
  margin-bottom:2ex;
  padding-top:0.5ex;
  padding-bottom:0.5ex;
}
div.entry > div {
  padding-left:0.5ex;
  padding-right:0.5ex;
}
div.entry div.question {
  border-bottom:1px solid #000;
  padding-bottom:0.5ex;
  margin-bottom:0.5ex;
}
div.entry div.question span.id {
  font-weight:bold;
  color:#090;
}
div.entry div span.letter {
  font-weight:bold;
}
body.b div.entry div.correct {
  background:#dfd;
  /*color:red;*/
}
</style>
<script type="text/javascript">
function toggleSolutions() {
  var c = document.body.className.split(/\s+/);
  if (c.indexOf('b') >= 0) {
    c = c.filter(function(x) { x != 'b' });
  } else {
    c.push('b')
  }
  document.body.className = c.join(' ');
}
function onKeyPress(event) {
  if (!event) event = window.event;
  var keyCode = event.keyCode;
  var charCode = event.charCode;
  var modifiers = (event.altKey || event.metaKey ? 1 : 0) |
      (event.ctrlKey ? 2 : 0) |
      (event.shiftKey ? 4 : 0);
  //alert(keyCode+';'+charCode);
  if (keyCode == 9 && charCode == 0 && modifiers == 0) {  // <Tab>
    toggleSolutions();
    event.preventDefault ? event.preventDefault() : (event.returnValue = false);
  }
}
if (document.addEventListener) {
  document.addEventListener('DOMContentLoaded', function() {
    document.addEventListener('keydown', onKeyPress, false);
  }, false);
} else {  // Internet Explorer 8.
  function onReadyStateChange() {
    if (document.readyState == 'complete') {
      document.detachEvent('onreadystatechange', onReadyStateChange)
      document.attachEvent('onkeydown', onKeyPress);
    }
  }
  document.attachEvent('onreadystatechange', onReadyStateChange);
}
</script>
</head><body>
<h1 class=top>%(title_html)s</h1>
<p>Press <i>Tab</i> to toggle showing the correct answers.
%(entries_html)s
</body>
'''

JS_ASSIGNMENT_RE = re.compile(r'[A-Za-z]\w*[ \t]*=\s*')

def unicode_to_utf8(obj):
  """Converts unicode to UTF-8-encoded str, recursively."""
  if obj is None or isinstance(obj, (int, long, float, bool)):
    return obj
  elif isinstance(obj, str):
    obj.decode('UTF-8')  # Raise UnicodeDecodeError if invalid.
    return 
  elif isinstance(obj, unicode):
    return obj.encode('UTF-8')
  elif isinstance(obj, (list, tuple)):
    return map(unicode_to_utf8, obj)  # list to list, tuple to tuple.
  elif isinstance(obj, dict):
    result = {}
    for key, value in sorted(obj.iteritems()):
      key = unicode_to_utf8(key)
      if key in result:
        raise KeyError(key)
      result[key] = unicode_to_utf8(value)
    return result


# TODO(pts): Replace this with something faster, because Python regexps always
# backtrack, and that's slow.
HTML_TOKEN_PREFIX_RE = re.compile(
    r'[^&<>]+|'
    r'&(?:#[xX][0-9a-fA-F]+|#[0-9]+|[-.\w]+);|'
    r'<\?(?:(?s).*?)\?>|'  # <?xml...?>
    r'<!--(?:(?s).*?)-->|'  # <!-- comment -->
    r'<[a-zA-Z][-:a-zA-Z]*(?:\s*[a-zA-Z][-:a-zA-Z]*(?:'
    r'=(?:[^<>="\s]*|"[^<>"]*"|\'[^<>\']*\')'  # HTML tag attribute.
    r')?)*/?>|'
    r'</[a-zA-Z][-:a-zA-Z]*>')


def is_html(text):
  """Does the text look like HTML? Nonvalidating, heuristic parser."""
  scanner = HTML_TOKEN_PREFIX_RE.scanner(text)
  i = 0
  while i < len(text):
    match = scanner.match()
    if not match:
      return False
    i = match.end()
  return True

assert is_html('')
assert is_html('Hello, <i>World</i>!')
assert is_html('Hello, <i>W&ouml;rld</i>!')
assert not is_html('<<')
assert not is_html('c<<')
assert not is_html('c&&')
assert not is_html('c&')
assert is_html('"')


def fix_text(text):
  text = text.strip()
  if not is_html(text):
    text = cgi.escape(text)
  text = text.replace('\n', '<br>')
  return text


ANSWER_LETTERS_RE = re.compile('[A-Z]*\Z')


def get_entries(filename):
  f = open(filename)
  try:
    data = f.read()
  finally:
    f.close()
  data = data.strip().rstrip(';')
  match = JS_ASSIGNMENT_RE.match(data)
  if match:
    data = data[match.end():]
  entries = unicode_to_utf8(json.loads(data))
  output = []
  # Question numbering starts from 0 (default of `enumerate').
  for i, e in enumerate(entries):
    answer_set = set(e)
    answer_set.discard('question')
    answer_set.discard('type')
    answer_set.discard('correct')
    # TODO(pts): Report a nice error (rather than KeyError) if missing.
    question, qtype, correct = e['question'], e['type'], e['correct']
    if not isinstance(question, str):
      raise ValueError
    if not isinstance(qtype, str):
      raise ValueError
    if not isinstance(correct, str):
      raise ValueError
    correct_set = set(correct)
    correct = ''.join(sorted(correct_set))
    if not correct:
      raise ValueError('No correct answer.')
    if not ANSWER_LETTERS_RE.match(correct):
      raise ValueError('Invalid correct answer spec: ' + repr(correct))
    output.append('<div class=entry>\n')
    question = fix_text(question)
    if qtype == 'tech':
      type_msg = ''
    else:
      type_msg = ' <span class=type>(%(type)s)</span>' % {
          'type': cgi.escape(qtype)}
    output.append(
        '  <div class=question><span class=id>%(i)s%(type_msg)s.</span> '
        '%(question)s</div>\n' %
        {'i': i, 'question': question, 'type_msg': type_msg})
    # TODO(pts): Warn if answers are not A, B, C, ... .
    for letter in sorted(answer_set):
      answer = e[letter].strip()
      if not answer:
        answer_set.remove(letter)
        continue
      answer = fix_text(answer)
      if letter in correct_set:
        class_attr = ' class=correct'
      else:
        class_attr = ''
      output.extend(
          '  <div%(class_attr)s><span class=letter>%(letter)s.</span> '
          '%(answer)s</div>\n' %
          {'class_attr': class_attr, 'letter': letter, 'answer': answer})
    output.append('</div>\n')
    # Check these only this late, because some answers are empty.
    if not answer_set:
      raise ValueError('No answers.')
    if not correct_set.issubset(answer_set):
      raise ValueError('Unknown correct answers: ' + repr(
          correct_set.difference(answer_set)))
  return ''.join(output)
  return r'''
<div class=entry>
  <div class=question><span class=id>1.</span> What is the answer?</div>
  <div>foo</div>
  <div class=correct>bar</div>
  <div>baz</div>
</div>
<div class=entry>
  <div class=question><span class=id>2.</span> How old is the captain?</div>
  <div>foo</div>
  <div>baz</div>
  <div class=correct>bar</div>
</div>'''.lstrip('\n')


def main(argv):
  if len(argv) == 2 and argv[1] != '--help':
    filename = argv[1]
  elif len(argv) == 1:
    filename = 'questions.js'
  else:
    print >>sys.stderr, 'Usage: %s [<questions.js>]'
    sys.exit(1)
  output_filename = os.path.splitext(filename)[0] + '.html'
  if output_filename == filename:
    print >>sys.stderr, (
        'error: Input and output filenames are the same: ' + filename)
    sys.exit(2)

  entries_html = get_entries(filename)
  title_html = 'Quiz questions'
  output = TEMPLATE % {
      'title_html': title_html,
      'entries_html': entries_html,
  }

  print >>sys.stderr, 'info: Writing HTML output: ' + output_filename
  f = open(output_filename, 'w')
  try:
    f.write(output)
  finally:
    f.close()


if __name__ == '__main__':
  sys.exit(main(sys.argv))
