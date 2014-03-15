#! /usr/bin/python
# by pts@fazekas.hu at Sat Mar 15 17:01:14 CET 2014

import json
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
  margin-top: 0px;
  margin-bottom: 1ex;
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
  font-weight: bold;
  color: #090;
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


def main(argv):
  title_html = 'Quiz questions'
  entries_html = r'''
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
  sys.stdout.write(TEMPLATE % {
      'title_html': title_html,
      'entries_html': entries_html,
  })


if __name__ == '__main__':
  sys.exit(main(sys.argv))
