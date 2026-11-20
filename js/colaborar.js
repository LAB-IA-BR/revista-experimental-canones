(function () {
  var form = document.getElementById("cadastro");
  var status = document.getElementById("form-status");
  var submit = document.getElementById("enviar");
  if (!form || !status || !submit) return;

  var ENDPOINT = "https://formsubmit.co/ajax/orlando.albertino@ufes.br";

  function setStatus(state, text) {
    status.dataset.state = state;
    status.textContent = text;
  }

  function collectedChecks(name) {
    return Array.prototype.slice
      .call(form.querySelectorAll('input[name="' + name + '"]:checked'))
      .map(function (el) {
        return el.value;
      })
      .join(", ");
  }

  form.addEventListener("submit", function (event) {
    event.preventDefault();
    if (form.website && form.website.value) return;

    var payload = {
      _subject: "Cadastro editorial — Revista Experimental de Crítica e Teoria Literária (DLT13973)",
      _template: "box",
      _captcha: "false",
      _honey: form.website ? form.website.value : "",
      nome_completo: form.nome_completo.value.trim(),
      nome_assinatura: form.nome_assinatura.value.trim(),
      email: form.email.value.trim(),
      whatsapp: form.whatsapp.value.trim(),
      vinculo: form.vinculo.value,
      matricula: form.matricula.value.trim(),
      equipe_regional: form.equipe_regional.value,
      oficios: collectedChecks("oficios"),
      idiomas: form.idiomas.value.trim(),
      proposta_nome: form.proposta_nome.value.trim(),
      interesse: form.interesse.value.trim(),
      lgpd: form.lgpd.checked ? "sim" : "nao",
    };

    try {
      localStorage.setItem(
        "revista-ficha",
        JSON.stringify({
          byline: payload.nome_assinatura,
          equipe: payload.equipe_regional,
          oficios: payload.oficios,
          em: Date.now(),
        })
      );
    } catch (err) {
      /* ficha local é um extra; o e-mail segue */
    }

    submit.disabled = true;
    setStatus("wait", "Enviando o cadastro…");

    fetch(ENDPOINT, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Accept: "application/json",
      },
      body: JSON.stringify(payload),
    })
      .then(function (res) {
        return res.json().then(function (data) {
          return { ok: res.ok, data: data };
        });
      })
      .then(function (result) {
        var data = result.data || {};
        var activated = data.success === true || data.success === "true";
        if (!result.ok || !activated) {
          var pending =
            String(data.message || "").toLowerCase().indexOf("activation") !== -1;
          if (pending) {
            throw new Error("activation");
          }
          throw new Error("Falha no envio");
        }
        form.reset();
        setStatus(
          "ok",
          "Cadastro recebido. A ficha chegou à redação."
        );
      })
      .catch(function (err) {
        var body = [
          "Nome: " + payload.nome_completo,
          "Assinatura: " + payload.nome_assinatura,
          "E-mail: " + payload.email,
          "WhatsApp: " + payload.whatsapp,
          "Vínculo: " + payload.vinculo,
          "Matrícula: " + payload.matricula,
          "Equipe: " + payload.equipe_regional,
          "Ofícios: " + payload.oficios,
          "Idiomas: " + payload.idiomas,
          "Proposta de nome: " + payload.proposta_nome,
          "",
          payload.interesse,
        ].join("\n");
        var mailto =
          "mailto:orlando.albertino@ufes.br?subject=" +
          encodeURIComponent("Cadastro editorial — Revista Experimental de Crítica e Teoria Literária (DLT13973)") +
          "&body=" +
          encodeURIComponent(body);
        var prefix =
          err && err.message === "activation"
            ? "O canal de e-mail da redação ainda está sendo ativado. Enquanto isso, envie pelo link a seguir."
            : "Não foi possível enviar pelo formulário agora. Use o e-mail da disciplina — o rascunho da sua ficha já vai no link a seguir.";
        status.dataset.state = "err";
        status.innerHTML =
          prefix +
          ' <a href="' +
          mailto +
          '">Abrir e-mail para orlando.albertino@ufes.br</a>.';
      })
      .finally(function () {
        submit.disabled = false;
      });
  });
})();
