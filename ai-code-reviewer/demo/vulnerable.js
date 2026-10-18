var express = require('express');
function run(db, name, el, cp, input) {
  db.query("SELECT * FROM users WHERE name = '" + name + "'");
  db.query(`SELECT * FROM users WHERE name = '${name}'`);
  el.innerHTML = input;
  document.write(input);
  cp.exec("ls " + input);
  eval(input);
  if (input == 1) { return new Function(input); }
}
