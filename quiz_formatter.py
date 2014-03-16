#! /usr/bin/python
# by pts@fazekas.hu at Sat Mar 15 17:01:14 CET 2014
# works on Python 2.4, 2.5, 2.6 and 2.7.

import cgi
import cStringIO
import csv
import json  # Needs Python 2.6 or the json module installed.
import os
import os.path
import re
import sys

HTML_TEMPLATE = r'''
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
  font-family: font-family: "Times New Roman", Cambria, "Hoefler Text", Utopia,
      "Nimbus Roman No9 L Regular", "Liberation Serif", Times, serif;
  font-size:12pt;
}
pre {
  margin-top:1ex;
  margin-bottom:1ex;
}
p {
  margin-top:1ex;
  margin-bottom:1ex;
}
pre, code, tt {
  font-size:80%%;  /* Typical typewriter fonts are too large. */
  font-family: "DejaVu Sans Mono", "Bitstream Vera Sans Mono",
      "Liberation Mono", Consolas, "Lucida Console",
      "Lucida Sans Typewriter", "Andale Mono WT", "Andale Mono",
      "Nimbus Mono L", Monaco, "Courier New", Courier, monospace;
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
div.entry div.note span.notehdr {
  font-weight:bold;
}
div.entry div.note {
  /* Don't use display:none here, so pressing Tab won't rebreak the page. */
  visibility:hidden;
  border-top: 1px solid #000;
  margin-top:0.5ex;
  padding-top:0.5ex;
}
body.b div.entry div.note {
  visibility:inherit;
  background:#fee;
}
body.b div.entry div.correct {
  background:#dfd;
  /*color:red;*/
}
.print {
  display:none;
}
.screen {
  display:inherit;
}
@media print {  /* Put this after the general rules to override. */
  body {
    margin:0px;
  }
  div.entry div.question span.id {
    color:#000;
  }
  body div.entry div span.letter {
    font-weight:normal;
  }
  body div.entry div.correct span.letter {
    font-weight:bold;
  }
  body div.entry div.correct {
    background:#fff;
    /*text-decoration:underline;*/  /* Doesn't play well with <sup>. */
    border-bottom:1px solid black;
    display:inline-block;
    margin-left:0.5ex;
    padding-left:0ex;
  }
  div.entry div.note {
    visibility:inherit;
  }
  .print {
    display:inherit;
  }
  .screen {
    display:none;
  }
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
<p class="screen">
<input type=button value="Toogle displaying of solutions and notes" onclick="toggleSolutions()"> (Also works with hot key <i>Tab</i>.)
</p>
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
# TODO(pts): Add support for <script and and <style
HTML_TOKEN_PREFIX_RE = re.compile(
    r'[^&<>]+|'
    r'&(?:#[xX][0-9a-fA-F]+|#[0-9]+|[-.\w]+);|'
    r'<\?(?:(?s).*?)\?>|'  # <?xml...?>
    r'<!--(?:(?s).*?)-->|'  # <!-- comment -->
    r'<(?:[a-zA-Z][-:a-zA-Z]*)(?:\s*[a-zA-Z][-:a-zA-Z]*(?:'
    r'=(?:[^<>="\s]*|"[^<>"]*"|\'[^<>\']*\')'  # HTML tag attribute.
    r')?)*\s*/?>|'
    r'</(?:[a-zA-Z][-:a-zA-Z]*)>')


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
assert is_html('Hello, <i>World!')
assert is_html('Hello, <i>World<i>!')
assert is_html('Hello, </i>World!')
assert is_html('Hello, <b>World</i>!')
assert is_html('Hello, <b>World<i>!')
assert is_html('Hello, <i>W&ouml;rld</i>!')
assert not is_html('<<')
assert not is_html('c<<')
assert not is_html('c&&')
assert not is_html('c&')
assert is_html('"')


PRE_OR_NL_RE = re.compile('\n|(<pre(?=[\s>])[^>]*>[^<>]*</pre>)')


def fix_text(text):
  text = text.strip()
  # TODO(pts): Implement and use is_balanced_html.
  if not is_html(text):
    text = cgi.escape(text)
  # Just like `text = text.replace('\n', '<br>')', but doesn't replace within
  # <pre>.
  text = PRE_OR_NL_RE.sub(lambda match: match.group(1) or '<br>', text)
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
  if not isinstance(entries, (list, tuple)):
    raise ValueError
  output_entries = []
  # Question numbering starts from 0 (default of `enumerate').
  for i, e in enumerate(entries):
    if not isinstance(e, dict): 
      raise ValueError
    e = dict(e)  # Shallow copy.
    output_entries.append(e)
    # TODO(pts): Report a nice error (rather than KeyError) if missing.
    question = e.pop('question')
    qtype = e.pop('type')
    correct = e.pop('correct')
    note = e.pop('note', '')
    answer_set = set(e)
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
    # TODO(pts): Warn if answers are not A, B, C, ... .
    for letter in sorted(answer_set):
      if not (letter and ANSWER_LETTERS_RE.match(letter)):
        raise ValueError('Invalid correct answer letter: ' + repr(letter))
      answer = e[letter].strip()
      if not answer:
        answer_set.remove(letter)
        continue
      e[letter] = answer = fix_text(answer)
    # Check these only this late, because some answers are empty.
    if not answer_set:
      raise ValueError('No answers.')
    if not correct_set.issubset(answer_set):
      raise ValueError('Unknown correct answers: ' + repr(
          correct_set.difference(answer_set)))
    e['question'] = question = fix_text(question)
    e['note'] = note = fix_text(note)
    e['type'] = qtype = fix_text(qtype)
    e['correct'] = correct
  return output_entries


def format_html(entries):
  output = []
  # Question numbering starts from 0 (default of `enumerate').
  for i, e in enumerate(entries):
    if not isinstance(e, dict): 
      raise TypeError
    e = dict(e)  # Shallow copy.
    question = e.pop('question')
    qtype = e.pop('type')
    correct = e.pop('correct')
    note = e.pop('note', '')
    answer_set = set(e)
    if not isinstance(question, str):
      raise TypeError
    if not isinstance(qtype, str):
      raise TypeError
    if not isinstance(correct, str):
      raise TypeError
    correct_set = set(correct)
    correct = ''.join(sorted(correct_set))
    output.append('<div class=entry>\n')
    if qtype == 'tech':
      type_msg = ''
    else:
      type_msg = ' <span class=type>(%(type)s)</span>' % {
          'type': cgi.escape(qtype)}
    output.append(
        '  <div class=question><span class=id>%(i)s%(type_msg)s.</span> '
        '%(question)s</div>\n' %
        {'i': i, 'question': question, 'type_msg': type_msg})
    for letter in sorted(answer_set):
      answer = e[letter].strip()
      if not answer:
        answer_set.remove(letter)
        continue
      if letter in correct_set:
        class_attr = ' class=correct'
      else:
        class_attr = ''
      output.append(
          '  <div%(class_attr)s><span class=letter>%(letter)s.</span> '
          '%(answer)s</div>\n' %
          {'class_attr': class_attr, 'letter': letter, 'answer': answer})
    if note:
      output.append(
          '<div class=note><span class=notehdr>Note:</span> '
          '%(note)s</div>\n' %
          {'note': note})
    output.append('</div>\n')
  return ''.join(output)


def format_csv(entries):
  f = cStringIO.StringIO()
  w = csv.writer(f)
  w.writerow(('Timestamp', 'Question', 'Answer A', 'Answer B', 'Answer C', 'Answer D', 'Correct\n'))
  letters = 'ABCD'
  for e in entries:
    columns = []
    e = dict(e)  # Shallow copy.
    question = e.pop('question')
    qtype = e.pop('type')
    correct = e.pop('correct')
    note = e.pop('note', '')
    answer = ''.join(sorted(e))
    if not set(e).issubset(letters):
      raise ValueError
    columns.append('')  # Timestamp.
    columns.append(question)
    for letter in letters:
      columns.append(e[letter])
    columns.append(correct)
    if '\t' in ''.join(columns):
      raise ValueError('\\t found in line %r.' % columns)
    w.writerow(columns)
  return f.getvalue()


def format_js(entries):
  return 'questions = %s;\n' % json.dumps(
      entries, sort_keys=True, indent=2, separators=(',', ': '))


def main(argv):
  is_help = False
  format = 'html'
  i = 1
  while i < len(argv):
    arg = argv[i]
    i += 1
    if arg == '--':
      break
    elif arg == '-' or not arg.startswith('-'):
      i -= 1
      break
    elif arg == '--help':
      is_help = True
    elif arg.startswith('--format='):
      format = arg.split('=', 1)[1].lower()
    else:
      print >>sys.stderr, 'error: Unknown flag: %s' % arg
      sys.exit(1)
  if is_help:
    print >>sys.stderr, (
        'Usage: %s [<flag> ...] [<questions.js>]\n'
        'Flags:\n'
        '--format=html\n'
        '--format=js\n'
        '--format=csv\n')
    sys.exit(1)
  if i == len(argv):
    filename = 'questions.js'
  elif i + 1 == len(argv):
    filename = argv[i]
  else:
    print >>sys.stderr, 'error: Too many command-line argumens: ' + repr(
        argv[i + 1:])
    sys.exit(1)

  if format not in ('html', 'csv', 'js'):
    print >>sys.stderr, 'error: Unknown output format: %s' % format
    sys.exit(1)

  output_filename = os.path.splitext(filename)[0] + '.' + format
  if output_filename == filename:
    print >>sys.stderr, (
        'error: Input and output filenames are the same: ' + filename)
    sys.exit(2)

  entries = get_entries(filename)
  if format == 'html':
    entries_html = format_html(entries)
    title_html = 'Quiz questions'
    output = HTML_TEMPLATE % {
        'title_html': title_html,
        'entries_html': entries_html,
    }
    print >>sys.stderr, 'info: Writing HTML output: ' + output_filename
  elif format == 'js':
    output = format_js(entries)
    print >>sys.stderr, 'info: Writing JavaScript output: ' + output_filename
  else:
    output = format_csv(entries)
    print >>sys.stderr, 'info: Writing CSV output: ' + output_filename
  f = open(output_filename, 'w')
  try:
    f.write(output)
  finally:
    f.close()


if __name__ == '__main__':
  sys.exit(main(sys.argv))
