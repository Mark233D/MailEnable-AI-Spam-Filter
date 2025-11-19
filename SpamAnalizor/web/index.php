<form id="consentForm">
  <label>Email (kullanıcı adı):</label>
  <input id="username" />
  <label>Servis:</label>
  <select id="provider">
    <option value="mailenable">MailEnable</option>
    <option value="outlook">Outlook</option>
    <option value="yandex">Yandex</option>
    <option value="generic">Diğer</option>
  </select>
  <label>Şifre:</label>
  <input id="imap_pass" type="password" />
  <button type="button" onclick="giveConsent()">İzin Ver</button>
</form>

<script>
async function giveConsent(){
  const payload = {
    username: document.getElementById('username').value,
    provider: document.getElementById('provider').value,
    imap_user: document.getElementById('username').value,
    imap_pass: document.getElementById('imap_pass').value,
    allow_auto_scan: true
  };
  const res = await fetch('http://127.0.0.1:8000/consent', {
    method:'POST',
    headers:{'Content-Type':'application/json'},
    body: JSON.stringify(payload)
  });
  if(res.ok) alert('İzin kaydedildi');
  else alert('Hata: ' + await res.text());
}
</script>
