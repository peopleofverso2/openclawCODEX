(async function () {
  const input = document.getElementById('aif-input');
  const output = document.getElementById('aif-output');
  const preview = document.getElementById('aif-preview');
  const btn = document.getElementById('aif-run');
  const copyBtn = document.getElementById('aif-copy');
  const mode = document.getElementById('aif-mode');
  const css = document.getElementById('aif-css');
  const style = document.getElementById('aif-style');
  const styleRow = document.getElementById('aif-style-row');

  function setCssPreset(preset) {
    preview.className = 'aif-preview aif-css-' + preset;
  }

  css.addEventListener('change', function () {
    setCssPreset(css.value);
  });

  mode.addEventListener('change', function () {
    styleRow.style.display = mode.value === 'ai_proofread' ? 'flex' : 'none';
  });

  setCssPreset(css.value);

  btn.addEventListener('click', async function () {
    if (!input.value.trim()) {
      return;
    }

    btn.disabled = true;
    btn.textContent = 'Traitement\u2026';

    try {
      var res = await window.wp.apiFetch({
        url: AIF.restUrl,
        method: 'POST',
        headers: { 'X-WP-Nonce': AIF.nonce },
        data: {
          text: input.value,
          mode: mode.value,
          css: css.value,
          style: style ? style.value : 'neutral'
        }
      });

      output.value = res.html;
      preview.innerHTML = res.html;
      setCssPreset(res.css);
      copyBtn.disabled = false;
    } catch (e) {
      alert(e && e.message ? e.message : 'Erreur lors du traitement.');
    } finally {
      btn.disabled = false;
      btn.textContent = 'Nettoyer & Formater';
    }
  });

  copyBtn.addEventListener('click', function () {
    if (!output.value) return;
    navigator.clipboard.writeText(output.value).then(function () {
      var original = copyBtn.textContent;
      copyBtn.textContent = 'Copie !';
      setTimeout(function () {
        copyBtn.textContent = original;
      }, 1500);
    });
  });
})();
