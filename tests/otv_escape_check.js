// ÖTV araç verilerinin HTML'e kaçışsız aktarılmadığını doğrular.
//
// Kaynak: excel_vlookup_api.py içindeki satır içi JavaScript. Ağır Python
// bağımlılıkları (pandas, pdfplumber) kurulmadan, yalnızca Node ile çalışır.

'use strict';

const fs = require('fs');
const path = require('path');

const sourcePath = path.join(__dirname, '..', 'excel_vlookup_api.py');
// Windows çalışma kopyaları CRLF, CI (Linux) LF kullanır; satır sonlarını
// normalize ederek kontrolün her iki ortamda da aynı sonucu vermesini sağla.
const source = fs.readFileSync(sourcePath, 'utf8').replace(/\r\n?/g, '\n');
const failures = [];

function check(condition, message) {
  if (!condition) {
    failures.push(message);
  }
}

// 1) esc() fonksiyonunu kaynaktan alıp davranışını doğrula.
const escMatch = source.match(/function esc\(v\)\{[^\n]*?\}\n/);
check(escMatch !== null, 'esc() fonksiyonu bulunamadı.');
if (escMatch) {
  // eslint-disable-next-line no-new-func
  const esc = new Function('return ' + escMatch[0].replace(/;$/, '') + ';')();
  check(esc('<img src=x onerror=alert(1)>') === '&lt;img src=x onerror=alert(1)&gt;', 'esc() < ve > kaçırmıyor.');
  check(esc('" onmouseover="alert(1)') === '&quot; onmouseover=&quot;alert(1)', 'esc() çift tırnağı kaçırmıyor.');
  check(esc("' onfocus='alert(1)") === '&#39; onfocus=&#39;alert(1)', 'esc() tek tırnağı kaçırmıyor.');
  check(esc(null) === '' && esc(undefined) === '', 'esc() null/undefined için boş dize döndürmüyor.');
  check(esc('a & b') === 'a &amp; b', 'esc() & kaçırmıyor.');
}

// 2) Araç verisinden gelen alanlar esc() içinden geçmeli.
const escapedFields = ['trim', 'locality', 'source_name', 'checked_at'];
for (const field of escapedFields) {
  check(
    source.includes('esc(v.' + field),
    'v.' + field + ' alanı esc() ile kaçırılmıyor.'
  );
}

// 3) Kaçışsız birleştirme kalıpları geri gelmemeli.
const rawPatterns = [
  "'+(v.brand||",
  "'+(v.model||",
  "'+(v.trim||",
  "'+(v.locality||",
  "'+(v.source_name||",
  "'+(v.checked_at||",
  '<h3>\'+(v.model||',
  "data-brand=\"'+String(b).replace("
];
for (const pattern of rawPatterns) {
  check(!source.includes(pattern), 'Kaçışsız HTML birleştirmesi bulundu: ' + pattern);
}

// 4) Marka çipi hem öznitelikte hem metinde kaçırılmalı.
check(
  source.includes('data-brand="\'+esc(b)+\'">\'+esc(b)'),
  'Marka çipi (data-brand) esc() ile kaçırılmıyor.'
);

if (failures.length) {
  console.error('ÖTV kaçış kontrolü BAŞARISIZ:');
  for (const failure of failures) {
    console.error(' - ' + failure);
  }
  process.exit(1);
}

console.log('ÖTV kaçış kontrolü geçti (' + sourcePath + ').');
