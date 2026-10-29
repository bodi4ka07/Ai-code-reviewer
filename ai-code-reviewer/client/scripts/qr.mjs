// Друкує QR-код у терміналі, щоб відкрити застосунок на телефоні.
// Запуск: npm run qr            (адреси комп'ютера в локальній мережі, порт 5173)
//         npm run qr -- https://my-tunnel.example.com   (власна адреса, наприклад тунель)
import os from 'node:os';
import qrcode from 'qrcode-terminal';

const port = process.env.PORT || 5173;
const custom = process.argv[2];

function lanAddresses() {
  const found = [];
  for (const [name, list] of Object.entries(os.networkInterfaces())) {
    for (const item of list || []) {
      if (item.family === 'IPv4' && !item.internal) found.push({ name, address: item.address });
    }
  }
  // Адреси домашніх мереж показуємо першими, віртуальні адаптери (Docker, WSL) останніми
  const rank = (a) => (/^(192\.168|10\.)/.test(a.address) ? 0 : /^172\.(1[6-9]|2\d|3[01])/.test(a.address) ? 2 : 1);
  return found.sort((a, b) => rank(a) - rank(b));
}

function show(url, label) {
  console.log(`\n${label}\n${url}\n`);
  qrcode.generate(url, { small: true });
}

if (custom) {
  show(custom, 'Відкрийте на телефоні:');
} else {
  const addresses = lanAddresses();
  if (addresses.length === 0) {
    console.log('Не знайдено мережевих адрес. Підключіться до Wi-Fi або передайте адресу: npm run qr -- https://...');
    process.exit(1);
  }
  addresses.forEach((a, i) => show(`http://${a.address}:${port}`, i === 0 ? `Відкрийте на телефоні (Wi-Fi: ${a.name}):` : `Інша адреса (${a.name}):`));
  console.log('Телефон має бути в тій самій Wi-Fi мережі, що й комп\'ютер.');
  console.log('Якщо сторінка не відкривається, дозвольте порт ' + port + ' у брандмауері Windows.');
  console.log('Встановити застосунок на телефон можна лише по HTTPS (тунель): npm run qr -- https://...');
}
